"""Unit tests for Celery configuration."""
from unittest.mock import patch

import pytest


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    with patch("redis.Redis") as mock:
        yield mock


def test_celery_app_exists(mock_redis):
    """Test that Celery app is properly initialized."""
    # Import after mocking Redis
    from src.workers.celery_app import celery_app

    assert celery_app is not None
    assert celery_app.main == "QuickBooks-Donation-Manager"


def test_celery_broker_configuration(mock_redis):
    """Test that Celery broker is configured correctly."""
    from src.workers.celery_app import celery_app

    # Get broker URL from configuration
    broker_url = celery_app.conf.broker_url
    assert broker_url is not None
    assert broker_url.startswith("redis://")


def test_celery_result_backend_configuration(mock_redis):
    """Test that Celery result backend is configured correctly."""
    from src.workers.celery_app import celery_app

    result_backend = celery_app.conf.result_backend
    assert result_backend is not None
    assert result_backend.startswith("redis://")


def test_celery_task_serialization(mock_redis):
    """Test that Celery uses JSON serialization."""
    from src.workers.celery_app import celery_app

    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.result_serializer == "json"
    assert celery_app.conf.accept_content == ["json"]
