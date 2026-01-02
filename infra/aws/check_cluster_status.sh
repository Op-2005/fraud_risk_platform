#!/bin/bash
# Check EKS cluster and nodegroup status
set -e

CLUSTER_NAME="fraud-detection-cluster"
REGION=${AWS_REGION:-us-west-2}

aws eks describe-cluster --name "$CLUSTER_NAME" --region "$REGION" --query 'cluster.status' --output text

NODEGROUPS=$(aws eks list-nodegroups --cluster-name "$CLUSTER_NAME" --region "$REGION" --query 'nodegroups[]' --output text)
for NG in $NODEGROUPS; do
    aws eks describe-nodegroup --cluster-name "$CLUSTER_NAME" --nodegroup-name "$NG" --region "$REGION" --query 'nodegroup.status' --output text
done
