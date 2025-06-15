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


# Commenting out unused function for now
# def get_socket_keepalive_options():
#     """Get platform-specific socket keepalive options.
#
#     Returns:
#         dict: Socket keepalive options for redis-py, or None if not supported
#     """
#     keepalive_options = {}
#
#     # Platform-specific handling
#     if sys.platform == "darwin":
#         # macOS/Darwin specific
#         # TCP_KEEPALIVE is not exported by Python's socket module on macOS
#         TCP_KEEPALIVE = 0x10  # Value from /usr/include
#
#         # Only use the options that are available on macOS
#         if hasattr(socket, "TCP_KEEPINTVL"):
#             keepalive_options[socket.TCP_KEEPINTVL] = 60  # Interval between probes
#         if hasattr(socket, "TCP_KEEPCNT"):
#             keepalive_options[socket.TCP_KEEPCNT] = 3  # Number of probes
#
#         # Note: macOS doesn't have TCP_KEEPIDLE, uses TCP_KEEPALIVE differently
#         # We could set TCP_KEEPALIVE but it serves a different purpose on macOS
#
#     else:
#         # Linux and other platforms
#         if hasattr(socket, "TCP_KEEPIDLE"):
#             keepalive_options[socket.TCP_KEEPIDLE] = 60  # Seconds before sending probes  # noqa: E501
#         if hasattr(socket, "TCP_KEEPINTVL"):
#             keepalive_options[socket.TCP_KEEPINTVL] = 60  # Interval between probes
#         if hasattr(socket, "TCP_KEEPCNT"):
#             keepalive_options[socket.TCP_KEEPCNT] = 3  # Number of probes
#
#     # Return None if no options are available
#     return keepalive_options if keepalive_options else None


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

    # Socket keepalive options disabled for now - causing issues on Heroku
    # keepalive_options = get_socket_keepalive_options()

    try:
        if redis_url.startswith("rediss://"):
            # For Heroku Redis with SSL
            logger.info("Creating Redis client with SSL (rediss://)")

            # Build connection parameters
            connection_params = {
                "decode_responses": decode_responses,
                "max_connections": max_connections,
                "socket_keepalive": True,
                "ssl_cert_reqs": None,  # Use None for better compatibility
                "ssl_check_hostname": False,
                "ssl_ca_certs": None,
                "retry_on_error": [redis.ConnectionError, redis.TimeoutError],
                "retry": Retry(ExponentialBackoff(cap=10, base=1), 3),
            }

            # Skip keepalive options for now - they're causing issues on Heroku
            # if keepalive_options:
            #     connection_params["socket_keepalive_options"] = keepalive_options
            #     logger.debug(f"Using socket keepalive options: {keepalive_options}")
            # else:
            #     logger.debug("Socket keepalive options not available on this platform")  # noqa: E501
            logger.debug("Socket keepalive enabled without custom options")

            client = redis.from_url(redis_url, **connection_params)
        else:
            # Non-SSL Redis
            logger.info("Creating Redis client without SSL (redis://)")

            # Build connection parameters
            connection_params = {
                "decode_responses": decode_responses,
                "max_connections": max_connections,
                "socket_keepalive": True,
                "retry_on_error": [redis.ConnectionError, redis.TimeoutError],
                "retry": Retry(ExponentialBackoff(cap=10, base=1), 3),
            }

            # Skip keepalive options for now - they're causing issues
            # if keepalive_options:
            #     connection_params["socket_keepalive_options"] = keepalive_options

            client = redis.from_url(redis_url, **connection_params)

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
