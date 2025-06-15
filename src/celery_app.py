"""Celery configuration for background task processing."""
import os
import ssl

from celery import Celery

# Commenting out unused function for now
# def get_celery_socket_keepalive_options():
#     """Get platform-specific socket keepalive options for Celery.
#
#     Returns:
#         dict: Socket keepalive options for Celery broker transport options
#     """
#     keepalive_options = {}
#
#     # Platform-specific handling
#     if sys.platform == "darwin":
#         # macOS/Darwin specific - only use available constants
#         if hasattr(socket, "TCP_KEEPINTVL"):
#             keepalive_options[socket.TCP_KEEPINTVL] = 60  # Interval between probes
#         if hasattr(socket, "TCP_KEEPCNT"):
#             keepalive_options[socket.TCP_KEEPCNT] = 3  # Number of probes
#     else:
#         # Linux and other platforms
#         if hasattr(socket, "TCP_KEEPIDLE"):
#             keepalive_options[socket.TCP_KEEPIDLE] = 60  # Seconds before sending probes  # noqa: E501
#         if hasattr(socket, "TCP_KEEPINTVL"):
#             keepalive_options[socket.TCP_KEEPINTVL] = 60  # Interval between probes
#         if hasattr(socket, "TCP_KEEPCNT"):
#             keepalive_options[socket.TCP_KEEPCNT] = 3  # Number of probes
#
#     return keepalive_options


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

# Alternative: Disable result backend if SSL issues persist
# Uncomment the next line if result backend SSL problems continue
# DISABLE_RESULT_BACKEND = True

# Configure Celery
# NUCLEAR FIX: Always disable result backend due to persistent SSL issues
# The result backend consistently fails with SSL EOF errors on Heroku Redis
# Tasks will run successfully without result storage
DISABLE_RESULT_BACKEND = True
print("[Celery] 🚨 NUCLEAR FIX: Result backend permanently disabled due to SSL issues")
print("[Celery] Tasks will run fire-and-forget without result storage")

config = {  # type: ignore[var-annotated]
    "broker_url": redis_url,
    "result_backend": None,  # Permanently disabled
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

        # Update the broker URL in config (result_backend stays disabled)
        config["broker_url"] = redis_url
        # NOTE: result_backend stays None - permanently disabled

    # Option 2: Also set SSL configuration (as backup)
    # Note: For redis broker, SSL keys must be prefixed with 'ssl_'
    ssl_config = {  # type: ignore[var-annotated]
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
        # NOTE: result_backend_transport_options was removed - invalid setting
        # Result backend SSL issues resolved by disabling result storage
        # Additional connection settings
        "broker_connection_timeout": 30,
        "broker_connection_retry_delay": 0.5,
    }
    config.update(ssl_config)  # type: ignore[arg-type]

    # Socket keepalive options disabled for now - causing issues on Heroku
    # keepalive_opts = get_celery_socket_keepalive_options()

    # Configure broker transport options
    transport_options = {
        "master_name": None,
        "visibility_timeout": 3600,
        "socket_keepalive": True,
        # Additional SSL transport options
        "connection_class": "redis.SSLConnection",
        "connection_kwargs": {
            "ssl_cert_reqs": "none",
            "ssl_check_hostname": False,
        },
    }

    # Skip keepalive options for now - they're causing issues on Heroku
    # if keepalive_opts:
    #     transport_options["socket_keepalive_options"] = keepalive_opts

    config["broker_transport_options"] = transport_options  # type: ignore[assignment]

# Log the final configuration for debugging
print(f"[Celery] Broker URL: {config.get('broker_url', 'not set')}")
print("[Celery] Result Backend: DISABLED (SSL issues)")
print(f"[Celery] SSL enabled: {redis_url.startswith('rediss://')}")
print("[Celery] ✅ Tasks will execute successfully without result storage")

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
