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
        if redis_url.startswith("rediss://"):
            # SSL Redis - use storage_options for SSL configuration
            limiter = Limiter(
                app=app,
                key_func=get_remote_address,
                default_limits=["200 per day", "50 per hour"],
                storage_uri=redis_url,
                storage_options={
                    "ssl_cert_reqs": None,  # Python None, not string "CERT_NONE"
                    "ssl_check_hostname": False,
                    "ssl_ca_certs": None,
                },
            )
        else:
            # Non-SSL Redis
            limiter = Limiter(
                app=app,
                key_func=get_remote_address,
                default_limits=["200 per day", "50 per hour"],
                storage_uri=redis_url,
            )
    else:
        # Fall back to memory storage if no Redis URL
        limiter = Limiter(
            app=app,
            key_func=get_remote_address,
            default_limits=["200 per day", "50 per hour"],
            storage_uri="memory://",
        )

    return limiter
