"""Configuration for Flask-Limiter with Heroku Redis SSL support."""
import os
import ssl
from urllib.parse import urlparse

import redis
from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from limits.storage import RedisStorage


def configure_limiter(app: Flask) -> Limiter:
    """
    Configure Flask-Limiter with proper Redis SSL support for Heroku.

    Args:
        app: Flask application instance

    Returns:
        Configured Limiter instance
    """
    redis_url = os.getenv("REDIS_URL")

    if redis_url and redis_url.startswith("rediss://"):
        # Parse Redis URL
        parsed = urlparse(redis_url)

        # Create Redis client with SSL configuration
        redis_client = redis.Redis(
            host=parsed.hostname or "localhost",
            port=parsed.port or 6379,
            password=parsed.password,
            ssl=True,
            ssl_cert_reqs=ssl.CERT_NONE,  # Disable cert verification for Heroku
            decode_responses=True,
        )

        # Create storage instance with the configured Redis client
        storage = RedisStorage(redis_client)

        # Initialize limiter without storage_uri
        limiter = Limiter(
            app=app,
            key_func=get_remote_address,
            default_limits=["200 per day", "50 per hour"],
        )

        # Manually set the storage
        limiter._storage = storage

    else:
        # For non-SSL Redis or no Redis, use standard configuration
        limiter = Limiter(
            app=app,
            key_func=get_remote_address,
            default_limits=["200 per day", "50 per hour"],
            storage_uri=redis_url if redis_url else "memory://",
        )

    return limiter
