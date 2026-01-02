"""Featurizer service - computes behavioral features from transaction events."""

import asyncio
import json
import os
from collections import deque
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

import redis.asyncio as redis
from fastapi import FastAPI
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response


# Prometheus metrics
feature_updates_total = Counter(
    'feature_updates_total',
    'Total number of feature updates written to Redis'
)

feature_freshness_lag_seconds = Histogram(
    'feature_freshness_lag_seconds',
    'Time lag between event timestamp and feature update (seconds)',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

redis_write_latency_seconds = Histogram(
    'redis_write_latency_seconds',
    'Time taken to write features to Redis (seconds)',
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
)


class EventWindow:
    """Maintains a sliding window of events for a user."""
    
    def __init__(self):
        self.events: deque = deque()
        self.total_amount: float = 0.0
        self.amount_count: int = 0
    
    def add_event(self, event: Dict[str, Any]) -> None:
        """Add event to window."""
        self.events.append(event)
        if 'amount' in event:
            self.total_amount += float(event['amount'])
            self.amount_count += 1
    
    def get_recent(self, seconds: int, now: datetime) -> List[Dict[str, Any]]:
        """Get events within the last N seconds."""
        cutoff = now - timedelta(seconds=seconds)
        return [
            e for e in self.events
            if datetime.fromisoformat(e['ts'].replace('Z', '+00:00')).replace(tzinfo=None) >= cutoff
        ]
    
    def get_user_mean_amount(self) -> float:
        """Calculate user's historical mean transaction amount."""
        return self.total_amount / self.amount_count if self.amount_count > 0 else 0.0
    
    def cleanup_old(self, cutoff_seconds: int, now: datetime) -> None:
        """Remove events older than cutoff."""
        cutoff = now - timedelta(seconds=cutoff_seconds)
        while self.events:
            first_event = self.events[0]
            event_ts = datetime.fromisoformat(first_event['ts'].replace('Z', '+00:00')).replace(tzinfo=None)
            if event_ts >= cutoff:
                break
            removed = self.events.popleft()
            if 'amount' in removed:
                self.total_amount -= float(removed['amount'])
                self.amount_count -= 1


class Featurizer:
    """Computes behavioral features from transaction events."""
    
    def __init__(self, redis_client: redis.Redis, stream_key: str = "transaction_events"):
        self.redis = redis_client
        self.stream_key = stream_key
        self.user_windows: Dict[str, EventWindow] = {}
        self.running = False
    
    def compute_features(self, event: Dict[str, Any], user_window: EventWindow, now: datetime) -> Dict[str, Any]:
        """Compute all behavioral features for a user."""
        # Get events in different time windows
        events_5m = user_window.get_recent(300, now)  # 5 minutes
        events_1h = user_window.get_recent(3600, now)  # 1 hour
        events_24h = user_window.get_recent(86400, now)  # 24 hours
        
        # Transaction counts
        txns_5m = len(events_5m)
        txns_1h = len(events_1h)
        txns_24h = len(events_24h)
        
        # Amount statistics
        amounts_1h = [float(e.get('amount', 0)) for e in events_1h]
        amounts_24h = [float(e.get('amount', 0)) for e in events_24h]
        
        avg_amount_1h = sum(amounts_1h) / len(amounts_1h) if amounts_1h else 0.0
        max_amount_24h = max(amounts_24h) if amounts_24h else 0.0
        
        # Unique counts
        unique_devices_24h = len(set(e.get('device_id', '') for e in events_24h))
        unique_ips_24h = len(set(e.get('ip', '') for e in events_24h))
        
        # Amount z-score
        user_mean = user_window.get_user_mean_amount()
        current_amount = float(event.get('amount', 0))
        if user_mean > 0:
            # Simple z-score approximation (using std=user_mean for simplicity)
            amount_zscore = (current_amount - user_mean) / user_mean if user_mean > 0 else 0.0
        else:
            amount_zscore = 0.0
        
        # Merchant velocity (transactions to same merchant in last hour)
        current_merchant = event.get('merchant_id', '')
        merchant_velocity_1h = sum(1 for e in events_1h if e.get('merchant_id') == current_merchant)
        
        # Device churn (number of device changes in last 24h)
        devices_24h = [e.get('device_id', '') for e in events_24h]
        device_churn_24h = sum(1 for i in range(1, len(devices_24h)) if devices_24h[i] != devices_24h[i-1])
        
        # IP changes (number of IP changes in last 24h)
        ips_24h = [e.get('ip', '') for e in events_24h]
        ip_changes_24h = sum(1 for i in range(1, len(ips_24h)) if ips_24h[i] != ips_24h[i-1])
        
        return {
            'txns_last_5m': txns_5m,
            'txns_last_1h': txns_1h,
            'txns_last_24h': txns_24h,
            'avg_amount_1h': avg_amount_1h,
            'max_amount_24h': max_amount_24h,
            'unique_devices_24h': unique_devices_24h,
            'unique_ips_24h': unique_ips_24h,
            'amount_zscore': amount_zscore,
            'merchant_velocity_1h': merchant_velocity_1h,
            'device_churn_24h': device_churn_24h,
            'ip_changes_24h': ip_changes_24h,
        }
    
    async def process_event(self, event_data: Dict[bytes, bytes]) -> None:
        """Process a single event from Redis stream."""
        # Decode event data
        event = {k.decode('utf-8'): v.decode('utf-8') for k, v in event_data.items()}
        
        user_id = event.get('user_id')
        if not user_id:
            return
        
        # Initialize user window if needed
        if user_id not in self.user_windows:
            self.user_windows[user_id] = EventWindow()
        
        user_window = self.user_windows[user_id]
        now = datetime.utcnow()
        event_ts = datetime.fromisoformat(event['ts'].replace('Z', '+00:00')).replace(tzinfo=None)
        
        # Add event to window
        user_window.add_event(event)
        
        # Cleanup old events (keep 48 hours of history)
        user_window.cleanup_old(172800, now)  # 48 hours
        
        # Compute behavioral features
        behavioral_features = self.compute_features(event, user_window, now)
        
        # Extract original model features (V1-V28 + Amount_normalized)
        original_features = {}
        for i in range(1, 29):
            v_key = f'V{i}'
            if v_key in event:
                original_features[v_key] = float(event[v_key])
        if 'Amount_normalized' in event:
            original_features['Amount_normalized'] = float(event['Amount_normalized'])
        
        # Combine all features
        all_features = {
            **original_features,
            **behavioral_features,
            'last_event_ts': event['ts'],
            'last_feature_update_ts': now.isoformat() + 'Z',
        }
        
        # Write to Redis hash
        redis_key = f"features:user:{user_id}"
        
        with redis_write_latency_seconds.time():
            pipe = self.redis.pipeline()
            # Convert all values to strings for Redis
            for key, value in all_features.items():
                pipe.hset(redis_key, key, str(value))
            # Set TTL (48 hours)
            pipe.expire(redis_key, 172800)
            await pipe.execute()
        
        # Update metrics
        feature_updates_total.inc()
        freshness_lag = (now - event_ts).total_seconds()
        feature_freshness_lag_seconds.observe(max(0, freshness_lag))
    
    async def consume_events(self) -> None:
        """Main event consumption loop."""
        last_id = "0"  # Start from beginning
        
        while self.running:
            try:
                # Read from stream (blocking for 1 second)
                messages = await self.redis.xread(
                    {self.stream_key: last_id},
                    count=10,  # Process up to 10 messages at a time
                    block=1000  # Block for 1 second
                )
                
                if not messages:
                    continue
                
                # Process messages
                stream_messages = messages[0][1]  # (stream_name, [(id, data), ...])
                for msg_id, event_data in stream_messages:
                    try:
                        await self.process_event(event_data)
                    except Exception as e:
                        print(f"Error processing event {msg_id}: {e}")
                        continue
                    
                    # Update last processed ID
                    last_id = msg_id.decode('utf-8') if isinstance(msg_id, bytes) else msg_id
                
            except Exception as e:
                print(f"Error reading from stream: {e}")
                await asyncio.sleep(1)
    
    async def start(self) -> None:
        """Start the featurizer."""
        self.running = True
        await self.consume_events()
    
    def stop(self) -> None:
        """Stop the featurizer."""
        self.running = False


# Global featurizer instance
featurizer: Optional[Featurizer] = None
redis_client: Optional[redis.Redis] = None
consumer_task: Optional[asyncio.Task] = None


# FastAPI app for metrics endpoint
app = FastAPI(title="Featurizer Service", version="1.0.0")


@app.on_event("startup")
async def startup():
    """Start the featurizer on application startup."""
    global featurizer, redis_client, consumer_task
    
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    stream_key = os.getenv("STREAM_KEY", "transaction_events")
    
    redis_client = redis.Redis(
        host=redis_host,
        port=redis_port,
        decode_responses=False
    )
    
    featurizer = Featurizer(redis_client, stream_key)
    consumer_task = asyncio.create_task(featurizer.start())


@app.on_event("shutdown")
async def shutdown():
    """Stop the featurizer on application shutdown."""
    global featurizer, consumer_task
    
    if featurizer:
        featurizer.stop()
    
    if consumer_task:
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass
    
    if redis_client:
        await redis_client.aclose()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
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

