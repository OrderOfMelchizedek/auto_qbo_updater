"""Centralized Redis connection with proper SSL for Heroku.

This module handles Redis connections for all components in the application.
Different components have different SSL requirements:
- Direct redis-py usage: ssl_cert_reqs=None works best
- Celery/Kombu: Requires ssl.CERT_NONE constant (configured separately)
- Heroku Redis: Uses self-signed certificates, requires SSL verification disabled
"""
import logging
import os

import redis
from redis.backoff import ExponentialBackoff
from redis.retry import Retry

logger = logging.getLogger(__name__)


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

    try:
        if redis_url.startswith("rediss://"):
            # For Heroku Redis with SSL
            logger.info("Creating Redis client with SSL (rediss://)")
            client = redis.from_url(
                redis_url,
                decode_responses=decode_responses,
                max_connections=max_connections,
                socket_keepalive=True,
                socket_keepalive_options={
                    1: 1,  # TCP_KEEPIDLE
                    2: 2,  # TCP_KEEPINTVL
                    3: 2,  # TCP_KEEPCNT
                },
                ssl_cert_reqs=None,  # Use None for better compatibility
                ssl_check_hostname=False,
                ssl_ca_certs=None,
                retry_on_error=[redis.ConnectionError, redis.TimeoutError],
                retry=Retry(ExponentialBackoff(cap=10, base=1), 3),
            )
        else:
            # Non-SSL Redis
            logger.info("Creating Redis client without SSL (redis://)")
            client = redis.from_url(
                redis_url,
                decode_responses=decode_responses,
                max_connections=max_connections,
                socket_keepalive=True,
                retry_on_error=[redis.ConnectionError, redis.TimeoutError],
                retry=Retry(ExponentialBackoff(cap=10, base=1), 3),
            )

        # Test the connection
        client.ping()
        logger.info("Redis connection established successfully")
        return client

    except redis.ConnectionError as e:
        logger.error(f"Failed to connect to Redis: {e}")
        logger.error(
            "If using Heroku Redis, ensure REDIS_URL starts with 'rediss://' for SSL"
        )
        return None
    except Exception as e:
        logger.error(f"Unexpected error creating Redis client: {e}")
        return None
