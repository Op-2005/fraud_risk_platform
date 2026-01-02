#!/bin/bash
# Setup IRSA for ingest service S3 access in EKS cluster
set -e

CLUSTER_NAME="fraud-detection-cluster"
REGION=${AWS_REGION:-us-west-2}
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
POLICY_NAME="FraudIngestS3Policy"
SERVICE_ACCOUNT_NAME="ingest-sa"
NAMESPACE="fraud-system"
BUCKET_NAME="fraud-events-${ACCOUNT_ID}-${REGION}"

cat > /tmp/s3-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["s3:PutObject", "s3:GetObject", "s3:ListBucket"],
    "Resource": [
      "arn:aws:s3:::${BUCKET_NAME}",
      "arn:aws:s3:::${BUCKET_NAME}/*"
    ]
  }]
}
EOF

POLICY_ARN=$(aws iam create-policy \
  --policy-name "$POLICY_NAME" \
  --policy-document file:///tmp/s3-policy.json \
  --query 'Policy.Arn' --output text 2>/dev/null || \
  aws iam get-policy --policy-arn "arn:aws:iam::${ACCOUNT_ID}:policy/${POLICY_NAME}" \
    --query 'Policy.Arn' --output text)

eksctl create iamserviceaccount \
  --name "$SERVICE_ACCOUNT_NAME" \
  --namespace "$NAMESPACE" \
  --cluster "$CLUSTER_NAME" \
  --region "$REGION" \
  --attach-policy-arn "$POLICY_ARN" \
  --approve \
  --override-existing-serviceaccounts

