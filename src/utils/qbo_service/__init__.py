"""
QuickBooks Online Service module.

This module provides a modular approach to QuickBooks Online integration,
splitting functionality into focused submodules while maintaining backward
compatibility through a facade class.
"""

from .auth import QBOAuthService
from .customers import QBOCustomerService
from .entities import QBOEntityService
from .sales_receipts import QBOSalesReceiptService

__all__ = ["QBOService", "QBOAuthService", "QBOCustomerService", "QBOEntityService", "QBOSalesReceiptService"]


class QBOService:
    """
    Facade class for QuickBooks Online integration.

    This class maintains backward compatibility while delegating to specialized
    service modules for different aspects of QuickBooks functionality.
    """

    def __init__(
        self,
        client_id=None,
        client_secret=None,
        redirect_uri=None,
        environment="sandbox",
        redis_client=None,
    ):
        """Initialize QBO service with OAuth credentials."""
        # Initialize auth service
        self.auth_service = QBOAuthService(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            environment=environment,
            redis_client=redis_client,
        )

        # Initialize other services with auth service
        self.customer_service = QBOCustomerService(self.auth_service)
        self.entity_service = QBOEntityService(self.auth_service)
        self.sales_receipt_service = QBOSalesReceiptService(self.auth_service)

    # Auth delegation properties and methods
    @property
    def access_token(self):
        """Get access token."""
        return self.auth_service.access_token

    @access_token.setter
    def access_token(self, value):
        """Set access token."""
        self.auth_service.access_token = value

    @property
    def refresh_token(self):
        """Get refresh token."""
        return self.auth_service.refresh_token

    @refresh_token.setter
    def refresh_token(self, value):
        """Set refresh token."""
        self.auth_service.refresh_token = value

    @property
    def realm_id(self):
        """Get realm ID."""
        return self.auth_service.realm_id

    @realm_id.setter
    def realm_id(self, value):
        """Set realm ID."""
        self.auth_service.realm_id = value

    @property
    def token_expires_at(self):
        """Get token expiration time."""
        return self.auth_service.token_expires_at

    @token_expires_at.setter
    def token_expires_at(self, value):
        """Set token expiration time."""
        self.auth_service.token_expires_at = value

    @property
    def environment(self):
        """Get the QBO environment setting.

        Returns:
            str: Either 'sandbox' or 'production'
        """
        return self.auth_service.environment

    def clear_tokens(self):
        """Clear all stored tokens."""
        return self.auth_service.clear_tokens()

    def get_authorization_url(self):
        """Generate OAuth authorization URL."""
        return self.auth_service.get_authorization_url()

    def get_tokens(self, authorization_code, realm_id=None):
        """Exchange authorization code for tokens."""
        # For backward compatibility, if realm_id is not provided, try to get it from the auth_service
        if realm_id is None:
            realm_id = self.auth_service.realm_id
        return self.auth_service.get_tokens(authorization_code, realm_id)

    def refresh_access_token(self):
        """Refresh the access token."""
        return self.auth_service.refresh_access_token()

    def refresh_tokens(self):
        """Alias for refresh_access_token for backward compatibility."""
        return self.auth_service.refresh_tokens()

    def is_token_valid(self):
        """Check if the current token is valid."""
        return self.auth_service.is_token_valid()

    def get_token_info(self):
        """Get current token information."""
        return self.auth_service.get_token_info()

    # Customer delegation methods
    def find_customers_batch(self, customer_lookups):
        """Find multiple customers in batch."""
        return self.customer_service.find_customers_batch(customer_lookups)

    def find_customer(self, customer_lookup):
        """Find a single customer."""
        return self.customer_service.find_customer(customer_lookup)

    def get_customer_cache_stats(self):
        """Get customer cache statistics."""
        return self.customer_service.get_customer_cache_stats()

    def create_customer(self, customer_data):
        """Create a new customer."""
        return self.customer_service.create_customer(customer_data)

    def update_customer(self, customer_data):
        """Update an existing customer."""
        return self.customer_service.update_customer(customer_data)

    def get_cached_customer(self, lookup_value):
        """Get customer from cache."""
        return self.customer_service.get_cached_customer(lookup_value)

    def clear_customer_cache(self):
        """Clear the customer cache."""
        return self.customer_service.clear_customer_cache()

    def get_all_customers(self, use_cache=True):
        """Get all customers."""
        return self.customer_service.get_all_customers(use_cache=use_cache)

    # Sales receipt delegation methods
    def find_sales_receipt(self, check_no, amount):
        """Find a sales receipt by check number and amount."""
        return self.sales_receipt_service.find_sales_receipt(check_no, amount)

    def create_sales_receipt(self, sales_receipt_data):
        """Create a new sales receipt."""
        return self.sales_receipt_service.create_sales_receipt(sales_receipt_data)

    # Entity delegation methods
    def create_account(self, account_data):
        """Create a new account."""
        return self.entity_service.create_account(account_data)

    def create_item(self, item_data):
        """Create a new item."""
        return self.entity_service.create_item(item_data)

    def create_payment_method(self, payment_method_data):
        """Create a new payment method."""
        return self.entity_service.create_payment_method(payment_method_data)

    def get_all_items(self):
        """Get all items."""
        return self.entity_service.get_all_items()

    def get_all_accounts(self):
        """Get all accounts."""
        return self.entity_service.get_all_accounts()

    def get_all_payment_methods(self):
        """Get all payment methods."""
        return self.entity_service.get_all_payment_methods()
