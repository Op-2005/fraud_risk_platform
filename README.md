# Real-Time Fraud Risk Scoring Platform

This project aims to create a fraud detection system that analyzes transaction patterns in real-time, computes behavioral features, and scores risk using machine learning. I built it to learn and demonstrate AWS infrastructure, containerization, microservices architecture, and real-time data processing.

## Motivation

The idea for this project came from observing how financial services like Stripe handle fraud detection at scale. When you make a payment, there's a complex system running behind the scenes that evaluates your transaction in milliseconds and check if the purchase amount is unusual for your account, whether you're using a device you've used before, if you're making too many purchases too quickly, and dozens of other signals.

I wanted to build something that demonstrates these concepts while learning the modern infrastructure stack: AWS services (EC2, EKS, S3, ECR, Athena), Docker containerization, Kubernetes orchestration, Redis for real-time data, and observability tools like Prometheus and Grafana. This project serves as both a learning exercise and a proof-of-concept showing how these technologies come together to solve real problems.

The system ingests transaction events, computes behavioral features on the fly (like transaction velocity and device churn), stores them in Redis for low-latency access, runs a machine learning model to generate risk scores, and stores everything in S3 for auditability and analysis.

## Setup and Dependencies

### Prerequisites

The project requires:
- Python 3.11+ with Poetry for dependency management
- Docker and Docker Compose for local development
- AWS CLI configured with appropriate credentials
- kubectl, eksctl, and helm for Kubernetes deployment (optional, for EKS)

### Dataset

The project uses the [Credit Card Fraud Detection dataset](https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud) from Kaggle, which contains real credit card transactions from European cardholders. The dataset is highly imbalanced (0.172% fraud rate) and contains PCA-transformed features (V1-V28) to protect cardholder privacy.

**Preprocessing Steps:**
1. Stratified train/validation/test split (70/15/15) to preserve fraud ratio across splits
2. Log transformation and standardization of transaction amounts (fitted only on training data to prevent leakage)
3. Generation of synthetic behavioral attributes: user_id, device_id, IP address, merchant_id, country, currency, and ISO 8601 timestamps
4. Feature engineering for the model: V1-V28 (from dataset) + normalized Amount

The preprocessed data is saved in `data/processed/` with train/val/test splits. A trained logistic regression model (converted to PyTorch TorchScript) achieves ~0.83 PR-AUC and ~71% recall at 0.5% false positive rate.

Everything is detailed under `notebooks/01_data_preprocessing`

## System Architecture

The platform consists of three microservices that work together to process transactions and generate fraud scores in real-time.

### 1. Ingest API (FastAPI)

**Purpose:** Receives transaction events from external systems.

