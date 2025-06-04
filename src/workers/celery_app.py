"""Celery application configuration."""
from celery import Celery

from src.config.settings import settings

# Create Celery app
celery_app = Celery(
    "QuickBooks-Donation-Manager",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Task execution settings
    task_soft_time_limit=300,  # 5 minutes soft limit
    task_time_limit=600,  # 10 minutes hard limit
    # Worker settings
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    # Task routing
    task_routes={
        "src.workers.tasks.document_tasks.*": {"queue": "documents"},
        "src.workers.tasks.quickbooks_tasks.*": {"queue": "quickbooks"},
        "src.workers.tasks.letter_tasks.*": {"queue": "letters"},
    },
)
