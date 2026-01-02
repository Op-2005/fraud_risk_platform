"""Inference API - real-time fraud risk scoring."""

import os
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional

import redis.asyncio as redis
import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response
from starlette.middleware.cors import CORSMiddleware

from feature_vector import build_feature_vector
from reasons import generate_reasons


# Prometheus metrics
predict_requests_total = Counter(
    'predict_requests_total',
    'Total number of prediction requests',
    ['status', 'decision']
)

predict_latency_seconds = Histogram(
    'predict_latency_seconds',
    'Time taken to process prediction request (seconds)',
    buckets=[0.01, 0.05, 0.1, 0.15, 0.2, 0.5, 1.0]
)

redis_fetch_latency_seconds = Histogram(
    'redis_fetch_latency_seconds',
    'Time taken to fetch features from Redis (seconds)',
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5]
)


# Global variables
model: Optional[torch.jit.ScriptModule] = None
redis_client: Optional[redis.Redis] = None
threshold_allow: float = 0.3
threshold_block: float = 0.7


class PredictionRequest(BaseModel):
    """Request model for prediction endpoint."""
    user_id: str


class PredictionResponse(BaseModel):
    """Response model for prediction endpoint."""
    user_id: str
    risk_score: float
    decision: str
    reasons: list[str]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - startup and shutdown."""
    global model, redis_client
    
    # Startup - load model
    model_path = os.getenv("MODEL_PATH", "/app/model.pt")
    try:
        model = torch.jit.load(model_path)
        model.eval()
        print(f"Model loaded from {model_path}")
    except Exception as e:
        raise RuntimeError(f"Failed to load model: {e}")
    
    # Connect to Redis
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    
    redis_client = redis.Redis(
        host=redis_host,
        port=redis_port,
        decode_responses=True
    )
    
    # Load thresholds from environment
    global threshold_allow, threshold_block
    threshold_allow = float(os.getenv("THRESHOLD_ALLOW", "0.3"))
    threshold_block = float(os.getenv("THRESHOLD_BLOCK", "0.7"))
    
    yield
    
    # Shutdown
    if redis_client:
        await redis_client.aclose()


app = FastAPI(
    title="Fraud Detection Inference API",
    description="Real-time fraud risk scoring service",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_default_features() -> Dict[str, Any]:
    """Return default feature values when user features are missing."""
    defaults = {}
    for i in range(1, 29):
        defaults[f'V{i}'] = 0.0
    defaults['Amount_normalized'] = 0.0
    return defaults


@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    """
    Predict fraud risk for a user.
    
    Fetches features from Redis, assembles feature vector, runs model,
    and returns risk score with decision and reason codes.
    """
    with predict_latency_seconds.time():
        try:
            user_id = request.user_id
            
            # Fetch features from Redis
            redis_key = f"features:user:{user_id}"
            
            with redis_fetch_latency_seconds.time():
                features = await redis_client.hgetall(redis_key)
            
            # If no features found, use defaults
            if not features:
                features = get_default_features()
                reasons = ['missing_features']
            else:
                reasons = []
            
            # Build feature vector
            feature_vector = build_feature_vector(features)
            
            # Run model inference
            with torch.no_grad():
                risk_score = model(feature_vector).item()
            
            # Apply decision logic
            if risk_score < threshold_allow:
                decision = "allow"
            elif risk_score < threshold_block:
                decision = "step_up"
            else:
                decision = "block"
            
            # Generate reason codes (if features available)
            if not reasons:  # Only generate if we have actual features
                reasons = generate_reasons(features, risk_score)
            
            # Update metrics
            predict_requests_total.labels(status='success', decision=decision).inc()
            
            return PredictionResponse(
                user_id=user_id,
                risk_score=round(risk_score, 4),
                decision=decision,
                reasons=reasons
            )
            
        except Exception as e:
            predict_requests_total.labels(status='error', decision='unknown').inc()
            raise HTTPException(status_code=500, detail=str(e))


@app.get("/features/{user_id}")
async def get_features(user_id: str):
    """
    Debug endpoint to view current features for a user.
    
    Returns all features stored in Redis for the given user_id.
    """
    try:
        redis_key = f"features:user:{user_id}"
        features = await redis_client.hgetall(redis_key)
        
        if not features:
            raise HTTPException(status_code=404, detail=f"No features found for user {user_id}")
        
        # Convert string values to appropriate types
        result = {}
        for key, value in features.items():
            try:
                # Try to convert to float
                result[key] = float(value)
            except ValueError:
                # Keep as string if not numeric
                result[key] = value
        
        return {"user_id": user_id, "features": result}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        await redis_client.ping()
        model_status = "loaded" if model is not None else "not_loaded"
        return {
            "status": "healthy",
            "redis": "connected",
            "model": model_status
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "redis": "disconnected",
            "error": str(e)
        }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

