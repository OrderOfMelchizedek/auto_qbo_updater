"""Centralized Redis connection with proper SSL for Heroku."""
import os

import redis
from redis.backoff import ExponentialBackoff
from redis.retry import Retry


def create_redis_client(decode_responses=True, max_connections=10):
    """Create Redis client with proper SSL configuration for Heroku.

    Args:
        decode_responses: Whether to decode responses to strings
        max_connections: Maximum number of connections in the pool

    Returns:
        Configured Redis client or None if REDIS_URL not set
    """
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return None

    if redis_url.startswith("rediss://"):
        # For Heroku Redis with SSL
        return redis.from_url(
            redis_url,
            decode_responses=decode_responses,
            max_connections=max_connections,
            socket_keepalive=True,
            socket_keepalive_options={
                1: 1,  # TCP_KEEPIDLE
                2: 2,  # TCP_KEEPINTVL
                3: 2,  # TCP_KEEPCNT
            },
            ssl_cert_reqs="none",  # String, not None!
            ssl_check_hostname=False,
            ssl_ca_certs=None,
            retry_on_error=[redis.ConnectionError, redis.TimeoutError],
            retry=Retry(ExponentialBackoff(cap=10, base=1), 3),
        )
    else:
        # Non-SSL Redis
        return redis.from_url(
            redis_url,
            decode_responses=decode_responses,
            max_connections=max_connections,
            socket_keepalive=True,
            retry_on_error=[redis.ConnectionError, redis.TimeoutError],
            retry=Retry(ExponentialBackoff(cap=10, base=1), 3),
        )
