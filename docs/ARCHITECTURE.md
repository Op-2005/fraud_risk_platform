# Fraud Detection Platform - Architecture

## Overview

Real-time fraud risk scoring platform with behavioral signals, deployed on AWS EC2 using Docker Compose.

## System Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│                    Ingest API (FastAPI)                      │
│  - Receives transaction events                               │
│  - Validates schema (Pydantic)                               │
│  - Publishes to Redis Stream                                 │
│  - Writes to S3 (Parquet)                                    │
└──────┬───────────────────────────────┬───────────────────────┘
       │                               │
       ▼                               ▼
┌──────────────┐              ┌──────────────────┐
│ Redis Stream │              │   S3 (Parquet)   │
└──────┬───────┘              └──────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│              Featurizer Service (Async)                     │
│  - Consumes from Redis Stream                                │
│  - Computes behavioral features (sliding windows)            │
│  - Stores features in Redis (hashes)                         │
│  - Tracks freshness metrics                                  │
└──────┬───────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────┐
│ Redis Hashes │
│ (Features)   │
└──────┬───────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│            Inference API (FastAPI + PyTorch)                 │
│  - Fetches features from Redis                                │
│  - Builds feature vector (V1-V28 + Amount_normalized)        │
│  - Runs TorchScript model                                    │
│  - Applies decision logic (allow/step_up/block)              │
│  - Generates reason codes                                    │
└──────┬───────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────┐
│   Response   │
│ (risk_score, │
│  decision,   │
│  reasons)    │
└──────────────┘
```

## Component Details

### 1. Ingest API (`services/ingest/`)
- **Technology**: FastAPI, Uvicorn
- **Port**: 8000
- **Responsibilities**:
  - Event validation (Pydantic schemas)
  - Redis Stream publishing
  - S3 Parquet writing (buffered)
  - Prometheus metrics

### 2. Featurizer Service (`services/featurizer/`)
- **Technology**: FastAPI, AsyncIO, Redis
- **Port**: 8002 (metrics/health)
- **Responsibilities**:
  - Redis Stream consumption
  - Behavioral feature computation:
    - Transaction velocity (5m, 1h, 24h)
    - Amount statistics (avg, max, z-score)
    - Device/IP churn
    - Merchant velocity
  - Redis hash storage (with TTL)
  - Feature freshness tracking

### 3. Inference API (`services/infer/`)
- **Technology**: FastAPI, PyTorch (TorchScript)
- **Port**: 8001
- **Responsibilities**:
  - Feature retrieval from Redis
  - Model inference (TorchScript)
  - Decision logic:
    - `allow`: risk_score < 0.3
    - `step_up`: 0.3 ≤ risk_score < 0.7
    - `block`: risk_score ≥ 0.7
  - Reason code generation
  - Prometheus metrics

### 4. Redis
- **Role**: Message stream + Feature store
- **Stream**: `transaction_events` (Ingest → Featurizer)
- **Hashes**: `features:user:{user_id}` (Featurizer → Infer)
- **TTL**: 24 hours

### 5. S3 Storage
- **Format**: Parquet (partitioned by dt/hour)
- **Path**: `s3://fraud-events-{account}-{region}/events/dt={date}/hour={hour}/`
- **Purpose**: Audit-grade event storage

### 6. Observability
- **Prometheus**: Metrics collection (port 9090)
- **Grafana**: Dashboards (port 3000)
- **Metrics**:
  - Request rate (QPS)
  - Latency (P50, P95, P99)
  - Error rate
  - Feature freshness
  - Redis operations

## Deployment Architecture

### EC2 Deployment
- **Instance**: t3.micro (20 GB storage)
- **Orchestration**: Docker Compose
- **Services**: All services in single docker-compose.yml
- **Networking**: Services communicate via Docker network
- **Storage**: 
  - Model: Mounted from host
  - S3: IAM role-based access

### IAM Roles
- **EC2 Instance Role**: S3 write access, ECR pull access
- **No IRSA needed**: Simpler than Kubernetes approach

## Data Flow

1. **Event Ingestion**:
   - Client → Ingest API (POST /events)
   - Ingest validates and publishes to Redis Stream
   - Ingest buffers and writes to S3 (Parquet)

2. **Feature Computation**:
   - Featurizer consumes from Redis Stream
   - Computes behavioral features (sliding windows)
   - Stores in Redis hashes (key: `features:user:{user_id}`)

3. **Prediction**:
   - Client → Inference API (POST /predict)
   - Infer fetches features from Redis
   - Builds feature vector (V1-V28 + Amount_normalized)
   - Runs TorchScript model
   - Returns risk_score, decision, reasons

## Technology Stack

- **Languages**: Python 3.11
- **Frameworks**: FastAPI, Uvicorn
- **ML**: PyTorch, TorchScript
- **Data Store**: Redis 7
- **Storage**: S3, Parquet
- **Observability**: Prometheus, Grafana
- **Containerization**: Docker, Docker Compose
- **Cloud**: AWS (EC2, ECR, S3, Athena)

## Scalability Considerations

- **Horizontal Scaling**: `docker-compose scale infer=3`
- **Redis**: Single instance (can be upgraded to cluster)
- **S3**: Unlimited storage
- **Load Balancing**: Can add ALB/NLB if needed

## Security

- **IAM Roles**: Least-privilege access
- **Network**: Security groups restrict access
- **Data**: Events stored in S3 (encrypted at rest)
- **Model**: TorchScript (no Python execution in production)

