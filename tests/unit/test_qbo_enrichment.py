"""Unit tests for QBO data enrichment functionality."""

import pytest

from src.utils.qbo_data_enrichment import QBODataEnrichment, calculate_string_similarity, normalize_phone, normalize_zip


class TestQBODataEnrichment:
    """Test cases for QBO data enrichment."""

    def test_extract_qbo_customer_data(self):
        """Test extracting all fields from QBO customer object."""
        # Sample QBO customer object
        qbo_customer = {
            "Id": "123",
            "SyncToken": "0",
            "DisplayName": "John Smith",
            "GivenName": "John",
            "FamilyName": "Smith",
            "FullyQualifiedName": "John Smith",
            "CompanyName": "Smith Enterprises",
            "BillAddr": {
                "Line1": "123 Main St",
                "City": "Springfield",
                "CountrySubDivisionCode": "IL",
                "PostalCode": "62701-1234",
            },
            "PrimaryEmailAddr": {"Address": "john@smithenterprises.com"},
            "PrimaryPhone": {"FreeFormNumber": "(555) 123-4567"},
            "Mobile": {"FreeFormNumber": "(555) 987-6543"},
        }

        result = QBODataEnrichment.extract_qbo_customer_data(qbo_customer)

        assert result["customer_lookup"] == "John Smith"
        assert result["first_name"] == "John"
        assert result["last_name"] == "Smith"
        assert result["full_name"] == "John Smith"
        assert result["qb_organization_name"] == "Smith Enterprises"
        assert result["qb_address_line_1"] == "123 Main St"
        assert result["qb_city"] == "Springfield"
        assert result["qb_state"] == "IL"
        assert result["qb_zip"] == "62701"  # Should normalize to 5 digits
        assert result["qb_email"] == ["john@smithenterprises.com"]
        assert result["qb_phone"] == ["(555) 123-4567", "(555) 987-6543"]
        assert result["qbo_customer_id"] == "123"
        assert result["qbo_sync_token"] == "0"

    def test_compare_addresses_no_update_needed(self):
        """Test address comparison when addresses match."""
        extracted = {"address_line_1": "123 Main Street", "city": "Springfield", "state": "IL", "zip": "62701"}

        qbo = {"qb_address_line_1": "123 Main St", "qb_city": "Springfield", "qb_state": "IL", "qb_zip": "62701"}

        result = QBODataEnrichment.compare_addresses(extracted, qbo)

        # Should not need update - addresses are similar enough
        assert result["address_needs_update"] is False
        assert result["similarity_score"] > 0.5

    def test_compare_addresses_update_needed(self):
        """Test address comparison when update is needed."""
        extracted = {"address_line_1": "456 Elm Avenue", "city": "Chicago", "state": "IL", "zip": "60601"}

        qbo = {"qb_address_line_1": "123 Main St", "qb_city": "Springfield", "qb_state": "IL", "qb_zip": "62701"}

        result = QBODataEnrichment.compare_addresses(extracted, qbo)

        assert result["address_needs_update"] is True
        assert len(result["differences"]) > 0
        assert result["similarity_score"] < 0.5

    def test_merge_email_phone_lists_add_new(self):
        """Test merging when QBO has no email/phone."""
        result = QBODataEnrichment.merge_email_phone_lists(
            "john@example.com", "(555) 123-4567", [], []  # No QBO emails  # No QBO phones
        )

        assert result["emails"] == ["john@example.com"]
        assert result["phones"] == ["(555) 123-4567"]
        assert result["email_added"] is True
        assert result["phone_added"] is True

    def test_merge_email_phone_lists_keep_existing(self):
        """Test merging when extracted matches QBO."""
        result = QBODataEnrichment.merge_email_phone_lists(
            "john@example.com", "(555) 123-4567", ["john@example.com"], ["(555) 123-4567"]
        )

        assert result["emails"] == ["john@example.com"]
        assert result["phones"] == ["(555) 123-4567"]
        assert result["email_added"] is False
        assert result["phone_added"] is False

    def test_merge_email_phone_lists_add_different(self):
        """Test merging when extracted differs from QBO."""
        result = QBODataEnrichment.merge_email_phone_lists(
            "john.new@example.com", "(555) 999-8888", ["john@example.com"], ["(555) 123-4567"]
        )

        assert result["emails"] == ["john@example.com", "john.new@example.com"]
        assert result["phones"] == ["(555) 123-4567", "(555) 999-8888"]
        assert result["email_added"] is True
        assert result["phone_added"] is True


class TestHelperFunctions:
    """Test helper functions."""

    def test_normalize_zip(self):
        """Test ZIP code normalization."""
        assert normalize_zip("62701") == "62701"
        assert normalize_zip("62701-1234") == "62701"
        assert normalize_zip("06511") == "06511"  # Preserve leading zero
        assert normalize_zip("6511") == "06511"  # Pad with leading zero
        assert normalize_zip("") == ""
        assert normalize_zip(None) == ""

    def test_normalize_phone(self):
        """Test phone number normalization."""
        assert normalize_phone("(555) 123-4567") == "5551234567"
        assert normalize_phone("555-123-4567") == "5551234567"
        assert normalize_phone("555.123.4567") == "5551234567"
        assert normalize_phone("15551234567") == "15551234567"
        assert normalize_phone("") == ""

    def test_calculate_string_similarity(self):
        """Test string similarity calculation."""
        # Exact match
        assert calculate_string_similarity("hello", "hello") == 1.0

        # No match
        assert calculate_string_similarity("hello", "world") < 0.5

        # Similar strings
        assert calculate_string_similarity("123 Main St", "123 Main Street") > 0.5

        # Empty strings
        assert calculate_string_similarity("", "") == 0.0
        assert calculate_string_similarity("hello", "") == 0.0
