#!/bin/bash
# Build and push Docker images to ECR
set -e

REGION=${AWS_REGION:-us-west-2}
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_BASE="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"
VERSION=${1:-latest}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

aws ecr get-login-password --region "$REGION" | \
    docker login --username AWS --password-stdin "$ECR_BASE"

SERVICES=("ingest" "featurizer" "infer")
for SERVICE in "${SERVICES[@]}"; do
    docker build -t "fraud-$SERVICE:$VERSION" "services/$SERVICE/"
    docker tag "fraud-$SERVICE:$VERSION" "$ECR_BASE/fraud-$SERVICE:$VERSION"
    docker push "$ECR_BASE/fraud-$SERVICE:$VERSION"
done
