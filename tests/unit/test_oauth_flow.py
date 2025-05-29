import json
import os
import sys
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from src.app import app
from src.utils.qbo_service import QBOService


class TestOAuthFlow(unittest.TestCase):
    """Test OAuth authentication flow for QuickBooks Online."""

    def setUp(self):
        """Set up test environment."""
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["WTF_CSRF_ENABLED"] = False  # Disable CSRF for testing
        self.client = self.app.test_client()

        # Mock environment variables
        self.env_patcher = patch.dict(
            os.environ,
            {
                "QBO_CLIENT_ID": "test_client_id",
                "QBO_CLIENT_SECRET": "test_client_secret",
                "QBO_REDIRECT_URI": "http://localhost:5000/qbo/callback",
                "FLASK_SECRET_KEY": "test_secret_key_for_testing_only_32chars",
                "GEMINI_API_KEY": "test_gemini_key",
            },
        )
        self.env_patcher.start()

    def tearDown(self):
        """Clean up after tests."""
        self.env_patcher.stop()

    def test_qbo_status_unauthenticated(self):
        """Test QBO status endpoint when not authenticated."""
        response = self.client.get("/qbo/status")

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertFalse(data["authenticated"])
        self.assertIsNone(data.get("realmId"))
        # tokenExpiry might not be in response when not authenticated
        self.assertIn("environment", data)

    def test_qbo_auth_status_unauthenticated(self):
        """Test QBO auth status endpoint when not authenticated."""
        response = self.client.get("/qbo/auth-status")

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertFalse(data["authenticated"])
        self.assertIsNone(data.get("company_id"))
        self.assertIn("environment", data)

    def test_qbo_authorize_redirect(self):
        """Test OAuth authorization redirect."""
        mock_auth_url = "https://appcenter.intuit.com/connect/oauth2?client_id=test"

        with patch.object(app.qbo_service, "get_authorization_url", return_value=mock_auth_url):
            response = self.client.get("/qbo/authorize")

            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, mock_auth_url)

    def test_qbo_callback_missing_parameters(self):
        """Test OAuth callback with missing parameters."""
        response = self.client.get("/qbo/callback")

        self.assertEqual(response.status_code, 302)  # Redirect to index
        # Should redirect to index page with error
        self.assertIn("/", response.location)
        self.assertIn("qbo_error", response.location)

    def test_qbo_callback_with_error(self):
        """Test OAuth callback with error parameter."""
        response = self.client.get("/qbo/callback?error=access_denied&error_description=User+denied+access")

        self.assertEqual(response.status_code, 302)  # Redirect to index
        self.assertIn("/", response.location)

    def test_qbo_callback_success(self):
        """Test successful OAuth callback."""
        with (
            patch.object(app.qbo_service, "get_tokens", return_value=True) as mock_get_tokens,
            patch.object(
                app.qbo_service,
                "get_all_customers",
                return_value=[
                    {"Id": "1", "DisplayName": "Test Customer 1"},
                    {"Id": "2", "DisplayName": "Test Customer 2"},
                ],
            ) as mock_get_customers,
            patch("src.services.validation.log_audit_event"),
        ):

            # Set token info on the service
            app.qbo_service.token_expires_at = 1234567890
            app.qbo_service.realm_id = "test-realm-123"

            response = self.client.get("/qbo/callback?code=test_code&realmId=test_realm")

            # Should redirect to index after successful auth
            self.assertEqual(response.status_code, 302)
            self.assertIn("/", response.location)

            # Verify get_tokens was called with correct parameters
            mock_get_tokens.assert_called_once_with("test_code", "test_realm")

            # Verify session was updated
            with self.client.session_transaction() as sess:
                self.assertTrue(sess.get("qbo_authenticated"))
                self.assertEqual(sess.get("qbo_company_id"), "test_realm")

    def test_qbo_callback_token_exchange_failure(self):
        """Test OAuth callback when token exchange fails."""
        with patch.object(app.qbo_service, "get_tokens", return_value=False):
            response = self.client.get("/qbo/callback?code=bad_code&realmId=test_realm")

            self.assertEqual(response.status_code, 302)
            self.assertIn("qbo_error=Failed", response.location)

    def test_qbo_disconnect(self):
        """Test QBO disconnect."""
        with self.client.session_transaction() as sess:
            sess["qbo_authenticated"] = True
            sess["qbo_company_id"] = "test_realm"

        with patch.object(app.qbo_service, "clear_tokens"):
            response = self.client.post("/qbo/disconnect", headers={"X-CSRFToken": "test-token"}, json={})

            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertTrue(data["success"])

            # Verify session was cleared
            with self.client.session_transaction() as sess:
                self.assertFalse(sess.get("qbo_authenticated", False))


if __name__ == "__main__":
    unittest.main()
