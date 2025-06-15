"""Configuration for Flask-Limiter with Heroku Redis SSL support."""
import os

from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


def configure_limiter(app: Flask) -> Limiter:
    """
    Configure Flask-Limiter with proper Redis SSL support for Heroku.

    Args:
        app: Flask application instance

    Returns:
        Configured Limiter instance
    """
    # Get Redis URL from environment
    redis_url = os.getenv("REDIS_URL")

    if redis_url:
        # Handle SSL for Heroku Redis (same approach as Celery)
        if redis_url.startswith("rediss://") and "ssl_cert_reqs" not in redis_url:
            # Parse URL to add parameters properly
            if "?" in redis_url:
                redis_url += "&ssl_cert_reqs=CERT_NONE"
            else:
                redis_url += "?ssl_cert_reqs=CERT_NONE"

        storage_uri = redis_url
    else:
        # Fall back to memory storage if no Redis URL
        storage_uri = "memory://"

    # Create limiter with native Redis support
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri=storage_uri,
    )

    return limiter
