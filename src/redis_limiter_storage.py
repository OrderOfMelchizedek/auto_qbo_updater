"""Custom Redis storage for Flask-Limiter that handles Heroku Redis SSL."""
from typing import Optional, Union

from limits.storage.redis import RedisStorage


class HerokuRedisStorage(RedisStorage):
    """Redis storage backend that properly handles Heroku Redis SSL."""

    def __init__(self, uri: str, **options):
        """Initialize Redis storage with proper SSL handling for Heroku."""
        # Use our centralized Redis connection
        from .redis_connection import create_redis_client

        # Create Redis client with proper SSL configuration
        self._client = create_redis_client(
            decode_responses=False,  # Flask-Limiter needs bytes
            max_connections=3,  # Keep connection pool small for rate limiter
        )

        if self._client is None:
            raise ValueError("Redis client could not be created - REDIS_URL not set")

        # Initialize parent without URI (we're handling connection ourselves)
        super(RedisStorage, self).__init__(**options)

    @property
    def storage(self):
        """Return the Redis client."""
        if hasattr(self, "_client"):
            return self._client
        return super().storage


def get_limiter_storage(redis_url: Optional[str]) -> Union[str, HerokuRedisStorage]:
    """
    Get the appropriate storage configuration for Flask-Limiter.

    Args:
        redis_url: The Redis URL from environment

    Returns:
        Storage URI or instance for Flask-Limiter
    """
    if not redis_url:
        return "memory://"

    # For Heroku Redis (rediss://), use our custom storage
    if redis_url.startswith("rediss://"):
        return HerokuRedisStorage(redis_url)

    # For regular Redis, use the URL directly
    return redis_url
