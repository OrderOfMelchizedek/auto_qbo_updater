"""Tests for QuickBooks sales receipt service."""
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.models.donation import DonationEntry, PaymentInfo, PaymentMethod
from src.models.quickbooks import QuickBooksSalesReceipt, SalesReceiptLine
from src.services.quickbooks.sales_receipt_service import SalesReceiptService
from src.utils.exceptions import QuickBooksIntegrationError


@pytest.fixture
def mock_oauth_token():
    """Mock OAuth token."""
    return {
        "access_token": "mock_access_token",
        "realm_id": "123456789",
        "refresh_token": "mock_refresh_token",
    }


@pytest.fixture
def mock_oauth_session():
    """Mock OAuth session."""
    with patch("src.services.quickbooks.sales_receipt_service.OAuth2Session") as mock:
        session = MagicMock()
        mock.return_value = session
        yield session


@pytest.fixture
def receipt_service(mock_oauth_token, mock_oauth_session):
    """Create sales receipt service instance."""
    return SalesReceiptService(mock_oauth_token)


@pytest.fixture
def sample_donation():
    """Sample donation entry."""
    return DonationEntry(
        payment_info=PaymentInfo(
            amount=Decimal("100.00"),
            check_number="1234",
            payment_date=date(2025, 1, 15),
            payment_method=PaymentMethod.CHECK,
            memo="Test donation",
        ),
        source_documents=["doc1", "doc2"],
    )


@pytest.fixture
def sample_receipt_response():
    """Sample QuickBooks sales receipt response."""
    return {
        "Id": "456",
        "SyncToken": "0",
        "DocNumber": "SR-1001",
        "TxnDate": "2025-01-15",
        "CustomerRef": {"value": "123"},
        "TotalAmt": 100.00,
        "PaymentMethodRef": {"value": "1"},
        "PaymentRefNum": "1234",
        "DepositToAccountRef": {"value": "35"},
        "PrivateNote": "Test donation",
        "Line": [
            {
                "Id": "1",
                "LineNum": 1,
                "DetailType": "SalesItemLineDetail",
                "Amount": 100.00,
                "SalesItemLineDetail": {"ItemRef": {"value": "21"}},
            }
        ],
    }


