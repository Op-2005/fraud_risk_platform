#!/bin/bash
# Create Glue database for Athena. Table creation must be done manually in Athena console.
set -e

REGION=${AWS_REGION:-us-west-2}
DATABASE_NAME="fraud_demo"

aws glue create-database \
  --database-input "Name=${DATABASE_NAME}" \
  --region "$REGION" 2>/dev/null || true

