"""Integration tests for QuickBooks Online service."""

import os
import sys
import unittest
from unittest.mock import MagicMock, call, patch

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from utils.qbo_service import QBOService


class TestQBOIntegration(unittest.TestCase):
    """Test QBO service integration scenarios."""

    def setUp(self):
        """Set up test environment."""
        # Mock environment variables
        self.env_patcher = patch.dict(
            os.environ,
            {
                "QBO_CLIENT_ID": "test-client-id",
                "QBO_CLIENT_SECRET": "test-client-secret",
                "QBO_REDIRECT_URI": "http://localhost/callback",
                "QBO_ENVIRONMENT": "sandbox",
            },
        )
        self.env_patcher.start()

        # Create QBO service instance
        self.qbo_service = QBOService(
            client_id="test-client-id",
            client_secret="test-client-secret",
            redirect_uri="http://localhost/callback",
            environment="sandbox",
        )

    def tearDown(self):
        """Clean up patches."""
        self.env_patcher.stop()

    @patch("requests.get")
    def test_customer_search_with_caching(self, mock_get):
        """Test customer search with caching behavior."""
        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "QueryResponse": {
                "Customer": [
                    {"Id": "123", "DisplayName": "John Smith", "PrimaryEmailAddr": {"Address": "john@example.com"}}
                ]
            }
        }
        mock_get.return_value = mock_response

        # Set up authentication
        self.qbo_service.access_token = "test-token"
        self.qbo_service.realm_id = "test-realm"

        # First search should hit API
        customer1 = self.qbo_service.find_customer("John Smith")
        self.assertIsNotNone(customer1)
        self.assertEqual(customer1["DisplayName"], "John Smith")
        self.assertEqual(mock_get.call_count, 1)

        # Second search should use cache
        customer2 = self.qbo_service.find_customer("John Smith")
        self.assertEqual(customer2["DisplayName"], "John Smith")
        self.assertEqual(mock_get.call_count, 1)  # No additional API call

    @patch("requests.post")
    @patch("requests.get")
    def test_create_sales_receipt_with_customer_lookup(self, mock_get, mock_post):
        """Test creating a sales receipt with customer lookup."""
        # Mock customer search
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "QueryResponse": {"Customer": [{"Id": "456", "DisplayName": "Jane Doe"}]}
        }
        mock_get.return_value = mock_get_response

        # Mock sales receipt creation
        mock_post_response = MagicMock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {
            "SalesReceipt": {"Id": "789", "DocNumber": "SR-001", "TotalAmt": 100.00}
        }
        mock_post.return_value = mock_post_response

        # Set up authentication
        self.qbo_service.access_token = "test-token"
        self.qbo_service.realm_id = "test-realm"

        # Find customer first
        customer = self.qbo_service.find_customer("Jane Doe")
        self.assertIsNotNone(customer)

        # Create sales receipt
        receipt_data = {
            "CustomerRef": {"value": customer["Id"]},
            "Line": [
                {
                    "Amount": 100.00,
                    "DetailType": "SalesItemLineDetail",
                    "SalesItemLineDetail": {"ItemRef": {"value": "1"}},
                }
            ],
        }

        result = self.qbo_service.create_sales_receipt(receipt_data)
        self.assertIsNotNone(result)
        self.assertEqual(result["DocNumber"], "SR-001")

    @patch("requests.post")
    def test_token_refresh_on_expiry(self, mock_post):
        """Test automatic token refresh when expired."""
        # Set up expired token
        self.qbo_service.access_token = "expired-token"
        self.qbo_service.refresh_token = "refresh-token"
        self.qbo_service.token_expires_at = 1  # Expired

        # Mock token refresh response
        mock_refresh_response = MagicMock()
        mock_refresh_response.status_code = 200
        mock_refresh_response.json.return_value = {
            "access_token": "new-access-token",
            "refresh_token": "new-refresh-token",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_refresh_response

        # Call a method that requires authentication
        headers = self.qbo_service._get_auth_headers()

        # Verify token was refreshed
        self.assertEqual(self.qbo_service.access_token, "new-access-token")
        self.assertEqual(headers["Authorization"], "Bearer new-access-token")

    @patch("requests.get")
    def test_batch_customer_lookup(self, mock_get):
        """Test batch customer lookup functionality."""
        # Mock multiple customer responses
        customers = [
            {"Id": "1", "DisplayName": "Customer 1"},
            {"Id": "2", "DisplayName": "Customer 2"},
            {"Id": "3", "DisplayName": "Customer 3"},
        ]

        mock_responses = []
        for customer in customers:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"QueryResponse": {"Customer": [customer]}}
            mock_responses.append(mock_response)

        mock_get.side_effect = mock_responses

        # Set up authentication
        self.qbo_service.access_token = "test-token"
        self.qbo_service.realm_id = "test-realm"

        # Batch lookup
        customer_names = ["Customer 1", "Customer 2", "Customer 3"]
        results = self.qbo_service.find_customers_batch(customer_names)

        # Verify all customers found
        self.assertEqual(len(results), 3)
        for name in customer_names:
            self.assertIn(name, results)
            self.assertIsNotNone(results[name])


if __name__ == "__main__":
    unittest.main()
