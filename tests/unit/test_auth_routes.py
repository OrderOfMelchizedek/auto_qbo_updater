"""
Unit tests for auth blueprint routes with fixed imports and mocking.
"""

import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest


class TestAuthRoutes:
    """Test authentication routes."""

    def test_auth_status_authenticated(self, client, app, mock_qbo_service):
        """Test auth status when authenticated."""
        mock_qbo_service.access_token = "test-access-token"
        mock_qbo_service.environment = "sandbox"
        mock_qbo_service.get_token_info.return_value = {
            "is_valid": True,
            "expires_in_hours": 1.5,
            "realm_id": "test-realm-123",
            "expires_at": "2024-12-31T23:59:59",
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
        assert "tokenExpiry" in data  # This was missing in original test

    def test_auth_status_not_authenticated(self, client, mock_qbo_service):
        """Test auth status when not authenticated."""
        mock_qbo_service.access_token = None
        mock_qbo_service.environment = "sandbox"

        with patch("src.routes.auth.get_qbo_service", return_value=mock_qbo_service):
            response = client.get("/qbo/auth-status")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["authenticated"] is False
        assert data["company_id"] is None
        assert "tokenExpiry" not in data  # Fixed expectation

    def test_qbo_authorize_redirect(self, client, mock_qbo_service):
        """Test QBO authorization redirect."""
        mock_qbo_service.get_authorization_url.return_value = "https://test.intuit.com/auth"

        with patch("src.routes.auth.get_qbo_service", return_value=mock_qbo_service):
            response = client.get("/qbo/authorize")

        assert response.status_code == 302
        assert response.location == "https://test.intuit.com/auth"

    def test_qbo_callback_success(self, client, mock_qbo_service):
        """Test successful QBO callback."""
        mock_qbo_service.get_tokens.return_value = True
        mock_qbo_service.token_expires_at = 1234567890
        mock_qbo_service.access_token = "new-access-token"
        mock_qbo_service.refresh_token = "new-refresh-token"
        mock_qbo_service.realm_id = "company-456"
        mock_qbo_service.get_token_info.return_value = {
            "is_valid": True,
            "expires_in_hours": 1.0,
            "realm_id": "company-456",
            "expires_at": "2024-12-31T23:59:59",
        }

        with (
            patch("src.routes.auth.get_qbo_service", return_value=mock_qbo_service),
            patch("src.services.validation.log_audit_event") as mock_audit,
        ):

            response = client.get("/qbo/callback?code=auth-code-123&realmId=company-456")

            assert response.status_code == 302  # Redirect
            assert response.location == "/"

            # Verify audit log was called
            mock_audit.assert_called_once()

            # Verify session was updated
            with client.session_transaction() as sess:
                assert sess.get("qbo_authenticated") is True
                assert sess.get("qbo_company_id") == "company-456"

    def test_qbo_callback_missing_code(self, client):
        """Test QBO callback with missing authorization code."""
        response = client.get("/qbo/callback?realmId=company-456")

        assert response.status_code == 302
        assert "qbo_error=Missing" in response.location

    def test_qbo_callback_exchange_failure(self, client, mock_qbo_service):
        """Test QBO callback when token exchange fails."""
        mock_qbo_service.get_tokens.return_value = False

        with patch("src.routes.auth.get_qbo_service", return_value=mock_qbo_service):
            response = client.get("/qbo/callback?code=bad-code&realmId=company-456")

            assert response.status_code == 302
            assert "qbo_error=Failed" in response.location

    def test_disconnect_success(self, client, mock_qbo_service):
        """Test successful QBO disconnect."""
        mock_qbo_service.clear_tokens = Mock()

        with patch("src.routes.auth.get_qbo_service", return_value=mock_qbo_service):
            with client.session_transaction() as sess:
                sess["qbo_authenticated"] = True
                sess["qbo_company_id"] = "test-company"

            response = client.post("/qbo/disconnect", headers={"X-CSRFToken": "test-token"}, json={})

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True

            # Verify tokens were cleared
            mock_qbo_service.clear_tokens.assert_called_once()

            # Verify session was cleared
            with client.session_transaction() as sess:
                assert sess.get("qbo_authenticated") is False

    def test_disconnect_with_error(self, client, mock_qbo_service):
        """Test QBO disconnect with error during token clearing."""
        mock_qbo_service.clear_tokens.side_effect = Exception("Clear tokens error")

        with patch("src.routes.auth.get_qbo_service", return_value=mock_qbo_service):
            response = client.post("/qbo/disconnect", headers={"X-CSRFToken": "test-token"}, json={})

            # Should still succeed and clear session
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True
