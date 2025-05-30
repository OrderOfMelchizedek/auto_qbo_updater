"""
Unit tests for QBO Auth Service module.
"""

import time
from datetime import datetime
from unittest.mock import Mock, patch

import pytest
import redis
import requests

from src.utils.exceptions import QBOAPIException
from src.utils.qbo_service.auth import QBOAuthService


class TestQBOAuthService:
    """Test the QBO authentication service."""

    @pytest.fixture
    def auth_service(self):
        """Create an auth service instance."""
        return QBOAuthService(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="http://localhost/callback",
            environment="sandbox",
        )

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        mock = Mock(spec=redis.Redis)
        return mock

    @pytest.fixture
    def auth_service_with_redis(self, mock_redis):
        """Create an auth service with Redis client."""
        return QBOAuthService(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="http://localhost/callback",
            environment="sandbox",
            redis_client=mock_redis,
        )

    def test_init_sandbox_environment(self):
        """Test initialization with sandbox environment."""
        service = QBOAuthService(
            client_id="test",
            client_secret="secret",
            redirect_uri="http://test",
            environment="sandbox",
        )

        assert service.environment == "sandbox"
        assert "sandbox-quickbooks" in service.api_base
        assert service.auth_endpoint == "https://appcenter.intuit.com/connect/oauth2"

    def test_init_production_environment(self):
        """Test initialization with production environment."""
        service = QBOAuthService(
            client_id="test",
            client_secret="secret",
            redirect_uri="http://test",
            environment="production",
        )

        assert service.environment == "production"
        assert "sandbox" not in service.api_base
        assert "quickbooks.api.intuit.com" in service.api_base

    def test_init_invalid_environment(self):
        """Test initialization with invalid environment."""
        with pytest.raises(ValueError, match="Environment must be 'sandbox' or 'production'"):
            QBOAuthService(
                client_id="test",
                client_secret="secret",
                redirect_uri="http://test",
                environment="invalid",
            )

    def test_get_authorization_url(self, auth_service):
        """Test authorization URL generation."""
        url = auth_service.get_authorization_url()

        assert auth_service.auth_endpoint in url
        assert "client_id=test_client_id" in url
        assert "response_type=code" in url
        assert "scope=com.intuit.quickbooks.accounting" in url
        assert "redirect_uri=http%3A%2F%2Flocalhost%2Fcallback" in url
        assert "state=" in url  # Should have a state parameter

    def test_is_token_valid_no_token(self, auth_service):
        """Test token validity when no token exists."""
        assert auth_service.is_token_valid() is False

    def test_is_token_valid_expired(self, auth_service):
        """Test token validity when token is expired."""
        auth_service._access_token = "test_token"
        auth_service._token_expires_at = int(time.time()) - 100  # Expired 100 seconds ago

        assert auth_service.is_token_valid() is False

    def test_is_token_valid_not_expired(self, auth_service):
        """Test token validity when token is valid."""
        auth_service._access_token = "test_token"
        auth_service._token_expires_at = int(time.time()) + 1000  # Expires in 1000 seconds

        assert auth_service.is_token_valid() is True

    def test_is_token_valid_near_expiry(self, auth_service):
        """Test token validity when token is near expiry (within 60 second buffer)."""
        auth_service._access_token = "test_token"
        auth_service._token_expires_at = int(time.time()) + 30  # Expires in 30 seconds

        assert auth_service.is_token_valid() is False  # Should be false due to 60 second buffer

    @patch("requests.post")
    def test_get_tokens_success(self, mock_post, auth_service):
        """Test successful token exchange."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_response

        result = auth_service.get_tokens("auth_code_123", "realm_123")

        assert result is True
        assert auth_service.access_token == "new_access_token"
        assert auth_service.refresh_token == "new_refresh_token"
        assert auth_service.realm_id == "realm_123"
        assert auth_service.token_expires_at > int(time.time())

    @patch("requests.post")
    def test_get_tokens_failure(self, mock_post, auth_service):
        """Test failed token exchange."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Invalid authorization code"
        mock_post.return_value = mock_response

        result = auth_service.get_tokens("bad_code", "realm_123")

        assert result is False
        assert auth_service.access_token is None

    @patch("requests.post")
    def test_get_tokens_network_error(self, mock_post, auth_service):
        """Test token exchange with network error."""
        mock_post.side_effect = requests.RequestException("Network error")

        with pytest.raises(QBOAPIException) as exc_info:
            auth_service.get_tokens("auth_code", "realm_123")

        assert "Network error" in str(exc_info.value)
        assert exc_info.value.user_message == "Unable to connect to QuickBooks. Please check your internet connection."

    @patch("requests.post")
    def test_refresh_access_token_success(self, mock_post, auth_service):
        """Test successful token refresh."""
        # Set up existing tokens
        auth_service._refresh_token = "existing_refresh_token"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "refreshed_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_response

        result = auth_service.refresh_access_token()

        assert result is True
        assert auth_service.access_token == "refreshed_access_token"
        assert auth_service.refresh_token == "new_refresh_token"

    def test_refresh_access_token_no_refresh_token(self, auth_service):
        """Test refresh when no refresh token exists."""
        auth_service._refresh_token = None

        result = auth_service.refresh_access_token()

        assert result is False

    @patch("requests.post")
    def test_refresh_access_token_failure(self, mock_post, auth_service):
        """Test failed token refresh."""
        auth_service._refresh_token = "existing_refresh_token"

        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Invalid refresh token"
        mock_post.return_value = mock_response

        result = auth_service.refresh_access_token()

        assert result is False

    def test_get_token_info(self, auth_service):
        """Test getting token information."""
        auth_service._access_token = "test_token"
        auth_service._realm_id = "test_realm"
        auth_service._token_expires_at = int(time.time()) + 3600

        info = auth_service.get_token_info()

        assert info is not None
        assert info["realm_id"] == "test_realm"
        assert info["is_valid"] is True
        assert "expires_at" in info
        assert "expires_in_hours" in info

    def test_get_token_info_no_token(self, auth_service):
        """Test getting token info when no token exists."""
        info = auth_service.get_token_info()
        assert info is None

    def test_token_property_setters(self, auth_service):
        """Test token property setters."""
        auth_service.access_token = "test_access"
        auth_service.refresh_token = "test_refresh"
        auth_service.realm_id = "test_realm"
        auth_service.token_expires_at = 1234567890

        assert auth_service.access_token == "test_access"
        assert auth_service.refresh_token == "test_refresh"
        assert auth_service.realm_id == "test_realm"
        assert auth_service.token_expires_at == 1234567890

    def test_clear_tokens(self, auth_service):
        """Test clearing all tokens."""
        # Set some tokens
        auth_service._access_token = "test"
        auth_service._refresh_token = "test"
        auth_service._realm_id = "test"
        auth_service._token_expires_at = 123

        # Clear them
        auth_service.clear_tokens()

        assert auth_service._access_token is None
        assert auth_service._refresh_token is None
        assert auth_service._realm_id is None
        assert auth_service._token_expires_at == 0

    def test_get_auth_headers_valid_token(self, auth_service):
        """Test getting auth headers with valid token."""
        auth_service._access_token = "test_token"
        auth_service._token_expires_at = int(time.time()) + 3600

        headers = auth_service.get_auth_headers()

        assert headers["Authorization"] == "Bearer test_token"
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"

    def test_get_auth_headers_no_token(self, auth_service):
        """Test getting auth headers with no token."""
        with pytest.raises(QBOAPIException) as exc_info:
            auth_service.get_auth_headers()

        assert exc_info.value.user_message == "Please connect to QuickBooks first."

    @patch("requests.post")
    def test_get_auth_headers_expired_token_refresh_success(self, mock_post, auth_service):
        """Test getting auth headers refreshes expired token."""
        # Set expired token
        auth_service._access_token = "expired_token"
        auth_service._refresh_token = "refresh_token"
        auth_service._token_expires_at = int(time.time()) - 100  # Expired

        # Mock successful refresh
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_token",
            "refresh_token": "new_refresh",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_response

        headers = auth_service.get_auth_headers()

        assert headers["Authorization"] == "Bearer new_token"
        assert auth_service.access_token == "new_token"

    @patch("requests.post")
    def test_get_auth_headers_expired_token_refresh_failure(self, mock_post, auth_service):
        """Test getting auth headers when refresh fails."""
        # Set expired token
        auth_service._access_token = "expired_token"
        auth_service._refresh_token = "refresh_token"
        auth_service._token_expires_at = int(time.time()) - 100  # Expired

        # Mock failed refresh
        mock_response = Mock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response

        with pytest.raises(QBOAPIException) as exc_info:
            auth_service.get_auth_headers()

        assert "authentication expired" in exc_info.value.user_message

    def test_redis_token_save(self, auth_service_with_redis):
        """Test saving tokens to Redis."""
        mock_redis = auth_service_with_redis.redis_client

        auth_service_with_redis.access_token = "test_access"

        mock_redis.setex.assert_called_with(
            "qbo_tokens:sandbox:access_token", 90 * 24 * 60 * 60, "test_access"  # 90 days
        )

    def test_redis_token_load(self, mock_redis):
        """Test loading tokens from Redis."""
        # Set up mock Redis responses
        mock_redis.get.side_effect = lambda key: {
            "qbo_tokens:sandbox:access_token": b"stored_access_token",
            "qbo_tokens:sandbox:refresh_token": b"stored_refresh_token",
            "qbo_tokens:sandbox:realm_id": b"stored_realm_id",
            "qbo_tokens:sandbox:token_expires_at": b"1234567890",
        }.get(key)

        # Create service with mocked Redis
        service = QBOAuthService(
            client_id="test",
            client_secret="secret",
            redirect_uri="http://test",
            environment="sandbox",
            redis_client=mock_redis,
        )

        assert service.access_token == "stored_access_token"
        assert service.refresh_token == "stored_refresh_token"
        assert service.realm_id == "stored_realm_id"
        assert service.token_expires_at == 1234567890

    def test_redis_clear_tokens(self, auth_service_with_redis):
        """Test clearing tokens from Redis."""
        mock_redis = auth_service_with_redis.redis_client

        auth_service_with_redis.clear_tokens()

        # Should delete all token keys
        expected_calls = [
            "qbo_tokens:sandbox:access_token",
            "qbo_tokens:sandbox:refresh_token",
            "qbo_tokens:sandbox:realm_id",
            "qbo_tokens:sandbox:token_expires_at",
        ]

        for key in expected_calls:
            mock_redis.delete.assert_any_call(key)

    def test_refresh_tokens_alias(self, auth_service):
        """Test that refresh_tokens is an alias for refresh_access_token."""
        auth_service._refresh_token = None

        # Both should return the same result
        assert auth_service.refresh_tokens() == auth_service.refresh_access_token()
        assert auth_service.refresh_tokens() is False
