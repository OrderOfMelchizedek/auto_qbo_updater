"""
Rate limiting utility for API calls.

This module provides a thread-safe rate limiter that can enforce
both per-minute and per-hour rate limits.
"""

import threading
from datetime import datetime, timedelta
from typing import List, Optional


class RateLimitExceededException(Exception):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, message: str, wait_time: float):
        """Initialize exception with message and wait time.

        Args:
            message: Error message
            wait_time: Time to wait in seconds before retry
        """
        super().__init__(message)
        self.wait_time = wait_time


class RateLimiter:
    """Thread-safe rate limiter for API calls."""

    def __init__(
        self,
        per_minute_limit: Optional[int] = None,
        per_hour_limit: Optional[int] = None,
    ):
        """Initialize rate limiter with specified limits.

        Args:
            per_minute_limit: Maximum calls allowed per minute
            per_hour_limit: Maximum calls allowed per hour
        """
        self.per_minute_limit = per_minute_limit
        self.per_hour_limit = per_hour_limit

        self._minute_calls: List[datetime] = []
        self._hour_calls: List[datetime] = []
        self._lock = threading.Lock()

    def check_and_record(self) -> None:
        """Check if rate limit allows a call and record it.

        Raises:
            RateLimitExceededException: If rate limit would be exceeded
        """
        with self._lock:
            now = datetime.now()

            # Clean up old entries
            if self.per_minute_limit:
                minute_ago = now - timedelta(minutes=1)
                self._minute_calls = [t for t in self._minute_calls if t > minute_ago]

            if self.per_hour_limit:
                hour_ago = now - timedelta(hours=1)
                self._hour_calls = [t for t in self._hour_calls if t > hour_ago]

            # Check minute limit
            if self.per_minute_limit and len(self._minute_calls) >= self.per_minute_limit:
                wait_time = (self._minute_calls[0] - (now - timedelta(minutes=1))).total_seconds()
                raise RateLimitExceededException(
                    f"Rate limit exceeded: {self.per_minute_limit} calls per minute. "
                    f"Please wait {wait_time:.1f} seconds.",
                    wait_time=wait_time,
                )

            # Check hour limit
            if self.per_hour_limit and len(self._hour_calls) >= self.per_hour_limit:
                wait_time_seconds = (self._hour_calls[0] - (now - timedelta(hours=1))).total_seconds()
                wait_time_minutes = wait_time_seconds / 60
                raise RateLimitExceededException(
                    f"Rate limit exceeded: {self.per_hour_limit} calls per hour. "
                    f"Please wait {wait_time_minutes:.1f} minutes.",
                    wait_time=wait_time_seconds,
                )

            # Record this call
            if self.per_minute_limit:
                self._minute_calls.append(now)
            if self.per_hour_limit:
                self._hour_calls.append(now)

    def reset(self) -> None:
        """Reset all rate limit tracking."""
        with self._lock:
            self._minute_calls.clear()
            self._hour_calls.clear()

    def get_usage_stats(self) -> dict:
        """Get current usage statistics.

        Returns:
            Dictionary with usage stats
        """
        with self._lock:
            now = datetime.now()
            minute_ago = now - timedelta(minutes=1)
            hour_ago = now - timedelta(hours=1)

            # Clean up for accurate counts
            minute_calls = [t for t in self._minute_calls if t > minute_ago]
            hour_calls = [t for t in self._hour_calls if t > hour_ago]

            stats = {
                "current_minute_calls": len(minute_calls),
                "current_hour_calls": len(hour_calls),
            }

            if self.per_minute_limit:
                stats["per_minute_limit"] = self.per_minute_limit
                stats["minute_remaining"] = max(0, self.per_minute_limit - len(minute_calls))

            if self.per_hour_limit:
                stats["per_hour_limit"] = self.per_hour_limit
                stats["hour_remaining"] = max(0, self.per_hour_limit - len(hour_calls))

            return stats
