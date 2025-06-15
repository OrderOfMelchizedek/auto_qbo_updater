"""Custom Redis storage for Flask-Limiter that handles Heroku Redis SSL."""
import ssl
from typing import Optional, Union
from urllib.parse import urlparse

import redis
from limits.storage.redis import RedisStorage


class HerokuRedisStorage(RedisStorage):
    """Redis storage backend that properly handles Heroku Redis SSL."""

    def __init__(self, uri: str, **options):
        """Initialize Redis storage with proper SSL handling for Heroku."""
        # Parse the Redis URL
        parsed = urlparse(uri)

        # Check if it's a secure Redis URL
        if parsed.scheme == "rediss":
            # Create SSL context that doesn't verify certificates
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            # Create Redis client directly with explicit parameters
            self._client = redis.Redis(
                host=parsed.hostname or "localhost",
                port=parsed.port or 6379,
                password=parsed.password,
                ssl=True,
                ssl_cert_reqs=None,
                ssl_ca_certs=None,
                ssl_check_hostname=False,
            )

            # Initialize parent without URI (we're handling connection ourselves)
            super(RedisStorage, self).__init__(**options)
        else:
            # For non-SSL Redis, use normal initialization
            super().__init__(uri=uri, **options)

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
