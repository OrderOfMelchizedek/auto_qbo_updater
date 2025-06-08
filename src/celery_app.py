"""Celery configuration for background task processing."""
import os
import ssl

from celery import Celery

# Get Redis URL
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create Celery instance
celery_app = Celery(
    "donation_processor",
    broker=redis_url,
    backend=redis_url,
    include=["src.tasks"],
)

# Configure Celery
config = {
    "task_serializer": "json",
    "accept_content": ["json"],
    "result_serializer": "json",
    "timezone": "UTC",
    "enable_utc": True,
    # Track task progress
    "task_track_started": True,
    "task_send_sent_event": True,
    # Result backend settings
    "result_expires": 3600,  # Results expire after 1 hour
    "result_persistent": True,
    # Worker settings
    "worker_prefetch_multiplier": 1,  # Process one task at a time
    "worker_max_tasks_per_child": 100,  # Restart worker after 100 tasks
    # Task execution settings
    "task_soft_time_limit": 600,  # 10 minutes soft limit
    "task_time_limit": 900,  # 15 minutes hard limit
    # Connection pool settings
    "broker_pool_limit": 5,  # Limit broker connections per worker
    "redis_max_connections": 10,  # Total Redis connection pool size
    "broker_connection_retry_on_startup": True,
    "broker_connection_retry": True,
    "broker_connection_max_retries": 10,
}

# Handle SSL for Heroku Redis
if redis_url.startswith("rediss://"):
    # Heroku Redis uses self-signed certificates
    config.update(
        {
            "broker_use_ssl": {
                "ssl_cert_reqs": ssl.CERT_NONE,
                "ssl_ca_certs": None,
                "ssl_certfile": None,
                "ssl_keyfile": None,
                "ssl_check_hostname": False,
            },
            "redis_backend_use_ssl": {
                "ssl_cert_reqs": ssl.CERT_NONE,
                "ssl_ca_certs": None,
                "ssl_certfile": None,
                "ssl_keyfile": None,
                "ssl_check_hostname": False,
            },
        }
    )

celery_app.conf.update(config)


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