class TestSalesReceiptService:
    """Test QuickBooks sales receipt service."""

    def test_create_sales_receipt_success(
        self,
        receipt_service,
        mock_oauth_session,
        sample_donation,
        sample_receipt_response,
    ):
        """Test successful sales receipt creation."""
        # Mock query responses for item and account lookups
        mock_oauth_session.get.return_value.json.side_effect = [
            {"QueryResponse": {"Item": [{"Id": "21", "Name": "Donation"}]}},
            {"QueryResponse": {"Account": [{"Id": "35", "Name": "Undeposited Funds"}]}},
            {"QueryResponse": {"PaymentMethod": [{"Id": "1", "Name": "Check"}]}},
        ]
        mock_oauth_session.get.return_value.raise_for_status = MagicMock()

        # Mock receipt creation
        mock_oauth_session.post.return_value.json.return_value = {
            "SalesReceipt": sample_receipt_response
        }
        mock_oauth_session.post.return_value.raise_for_status = MagicMock()

        # Create receipt
        receipt = receipt_service.create_sales_receipt(sample_donation, "123")

        # Verify result
        assert isinstance(receipt, QuickBooksSalesReceipt)
        assert receipt.id == "456"
        assert receipt.doc_number == "SR-1001"
        assert receipt.total_amt == Decimal("100.00")
        assert receipt.customer_ref == "123"

        # Verify API calls
        assert mock_oauth_session.post.called
        call_args = mock_oauth_session.post.call_args
        request_data = call_args[1]["json"]

        assert request_data["CustomerRef"]["value"] == "123"
        assert request_data["TxnDate"] == "2025-01-15"
        assert request_data["Line"][0]["Amount"] == 100.0
        assert request_data["PaymentRefNum"] == "1234"

    def test_create_sales_receipt_no_payment_info(
        self, receipt_service, mock_oauth_session
    ):
        """Test sales receipt creation without payment info."""
        donation = DonationEntry(source_documents=["doc1"])

        with pytest.raises(ValueError) as exc:
            receipt_service.create_sales_receipt(donation, "123")

        assert "must have payment information" in str(exc.value)

    def test_create_sales_receipt_api_error(
        self, receipt_service, mock_oauth_session, sample_donation
    ):
        """Test sales receipt creation with API error."""
        # Mock query responses for item, account, and payment method lookups
        mock_oauth_session.get.return_value.json.side_effect = [
            {"QueryResponse": {"Item": [{"Id": "21", "Name": "Donation"}]}},
            {"QueryResponse": {"Account": [{"Id": "35", "Name": "Undeposited Funds"}]}},
            {"QueryResponse": {"PaymentMethod": [{"Id": "1", "Name": "Check"}]}},
        ]
        mock_oauth_session.get.return_value.raise_for_status = MagicMock()

        # Mock API error on receipt creation
        mock_oauth_session.post.side_effect = requests.RequestException("API Error")

        with pytest.raises(QuickBooksIntegrationError) as exc:
            receipt_service.create_sales_receipt(sample_donation, "123")

        assert "Sales receipt creation failed" in str(exc.value)

    def test_get_or_create_donation_item_exists(
        self, receipt_service, mock_oauth_session
    ):
        """Test getting existing donation item."""
        # Mock query response
        mock_oauth_session.get.return_value.json.return_value = {
            "QueryResponse": {"Item": [{"Id": "21", "Name": "Donation"}]}
        }
        mock_oauth_session.get.return_value.raise_for_status = MagicMock()

        # Get item
        item_id = receipt_service._get_or_create_donation_item()

        assert item_id == "21"
        assert mock_oauth_session.get.called
        assert not mock_oauth_session.post.called

    def test_get_or_create_donation_item_create_new(
        self, receipt_service, mock_oauth_session
    ):
        """Test creating new donation item."""
        # Mock empty query response
        mock_oauth_session.get.return_value.json.side_effect = [
            {"QueryResponse": {"Item": []}},  # No donation item
            {"QueryResponse": {"Account": [{"Id": "4", "Name": "Donation Income"}]}},
        ]
        mock_oauth_session.get.return_value.raise_for_status = MagicMock()

        # Mock item creation
        mock_oauth_session.post.return_value.json.return_value = {
            "Item": {"Id": "22", "Name": "Donation"}
        }
        mock_oauth_session.post.return_value.raise_for_status = MagicMock()

        # Create item
        item_id = receipt_service._get_or_create_donation_item()

        assert item_id == "22"
        assert mock_oauth_session.post.called

    def test_get_sales_receipt_success(
        self, receipt_service, mock_oauth_session, sample_receipt_response
    ):
        """Test getting sales receipt by ID."""
        # Mock response
        mock_oauth_session.get.return_value.json.return_value = {
            "SalesReceipt": sample_receipt_response
        }
        mock_oauth_session.get.return_value.raise_for_status = MagicMock()

        # Get receipt
        receipt = receipt_service.get_sales_receipt("456")

        # Verify result
        assert isinstance(receipt, QuickBooksSalesReceipt)
        assert receipt.id == "456"
        assert len(receipt.lines) == 1
        assert receipt.lines[0].amount == Decimal("100.00")

    def test_batch_create_sales_receipts(
        self,
        receipt_service,
        mock_oauth_session,
        sample_donation,
        sample_receipt_response,
    ):
        """Test batch creation of sales receipts."""
        # Mock successful responses - cycle through responses for multiple calls
        mock_oauth_session.get.return_value.json.side_effect = [
            {"QueryResponse": {"Item": [{"Id": "21", "Name": "Donation"}]}},
            {"QueryResponse": {"Account": [{"Id": "35", "Name": "Undeposited Funds"}]}},
            {"QueryResponse": {"PaymentMethod": [{"Id": "1", "Name": "Check"}]}},
            {
                "QueryResponse": {"PaymentMethod": [{"Id": "1", "Name": "Check"}]}
            },  # Second receipt
        ]
        mock_oauth_session.post.return_value.json.return_value = {
            "SalesReceipt": sample_receipt_response
        }
        mock_oauth_session.get.return_value.raise_for_status = MagicMock()
        mock_oauth_session.post.return_value.raise_for_status = MagicMock()

        # Create batch
        donations_with_customers = [
            (sample_donation, "123"),
            (sample_donation, "124"),
        ]

        results = receipt_service.batch_create_sales_receipts(donations_with_customers)

        # Verify results
        assert len(results) == 2
        assert all(r["success"] for r in results)
        assert results[0]["receipt_id"] == "456"
        assert results[0]["customer_id"] == "123"

    def test_batch_create_sales_receipts_with_failures(
        self, receipt_service, mock_oauth_session, sample_donation
    ):
        """Test batch creation with some failures."""
        # Mock query responses - item, account, and payment method lookups
        mock_oauth_session.get.return_value.json.side_effect = [
            {"QueryResponse": {"Item": [{"Id": "21", "Name": "Donation"}]}},
            {"QueryResponse": {"Account": [{"Id": "35", "Name": "Undeposited Funds"}]}},
            {"QueryResponse": {"PaymentMethod": [{"Id": "1", "Name": "Check"}]}},
            {
                "QueryResponse": {"PaymentMethod": [{"Id": "1", "Name": "Check"}]}
            },  # Second receipt
        ]
        mock_oauth_session.get.return_value.raise_for_status = MagicMock()

        # Mock one success, one failure
        successful_response = {
            "SalesReceipt": {
                "Id": "456",
                "SyncToken": "0",
                "DocNumber": "SR-1001",
                "TxnDate": "2025-01-15",
                "CustomerRef": {"value": "123"},
                "TotalAmt": 100.00,
                "Line": [
                    {
                        "Id": "1",
                        "LineNum": 1,
                        "DetailType": "SalesItemLineDetail",
                        "Amount": 100.00,
                        "SalesItemLineDetail": {"ItemRef": {"value": "21"}},
                    }
                ],
            }
        }
        successful_post = MagicMock()
        successful_post.json.return_value = successful_response
        successful_post.raise_for_status = MagicMock()

        mock_oauth_session.post.side_effect = [
            successful_post,
            requests.RequestException("API Error"),
        ]

        # Create batch
        donations_with_customers = [
            (sample_donation, "123"),
            (sample_donation, "124"),
        ]

        results = receipt_service.batch_create_sales_receipts(donations_with_customers)

        # Verify mixed results
        assert len(results) == 2
        assert results[0]["success"] is True
        assert results[1]["success"] is False
        assert "API Error" in results[1]["error"]

    def test_get_payment_method_ref(self, receipt_service, mock_oauth_session):
        """Test getting payment method reference."""
        # Mock response
        mock_oauth_session.get.return_value.json.return_value = {
            "QueryResponse": {"PaymentMethod": [{"Id": "1", "Name": "Check"}]}
        }
        mock_oauth_session.get.return_value.raise_for_status = MagicMock()

        # Get payment method
        ref = receipt_service._get_payment_method_ref("check")

        assert ref == {"value": "1"}

    def test_parse_sales_receipt(self, receipt_service, sample_receipt_response):
        """Test parsing sales receipt response."""
        receipt = receipt_service._parse_sales_receipt(sample_receipt_response)

        assert isinstance(receipt, QuickBooksSalesReceipt)
        assert receipt.id == "456"
        assert receipt.sync_token == "0"
        assert receipt.doc_number == "SR-1001"
        assert receipt.txn_date == "2025-01-15"
        assert receipt.customer_ref == "123"
        assert receipt.total_amt == Decimal("100.00")
        assert receipt.payment_ref_num == "1234"
        assert len(receipt.lines) == 1
        assert isinstance(receipt.lines[0], SalesReceiptLine)
