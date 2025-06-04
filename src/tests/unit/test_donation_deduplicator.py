"""Tests for donation deduplication service."""
import pytest

from src.models.donation import DonationEntry
from src.services.deduplication.donation_deduplicator import (
    DeduplicationError,
    DonationDeduplicator,
)


@pytest.fixture
def deduplicator():
    """Create deduplicator instance."""
    return DonationDeduplicator()


@pytest.fixture
def sample_donations():
    """Sample donation data with duplicates."""
    return [
        {
            "payment_info": {
                "payment_method": "check",
                "check_no": "001234",
                "amount": 100.00,
                "payment_date": "2025-01-15",
            },
            "payer_info": {
                "name": "John Doe",
                "aliases": ["John Doe"],
            },
            "contact_info": {
                "address_line_1": "123 Main St",
                "city": "Anytown",
                "state": "CA",
                "zip": "12345",
            },
            "source_documents": ["doc1"],
        },
        {
            # Duplicate of first (same check # and amount)
            "payment_info": {
                "payment_method": "check",
                "check_no": "1234",  # Leading zeros stripped
                "amount": 100.00,
                "payment_date": "2025-01-16",  # Different date
            },
            "payer_info": {
                "name": "J. Doe",
                "aliases": ["J. Doe"],  # Different alias
            },
            "contact_info": {
                "address_line_1": "123 Main Street",  # Slightly different
                "city": "Anytown",
                "state": "CA",
                "zip": "12345",
                "email": "john@example.com",  # Additional info
            },
            "source_documents": ["doc2"],
        },
        {
            # Different donation
            "payment_info": {
                "payment_method": "check",
                "check_no": "5678",
                "amount": 200.00,
                "payment_date": "2025-01-15",
            },
            "payer_info": {
                "name": "Jane Smith",
                "aliases": ["Jane Smith"],
            },
            "contact_info": {
                "address_line_1": "456 Oak Ave",
                "city": "Other City",
                "state": "NY",
                "zip": "54321",
            },
            "source_documents": ["doc3"],
        },
    ]


class TestDonationDeduplicator:
    """Test donation deduplication functionality."""

    def test_deduplicate_empty_list(self, deduplicator):
        """Test deduplication with empty list."""
        donations, merge_log = deduplicator.deduplicate_donations([])

        assert donations == []
        assert merge_log == []

    def test_deduplicate_no_duplicates(self, deduplicator):
        """Test deduplication when there are no duplicates."""
        donations = [
            {
                "payment_info": {
                    "payment_method": "check",
                    "check_no": "1111",
                    "amount": 100.00,
                },
                "source_documents": ["doc1"],
            },
            {
                "payment_info": {
                    "payment_method": "check",
                    "check_no": "2222",
                    "amount": 200.00,
                },
                "source_documents": ["doc2"],
            },
        ]

        result, merge_log = deduplicator.deduplicate_donations(donations)

        assert len(result) == 2
        assert len(merge_log) == 0

    def test_deduplicate_with_duplicates(self, deduplicator, sample_donations):
        """Test deduplication with duplicate entries."""
        result, merge_log = deduplicator.deduplicate_donations(sample_donations)

        # Should have 2 unique donations (first two are duplicates)
        assert len(result) == 2
        assert len(merge_log) == 1

        # Check merge log
        assert merge_log[0]["merged_count"] == 2
        assert merge_log[0]["check_no"] == "1234"
        assert merge_log[0]["amount"] == 100.00
        assert set(merge_log[0]["source_documents"]) == {"doc1", "doc2"}

    def test_check_number_cleaning(self, deduplicator):
        """Test check number cleaning logic."""
        # Test leading zero stripping
        assert deduplicator._clean_check_number("001234") == "1234"
        assert deduplicator._clean_check_number("0001") == "0001"  # Keep if ≤4 digits
        assert deduplicator._clean_check_number("1234") == "1234"
        assert deduplicator._clean_check_number(None) is None
        assert deduplicator._clean_check_number("") is None

    def test_merge_aliases(self, deduplicator, sample_donations):
        """Test that aliases are properly merged."""
        result, _ = deduplicator.deduplicate_donations(sample_donations)

        # Find the merged donation
        merged_donation = None
        for donation in result:
            if donation.payment_info and donation.payment_info.amount == 100.00:
                merged_donation = donation
                break

        assert merged_donation is not None
        assert merged_donation.payer_info is not None
        # Should have both aliases
        assert set(merged_donation.payer_info.aliases) == {"John Doe", "J. Doe"}

    def test_merge_contact_info(self, deduplicator, sample_donations):
        """Test that contact info is properly merged."""
        result, _ = deduplicator.deduplicate_donations(sample_donations)

        # Find the merged donation
        merged_donation = None
        for donation in result:
            if donation.payment_info and donation.payment_info.amount == 100.00:
                merged_donation = donation
                break

        assert merged_donation is not None
        assert merged_donation.contact_info is not None
        # Should have the email from the second record
        assert merged_donation.contact_info.email == "john@example.com"
        # Should use the longer address
        assert merged_donation.contact_info.address is not None
        assert "Street" in merged_donation.contact_info.address.street1

    def test_earliest_date_selection(self, deduplicator, sample_donations):
        """Test that earliest date is selected when merging."""
        result, _ = deduplicator.deduplicate_donations(sample_donations)

        # Find the merged donation
        merged_donation = None
        for donation in result:
            if donation.payment_info and donation.payment_info.amount == 100.00:
                merged_donation = donation
                break

        assert merged_donation is not None
        assert merged_donation.payment_info is not None
        # Should have the earlier date (2025-01-15)
        assert str(merged_donation.payment_info.payment_date) == "2025-01-15"

    def test_no_check_number(self, deduplicator):
        """Test handling donations without check numbers."""
        donations = [
            {
                "payment_info": {
                    "payment_method": "cash",
                    "amount": 50.00,
                },
                "source_documents": ["doc1"],
            },
            {
                "payment_info": {
                    "payment_method": "cash",
                    "amount": 50.00,
                },
                "source_documents": ["doc2"],
            },
        ]

        result, merge_log = deduplicator.deduplicate_donations(donations)

        # Without check numbers, these are treated as separate
        assert len(result) == 2
        assert len(merge_log) == 0

    def test_different_amounts_not_merged(self, deduplicator):
        """Test entries with same check number but different amounts not merged."""
        donations = [
            {
                "payment_info": {
                    "payment_method": "check",
                    "check_no": "1234",
                    "amount": 100.00,
                },
                "source_documents": ["doc1"],
            },
            {
                "payment_info": {
                    "payment_method": "check",
                    "check_no": "1234",
                    "amount": 150.00,  # Different amount
                },
                "source_documents": ["doc2"],
            },
        ]

        result, merge_log = deduplicator.deduplicate_donations(donations)

        # Should not merge due to different amounts
        assert len(result) == 2
        assert len(merge_log) == 0

    def test_donation_entry_creation(self, deduplicator, sample_donations):
        """Test that DonationEntry objects are properly created."""
        result, _ = deduplicator.deduplicate_donations(sample_donations)

        assert all(isinstance(donation, DonationEntry) for donation in result)

        # Check that all have required fields
        for donation in result:
            assert donation.source_documents is not None
            assert len(donation.source_documents) > 0

    def test_error_handling(self, deduplicator):
        """Test error handling for invalid data."""
        # Invalid data structure - not a list of dictionaries
        invalid_donations = "not a list"

        with pytest.raises(DeduplicationError):
            deduplicator.deduplicate_donations(invalid_donations)
