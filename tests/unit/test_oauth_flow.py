"""
Unit tests for OAuth authentication flow for QuickBooks Online.
"""

import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest


class TestOAuthFlow:
    """Test OAuth authentication flow for QuickBooks Online."""

    def test_qbo_status_unauthenticated(self, client, app, mock_qbo_service):
        """Test QBO status endpoint when not authenticated."""
        mock_qbo_service.is_token_valid.return_value = False
        mock_qbo_service.environment = "sandbox"

        # Set the mock on the app
        app.qbo_service = mock_qbo_service

        response = client.get("/qbo/status")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["authenticated"] is False
        assert data["environment"] == "sandbox"

    def test_qbo_status_authenticated(self, client, app, mock_qbo_service):
        """Test QBO status endpoint when authenticated."""
        mock_qbo_service.is_token_valid.return_value = True
        mock_qbo_service.environment = "sandbox"
        mock_qbo_service.get_company_info.return_value = {
            "CompanyName": "Test Company",
            "Id": "123456789",
        }

        # Set the mock on the app
        app.qbo_service = mock_qbo_service

        response = client.get("/qbo/status")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["authenticated"] is True
        assert data["environment"] == "sandbox"
        assert "company" in data
        assert data["company"]["name"] == "Test Company"
        assert data["company"]["id"] == "123456789"

    def test_qbo_auth_status_unauthenticated(self, client, app, mock_qbo_service):
        """Test QBO auth status endpoint when not authenticated."""
        mock_qbo_service.access_token = None
        mock_qbo_service.environment = "sandbox"

        # Set the mock on the app
        app.qbo_service = mock_qbo_service

        response = client.get("/qbo/auth-status")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["authenticated"] is False
        assert data.get("company_id") is None
        assert data["environment"] == "sandbox"

    def test_qbo_auth_status_authenticated(self, client, app, mock_qbo_service):
        """Test QBO auth status endpoint when authenticated."""
        mock_qbo_service.access_token = "test-access-token"
        mock_qbo_service.environment = "sandbox"
        mock_qbo_service.get_token_info.return_value = {
            "is_valid": True,
            "expires_in_seconds": 3600,
        }

        # Set the mock on the app
        app.qbo_service = mock_qbo_service

        with client.session_transaction() as sess:
            sess["qbo_authenticated"] = True
            sess["qbo_company_id"] = "test-company-123"
            sess["qbo_token_expires_at"] = "2024-12-31T23:59:59"

        response = client.get("/qbo/auth-status")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["authenticated"] is True
        assert data["company_id"] == "test-company-123"
        assert data["environment"] == "sandbox"
        assert data["token_valid"] is True
        assert data["token_expires_in"] == 3600

    def test_qbo_authorize_redirect(self, client, app, mock_qbo_service):
        """Test OAuth authorization redirect."""
        mock_auth_url = "https://appcenter.intuit.com/connect/oauth2?client_id=test"
        mock_qbo_service.get_authorization_url.return_value = mock_auth_url

        # Set the mock on the app
        app.qbo_service = mock_qbo_service

        response = client.get("/qbo/authorize")

        assert response.status_code == 302
        assert response.location == mock_auth_url

    def test_qbo_callback_missing_parameters(self, client, app, mock_qbo_service):
        """Test OAuth callback with missing parameters."""
        # Set the mock on the app
        app.qbo_service = mock_qbo_service

        response = client.get("/qbo/callback")

        assert response.status_code == 302  # Redirect to index
        assert "/" in response.location
        assert "qbo_error" in response.location

    def test_qbo_callback_with_error(self, client, app, mock_qbo_service):
        """Test OAuth callback with error parameter."""
        # Set the mock on the app
        app.qbo_service = mock_qbo_service

        response = client.get("/qbo/callback?error=access_denied&error_description=User+denied+access")

        assert response.status_code == 302  # Redirect to index
        assert "/" in response.location

    def test_qbo_callback_success(self, client, app, mock_qbo_service):
        """Test successful OAuth callback."""
        mock_qbo_service.get_tokens.return_value = True
        mock_qbo_service.token_expires_at = 1234567890
        mock_qbo_service.realm_id = "test-realm-123"

        # Set the mock on the app
        app.qbo_service = mock_qbo_service

        with patch("src.services.validation.log_audit_event"):
            response = client.get("/qbo/callback?code=test_code&realmId=test_realm")

        # Should redirect to index after successful auth
        assert response.status_code == 302
        assert "/" in response.location

        # Verify get_tokens was called with correct parameters
        mock_qbo_service.get_tokens.assert_called_once_with("test_code", "test_realm")

        # Verify session was updated
        with client.session_transaction() as sess:
            assert sess.get("qbo_authenticated") is True
            assert sess.get("qbo_company_id") == "test_realm"

    def test_qbo_callback_token_exchange_failure(self, client, app, mock_qbo_service):
        """Test OAuth callback when token exchange fails."""
        mock_qbo_service.get_tokens.return_value = False

        # Set the mock on the app
        app.qbo_service = mock_qbo_service

        response = client.get("/qbo/callback?code=bad_code&realmId=test_realm")

        assert response.status_code == 302
        assert "qbo_error=Failed" in response.location

    def test_qbo_disconnect(self, client, app, mock_qbo_service):
        """Test QBO disconnect."""
        mock_qbo_service.redis_client = None  # Simulate no Redis

        # Set the mock on the app
        app.qbo_service = mock_qbo_service

        with client.session_transaction() as sess:
            sess["qbo_authenticated"] = True
            sess["qbo_company_id"] = "test_realm"

        response = client.post("/qbo/disconnect", headers={"Content-Type": "application/json"}, data=json.dumps({}))

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True

        # Verify session was cleared
        with client.session_transaction() as sess:
            assert sess.get("qbo_authenticated", False) is False

    def test_qbo_disconnect_with_redis(self, client, app, mock_qbo_service):
        """Test QBO disconnect with Redis token clearing."""
        mock_redis = Mock()
        mock_qbo_service.redis_client = mock_redis
        mock_qbo_service.clear_tokens = Mock()

        # Set the mock on the app
        app.qbo_service = mock_qbo_service

        with client.session_transaction() as sess:
            sess["qbo_authenticated"] = True
            sess["qbo_company_id"] = "test_realm"

        response = client.post("/qbo/disconnect", headers={"Content-Type": "application/json"}, data=json.dumps({}))

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True

        # Verify Redis tokens were cleared
        mock_qbo_service.clear_tokens.assert_called_once()

        # Verify session was cleared
        with client.session_transaction() as sess:
            assert sess.get("qbo_authenticated", False) is False
