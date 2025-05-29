"""
Retry logic for handling transient failures in external API calls.
"""

import functools
import logging
import time
from typing import Callable, Tuple, Type, Union

from .exceptions import ExternalAPIException, RetryableException

# Configure logger
logger = logging.getLogger(__name__)


def exponential_backoff(
    attempt: int, base_delay: float = 1.0, max_delay: float = 60.0
) -> float:
    """Calculate exponential backoff delay."""
    delay = min(base_delay * (2**attempt), max_delay)
    # Add jitter to prevent thundering herd
    jitter = delay * 0.1 * (0.5 - time.time() % 1)
    return delay + jitter


def is_retryable_error(exception: Exception) -> bool:
    """Determine if an error should be retried."""
    # Always retry RetryableException
    if isinstance(exception, RetryableException):
        return True

    # Retry external API errors with specific status codes
    if isinstance(exception, ExternalAPIException):
        if exception.status_code in [
            429,
            500,
            502,
            503,
            504,
        ]:  # Rate limit or server errors
            return True

    # Retry connection errors
    if isinstance(exception, (ConnectionError, TimeoutError)):
        return True

    return False


def retry_on_failure(
    max_attempts: int = 3,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    delay_func: Callable[[int], float] = exponential_backoff,
    on_retry: Callable[[Exception, int], None] = None,
):
    """
    Decorator to retry a function on failure.

    Args:
        max_attempts: Maximum number of attempts (including initial)
        exceptions: Tuple of exception types to catch
        delay_func: Function to calculate delay between retries
        on_retry: Optional callback when retrying
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    # Check if we should retry
                    if not is_retryable_error(e) or attempt == max_attempts - 1:
                        raise

                    # Calculate delay
                    delay = delay_func(attempt)

                    # Log retry attempt
                    logger.warning(
                        f"Retry {attempt + 1}/{max_attempts} for {func.__name__} "
                        f"after {type(e).__name__}: {str(e)}. "
                        f"Waiting {delay:.1f}s before retry."
                    )

                    # Call retry callback if provided
                    if on_retry:
                        on_retry(e, attempt + 1)

                    # Wait before retrying
                    time.sleep(delay)

            # This should never be reached, but just in case
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


def retry_api_call(func: Callable, service_name: str, *args, **kwargs):
    """
    Utility function to retry an API call with standard error handling.

    Args:
        func: The function to call
        service_name: Name of the service for logging
        *args, **kwargs: Arguments to pass to the function

    Returns:
        The result of the function call
    """

    @retry_on_failure(
        max_attempts=3,
        exceptions=(Exception,),
        on_retry=lambda e, attempt: logger.info(
            f"Retrying {service_name} call, attempt {attempt}"
        ),
    )
    def wrapped_call():
        return func(*args, **kwargs)

    try:
        return wrapped_call()
    except Exception as e:
        logger.error(f"Failed to call {service_name} after all retries: {str(e)}")
        raise
