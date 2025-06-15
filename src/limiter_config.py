"""Configuration for Flask-Limiter with Heroku Redis SSL support."""
import os

from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from .redis_limiter_storage import get_limiter_storage


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

    # Get appropriate storage (Redis with SSL support or memory fallback)
    storage = get_limiter_storage(redis_url)

    # Create limiter
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri=storage,
    )

    return limiter
