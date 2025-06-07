"""Tests for customer matching logic."""
from unittest.mock import MagicMock, patch

import pytest

from src.customer_matcher import (
    CustomerMatcher,
    calculate_match_score,
    compare_addresses,
)


class TestAddressComparison:
    """Test address comparison logic."""

    def test_compare_addresses_exact_match(self):
        """Test exact address match."""
        extracted = {
            "line1": "123 Main St",
            "city": "Springfield",
            "state": "CA",
            "zip": "94025",
        }
        qb = {
            "line1": "123 Main St",
            "city": "Springfield",
            "state": "CA",
            "zip": "94025",
        }
        result = compare_addresses(extracted, qb)
        assert result["match_percentage"] == 100
        assert result["should_update"] is False

    def test_compare_addresses_minor_differences(self):
        """Test addresses with minor differences (< 50%)."""
        extracted = {
            "line1": "123 Main Street",  # Street vs St
            "city": "Springfield",
            "state": "CA",
            "zip": "94025",
        }
        qb = {
            "line1": "123 Main St",
            "city": "Springfield",
            "state": "CA",
            "zip": "94025",
        }
        result = compare_addresses(extracted, qb)
        assert result["match_percentage"] > 50
        assert result["should_update"] is False

    def test_compare_addresses_major_differences(self):
        """Test addresses with major differences (> 50%)."""
        extracted = {
            "line1": "456 Oak Avenue Apt 5B",
            "city": "San Francisco",
            "state": "CA",
            "zip": "94105",
        }
        qb = {
            "line1": "123 Main St",
            "city": "Springfield",
            "state": "CA",
            "zip": "94025",
        }
        result = compare_addresses(extracted, qb)
        assert result["match_percentage"] < 50
        assert result["should_update"] is True

    def test_compare_addresses_empty_qb(self):
        """Test when QB has no address."""
        extracted = {
            "line1": "123 Main St",
            "city": "Springfield",
            "state": "CA",
            "zip": "94025",
        }
        qb = {"line1": "", "city": "", "state": "", "zip": ""}
        result = compare_addresses(extracted, qb)
        assert result["should_update"] is True

    def test_compare_addresses_empty_extracted(self):
        """Test when extracted has no address."""
        extracted = {"line1": "", "city": "", "state": "", "zip": ""}
        qb = {
            "line1": "123 Main St",
            "city": "Springfield",
            "state": "CA",
            "zip": "94025",
        }
        result = compare_addresses(extracted, qb)
        assert result["should_update"] is False


class TestMatchScoring:
    """Test customer match scoring."""

    def test_calculate_match_score_exact_name(self):
        """Test exact name match."""
        donation = {"PayerInfo": {"Aliases": ["John Smith"]}}
        customer = {"DisplayName": "John Smith"}
        score = calculate_match_score(donation, customer)
        assert score == 100

    def test_calculate_match_score_case_insensitive(self):
        """Test case-insensitive matching."""
        donation = {"PayerInfo": {"Aliases": ["john smith"]}}
        customer = {"DisplayName": "John Smith"}
        score = calculate_match_score(donation, customer)
        assert score == 100

    def test_calculate_match_score_partial_match(self):
        """Test partial name match."""
        donation = {"PayerInfo": {"Aliases": ["John Smith", "J. Smith"]}}
        customer = {"DisplayName": "J. Smith"}
        score = calculate_match_score(donation, customer)
        assert score == 100  # One alias matches exactly

    def test_calculate_match_score_organization(self):
        """Test organization name matching."""
        donation = {"PayerInfo": {"Organization_Name": "Smith Foundation"}}
        customer = {
            "CompanyName": "Smith Foundation",
            "DisplayName": "Smith Foundation",
        }
        score = calculate_match_score(donation, customer)
        assert score == 100

    def test_calculate_match_score_no_match(self):
        """Test no match."""
        donation = {"PayerInfo": {"Aliases": ["John Smith"]}}
        customer = {"DisplayName": "Jane Doe"}
        score = calculate_match_score(donation, customer)
        assert score < 50


