"""Unit tests for authentication endpoints."""
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.app import app

client = TestClient(app)


def test_quickbooks_auth_redirect():
    """Test QuickBooks OAuth initiation endpoint."""
    with patch("src.api.endpoints.auth.qb_oauth.generate_auth_url") as mock_generate:
        mock_generate.return_value = "https://appcenter.intuit.com/connect/oauth2"

        response = client.get("/api/auth/quickbooks")

        assert response.status_code == 200
        assert "auth_url" in response.json()
        assert response.json()["auth_url"].startswith("https://")


def test_quickbooks_callback_success():
    """Test successful QuickBooks OAuth callback."""
    with patch("src.api.endpoints.auth.qb_oauth.handle_oauth_callback") as mock_handle:
        mock_handle.return_value = {
            "access_token": "qb_access_token",
            "refresh_token": "qb_refresh_token",
            "company_id": "123456789",
        }

        response = client.get("/api/auth/callback?code=test_code&state=test_state")

        assert response.status_code == 200
        assert "access_token" in response.json()
        assert "message" in response.json()
        assert response.json()["message"] == "Successfully connected to QuickBooks"


def test_quickbooks_callback_error():
    """Test QuickBooks OAuth callback with error."""
    response = client.get("/api/auth/callback?error=access_denied")

    assert response.status_code == 400
    assert "detail" in response.json()
    assert "access_denied" in response.json()["detail"]


def test_protected_endpoint_without_token():
    """Test accessing protected endpoint without token."""
    response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_protected_endpoint_with_valid_token():
    """Test accessing protected endpoint with valid token."""
    from src.services.auth.jwt_handler import create_access_token

    token = create_access_token({"sub": "user@example.com", "role": "admin"})

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["email"] == "user@example.com"
    assert response.json()["role"] == "admin"
