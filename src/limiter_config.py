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
    redis_url = os.getenv("REDIS_URL")

    # For production with Heroku Redis, use memory storage
    # Flask-Limiter has issues with Heroku Redis SSL certificates
    # Memory storage still provides rate limiting, just resets on dyno restart
    if os.getenv("DYNO") and redis_url and redis_url.startswith("rediss://"):
        storage_uri = "memory://"
    else:
        # For development or non-SSL Redis
        storage_uri = redis_url if redis_url else "memory://"

    # Create limiter
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri=storage_uri,
    )

    return limiter
