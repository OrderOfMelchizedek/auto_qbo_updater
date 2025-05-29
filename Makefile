# Makefile for FOM to QBO Automation

.PHONY: help install install-dev test test-unit test-integration test-coverage run worker clean lint format check-format type-check setup-db migrate

# Default target
help:
	@echo "Available commands:"
	@echo "  make install        Install production dependencies"
	@echo "  make install-dev    Install development dependencies"
	@echo "  make test          Run all tests"
	@echo "  make test-unit     Run unit tests only"
	@echo "  make test-integration Run integration tests only"
	@echo "  make test-coverage Run tests with coverage report"
	@echo "  make run           Run the Flask application"
	@echo "  make worker        Start Celery worker"
	@echo "  make clean         Clean up temporary files"
	@echo "  make lint          Run code linting"
	@echo "  make format        Format code with black"
	@echo "  make check-format  Check code formatting"
	@echo "  make type-check    Run type checking with mypy"

# Install dependencies
install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements/dev.txt

# Testing
test:
	pytest tests/

test-unit:
	pytest tests/unit/

test-integration:
	pytest tests/integration/

test-coverage:
	pytest --cov=src --cov-report=html --cov-report=term tests/

# Run application
run:
	python src/run.py

run-prod:
	gunicorn -c gunicorn.conf.py src.app:app

# Celery
worker:
	celery -A src.utils.celery_app worker --loglevel=info

worker-beat:
	celery -A src.utils.celery_app beat --loglevel=info

# Code quality
lint:
	flake8 src/ tests/ --max-line-length=100 --extend-ignore=E203,W503

format:
	black src/ tests/ --line-length=100
	isort src/ tests/

check-format:
	black src/ tests/ --line-length=100 --check
	isort src/ tests/ --check-only

type-check:
	mypy src/ --ignore-missing-imports

# Cleanup
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type f -name ".coverage" -delete
	rm -rf htmlcov/
	rm -rf uploads/*
	rm -rf logs/*.log

# Development setup
setup:
	cp .env.example .env
	@echo "Please edit .env with your configuration values"

# Monitoring
monitor-logs:
	tail -f logs/*.log

monitor-errors:
	./scripts/monitoring/monitor_errors.sh

monitor-memory:
	python tests/integration/test_memory.py

# Database operations (if needed in future)
db-init:
	@echo "No database initialization needed for current version"

# Docker operations (if needed in future)
docker-build:
	@echo "Docker support not yet implemented"

docker-up:
	@echo "Docker support not yet implemented"

docker-down:
	@echo "Docker support not yet implemented"
