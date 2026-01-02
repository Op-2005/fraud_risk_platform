#!/bin/bash
# Create ECR repositories for fraud detection services
set -e

REGION=${AWS_REGION:-us-west-2}
REPOS=("fraud-ingest" "fraud-featurizer" "fraud-infer")

for REPO in "${REPOS[@]}"; do
    aws ecr create-repository \
        --repository-name "$REPO" \
        --region "$REGION" \
        --image-scanning-configuration scanOnPush=true \
        --encryption-configuration encryptionType=AES256 \
        2>/dev/null || true
done
