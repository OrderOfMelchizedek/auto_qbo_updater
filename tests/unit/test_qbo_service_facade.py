"""
Unit tests for QBO Service Facade.

This tests the facade pattern that maintains backward compatibility.
"""

from unittest.mock import Mock, patch

import pytest

from src.utils.qbo_service import QBOService
from src.utils.qbo_service.auth import QBOAuthService
from src.utils.qbo_service.customers import QBOCustomerService
from src.utils.qbo_service.entities import QBOEntityService
from src.utils.qbo_service.sales_receipts import QBOSalesReceiptService


class TestQBOServiceFacade:
    """Test the QBO service facade for backward compatibility."""

    @pytest.fixture
    def qbo_service(self):
        """Create a QBO service instance."""
        return QBOService(
            client_id="test_client",
            client_secret="test_secret",
            redirect_uri="http://test/callback",
            environment="sandbox",
        )

    def test_init_creates_all_services(self, qbo_service):
        """Test that initialization creates all sub-services."""
        assert isinstance(qbo_service.auth_service, QBOAuthService)
        assert isinstance(qbo_service.customer_service, QBOCustomerService)
        assert isinstance(qbo_service.entity_service, QBOEntityService)
        assert isinstance(qbo_service.sales_receipt_service, QBOSalesReceiptService)

    def test_init_passes_auth_to_services(self, qbo_service):
        """Test that auth service is passed to other services."""
        # All services should share the same auth service
        assert qbo_service.customer_service.auth_service == qbo_service.auth_service
        assert qbo_service.entity_service.auth_service == qbo_service.auth_service
        assert qbo_service.sales_receipt_service.auth_service == qbo_service.auth_service

    # Auth Property Tests
    def test_access_token_property(self, qbo_service):
        """Test access token property delegation."""
        # Set via facade
        qbo_service.access_token = "test_token"

        # Should be set on auth service
        assert qbo_service.auth_service.access_token == "test_token"

        # Get via facade
        assert qbo_service.access_token == "test_token"

    def test_refresh_token_property(self, qbo_service):
        """Test refresh token property delegation."""
        qbo_service.refresh_token = "refresh_token"

        assert qbo_service.auth_service.refresh_token == "refresh_token"
        assert qbo_service.refresh_token == "refresh_token"

    def test_realm_id_property(self, qbo_service):
        """Test realm ID property delegation."""
        qbo_service.realm_id = "test_realm"

        assert qbo_service.auth_service.realm_id == "test_realm"
        assert qbo_service.realm_id == "test_realm"

    def test_token_expires_at_property(self, qbo_service):
        """Test token expiration property delegation."""
        qbo_service.token_expires_at = 1234567890

        assert qbo_service.auth_service.token_expires_at == 1234567890
        assert qbo_service.token_expires_at == 1234567890

    def test_environment_property(self, qbo_service):
        """Test environment property delegation."""
        # Environment is read-only and set during initialization
        assert qbo_service.environment == "sandbox"
        assert qbo_service.auth_service.environment == "sandbox"

    # Auth Method Tests
    def test_clear_tokens_delegation(self, qbo_service):
        """Test clear_tokens method delegation."""
        with patch.object(qbo_service.auth_service, "clear_tokens") as mock_clear:
            qbo_service.clear_tokens()

        mock_clear.assert_called_once()

    def test_get_authorization_url_delegation(self, qbo_service):
        """Test get_authorization_url method delegation."""
        with patch.object(
            qbo_service.auth_service, "get_authorization_url", return_value="http://auth.url"
        ) as mock_method:
            result = qbo_service.get_authorization_url()

        assert result == "http://auth.url"
        mock_method.assert_called_once()

    def test_get_tokens_delegation(self, qbo_service):
        """Test get_tokens method delegation."""
        with patch.object(qbo_service.auth_service, "get_tokens", return_value=True) as mock_method:
            result = qbo_service.get_tokens("auth_code", "realm_id")

        assert result is True
        mock_method.assert_called_once_with("auth_code", "realm_id")

    def test_refresh_access_token_delegation(self, qbo_service):
        """Test refresh_access_token method delegation."""
        with patch.object(qbo_service.auth_service, "refresh_access_token", return_value=True) as mock_method:
            result = qbo_service.refresh_access_token()

        assert result is True
        mock_method.assert_called_once()

    def test_refresh_tokens_delegation(self, qbo_service):
        """Test refresh_tokens method delegation."""
        with patch.object(qbo_service.auth_service, "refresh_tokens", return_value=True) as mock_method:
            result = qbo_service.refresh_tokens()

        assert result is True
        mock_method.assert_called_once()

    def test_is_token_valid_delegation(self, qbo_service):
        """Test is_token_valid method delegation."""
        with patch.object(qbo_service.auth_service, "is_token_valid", return_value=True) as mock_method:
            result = qbo_service.is_token_valid()

        assert result is True
        mock_method.assert_called_once()

    def test_get_token_info_delegation(self, qbo_service):
        """Test get_token_info method delegation."""
        token_info = {"realm_id": "test", "is_valid": True}
        with patch.object(qbo_service.auth_service, "get_token_info", return_value=token_info) as mock_method:
            result = qbo_service.get_token_info()

        assert result == token_info
        mock_method.assert_called_once()

    # Customer Method Tests
    def test_find_customer_delegation(self, qbo_service):
        """Test find_customer method delegation."""
        customer = {"Id": "123", "DisplayName": "Test"}
        with patch.object(qbo_service.customer_service, "find_customer", return_value=customer) as mock_method:
            result = qbo_service.find_customer("Test")

        assert result == customer
        mock_method.assert_called_once_with("Test")

    def test_find_customers_batch_delegation(self, qbo_service):
        """Test find_customers_batch method delegation."""
        customers = {"John": {"Id": "1"}, "Jane": {"Id": "2"}}
        with patch.object(qbo_service.customer_service, "find_customers_batch", return_value=customers) as mock_method:
            result = qbo_service.find_customers_batch(["John", "Jane"])

        assert result == customers
        mock_method.assert_called_once_with(["John", "Jane"])

    def test_get_customer_cache_stats_delegation(self, qbo_service):
        """Test get_customer_cache_stats method delegation."""
        stats = {"cache_size": 10, "cache_valid": True}
        with patch.object(qbo_service.customer_service, "get_customer_cache_stats", return_value=stats) as mock_method:
            result = qbo_service.get_customer_cache_stats()

        assert result == stats
        mock_method.assert_called_once()

    def test_create_customer_delegation(self, qbo_service):
        """Test create_customer method delegation."""
        customer_data = {"DisplayName": "New Customer"}
        created = {"Id": "123", **customer_data}
        with patch.object(qbo_service.customer_service, "create_customer", return_value=created) as mock_method:
            result = qbo_service.create_customer(customer_data)

        assert result == created
        mock_method.assert_called_once_with(customer_data)

    def test_update_customer_delegation(self, qbo_service):
        """Test update_customer method delegation."""
        customer_data = {"Id": "123", "DisplayName": "Updated"}
        with patch.object(qbo_service.customer_service, "update_customer", return_value=customer_data) as mock_method:
            result = qbo_service.update_customer(customer_data)

        assert result == customer_data
        mock_method.assert_called_once_with(customer_data)

    def test_get_cached_customer_delegation(self, qbo_service):
        """Test get_cached_customer method delegation."""
        customer = {"Id": "123"}
        with patch.object(qbo_service.customer_service, "get_cached_customer", return_value=customer) as mock_method:
            result = qbo_service.get_cached_customer("lookup_value")

        assert result == customer
        mock_method.assert_called_once_with("lookup_value")

    def test_clear_customer_cache_delegation(self, qbo_service):
        """Test clear_customer_cache method delegation."""
        with patch.object(qbo_service.customer_service, "clear_customer_cache") as mock_method:
            qbo_service.clear_customer_cache()

        mock_method.assert_called_once()

    def test_get_all_customers_delegation(self, qbo_service):
        """Test get_all_customers method delegation."""
        customers = [{"Id": "1"}, {"Id": "2"}]
        with patch.object(qbo_service.customer_service, "get_all_customers", return_value=customers) as mock_method:
            result = qbo_service.get_all_customers(use_cache=False)

        assert result == customers
        mock_method.assert_called_once_with(use_cache=False)

    # Sales Receipt Method Tests
    def test_find_sales_receipt_delegation(self, qbo_service):
        """Test find_sales_receipt method delegation."""
        receipt = {"Id": "SR123"}
        with patch.object(qbo_service.sales_receipt_service, "find_sales_receipt", return_value=receipt) as mock_method:
            result = qbo_service.find_sales_receipt("CHK123", "100.00")

        assert result == receipt
        mock_method.assert_called_once_with("CHK123", "100.00")

    def test_create_sales_receipt_delegation(self, qbo_service):
        """Test create_sales_receipt method delegation."""
        receipt_data = {"CustomerRef": {"value": "123"}}
        created = {"Id": "SR123", **receipt_data}
        with patch.object(
            qbo_service.sales_receipt_service, "create_sales_receipt", return_value=created
        ) as mock_method:
            result = qbo_service.create_sales_receipt(receipt_data)

        assert result == created
        mock_method.assert_called_once_with(receipt_data)

    # Entity Method Tests
    def test_create_account_delegation(self, qbo_service):
        """Test create_account method delegation."""
        account_data = {"Name": "Test Account", "AccountType": "Income"}
        created = {"Id": "1", **account_data}
        with patch.object(qbo_service.entity_service, "create_account", return_value=created) as mock_method:
            result = qbo_service.create_account(account_data)

        assert result == created
        mock_method.assert_called_once_with(account_data)

    def test_create_item_delegation(self, qbo_service):
        """Test create_item method delegation."""
        item_data = {"Name": "Test Item", "Type": "Service"}
        created = {"Id": "1", **item_data}
        with patch.object(qbo_service.entity_service, "create_item", return_value=created) as mock_method:
            result = qbo_service.create_item(item_data)

        assert result == created
        mock_method.assert_called_once_with(item_data)

    def test_create_payment_method_delegation(self, qbo_service):
        """Test create_payment_method method delegation."""
        pm_data = {"Name": "Check"}
        created = {"Id": "1", **pm_data}
        with patch.object(qbo_service.entity_service, "create_payment_method", return_value=created) as mock_method:
            result = qbo_service.create_payment_method(pm_data)

        assert result == created
        mock_method.assert_called_once_with(pm_data)

    def test_get_all_items_delegation(self, qbo_service):
        """Test get_all_items method delegation."""
        items = [{"Id": "1"}, {"Id": "2"}]
        with patch.object(qbo_service.entity_service, "get_all_items", return_value=items) as mock_method:
            result = qbo_service.get_all_items()

        assert result == items
        mock_method.assert_called_once()

    def test_get_all_accounts_delegation(self, qbo_service):
        """Test get_all_accounts method delegation."""
        accounts = [{"Id": "1"}, {"Id": "2"}]
        with patch.object(qbo_service.entity_service, "get_all_accounts", return_value=accounts) as mock_method:
            result = qbo_service.get_all_accounts()

        assert result == accounts
        mock_method.assert_called_once()

    def test_get_all_payment_methods_delegation(self, qbo_service):
        """Test get_all_payment_methods method delegation."""
        payment_methods = [{"Id": "1"}, {"Id": "2"}]
        with patch.object(
            qbo_service.entity_service, "get_all_payment_methods", return_value=payment_methods
        ) as mock_method:
            result = qbo_service.get_all_payment_methods()

        assert result == payment_methods
        mock_method.assert_called_once()

    def test_backward_compatibility_imports(self):
        """Test that old imports still work."""
        # This is what existing code would do
        from src.utils.qbo_service import QBOService as ImportedService

        # Should be the same class
        assert ImportedService == QBOService

    def test_redis_client_passed_to_auth(self):
        """Test that redis client is passed to auth service."""
        mock_redis = Mock()

        service = QBOService(
            client_id="test", client_secret="secret", redirect_uri="http://test", redis_client=mock_redis
        )

        assert service.auth_service.redis_client == mock_redis

    def test_all_exported_classes_available(self):
        """Test that all service classes are exported from the module."""
        from src.utils.qbo_service import QBOAuthService, QBOCustomerService, QBOEntityService, QBOSalesReceiptService

        # Just verify they can be imported
        assert QBOAuthService is not None
        assert QBOCustomerService is not None
        assert QBOEntityService is not None
        assert QBOSalesReceiptService is not None
