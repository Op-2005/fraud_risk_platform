#!/bin/bash
# Deploy services to EC2 instance using Docker Compose
set -e

REGION=${AWS_REGION:-us-west-2}
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REGISTRY="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"
BUCKET_NAME="fraud-events-${ACCOUNT_ID}-${REGION}"

if [ -n "$1" ]; then
    EC2_IP="$1"
    KEY_NAME="fraud-demo-key"
    KEY_PATH="$HOME/.ssh/${KEY_NAME}.pem"
    scp -i "$KEY_PATH" "$0" ec2-user@${EC2_IP}:/tmp/deploy.sh
    ssh -i "$KEY_PATH" ec2-user@${EC2_IP} "chmod +x /tmp/deploy.sh && /tmp/deploy.sh"
    exit 0
fi

aws ecr get-login-password --region "$REGION" | \
    docker login --username AWS --password-stdin "$ECR_REGISTRY"

docker pull "${ECR_REGISTRY}/fraud-ingest:latest"
docker pull "${ECR_REGISTRY}/fraud-featurizer:latest"
docker pull "${ECR_REGISTRY}/fraud-infer:latest"

docker tag "${ECR_REGISTRY}/fraud-ingest:latest" fraud-ingest:latest
docker tag "${ECR_REGISTRY}/fraud-featurizer:latest" fraud-featurizer:latest
docker tag "${ECR_REGISTRY}/fraud-infer:latest" fraud-infer:latest

cd /opt/fraud-demo

cat > docker-compose.yml <<EOF
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  ingest:
    image: fraud-ingest:latest
    ports:
      - "8000:8000"
    environment:
      - S3_BUCKET=s3://${BUCKET_NAME}
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - STREAM_KEY=transaction_events
      - FLUSH_INTERVAL=10
      - BATCH_SIZE=100
    depends_on:
      redis:
        condition: service_healthy

  featurizer:
    image: fraud-featurizer:latest
    ports:
      - "8002:8000"
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - STREAM_KEY=transaction_events
    depends_on:
      redis:
        condition: service_healthy

  infer:
    image: fraud-infer:latest
    ports:
      - "8001:8000"
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - MODEL_PATH=/opt/fraud-demo/model.pt
      - THRESHOLD_ALLOW=0.3
      - THRESHOLD_BLOCK=0.7
    depends_on:
      redis:
        condition: service_healthy
    volumes:
      - /opt/fraud-demo/model.pt:/opt/fraud-demo/model.pt:ro

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
EOF

mkdir -p prometheus
cat > prometheus/prometheus.yml <<EOF
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'ingest'
    static_configs:
      - targets: ['ingest:8000']
  - job_name: 'featurizer'
    static_configs:
      - targets: ['featurizer:8000']
  - job_name: 'infer'
    static_configs:
      - targets: ['infer:8000']
  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']
EOF

docker-compose up -d

