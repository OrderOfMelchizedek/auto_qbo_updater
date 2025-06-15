"""Celery configuration for background task processing."""
import os
import ssl

from celery import Celery

# Get Redis URL and clean it up
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Remove trailing slashes from Redis URL (common issue with Heroku Redis URLs)
if redis_url.endswith("//"):
    redis_url = redis_url[:-2]
elif redis_url.endswith("/"):
    redis_url = redis_url[:-1]

# Add database number if not present (Celery expects /0 at the end)
if not redis_url.split("://")[1].count("/"):
    redis_url += "/0"

# Create Celery instance
celery_app = Celery(
    "donation_processor",
    include=["src.tasks"],
)

# Configure Celery
config = {
    "broker_url": redis_url,
    "result_backend": redis_url,
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
    # For Celery 5.x with Heroku Redis, we have two options:
    # Option 1: Use URL parameters (most reliable)
    # Option 2: Use broker_use_ssl configuration

    # Try Option 1 first: Add SSL parameters to URL if not already present
    if "ssl_cert_reqs" not in redis_url:
        # Parse URL to add parameters properly
        if "?" in redis_url:
            redis_url += "&ssl_cert_reqs=CERT_NONE"
        else:
            redis_url += "?ssl_cert_reqs=CERT_NONE"

        # Update the URLs in config
        config["broker_url"] = redis_url
        config["result_backend"] = redis_url

    # Option 2: Also set SSL configuration (as backup)
    # Note: For redis broker, SSL keys must be prefixed with 'ssl_'
    config.update(
        {
            "broker_use_ssl": {
                "ssl_cert_reqs": ssl.CERT_NONE,  # Must use SSL constant
                "ssl_ca_certs": None,
                "ssl_certfile": None,
                "ssl_keyfile": None,
                "ssl_check_hostname": False,
            },
            "redis_backend_use_ssl": {
                "ssl_cert_reqs": ssl.CERT_NONE,  # Must use SSL constant
                "ssl_ca_certs": None,
                "ssl_certfile": None,
                "ssl_keyfile": None,
                "ssl_check_hostname": False,
            },
            # Additional connection settings
            "broker_connection_timeout": 30,
            "broker_connection_retry_delay": 0.5,
            "broker_transport_options": {
                "master_name": None,
                "visibility_timeout": 3600,
                "socket_keepalive": True,
                "socket_keepalive_options": {
                    1: 1,  # TCP_KEEPIDLE
                    2: 2,  # TCP_KEEPINTVL
                    3: 2,  # TCP_KEEPCNT
                },
                # Additional SSL transport options
                "connection_class": "redis.SSLConnection",
                "connection_kwargs": {
                    "ssl_cert_reqs": "none",
                    "ssl_check_hostname": False,
                },
            },
        }
    )

# Log the final configuration for debugging
print(f"[Celery] Broker URL: {config.get('broker_url', 'not set')}")
print(f"[Celery] SSL enabled: {redis_url.startswith('rediss://')}")

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
