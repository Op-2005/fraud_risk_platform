.PHONY: help install test build push deploy-local clean

help:
	@echo "Available targets:"
	@echo "  install       - Install Python dependencies"
	@echo "  test          - Run all tests"
	@echo "  build         - Build all Docker images"
	@echo "  push          - Push images to ECR"
	@echo "  deploy-local  - Deploy to local Kubernetes"
	@echo "  clean         - Clean up generated files"

install:
	poetry install

test:
	poetry run pytest services/*/tests/ -v

build:
	docker build -t fraud-ingest:latest services/ingest/
	docker build -t fraud-featurizer:latest services/featurizer/
	docker build -t fraud-infer:latest services/infer/

push:
	@echo "Tagging and pushing to ECR..."
	./infra/aws/03_push_images.sh

deploy-local:
	kubectl apply -f infra/k8s/namespace.yaml
	kubectl apply -f infra/k8s/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
	rm -rf data/processed/*
