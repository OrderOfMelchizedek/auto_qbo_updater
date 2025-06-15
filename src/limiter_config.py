"""Configuration for Flask-Limiter with Heroku Redis SSL support."""
import os

from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


def configure_limiter(app: Flask) -> Limiter:
    """
    Configure Flask-Limiter with proper Redis SSL support for Heroku.

    Uses our centralized Redis connection that already works with SSL.

    Args:
        app: Flask application instance

    Returns:
        Configured Limiter instance
    """
    # Get Redis URL from environment
    redis_url = os.getenv("REDIS_URL")

    if redis_url:
        if redis_url.startswith("rediss://"):
            # SSL Redis - use our proven Redis connection module
            from .redis_connection import create_redis_client

            # Create Redis client using our working SSL configuration
            redis_client = create_redis_client(
                decode_responses=False,  # Flask-Limiter needs bytes
                max_connections=5,  # Smaller pool for rate limiter
            )

            if redis_client:
                # Use the connection pool from our working Redis client
                limiter = Limiter(
                    app=app,
                    key_func=get_remote_address,
                    default_limits=["200 per day", "50 per hour"],
                    storage_uri=redis_url,
                    storage_options={"connection_pool": redis_client.connection_pool},
                )
            else:
                # Fall back to memory if Redis connection fails
                limiter = Limiter(
                    app=app,
                    key_func=get_remote_address,
                    default_limits=["200 per day", "50 per hour"],
                    storage_uri="memory://",
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


def configure_limiter_with_connection_pool(app: Flask) -> Limiter:
    """
    Alternative: Configure Flask-Limiter using existing redis_connection.py module.

    This approach reuses the working Redis connection configuration from
    redis_connection.py to ensure consistency across the application.

    Args:
        app: Flask application instance

    Returns:
        Configured Limiter instance
    """
    redis_url = os.getenv("REDIS_URL")

    if redis_url:
        try:
            # Import here to avoid circular imports
            from .redis_connection import create_redis_client

            # Create Redis client using our working configuration
            redis_client = create_redis_client(
                decode_responses=True, max_connections=10
            )

            if redis_client:
                # Use the working Redis client with Flask-Limiter
                limiter = Limiter(
                    app=app,
                    key_func=get_remote_address,
                    default_limits=["200 per day", "50 per hour"],
                    storage_uri="redis://",  # Dummy URI for connection_pool
                    storage_options={"connection_pool": redis_client.connection_pool},
                )
                app.logger.info("Flask-Limiter configured with connection pool")
                return limiter
        except Exception as e:
            app.logger.error(f"Failed to configure limiter with connection pool: {e}")
            # Fall through to memory storage

    # Fall back to memory storage
    app.logger.warning("Flask-Limiter falling back to memory storage")
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri="memory://",
    )

    return limiter


def configure_limiter_with_url_params(app: Flask) -> Limiter:
    """
    Alternative: Configure Flask-Limiter by modifying Redis URL to include SSL params.

    This approach appends SSL parameters directly to the Redis URL, which is a
    reliable workaround for Heroku Redis SSL issues.

    Args:
        app: Flask application instance

    Returns:
        Configured Limiter instance
    """
    redis_url = os.getenv("REDIS_URL")

    if redis_url and redis_url.startswith("rediss://"):
        # Append SSL parameters to the URL to bypass SSL verification
        if "?" not in redis_url:
            redis_url += "?ssl_cert_reqs=none"
        else:
            redis_url += "&ssl_cert_reqs=none"

        app.logger.info("Flask-Limiter configured with SSL bypass in URL")

    if redis_url:
        limiter = Limiter(
            app=app,
            key_func=get_remote_address,
            default_limits=["200 per day", "50 per hour"],
            storage_uri=redis_url,
        )
    else:
        # Fall back to memory storage
        limiter = Limiter(
            app=app,
            key_func=get_remote_address,
            default_limits=["200 per day", "50 per hour"],
            storage_uri="memory://",
        )

    return limiter
