#!/bin/bash
# Create S3 bucket for fraud event storage with versioning and encryption
set -e

REGION=${AWS_REGION:-us-west-2}
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET_NAME="fraud-events-${ACCOUNT_ID}-${REGION}"

if [ "$REGION" = "us-east-1" ]; then
    aws s3api create-bucket --bucket "$BUCKET_NAME" --region "$REGION" 2>/dev/null || true
else
    aws s3api create-bucket --bucket "$BUCKET_NAME" --region "$REGION" \
        --create-bucket-configuration LocationConstraint="$REGION" 2>/dev/null || true
fi

aws s3api put-bucket-versioning \
    --bucket "$BUCKET_NAME" \
    --versioning-configuration Status=Enabled

aws s3api put-public-access-block \
    --bucket "$BUCKET_NAME" \
    --public-access-block-configuration \
        "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

aws s3api put-bucket-encryption \
    --bucket "$BUCKET_NAME" \
    --server-side-encryption-configuration '{
        "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
    }'

aws s3api put-bucket-lifecycle-configuration \
    --bucket "$BUCKET_NAME" \
    --lifecycle-configuration '{
        "Rules": [{
            "ID": "TransitionOldEvents",
            "Status": "Enabled",
            "Filter": {},
            "Transitions": [{"Days": 90, "StorageClass": "GLACIER"}]
        }]
    }'
