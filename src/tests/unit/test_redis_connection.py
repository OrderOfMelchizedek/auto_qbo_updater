"""Unit tests for Redis connection."""
from unittest.mock import Mock, patch

import pytest

from src.utils.redis_client import RedisConnectionError, get_redis_client


def test_get_redis_client_returns_client():
    """Test that get_redis_client returns a Redis client."""
    # Reset the global client to None to force reconnection
    import src.utils.redis_client

    src.utils.redis_client._redis_client = None

    with patch("src.utils.redis_client.redis.from_url") as mock_from_url:
        mock_client = Mock()
        mock_client.ping.return_value = True  # Mock the ping method
        mock_from_url.return_value = mock_client

        client = get_redis_client()

        assert client == mock_client
        mock_from_url.assert_called_once()


def test_get_redis_client_handles_connection_error():
    """Test that get_redis_client handles connection errors gracefully."""
    # Reset the global client to None to force reconnection
    import src.utils.redis_client

    src.utils.redis_client._redis_client = None

    with patch("src.utils.redis_client.redis.from_url") as mock_from_url:
        mock_from_url.side_effect = Exception("Connection failed")

        with pytest.raises(RedisConnectionError) as exc_info:
            get_redis_client()

        assert "Failed to connect to Redis" in str(exc_info.value)