**Responsibilities:**
- Validates incoming transaction events using Pydantic schemas
- Immediately publishes events to a Redis Stream for downstream processing
- Buffers events in memory and periodically writes them to S3 in Parquet format (partitioned by date/hour for efficient querying)
- Returns HTTP 200 immediately after validation (doesn't wait for S3 write)

**Endpoints:**
- `POST /events` - Ingest a transaction event
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics

**Technology:** FastAPI, Redis Streams, PyArrow (Parquet), boto3 (S3)


### 2. Featurizer Service (Python AsyncIO)

**Purpose:** Consumes events from Redis Streams and computes behavioral features in real-time.

**Responsibilities:**
- Consumes events from the Redis Stream using consumer groups
- Maintains sliding time windows (5 minutes, 1 hour, 24 hours) of transaction history per user
- Computes behavioral features such as:
  - Transaction velocity (counts over different time windows)
  - Average and maximum transaction amounts
  - Device and IP churn (how often these change)
  - Amount z-scores (how unusual the current amount is compared to user's history)
  - Merchant velocity and country patterns
- Stores both behavioral features and original model features (V1-V28, Amount_normalized) in Redis Hashes
- Uses Redis pipelining to batch writes for efficiency
- Sets TTL on feature records (24-48 hours) for automatic cleanup

**Endpoints:**
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics (feature freshness, update latency)

**Technology:** Python asyncio, Redis Streams, Redis Hashes


### 3. Inference API (FastAPI + PyTorch)

**Purpose:** Provides real-time fraud risk scores and decisions.

**Responsibilities:**
- Receives prediction requests with a user_id
- Fetches features from Redis (both behavioral and original model features)
- Assembles feature vector in the correct order (V1-V28, Amount_normalized)
- Runs inference using a TorchScript model
- Applies decision logic based on risk score thresholds:
  - Risk < 0.3: Allow (automatic approval)
  - Risk 0.3-0.7: Step-up (require additional authentication)
  - Risk > 0.7: Block (automatic denial)
- Generates explainable reason codes (e.g., "high_velocity_5m", "unusual_amount", "high_device_churn")
- Returns risk score, decision, and reasons

**Endpoints:**
- `POST /predict` - Get fraud risk score for a user
- `GET /features/{user_id}` - View current features for a user (debug endpoint)
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics (latency, request counts)

**Technology:** FastAPI, PyTorch (TorchScript), Redis Hashes

**Example API Response:**
```bash
$ curl -X POST http://localhost:8001/predict \
    -H "Content-Type: application/json" \
    -d '{"user_id": "user_4562"}'

{
  "user_id": "user_4562",
  "risk_score": 0.6234,
  "decision": "step_up",
  "reasons": [
    "high_velocity_5m",
    "unusual_amount",
    "high_merchant_velocity"
  ]
}
```

*[Screenshot: Terminal showing curl command and JSON response]*

### Data Flow

1. **Event Ingestion:** External system sends transaction event to Ingest API
2. **Stream Publishing:** Ingest API validates event and publishes to Redis Stream
3. **S3 Storage:** Ingest API buffers events and periodically flushes to S3 as Parquet files
4. **Feature Computation:** Featurizer service consumes from Redis Stream, computes behavioral features, stores in Redis Hashes
5. **Risk Scoring:** Inference API receives prediction request, fetches features from Redis, runs model, returns decision
6. **Analytics:** S3 data is queryable via AWS Athena for historical analysis and auditing

### Supporting Infrastructure

**Redis:** Used for two purposes:
- Redis Streams: Message queue between Ingest and Featurizer (high-throughput, ordered events)
- Redis Hashes: Feature store for Inference API (low-latency key-value lookups)

**AWS S3:** Audit-grade storage for all transaction events in Parquet format, partitioned by date and hour.

**Prometheus + Grafana:** Observability stack for monitoring service health, latency, throughput, and feature freshness.

**AWS Athena:** SQL interface for querying historical transaction data stored in S3.

*[Screenshot: Grafana dashboard showing service metrics]*

## Performance Metrics

The system is designed to handle high throughput with low latency. Load testing with k6 shows:

- **Throughput:** Successfully handles 346 requests/second sustained load
- **Latency:** P50: 249ms, P95: 939ms, P99: varies (tested on t3.micro EC2 instance)
- **Error Rate:** < 0.1% under normal load
- **Feature Freshness:** Behavioral features updated within 10 seconds of event ingestion (P95)

The P95 latency exceeds the 150ms target on a t3.micro instance due to resource constraints. Scaling to larger instances or horizontally scaling the inference service (via Docker Compose scaling or Kubernetes HPA) improves performance significantly.

Model performance metrics:
- PR-AUC: ~0.83
- Recall at 0.5% FPR: ~71%

*[Screenshot: Grafana dashboard showing latency percentiles over time]*



## Challenges & Future Improvements

The biggest challenge was attempting to deploy on AWS EKS, which kept timing out after 30+ minutes due to nodegroup provisioning issues (likely EC2 quota limits). After multiple failed attempts, I pivoted to Docker Compose on a single EC2 instance, which was simpler and cheaper while still demonstrating containerization. For production scale, the system would need proper EKS deployment with HPA for autoscaling and canary rollouts for safe deployments (the K8s manifests are already in `infra/k8s/`). Other issues included data leakage from fitting the scaler before splitting (fixed by splitting first), cross-platform Docker builds from M1 Mac to x86_64 EC2 (solved with `buildx --platform linux/amd64`), and performance degradation under load (P95 jumped to 939ms at 1000 concurrent users vs 34ms at steady state). The inference service needs more Gunicorn workers, Redis connection pooling, and request batching to handle burst traffic properly.

I also ran out of time to implement the S3 data pipeline, so the ingest service writes to local filesystem instead of uploading Parquet files to S3, leaving Athena with no data to query. The infrastructure is configured (S3 bucket, Athena table, IAM roles), but the actual boto3 integration needs to be added. If I were doing this again, I'd start with simpler infrastructure from the beginning (EKS added complexity without much demo benefit), load test incrementally at 100/500/1k RPS to catch bottlenecks earlier, and validate end-to-end functionality before adding monitoring dashboards. The core lesson: infrastructure always takes longer than expected (deployment debugging took 6-7 hours vs 8 hours for the actual ML and service code), so budget time accordingly and prioritize working features over perfect architecture.


## Getting Started

See `docs/GETTING_STARTED.md` for detailed setup instructions. Quick start:

1. **Clone the repository and install dependencies:**
   ```bash
   poetry install
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your AWS credentials and configuration
   ```

3. **Run locally with Docker Compose:**
   ```bash
   docker-compose up
   ```

4. **Deploy to AWS:**
   ```bash
   cd infra/aws
   ./01_ecr.sh          # Create ECR repositories
   ./02_s3.sh           # Create S3 bucket
   ./03_push_images.sh  # Build and push Docker images
   ./05_deploy_to_ec2.sh <EC2_IP>  # Deploy to EC2 instance
   ```

For Kubernetes deployment, see `docs/OPERATIONS.md` and `infra/k8s/` directory.

## Project Structure

```
streamlite-inference/
├── services/           # Microservices (ingest, featurizer, infer)
├── notebooks/          # Data preprocessing and model training
├── infra/
│   ├── aws/           # AWS infrastructure scripts
│   ├── k8s/           # Kubernetes manifests (HPA, canary, deployments)
│   └── observability/ # Prometheus and Grafana configs
├── data/              # Dataset and processed data (gitignored)
├── benchmarks/        # Load testing scripts and results
└── docs/              # Additional documentation
```


