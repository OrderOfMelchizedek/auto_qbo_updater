"""Unit tests for Celery configuration."""
from src.workers.celery_app import celery_app


def test_celery_app_exists():
    """Test that Celery app is properly initialized."""
    assert celery_app is not None
    assert celery_app.main == "QuickBooks-Donation-Manager"


def test_celery_broker_configuration():
    """Test that Celery broker is configured correctly."""
    # Get broker URL from configuration
    broker_url = celery_app.conf.broker_url
    assert broker_url is not None
    assert broker_url.startswith("redis://")


def test_celery_result_backend_configuration():
    """Test that Celery result backend is configured correctly."""
    result_backend = celery_app.conf.result_backend
    assert result_backend is not None
    assert result_backend.startswith("redis://")


def test_celery_task_serialization():
    """Test that Celery uses JSON serialization."""
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.result_serializer == "json"
    assert celery_app.conf.accept_content == ["json"]
