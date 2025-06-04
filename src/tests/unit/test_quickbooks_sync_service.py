"""Tests for QuickBooks sync service."""
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from src.models.donation import (
    ContactInfo,
    DonationEntry,
    PayerInfo,
    PaymentInfo,
    PaymentMethod,
    QuickBooksInfo,
)
from src.models.quickbooks import (
    CustomerMatch,
    QuickBooksCustomer,
    QuickBooksSalesReceipt,
    QuickBooksSyncResult,
    SyncStatus,
)
from src.services.quickbooks.sync_service import MatchStrategy, QuickBooksSyncService


@pytest.fixture
def mock_oauth_token():
    """Mock OAuth token."""
    return {
        "access_token": "mock_access_token",
        "realm_id": "123456789",
        "refresh_token": "mock_refresh_token",
    }


@pytest.fixture
def mock_customer_service():
    """Mock customer service."""
    with patch("src.services.quickbooks.sync_service.CustomerService") as mock_class:
        yield mock_class.return_value


@pytest.fixture
def mock_receipt_service():
    """Mock receipt service."""
    with patch(
        "src.services.quickbooks.sync_service.SalesReceiptService"
    ) as mock_class:
        yield mock_class.return_value


@pytest.fixture
def mock_redis_client():
    """Mock Redis client."""
    with patch("src.services.quickbooks.sync_service.get_redis_client") as mock:
        client = MagicMock()
        # Configure Redis mock to return None for cache misses
        client.get.return_value = None
        mock.return_value = client
        yield client


@pytest.fixture
def sync_service(
    mock_oauth_token, mock_customer_service, mock_receipt_service, mock_redis_client
):
    """Create sync service instance."""
    return QuickBooksSyncService(mock_oauth_token)


@pytest.fixture
def sample_donation():
    """Sample donation entry."""
    return DonationEntry(
        payer_info=PayerInfo(name="John Smith", aliases=["J. Smith"]),
        payment_info=PaymentInfo(
            amount=Decimal("100.00"),
            check_number="1234",
            payment_date=date(2025, 1, 15),
            payment_method=PaymentMethod.CHECK,
        ),
        contact_info=ContactInfo(email="john@example.com"),
        source_documents=["doc1"],
        quickbooks_info=QuickBooksInfo(),
    )


@pytest.fixture
def sample_customer_match():
    """Sample customer match."""
    return CustomerMatch(
        customer_id="123",
        display_name="John Smith",
        email="john@example.com",
        confidence_score=0.9,
        match_reasons=["Name match", "Email match"],
    )


@pytest.fixture
def sample_customer():
    """Sample QuickBooks customer."""
    return QuickBooksCustomer(
        id="123",
        sync_token="0",
        display_name="John Smith",
        email="john@example.com",
        active=True,
    )


@pytest.fixture
def sample_receipt():
    """Sample sales receipt."""
    return QuickBooksSalesReceipt(
        id="456",
        sync_token="0",
        doc_number="SR-1001",
        txn_date="2025-01-15",
        customer_ref="123",
        total_amt=Decimal("100.00"),
    )


