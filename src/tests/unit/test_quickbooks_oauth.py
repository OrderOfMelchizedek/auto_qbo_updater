"""Unit tests for QuickBooks OAuth service."""
from unittest.mock import Mock, patch

import pytest

from src.services.auth.quickbooks_oauth import QuickBooksAuthError, QuickBooksOAuth


@pytest.fixture
def qb_oauth():
    """Create QuickBooks OAuth instance for testing."""
    return QuickBooksOAuth(
        client_id="test_client_id",
        client_secret="test_client_secret",
        redirect_uri="http://localhost:8000/callback",
        environment="sandbox",
    )


def test_quickbooks_oauth_initialization(qb_oauth):
    """Test QuickBooks OAuth initialization."""
    assert qb_oauth.client_id == "test_client_id"
    assert qb_oauth.client_secret == "test_client_secret"
    assert qb_oauth.redirect_uri == "http://localhost:8000/callback"
    assert qb_oauth.environment == "sandbox"
    assert "sandbox" in qb_oauth.discovery_document_url


def test_generate_auth_url(qb_oauth):
    """Test generating QuickBooks auth URL."""
    with patch.object(qb_oauth, "_generate_state") as mock_state:
        mock_state.return_value = "test_state_123"

        auth_url = qb_oauth.generate_auth_url()

        assert auth_url is not None
        assert "https://appcenter.intuit.com/connect/oauth2" in auth_url
        assert "client_id=test_client_id" in auth_url
        assert "redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fcallback" in auth_url
        assert "state=test_state_123" in auth_url
        assert "scope=com.intuit.quickbooks.accounting" in auth_url


def test_handle_oauth_callback_success(qb_oauth):
    """Test successful OAuth callback handling."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "access_token": "access_123",
        "refresh_token": "refresh_123",
        "expires_in": 3600,
        "x_refresh_token_expires_in": 8726400,
    }

    with (
        patch("requests.post", return_value=mock_response) as mock_post,
        patch.object(qb_oauth, "_verify_state") as mock_verify,
        patch.object(qb_oauth, "redis_client") as mock_redis,
    ):
        mock_verify.return_value = True
        mock_redis.setex = Mock()

        result = qb_oauth.handle_oauth_callback("auth_code_123", "test_state")

        assert result["access_token"] == "access_123"
        assert result["refresh_token"] == "refresh_123"
        assert "company_id" in result

        # Verify token exchange was called
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "auth_code_123" in str(call_args)


def test_handle_oauth_callback_invalid_state(qb_oauth):
    """Test OAuth callback with invalid state."""
    with patch.object(qb_oauth, "_verify_state") as mock_verify:
        mock_verify.return_value = False

        with pytest.raises(QuickBooksAuthError) as exc_info:
            qb_oauth.handle_oauth_callback("auth_code", "invalid_state")

        assert "Invalid state parameter" in str(exc_info.value)


def test_handle_oauth_callback_token_exchange_failure(qb_oauth):
    """Test OAuth callback when token exchange fails."""
    mock_response = Mock()
    mock_response.status_code = 400
    mock_response.text = "Invalid authorization code"

    with (
        patch("requests.post", return_value=mock_response),
        patch.object(qb_oauth, "_verify_state", return_value=True),
    ):
        with pytest.raises(QuickBooksAuthError) as exc_info:
            qb_oauth.handle_oauth_callback("invalid_code", "test_state")

        assert "Token exchange failed" in str(exc_info.value)


def test_refresh_access_token_success(qb_oauth):
    """Test successful access token refresh."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "access_token": "new_access_123",
        "refresh_token": "new_refresh_123",
        "expires_in": 3600,
    }

    with patch("requests.post", return_value=mock_response):
        result = qb_oauth.refresh_access_token("old_refresh_token")

        assert result["access_token"] == "new_access_123"
        assert result["refresh_token"] == "new_refresh_123"
