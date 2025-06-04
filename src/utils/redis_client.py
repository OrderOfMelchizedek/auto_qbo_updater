"""Redis client utility."""
from typing import Optional

import redis

from src.config.settings import settings


class RedisConnectionError(Exception):
    """Custom exception for Redis connection errors."""

    pass


_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    """
    Get Redis client instance.

    Returns:
        Redis client instance

    Raises:
        RedisConnectionError: If connection to Redis fails
    """
    global _redis_client

    if _redis_client is None:
        try:
            _redis_client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            # Test connection
            _redis_client.ping()
        except Exception as e:
            raise RedisConnectionError(f"Failed to connect to Redis: {str(e)}")

    return _redis_client