class TestQuickBooksSyncService:
    """Test QuickBooks sync service."""

    def test_sync_donation_auto_match_success(
        self,
        sync_service,
        mock_customer_service,
        mock_receipt_service,
        sample_donation,
        sample_customer_match,
        sample_customer,
        sample_receipt,
    ):
        """Test successful auto-match sync."""
        # Setup mocks
        mock_customer_service.search_customers.return_value = [sample_customer_match]
        mock_customer_service.get_customer.return_value = sample_customer
        mock_receipt_service.create_sales_receipt.return_value = sample_receipt

        # Sync donation
        result = sync_service.sync_donation(
            sample_donation, MatchStrategy.AUTO_MATCH_HIGH_CONFIDENCE
        )

        # Verify result
        assert isinstance(result, QuickBooksSyncResult)
        assert result.status == SyncStatus.SYNCED
        assert result.customer_id == "123"
        assert result.receipt_id == "456"
        assert result.match_confidence == 0.9

        # Verify service calls
        mock_customer_service.search_customers.assert_called_once()
        mock_customer_service.get_customer.assert_called_once_with("123")
        mock_receipt_service.create_sales_receipt.assert_called_once()

        # Verify donation was updated
        assert sample_donation.quickbooks_info.customer_id == "123"
        assert sample_donation.quickbooks_info.receipt_id == "456"

    def test_sync_donation_low_confidence_requires_review(
        self,
        sync_service,
        mock_customer_service,
        sample_donation,
        sample_customer_match,
    ):
        """Test low confidence match requires manual review."""
        # Setup low confidence match
        sample_customer_match.confidence_score = 0.5
        mock_customer_service.search_customers.return_value = [sample_customer_match]

        # Sync donation
        result = sync_service.sync_donation(
            sample_donation, MatchStrategy.AUTO_MATCH_HIGH_CONFIDENCE
        )

        # Verify pending review status
        assert result.status == SyncStatus.PENDING_REVIEW
        assert result.customer_matches == [sample_customer_match]
        assert result.customer_id is None
        assert result.receipt_id is None

    def test_sync_donation_create_new_customer(
        self,
        sync_service,
        mock_customer_service,
        mock_receipt_service,
        sample_donation,
        sample_customer,
        sample_receipt,
    ):
        """Test creating new customer when specified."""
        # Setup mocks
        mock_customer_service.create_customer.return_value = sample_customer
        mock_receipt_service.create_sales_receipt.return_value = sample_receipt

        # Sync with create new strategy
        result = sync_service.sync_donation(sample_donation, MatchStrategy.CREATE_NEW)

        # Verify result
        assert result.status == SyncStatus.SYNCED
        assert result.customer_id == "123"
        assert result.match_confidence == 1.0

        # Verify customer was created
        mock_customer_service.create_customer.assert_called_once()
        mock_customer_service.search_customers.assert_not_called()

    def test_sync_donation_manual_customer_id(
        self,
        sync_service,
        mock_customer_service,
        mock_receipt_service,
        sample_donation,
        sample_customer,
        sample_receipt,
    ):
        """Test sync with pre-selected customer ID."""
        # Setup mocks
        mock_customer_service.get_customer.return_value = sample_customer
        mock_receipt_service.create_sales_receipt.return_value = sample_receipt

        # Sync with manual customer ID
        result = sync_service.sync_donation(
            sample_donation,
            MatchStrategy.AUTO_MATCH_HIGH_CONFIDENCE,
            customer_id="123",
        )

        # Verify result
        assert result.status == SyncStatus.SYNCED
        assert result.customer_id == "123"
        assert result.match_confidence == 1.0

        # Verify no search was performed
        mock_customer_service.search_customers.assert_not_called()

    def test_sync_donation_no_payer_info(self, sync_service):
        """Test sync with missing payer info."""
        donation = DonationEntry(
            payment_info=PaymentInfo(amount=Decimal("100")),
            source_documents=["doc1"],
        )

        result = sync_service.sync_donation(donation)

        assert result.status == SyncStatus.ERROR
        assert "payer information" in result.error_message

    def test_sync_donation_exception_handling(
        self, sync_service, mock_customer_service, sample_donation
    ):
        """Test exception handling during sync."""
        # Mock exception
        mock_customer_service.search_customers.side_effect = Exception("API Error")

        # Sync donation
        result = sync_service.sync_donation(sample_donation)

        # Verify error result
        assert result.status == SyncStatus.ERROR
        assert "API Error" in result.error_message

    def test_sync_donations_batch(
        self,
        sync_service,
        mock_customer_service,
        mock_receipt_service,
        sample_donation,
        sample_customer_match,
        sample_customer,
        sample_receipt,
    ):
        """Test batch sync of donations."""
        # Create multiple donations
        donation1 = sample_donation
        donation2 = DonationEntry(
            payer_info=PayerInfo(name="Jane Doe"),
            payment_info=PaymentInfo(amount=Decimal("200")),
            source_documents=["doc2"],
        )

        # Setup mocks for auto-match
        sample_customer_match.confidence_score = 0.9
        mock_customer_service.search_customers.return_value = [sample_customer_match]
        mock_customer_service.get_customer.return_value = sample_customer
        mock_receipt_service.create_sales_receipt.return_value = sample_receipt

        # Sync batch
        results = sync_service.sync_donations_batch([donation1, donation2])

        # Verify results
        assert len(results) == 2
        assert results[0].status == SyncStatus.SYNCED
        assert results[1].status == SyncStatus.SYNCED

    def test_search_customers_with_cache_hit(
        self, sync_service, mock_customer_service, mock_redis_client, sample_donation
    ):
        """Test customer search with cache hit."""
        # Mock cache hit
        import json

        cached_match = {
            "customer_id": "123",
            "display_name": "John Smith",
            "confidence_score": 0.9,
            "match_reasons": ["Cached"],
        }
        mock_redis_client.get.return_value = json.dumps([cached_match])

        # Search customers
        matches = sync_service._search_customers_with_cache(sample_donation)

        # Verify cache was used
        assert len(matches) == 1
        assert matches[0].customer_id == "123"
        mock_customer_service.search_customers.assert_not_called()

    def test_search_customers_with_cache_miss(
        self,
        sync_service,
        mock_customer_service,
        mock_redis_client,
        sample_donation,
        sample_customer_match,
    ):
        """Test customer search with cache miss."""
        # Mock cache miss
        mock_redis_client.get.return_value = None
        mock_customer_service.search_customers.return_value = [sample_customer_match]

        # Search customers
        matches = sync_service._search_customers_with_cache(sample_donation)

        # Verify search was performed
        assert len(matches) == 1
        mock_customer_service.search_customers.assert_called_once()

        # Verify cache was set
        mock_redis_client.setex.assert_called_once()

    def test_validate_oauth_token_valid(self, sync_service, mock_customer_service):
        """Test OAuth token validation success."""
        # Mock successful query
        mock_customer_service._execute_query.return_value = []

        # Validate token
        is_valid = sync_service.validate_oauth_token()

        assert is_valid is True

    def test_validate_oauth_token_invalid(self, sync_service, mock_customer_service):
        """Test OAuth token validation failure."""
        # Mock failed query
        mock_customer_service._execute_query.side_effect = Exception("Unauthorized")

        # Validate token
        is_valid = sync_service.validate_oauth_token()

        assert is_valid is False

    def test_get_sync_statistics(self, sync_service):
        """Test getting sync statistics."""
        stats = sync_service.get_sync_statistics("2025-01-01", "2025-01-31")

        # Verify structure (placeholder implementation)
        assert isinstance(stats, dict)
        assert "total_donations" in stats
        assert "synced" in stats
        assert "pending_review" in stats
        assert "errors" in stats
