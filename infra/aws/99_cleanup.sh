#!/bin/bash
# Delete all AWS resources created by this project (EKS, S3, ECR, IAM)
set -e

REGION=${AWS_REGION:-us-west-2}
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
CLUSTER_NAME="fraud-detection-cluster"

read -p "Delete all AWS resources? (type 'yes'): " confirm
[ "$confirm" != "yes" ] && exit 0

eksctl delete cluster --name "$CLUSTER_NAME" --region "$REGION" --wait 2>/dev/null || true

BUCKET_NAME="fraud-events-${ACCOUNT_ID}-${REGION}"
aws s3 rm s3://$BUCKET_NAME --recursive 2>/dev/null || true
aws s3api delete-bucket --bucket "$BUCKET_NAME" --region "$REGION" 2>/dev/null || true

REPOS=("fraud-ingest" "fraud-featurizer" "fraud-infer")
for REPO in "${REPOS[@]}"; do
    aws ecr delete-repository --repository-name "$REPO" --region "$REGION" --force 2>/dev/null || true
done

POLICY_ARN="arn:aws:iam::${ACCOUNT_ID}:policy/FraudIngestS3Policy"
aws iam delete-policy --policy-arn "$POLICY_ARN" 2>/dev/null || true
