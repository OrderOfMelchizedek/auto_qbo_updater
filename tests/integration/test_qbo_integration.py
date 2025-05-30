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

    @patch("requests.request")
    def test_customer_search_with_caching(self, mock_request):
        """Test customer search with caching behavior."""

        def mock_response_func(method, url, **kwargs):
            # Mock API response for exact match
            mock_response = MagicMock()
            mock_response.status_code = 200
            # Check if this is an exact match query
            if "DisplayName%20%3D%20" in url:  # Exact match query
                mock_response.json.return_value = {
                    "QueryResponse": {
                        "Customer": [
                            {
                                "Id": "123",
                                "DisplayName": "John Smith",
                                "PrimaryEmailAddr": {"Address": "john@example.com"},
                            }
                        ]
                    }
                }
            else:
                mock_response.json.return_value = {"QueryResponse": {}}
            return mock_response

        mock_request.side_effect = mock_response_func

        # Set up authentication via auth service
        self.qbo_service.auth_service._access_token = "test-token"
        self.qbo_service.auth_service._realm_id = "test-realm"
        self.qbo_service.auth_service._token_expires_at = 9999999999  # Far future

        # First search should hit API
        customer1 = self.qbo_service.find_customer("John Smith")
        self.assertIsNotNone(customer1)
        self.assertEqual(customer1["DisplayName"], "John Smith")
        # Should make exactly 1 API call (exact match found)
        self.assertEqual(mock_request.call_count, 1)

        # Check cache state after first search
        cache_stats = self.qbo_service.get_customer_cache_stats()
        print(f"Cache stats after first search: {cache_stats}")
        print(f"Cache content: {self.qbo_service.customer_service._customer_cache}")

        # Second search should use cache (with new caching implementation)
        customer2 = self.qbo_service.find_customer("John Smith")
        self.assertEqual(customer2["DisplayName"], "John Smith")
        # Cache is used, so no additional API call
        print(f"API call count after second search: {mock_request.call_count}")
        self.assertEqual(mock_request.call_count, 1)

        # Clear the cache to test without cache
        self.qbo_service.clear_customer_cache()

        # Third search should hit API again
        customer3 = self.qbo_service.find_customer("John Smith")
        self.assertEqual(customer3["DisplayName"], "John Smith")
        self.assertEqual(mock_request.call_count, 2)

    @patch("requests.request")
    def test_create_sales_receipt_with_customer_lookup(self, mock_request):
        """Test creating a sales receipt with customer lookup."""
        # Mock responses for both customer search and sales receipt creation
        customer_response = MagicMock()
        customer_response.status_code = 200
        customer_response.json.return_value = {
            "QueryResponse": {"Customer": [{"Id": "456", "DisplayName": "Jane Doe"}]}
        }

        receipt_response = MagicMock()
        receipt_response.status_code = 200
        receipt_response.json.return_value = {"SalesReceipt": {"Id": "789", "DocNumber": "SR-001", "TotalAmt": 100.00}}

        # Return customer response for GET, receipt response for POST
        def side_effect(method, *args, **kwargs):
            if method == "GET":
                return customer_response
            else:
                return receipt_response

        mock_request.side_effect = side_effect

        # Set up authentication via auth service
        self.qbo_service.auth_service._access_token = "test-token"
        self.qbo_service.auth_service._realm_id = "test-realm"
        self.qbo_service.auth_service._token_expires_at = 9999999999

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
        # Set up expired token via auth service
        self.qbo_service.auth_service._access_token = "expired-token"
        self.qbo_service.auth_service._refresh_token = "refresh-token"
        self.qbo_service.auth_service._realm_id = "test-realm"
        self.qbo_service.auth_service._token_expires_at = 1  # Expired

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
        headers = self.qbo_service.auth_service.get_auth_headers()

        # Verify token was refreshed
        self.assertEqual(self.qbo_service.auth_service.access_token, "new-access-token")
        self.assertEqual(headers["Authorization"], "Bearer new-access-token")

    @patch("requests.request")
    def test_batch_customer_lookup(self, mock_request):
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

        mock_request.side_effect = mock_responses

        # Set up authentication via auth service
        self.qbo_service.auth_service._access_token = "test-token"
        self.qbo_service.auth_service._realm_id = "test-realm"
        self.qbo_service.auth_service._token_expires_at = 9999999999

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
