"""Celery configuration for background task processing."""
import os

from celery import Celery

# Create Celery instance
celery_app = Celery(
    "donation_processor",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    include=["src.tasks"],
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Track task progress
    task_track_started=True,
    task_send_sent_event=True,
    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    result_persistent=True,
    # Worker settings
    worker_prefetch_multiplier=1,  # Process one task at a time
    worker_max_tasks_per_child=100,  # Restart worker after 100 tasks
    # Task execution settings
    task_soft_time_limit=600,  # 10 minutes soft limit
    task_time_limit=900,  # 15 minutes hard limit
)


# Initialize Celery app context
def init_celery(app=None):
    """Initialize Celery with Flask app context."""
    if app is not None:
        celery_app.conf.update(app.config)

        class ContextTask(celery_app.Task):
            """Make celery tasks work with Flask app context."""

            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)

        celery_app.Task = ContextTask

    return celery_app
