#!/bin/bash
# Verify required tools and dependencies for local development
set -e

check_tool() {
    command -v "$1" &>/dev/null || { echo "$1: NOT FOUND"; exit 1; }
}

check_tool python3
check_tool docker
check_tool docker-compose || docker compose version &>/dev/null || exit 1

python3 --version
docker --version

if ! aws sts get-caller-identity &>/dev/null; then
    echo "AWS credentials not configured"
    exit 1
fi

if ! docker ps &>/dev/null; then
    echo "Docker daemon not running"
    exit 1
fi
