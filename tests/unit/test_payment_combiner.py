"""Unit tests for payment combiner functionality."""

import pytest

from src.utils.payment_combiner import PaymentCombiner
from src.utils.qbo_data_enrichment import QBODataEnrichment


class TestPaymentCombiner:
    """Test cases for payment combiner."""

    @pytest.fixture
    def combiner(self):
        """Create a payment combiner instance."""
        return PaymentCombiner()

    def test_extract_payment_info(self, combiner):
        """Test extracting payment info from legacy format."""
        legacy_payment = {
            "Check No.": "1234",
            "Gift Amount": "$500.00",
            "Check Date": "2025-05-28",
            "Deposit Date": "2025-05-30",
            "Deposit Method": "Mobile Deposit",
            "Memo": "Annual contribution",
        }

        result = combiner._extract_payment_info(legacy_payment)

        assert result["check_no_or_payment_ref"] == "1234"
        assert result["amount"] == 500.0
        assert result["payment_date"] == "2025-05-28"
        assert result["deposit_date"] == "2025-05-30"
        assert result["deposit_method"] == "Mobile Deposit"
        assert result["memo"] == "Annual contribution"

    def test_extract_payment_info_online_payment(self, combiner):
        """Test extracting payment info for online payment."""
        legacy_payment = {
            "Payment Ref": "REF-12345",
            "Gift Amount": "1000",
            "Deposit Date": "2025-05-30",
            "Deposit Method": "Online - Stripe",
        }

        result = combiner._extract_payment_info(legacy_payment)

        assert result["check_no_or_payment_ref"] == "REF-12345"
        assert result["amount"] == 1000.0
        assert result["payment_date"] == "2025-05-30"  # Falls back to deposit date

    def test_combine_payment_data_no_match(self, combiner):
        """Test combining payment data when no QBO match."""
        extracted = {
            "Donor Name": "John Doe",
            "Check No.": "5678",
            "Gift Amount": "250.00",
            "Check Date": "2025-05-28",
            "Deposit Date": "2025-05-30",
            "Address - Line 1": "123 Main St",
            "City": "Springfield",
            "State": "IL",
            "ZIP": "62701",
            "Email": "john@example.com",
            "Phone": "(555) 123-4567",
        }

        result = combiner.combine_payment_data(extracted, None, "New")

        # Check payment info
        assert result["payment_info"]["check_no_or_payment_ref"] == "5678"
        assert result["payment_info"]["amount"] == 250.0

        # Check payer info
        assert result["payer_info"]["customer_lookup"] == "John Doe"
        assert result["payer_info"]["qb_address_line_1"] == "123 Main St"
        assert result["payer_info"]["qb_email"] == ["john@example.com"]
        assert result["payer_info"]["qb_phone"] == ["(555) 123-4567"]
        assert result["payer_info"]["address_needs_update"] is False

        # Check metadata
        assert result["match_status"] == "New"
        assert result["qbo_customer_id"] is None

    def test_combine_payment_data_with_match(self, combiner):
        """Test combining payment data with QBO match."""
        extracted = {
            "Donor Name": "John Smith",
            "Check No.": "9999",
            "Gift Amount": "500",
            "Check Date": "2025-05-28",
            "Address - Line 1": "456 Elm St",  # Different from QBO
            "City": "Chicago",
            "State": "IL",
            "ZIP": "60601",
            "Email": "john.new@example.com",  # New email
        }

        qbo_customer = {
            "Id": "123",
            "SyncToken": "0",
            "DisplayName": "John Smith",
            "GivenName": "John",
            "FamilyName": "Smith",
            "FullyQualifiedName": "John Smith",
            "BillAddr": {
                "Line1": "123 Main St",
                "City": "Springfield",
                "CountrySubDivisionCode": "IL",
                "PostalCode": "62701",
            },
            "PrimaryEmailAddr": {"Address": "john@smithco.com"},
        }

        result = combiner.combine_payment_data(extracted, qbo_customer, "Matched")

        # Check that QBO data is used
        assert result["payer_info"]["customer_lookup"] == "John Smith"
        assert result["payer_info"]["first_name"] == "John"
        assert result["payer_info"]["last_name"] == "Smith"

        # Check address comparison
        assert result["payer_info"]["address_needs_update"] is True
        assert result["payer_info"]["qb_address_line_1"] == "123 Main St"
        assert result["payer_info"]["extracted_address"]["line_1"] == "456 Elm St"

        # Check email was added
        assert "john@smithco.com" in result["payer_info"]["qb_email"]
        assert "john.new@example.com" in result["payer_info"]["qb_email"]

        # Check metadata
        assert result["match_status"] == "Matched"
        assert result["qbo_customer_id"] == "123"
        assert result["qbo_sync_token"] == "0"

    def test_process_batch(self, combiner):
        """Test processing a batch of payments."""
        payments = [
            {"Donor Name": "Alice Johnson", "Check No.": "1111", "Gift Amount": "100", "qbCustomerStatus": "New"},
            {
                "Donor Name": "Bob Smith",
                "Check No.": "2222",
                "Gift Amount": "200",
                "qbCustomerStatus": "Matched",
                "qboCustomerId": "456",
                "customerLookup": "Robert Smith",
                "matchMethod": "donor name",
                "matchConfidence": "high",
            },
        ]

        results = combiner.process_batch(payments)

        assert len(results) == 2

        # First payment - no match
        assert results[0]["match_status"] == "New"
        assert results[0]["payment_info"]["check_no_or_payment_ref"] == "1111"

        # Second payment - matched
        assert results[1]["match_status"] == "Matched"
        assert results[1]["payment_info"]["check_no_or_payment_ref"] == "2222"
        assert results[1]["match_method"] == "donor name"
        assert results[1]["match_confidence"] == "high"
