"""Redis retry utility for handling transient SSL errors."""
import functools
import logging
import time
from typing import Any, Callable, TypeVar

import redis

logger = logging.getLogger(__name__)

T = TypeVar("T")


def redis_retry(
    max_retries: int = 3,
    initial_delay: float = 0.1,
    backoff_factor: float = 2.0,
    exceptions: tuple = (redis.ConnectionError, redis.TimeoutError),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Retry Redis operations with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Factor to multiply delay by after each retry
        exceptions: Tuple of exceptions to catch and retry

    Returns:
        Decorated function that retries on specified exceptions
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        # Check if it's an SSL error
                        error_msg = str(e).lower()
                        if "ssl" in error_msg or "eof" in error_msg:
                            logger.warning(
                                f"SSL error in {func.__name__} "
                                f"(attempt {attempt + 1}/{max_retries + 1}): {e}"
                            )
                        else:
                            logger.warning(
                                f"Redis error in {func.__name__} "
                                f"(attempt {attempt + 1}/{max_retries + 1}): {e}"
                            )

                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        # Final attempt failed
                        logger.error(
                            f"Failed {func.__name__} after "
                            f"{max_retries + 1} attempts: {e}"
                        )

            # If we get here, all retries failed
            if last_exception:
                raise last_exception
            else:
                raise RuntimeError(f"{func.__name__} failed without exception")

        return wrapper

    return decorator


def warm_redis_connection(redis_client: redis.Redis) -> bool:
    """
    Pre-warm a Redis connection by performing a simple operation.

    Args:
        redis_client: Redis client to warm up

    Returns:
        True if connection is working, False otherwise
    """
    try:
        # Perform a simple PING operation to establish connection
        redis_client.ping()
        logger.info("✓ Redis connection warmed up successfully")
        return True
    except redis.ConnectionError as e:
        logger.error(f"✗ Failed to warm Redis connection: {e}")
        return False
    except Exception as e:
        logger.error(f"✗ Unexpected error warming Redis connection: {e}")
        return False


def warm_connection_pool(redis_client: redis.Redis, pool_size: int = 3) -> bool:
    """
    Pre-warm multiple connections in the Redis connection pool.

    Args:
        redis_client: Redis client with connection pool
        pool_size: Number of connections to warm up

    Returns:
        True if all connections warmed successfully
    """
    if not hasattr(redis_client, "connection_pool"):
        logger.warning("Redis client has no connection pool to warm")
        return warm_redis_connection(redis_client)

    success_count = 0
    for i in range(pool_size):
        try:
            # Each operation may use a different connection from the pool
            redis_client.ping()
            success_count += 1
        except Exception as e:
            logger.warning(f"Failed to warm connection {i + 1}/{pool_size}: {e}")

    logger.info(f"✓ Warmed {success_count}/{pool_size} Redis connections")
    return success_count > 0


def warm_session_backend() -> bool:
    """
    Pre-warm the session backend's Redis connection.

    Returns:
        True if successful, False otherwise
    """
    try:
        from .config import session_backend
        from .session import RedisSession

        if isinstance(session_backend, RedisSession) and hasattr(
            session_backend, "redis_client"
        ):
            logger.info("Pre-warming session backend Redis connection...")
            return warm_redis_connection(session_backend.redis_client)
        else:
            logger.info("Session backend is not using Redis, no warm-up needed")
            return True
    except Exception as e:
        logger.error(f"Failed to warm session backend: {e}")
        return False
