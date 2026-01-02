"""FastAPI application for ingesting transaction events."""

import asyncio
import os
from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import FastAPI, HTTPException
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response
from starlette.middleware.cors import CORSMiddleware

from schemas import TransactionEvent
from s3_writer import ParquetWriter


# Prometheus metrics
ingest_events_total = Counter(
    'ingest_events_total',
    'Total number of events ingested',
    ['status']
)

ingest_flushes_total = Counter(
    'ingest_flushes_total',
    'Total number of buffer flushes'
)

ingest_buffer_size = Gauge(
    'ingest_buffer_size',
    'Current size of event buffer'
)

ingest_flush_latency_seconds = Histogram(
    'ingest_flush_latency_seconds',
    'Time taken to flush buffer to Parquet',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

# Global variables
redis_client: redis.Redis = None
parquet_writer: ParquetWriter = None
background_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - startup and shutdown."""
    global redis_client, parquet_writer, background_task
    
    # Startup
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    
    redis_client = redis.Redis(
        host=redis_host,
        port=redis_port,
        decode_responses=False  # Redis streams need bytes
    )
    
    # Initialize Parquet writer
    base_path = os.getenv("S3_BUCKET", "./data/local-s3")
    flush_interval = int(os.getenv("FLUSH_INTERVAL", "10"))
    batch_size = int(os.getenv("BATCH_SIZE", "100"))
    
    parquet_writer = ParquetWriter(
        base_path=base_path,
        flush_interval=flush_interval,
        batch_size=batch_size
    )
    
    # Start background flusher
    background_task = asyncio.create_task(parquet_writer.start_background_flusher())
    
    yield
    
    # Shutdown
    if background_task:
        background_task.cancel()
        try:
            await background_task
        except asyncio.CancelledError:
            pass
    
    # Final flush
    if parquet_writer:
        await parquet_writer.flush()
    
    if redis_client:
        await redis_client.aclose()


app = FastAPI(
    title="Transaction Ingest API",
    description="Ingest transaction events and write to Parquet storage",
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


@app.post("/events")
async def ingest_event(event: TransactionEvent):
    """
    Ingest a transaction event.
    
    Validates the event, adds to buffer, publishes to Redis stream,
    and returns immediately.
    """
    try:
        # Convert Pydantic model to dict for buffering
        event_dict = event.model_dump()
        
        # Add to Parquet buffer (will be flushed by background task)
        await parquet_writer.add_event(event_dict)
        
        # Publish to Redis stream for featurizer
        stream_key = os.getenv("STREAM_KEY", "transaction_events")
        # Redis streams require string->bytes mapping
        stream_data = {
            k.encode('utf-8'): str(v).encode('utf-8') 
            for k, v in event_dict.items()
        }
        await redis_client.xadd(
            stream_key,
            stream_data,
            maxlen=10000  # Ring buffer - keep last 10k events
        )
        
        ingest_events_total.labels(status='success').inc()
        buffer_size = parquet_writer.get_buffer_size()
        ingest_buffer_size.set(buffer_size)
        
        # Check if buffer reached batch size (trigger immediate flush)
        if buffer_size >= parquet_writer.batch_size:
            # Flush immediately (non-blocking task)
            asyncio.create_task(parquet_writer.flush())
        
        return {"status": "ok", "event_id": event.event_id}
    
    except Exception as e:
        ingest_events_total.labels(status='error').inc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check Redis connection
        await redis_client.ping()
        return {"status": "healthy", "redis": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "redis": "disconnected", "error": str(e)}


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

