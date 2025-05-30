"""Integration tests for the modularized QBO service structure."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from utils.qbo_service import QBOService
from utils.qbo_service.auth import QBOAuthService
from utils.qbo_service.customers import QBOCustomerService
from utils.qbo_service.entities import QBOEntityService
from utils.qbo_service.sales_receipts import QBOSalesReceiptService


class TestQBOModularIntegration(unittest.TestCase):
    """Test integration scenarios with the modular QBO service structure."""

    def setUp(self):
        """Set up test environment."""
        # Create QBO service instance
        self.qbo_service = QBOService(
            client_id="test-client-id",
            client_secret="test-client-secret",
            redirect_uri="http://localhost/callback",
            environment="sandbox",
        )

    def test_service_initialization_and_delegation(self):
        """Test that all services are properly initialized and connected."""
        # Verify auth service is initialized
        self.assertIsInstance(self.qbo_service.auth_service, QBOAuthService)

        # Verify all sub-services are initialized
        self.assertIsInstance(self.qbo_service.customer_service, QBOCustomerService)
        self.assertIsInstance(self.qbo_service.sales_receipt_service, QBOSalesReceiptService)
        self.assertIsInstance(self.qbo_service.entity_service, QBOEntityService)

        # Verify all services share the same auth service
        self.assertIs(self.qbo_service.customer_service.auth_service, self.qbo_service.auth_service)
        self.assertIs(self.qbo_service.sales_receipt_service.auth_service, self.qbo_service.auth_service)
        self.assertIs(self.qbo_service.entity_service.auth_service, self.qbo_service.auth_service)

    @patch("requests.post")
    def test_auth_token_refresh_propagates_to_all_services(self, mock_post):
        """Test that token refresh in auth service is available to all sub-services."""
        # Set up initial token
        self.qbo_service.auth_service._access_token = "old-token"
        self.qbo_service.auth_service._refresh_token = "refresh-token"
        self.qbo_service.auth_service._realm_id = "test-realm"
        self.qbo_service.auth_service._token_expires_at = 1  # Expired

        # Mock token refresh response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new-token",
            "refresh_token": "new-refresh-token",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_response

        # Refresh token
        result = self.qbo_service.refresh_access_token()
        self.assertTrue(result)

        # Verify new token is available to all services
        self.assertEqual(self.qbo_service.auth_service.access_token, "new-token")

        # Get auth headers from each service's perspective
        customer_headers = self.qbo_service.customer_service.auth_service.get_auth_headers()
        self.assertEqual(customer_headers["Authorization"], "Bearer new-token")

        sales_headers = self.qbo_service.sales_receipt_service.auth_service.get_auth_headers()
        self.assertEqual(sales_headers["Authorization"], "Bearer new-token")

    @patch("requests.request")
    def test_customer_cache_shared_within_service(self, mock_request):
        """Test that customer cache is properly shared within the customer service."""
        # Set up authentication
        self.qbo_service.auth_service._access_token = "test-token"
        self.qbo_service.auth_service._realm_id = "test-realm"
        self.qbo_service.auth_service._token_expires_at = 9999999999

        # Mock customer response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "QueryResponse": {"Customer": [{"Id": "123", "DisplayName": "Test Customer"}]}
        }
        mock_request.return_value = mock_response

        # Find customer (should cache it)
        customer1 = self.qbo_service.find_customer("Test Customer")
        self.assertIsNotNone(customer1)
        self.assertEqual(mock_request.call_count, 1)

        # Get cache stats
        stats = self.qbo_service.get_customer_cache_stats()
        self.assertEqual(stats["cache_size"], 1)
        self.assertTrue(stats["cache_valid"])

        # Find same customer again (should use cache)
        customer2 = self.qbo_service.find_customer("Test Customer")
        self.assertIsNotNone(customer2)
        self.assertEqual(customer1, customer2)
        self.assertEqual(mock_request.call_count, 1)  # No additional API call

    @patch("requests.request")
    def test_cross_service_operation_create_receipt_with_customer(self, mock_request):
        """Test creating a sales receipt that requires customer lookup."""
        # Set up authentication
        self.qbo_service.auth_service._access_token = "test-token"
        self.qbo_service.auth_service._realm_id = "test-realm"
        self.qbo_service.auth_service._token_expires_at = 9999999999

        # Mock responses
        def mock_response_func(method, url, **kwargs):
            mock_response = MagicMock()
            mock_response.status_code = 200

            if method == "GET" and "Customer" in url:
                # Customer search response
                mock_response.json.return_value = {
                    "QueryResponse": {"Customer": [{"Id": "456", "DisplayName": "Jane Smith"}]}
                }
            elif method == "POST" and "salesreceipt" in url:
                # Sales receipt creation response
                mock_response.json.return_value = {
                    "SalesReceipt": {
                        "Id": "SR789",
                        "DocNumber": "1001",
                        "CustomerRef": {"value": "456"},
                        "TotalAmt": 150.00,
                    }
                }
            return mock_response

        mock_request.side_effect = mock_response_func

        # Find customer first
        customer = self.qbo_service.find_customer("Jane Smith")
        self.assertIsNotNone(customer)
        self.assertEqual(customer["Id"], "456")

        # Create sales receipt for that customer
        receipt_data = {
            "CustomerRef": {"value": customer["Id"]},
            "Line": [
                {
                    "Amount": 150.00,
                    "DetailType": "SalesItemLineDetail",
                    "SalesItemLineDetail": {"ItemRef": {"value": "1"}},
                }
            ],
        }

        receipt = self.qbo_service.create_sales_receipt(receipt_data)
        self.assertIsNotNone(receipt)
        self.assertEqual(receipt["CustomerRef"]["value"], "456")
        self.assertEqual(receipt["TotalAmt"], 150.00)

    @patch("requests.request")
    def test_entity_service_operations(self, mock_request):
        """Test entity service operations for accounts, items, and payment methods."""
        # Set up authentication
        self.qbo_service.auth_service._access_token = "test-token"
        self.qbo_service.auth_service._realm_id = "test-realm"
        self.qbo_service.auth_service._token_expires_at = 9999999999

        # Mock responses for different entity types
        def mock_response_func(method, url, **kwargs):
            mock_response = MagicMock()
            mock_response.status_code = 200

            if method == "POST":
                if "account" in url:
                    mock_response.json.return_value = {
                        "Account": {"Id": "ACC123", "Name": "Donation Income", "AccountType": "Income"}
                    }
                elif "item" in url:
                    mock_response.json.return_value = {"Item": {"Id": "ITEM123", "Name": "Donation", "Type": "Service"}}
                elif "paymentmethod" in url:
                    mock_response.json.return_value = {"PaymentMethod": {"Id": "PM123", "Name": "Check"}}
            elif method == "GET":
                # Get all items/accounts/payment methods
                if "Item" in url:
                    mock_response.json.return_value = {"QueryResponse": {"Item": [{"Id": "1", "Name": "Item1"}]}}
                elif "Account" in url:
                    mock_response.json.return_value = {"QueryResponse": {"Account": [{"Id": "1", "Name": "Account1"}]}}
                elif "PaymentMethod" in url:
                    mock_response.json.return_value = {"QueryResponse": {"PaymentMethod": [{"Id": "1", "Name": "PM1"}]}}

            return mock_response

        mock_request.side_effect = mock_response_func

        # Test creating account
        account = self.qbo_service.create_account({"Name": "Donation Income", "AccountType": "Income"})
        self.assertIsNotNone(account)
        self.assertEqual(account["Name"], "Donation Income")

        # Test creating item
        item = self.qbo_service.create_item({"Name": "Donation", "Type": "Service"})
        self.assertIsNotNone(item)
        self.assertEqual(item["Name"], "Donation")

        # Test creating payment method
        pm = self.qbo_service.create_payment_method({"Name": "Check"})
        self.assertIsNotNone(pm)
        self.assertEqual(pm["Name"], "Check")

        # Test getting all entities
        items = self.qbo_service.get_all_items()
        self.assertEqual(len(items), 1)

        accounts = self.qbo_service.get_all_accounts()
        self.assertEqual(len(accounts), 1)

        payment_methods = self.qbo_service.get_all_payment_methods()
        self.assertEqual(len(payment_methods), 1)

    def test_backward_compatibility_properties(self):
        """Test that backward compatibility properties work correctly."""
        # Set token via facade
        self.qbo_service.access_token = "test-token"
        self.qbo_service.refresh_token = "refresh-token"
        self.qbo_service.realm_id = "test-realm"
        self.qbo_service.token_expires_at = 12345

        # Verify tokens are set on auth service
        self.assertEqual(self.qbo_service.auth_service._access_token, "test-token")
        self.assertEqual(self.qbo_service.auth_service._refresh_token, "refresh-token")
        self.assertEqual(self.qbo_service.auth_service._realm_id, "test-realm")
        self.assertEqual(self.qbo_service.auth_service._token_expires_at, 12345)

        # Verify getters work
        self.assertEqual(self.qbo_service.access_token, "test-token")
        self.assertEqual(self.qbo_service.refresh_token, "refresh-token")
        self.assertEqual(self.qbo_service.realm_id, "test-realm")
        self.assertEqual(self.qbo_service.token_expires_at, 12345)


if __name__ == "__main__":
    unittest.main()