class TestCustomerMatcher:
    """Test customer matching functionality."""

    @pytest.fixture
    def matcher(self):
        """Create matcher with mocked data source."""
        with patch("src.customer_matcher.create_customer_data_source") as mock_create:
            mock_data_source = MagicMock()
            mock_create.return_value = mock_data_source
            matcher = CustomerMatcher(session_id="test-session")
            return matcher

    @pytest.fixture
    def sample_donation(self):
        """Sample extracted donation data."""
        return {
            "PaymentInfo": {"Payment_Ref": "1234", "Amount": 100.00},
            "PayerInfo": {"Aliases": ["John Smith", "J. Smith"], "Salutation": "Mr."},
            "ContactInfo": {
                "Address_Line_1": "123 Main St",
                "City": "Springfield",
                "State": "CA",
                "ZIP": "94025",
                "Email": "john@example.com",
                "Phone": "555-1234",
            },
        }

    @pytest.fixture
    def sample_qb_customer(self):
        """Sample QuickBooks customer data (formatted)."""
        return {
            "customer_ref": {
                "id": "1",
                "first_name": "John",
                "last_name": "Smith",
                "full_name": "John Smith",
                "company_name": None,
            },
            "qb_address": {
                "line1": "123 Main St",
                "city": "Springfield",
                "state": "CA",
                "zip": "94025",
            },
            "qb_email": ["john@example.com"],
            "qb_phone": ["555-1234"],
        }

    def test_match_donation_exact_match(self, matcher, sample_donation):
        """Test exact customer match."""
        # Mock search results
        matcher.data_source.search_customer = MagicMock(
            return_value=[{"Id": "1", "DisplayName": "John Smith"}]
        )
        matcher.data_source.get_customer = MagicMock(
            return_value={
                "Id": "1",
                "DisplayName": "John Smith",
                "GivenName": "John",
                "FamilyName": "Smith",
            }
        )
        matcher.data_source.format_customer_data = MagicMock(
            return_value={
                "customer_ref": {
                    "id": "1",
                    "first_name": "John",
                    "last_name": "Smith",
                    "full_name": "John Smith",
                    "company_name": None,
                },
                "qb_address": {
                    "line1": "123 Main St",
                    "city": "Springfield",
                    "state": "CA",
                    "zip": "94025",
                },
                "qb_email": ["john@example.com"],
                "qb_phone": ["555-1234"],
            }
        )

        result = matcher.match_donation_to_customer(sample_donation)

        assert result["match_status"] == "matched"
        assert result["customer_ref"]["id"] == "1"
        assert result["updates_needed"]["address"] is False
        assert result["updates_needed"]["email_added"] is False
        assert result["updates_needed"]["phone_added"] is False

    def test_match_donation_no_match(self, matcher, sample_donation):
        """Test when no customer matches."""
        matcher.data_source.search_customer = MagicMock(return_value=[])

        result = matcher.match_donation_to_customer(sample_donation)

        assert result["match_status"] == "new_customer"
        assert result["customer_ref"] is None

    def test_match_donation_address_update_needed(self, matcher, sample_donation):
        """Test when address needs updating."""
        sample_donation["ContactInfo"]["Address_Line_1"] = "456 Oak Ave"

        matcher.data_source.search_customer = MagicMock(
            return_value=[{"Id": "1", "DisplayName": "John Smith"}]
        )
        matcher.data_source.get_customer = MagicMock(
            return_value={
                "Id": "1",
                "DisplayName": "John Smith",
            }
        )
        matcher.data_source.format_customer_data = MagicMock(
            return_value={
                "customer_ref": {"id": "1", "full_name": "John Smith"},
                "qb_address": {
                    "line1": "123 Main St",
                    "city": "Springfield",
                    "state": "CA",
                    "zip": "94025",
                },
                "qb_email": ["john@example.com"],
                "qb_phone": ["555-1234"],
            }
        )

        result = matcher.match_donation_to_customer(sample_donation)

        assert result["match_status"] == "matched"
        assert result["updates_needed"]["address"] is True
        # Updated address should be included
        assert result["qb_address"]["line1"] == "456 Oak Ave"

    def test_match_donation_add_missing_email(self, matcher, sample_donation):
        """Test adding email when QB doesn't have one."""
        matcher.data_source.search_customer = MagicMock(
            return_value=[{"Id": "1", "DisplayName": "John Smith"}]
        )
        matcher.data_source.format_customer_data = MagicMock(
            return_value={
                "customer_ref": {"id": "1", "full_name": "John Smith"},
                "qb_address": {
                    "line1": "123 Main St",
                    "city": "Springfield",
                    "state": "CA",
                    "zip": "94025",
                },
                "qb_email": [],  # No email in QB
                "qb_phone": ["555-1234"],
            }
        )

        result = matcher.match_donation_to_customer(sample_donation)

        assert result["updates_needed"]["email_added"] is True
        assert "john@example.com" in result["qb_email"]

    def test_match_donation_add_missing_phone(self, matcher, sample_donation):
        """Test adding phone when QB doesn't have one."""
        matcher.data_source.search_customer = MagicMock(
            return_value=[{"Id": "1", "DisplayName": "John Smith"}]
        )
        matcher.data_source.format_customer_data = MagicMock(
            return_value={
                "customer_ref": {"id": "1", "full_name": "John Smith"},
                "qb_address": {
                    "line1": "123 Main St",
                    "city": "Springfield",
                    "state": "CA",
                    "zip": "94025",
                },
                "qb_email": ["john@example.com"],
                "qb_phone": [],  # No phone in QB
            }
        )

        result = matcher.match_donation_to_customer(sample_donation)

        assert result["updates_needed"]["phone_added"] is True
        assert "555-1234" in result["qb_phone"]

    def test_match_donation_dont_overwrite_existing_contact(
        self, matcher, sample_donation
    ):
        """Test that existing QB email/phone is not overwritten."""
        sample_donation["ContactInfo"]["Email"] = "newemail@example.com"
        sample_donation["ContactInfo"]["Phone"] = "555-9999"

        matcher.data_source.search_customer = MagicMock(
            return_value=[{"Id": "1", "DisplayName": "John Smith"}]
        )
        matcher.data_source.format_customer_data = MagicMock(
            return_value={
                "customer_ref": {"id": "1", "full_name": "John Smith"},
                "qb_address": {
                    "line1": "123 Main St",
                    "city": "Springfield",
                    "state": "CA",
                    "zip": "94025",
                },
                "qb_email": ["john@example.com"],
                "qb_phone": ["555-1234"],
            }
        )

        result = matcher.match_donation_to_customer(sample_donation)

        # Should add new contact info, not replace
        assert "john@example.com" in result["qb_email"]
        assert "newemail@example.com" in result["qb_email"]
        assert "555-1234" in result["qb_phone"]
        assert "555-9999" in result["qb_phone"]

    def test_match_donation_organization(self, matcher):
        """Test matching organization customers."""
        donation = {
            "PaymentInfo": {"Payment_Ref": "5678", "Amount": 500.00},
            "PayerInfo": {"Organization_Name": "Smith Foundation"},
            "ContactInfo": {"Email": "info@smithfoundation.org"},
        }

        matcher.data_source.search_customer = MagicMock(
            return_value=[
                {
                    "Id": "2",
                    "DisplayName": "Smith Foundation",
                    "CompanyName": "Smith Foundation",
                }
            ]
        )
        matcher.data_source.format_customer_data = MagicMock(
            return_value={
                "customer_ref": {
                    "id": "2",
                    "full_name": "Smith Foundation",
                    "company_name": "Smith Foundation",
                },
                "qb_address": {},
                "qb_email": ["info@smithfoundation.org"],
                "qb_phone": [],
            }
        )

        result = matcher.match_donation_to_customer(donation)

        assert result["match_status"] == "matched"
        assert result["customer_ref"]["company_name"] == "Smith Foundation"

    def test_merge_customer_data(self, matcher, sample_donation, sample_qb_customer):
        """Test merging extracted and QB data."""
        result = matcher.merge_customer_data(sample_donation, sample_qb_customer)

        # Should have all QB data
        assert result["customer_ref"] == sample_qb_customer["customer_ref"]
        assert result["qb_address"] == sample_qb_customer["qb_address"]

        # Should not have duplicated contact info
        assert len(result["qb_email"]) == 1
        assert len(result["qb_phone"]) == 1

        # Should indicate no updates needed
        assert result["updates_needed"]["address"] is False
        assert result["updates_needed"]["email_added"] is False
        assert result["updates_needed"]["phone_added"] is False
