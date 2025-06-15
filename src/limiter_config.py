"""Configuration for Flask-Limiter with Heroku Redis SSL support."""
import os
from typing import Union

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

    # Use our custom Redis storage that handles SSL properly
    storage_uri: Union[str, object]
    if redis_url:
        from .redis_limiter_storage import HerokuRedisStorage

        storage_uri = HerokuRedisStorage(redis_url)
    else:
        # For development without Redis
        storage_uri = "memory://"

    # Create limiter
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri=storage_uri,
    )

    return limiter
