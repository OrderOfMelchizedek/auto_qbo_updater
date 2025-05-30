"""
Unit tests for rate limiter module.
"""

import time
from datetime import datetime, timedelta
from threading import Thread
from unittest.mock import patch

import pytest

from src.utils.rate_limiter import RateLimiter, RateLimitExceededException


class TestRateLimiter:
    """Test the rate limiter functionality."""

    def test_init_with_limits(self):
        """Test initialization with rate limits."""
        limiter = RateLimiter(per_minute_limit=60, per_hour_limit=1000)

        assert limiter.per_minute_limit == 60
        assert limiter.per_hour_limit == 1000
        assert len(limiter._minute_calls) == 0
        assert len(limiter._hour_calls) == 0

    def test_init_without_limits(self):
        """Test initialization without rate limits."""
        limiter = RateLimiter()

        assert limiter.per_minute_limit is None
        assert limiter.per_hour_limit is None

    def test_check_and_record_within_limits(self):
        """Test that calls within limits are allowed."""
        limiter = RateLimiter(per_minute_limit=5, per_hour_limit=100)

        # Should allow 5 calls
        for _ in range(5):
            limiter.check_and_record()

        # Verify calls were recorded
        assert len(limiter._minute_calls) == 5
        assert len(limiter._hour_calls) == 5

    def test_minute_limit_exceeded(self):
        """Test that minute limit is enforced."""
        limiter = RateLimiter(per_minute_limit=3)

        # Allow 3 calls
        for _ in range(3):
            limiter.check_and_record()

        # 4th call should raise exception
        with pytest.raises(RateLimitExceededException) as exc_info:
            limiter.check_and_record()

        assert "3 calls per minute" in str(exc_info.value)
        assert exc_info.value.wait_time > 0

    def test_hour_limit_exceeded(self):
        """Test that hour limit is enforced."""
        limiter = RateLimiter(per_hour_limit=3)

        # Allow 3 calls
        for _ in range(3):
            limiter.check_and_record()

        # 4th call should raise exception
        with pytest.raises(RateLimitExceededException) as exc_info:
            limiter.check_and_record()

        assert "3 calls per hour" in str(exc_info.value)
        assert exc_info.value.wait_time > 0

    def test_old_calls_cleanup(self):
        """Test that old calls are cleaned up."""
        limiter = RateLimiter(per_minute_limit=2)

        # Mock time to simulate passage of time
        base_time = datetime.now()

        with patch("src.utils.rate_limiter.datetime") as mock_datetime:
            # First call at base time
            mock_datetime.now.return_value = base_time
            limiter.check_and_record()

            # Second call 30 seconds later
            mock_datetime.now.return_value = base_time + timedelta(seconds=30)
            limiter.check_and_record()

            # Third call 61 seconds after first (should be allowed)
            mock_datetime.now.return_value = base_time + timedelta(seconds=61)
            limiter.check_and_record()

            # Should have only 2 calls tracked (first one expired)
            assert len(limiter._minute_calls) == 2

    def test_reset(self):
        """Test resetting the rate limiter."""
        limiter = RateLimiter(per_minute_limit=5, per_hour_limit=100)

        # Add some calls
        for _ in range(3):
            limiter.check_and_record()

        assert len(limiter._minute_calls) == 3
        assert len(limiter._hour_calls) == 3

        # Reset
        limiter.reset()

        assert len(limiter._minute_calls) == 0
        assert len(limiter._hour_calls) == 0

    def test_get_usage_stats(self):
        """Test getting usage statistics."""
        limiter = RateLimiter(per_minute_limit=5, per_hour_limit=100)

        # Add some calls
        for _ in range(3):
            limiter.check_and_record()

        stats = limiter.get_usage_stats()

        assert stats["current_minute_calls"] == 3
        assert stats["current_hour_calls"] == 3
        assert stats["per_minute_limit"] == 5
        assert stats["per_hour_limit"] == 100
        assert stats["minute_remaining"] == 2
        assert stats["hour_remaining"] == 97

    def test_get_usage_stats_no_limits(self):
        """Test getting usage stats when no limits are set."""
        limiter = RateLimiter()

        # Add some calls (should be allowed since no limits)
        limiter.check_and_record()
        limiter.check_and_record()

        stats = limiter.get_usage_stats()

        assert stats["current_minute_calls"] == 0  # Not tracked
        assert stats["current_hour_calls"] == 0  # Not tracked
        assert "per_minute_limit" not in stats
        assert "per_hour_limit" not in stats

    def test_thread_safety(self):
        """Test that rate limiter is thread-safe."""
        limiter = RateLimiter(per_minute_limit=20)  # Increased to allow all calls
        call_counts = []

        def make_calls():
            count = 0
            for _ in range(5):
                try:
                    limiter.check_and_record()
                    count += 1
                    time.sleep(0.01)  # Small delay to increase contention
                except RateLimitExceededException:
                    break
            call_counts.append(count)

        # Create multiple threads
        threads = [Thread(target=make_calls) for _ in range(3)]

        # Start all threads
        for t in threads:
            t.start()

        # Wait for completion
        for t in threads:
            t.join()

        # Total successful calls should be 15 (3 threads × 5 calls)
        total_calls = sum(call_counts)
        assert total_calls == 15

        # Should have recorded exactly 15 calls
        assert len(limiter._minute_calls) == 15

    def test_wait_time_calculation(self):
        """Test that wait time is calculated correctly."""
        limiter = RateLimiter(per_minute_limit=2)

        base_time = datetime.now()

        with patch("src.utils.rate_limiter.datetime") as mock_datetime:
            # First call
            mock_datetime.now.return_value = base_time
            limiter.check_and_record()

            # Second call 20 seconds later
            mock_datetime.now.return_value = base_time + timedelta(seconds=20)
            limiter.check_and_record()

            # Third call should fail and report correct wait time
            mock_datetime.now.return_value = base_time + timedelta(seconds=30)
            with pytest.raises(RateLimitExceededException) as exc_info:
                limiter.check_and_record()

            # Should wait ~30 seconds (60 - 30)
            assert 29 <= exc_info.value.wait_time <= 31

    def test_no_limit_enforcement_when_none_set(self):
        """Test that no limits are enforced when limits are None."""
        limiter = RateLimiter(per_minute_limit=None, per_hour_limit=None)

        # Should allow unlimited calls
        for _ in range(100):
            limiter.check_and_record()

        # No calls should be tracked
        assert len(limiter._minute_calls) == 0
        assert len(limiter._hour_calls) == 0
