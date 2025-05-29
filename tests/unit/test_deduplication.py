"""
Unit tests for the deduplication service module.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from services.deduplication import DeduplicationService


class TestDeduplicationService:
    """Test the DeduplicationService class."""

    def test_deduplicate_empty_lists(self):
        """Test deduplication with empty lists."""
        result = DeduplicationService.deduplicate_donations([], [])
        assert result == []

    def test_deduplicate_no_duplicates(self):
        """Test deduplication when there are no duplicates."""
        existing = [
            {"Check No.": "1001", "Gift Amount": "100.00", "Donor Name": "John Doe", "internalId": "donation_0"}
        ]
        new = [{"Check No.": "1002", "Gift Amount": "200.00", "Donor Name": "Jane Smith", "internalId": "donation_1"}]

        result = DeduplicationService.deduplicate_donations(existing, new)

        assert len(result) == 2
        assert any(d["Check No."] == "1001" for d in result)
        assert any(d["Check No."] == "1002" for d in result)

    def test_deduplicate_with_duplicates(self):
        """Test deduplication with duplicate check numbers and amounts."""
        existing = [{"Check No.": "1001", "Gift Amount": "100.00", "Donor Name": "John Doe", "qbCustomerStatus": "New"}]
        new = [
            {
                "Check No.": "1001",
                "Gift Amount": "$100.00",  # With currency symbol
                "Donor Name": "John Doe",
                "Address - Line 1": "123 Main St",  # Additional info
                "qbCustomerStatus": "Matched",
                "qboCustomerId": "QB123",
            }
        ]

        with patch("src.services.deduplication.logger") as mock_logger:
            result = DeduplicationService.deduplicate_donations(existing, new)

        assert len(result) == 1
        donation = result[0]
        assert donation["Check No."] == "1001"
        assert donation["Gift Amount"] == "$100.00"
        assert donation["Address - Line 1"] == "123 Main St"
        # Should preserve the matched status from new donation
        assert donation["qbCustomerStatus"] == "Matched"
        assert donation["qboCustomerId"] == "QB123"

    def test_deduplicate_non_check_donations(self):
        """Test deduplication of non-check donations using donor/amount/date."""
        existing = [
            {
                "Donor Name": "John Doe",
                "Gift Amount": "50.00",
                "Gift Date": "2024-01-15",
                "Check No.": "",  # No check number
            }
        ]
        new = [
            {
                "Donor Name": "JOHN DOE",  # Different case
                "Gift Amount": "50.00",
                "Gift Date": "01/15/2024",  # Different format
                "Check No.": "",
                "Memo": "Online donation",
            }
        ]

        result = DeduplicationService.deduplicate_donations(existing, new)

        assert len(result) == 1
        assert result[0]["Memo"] == "Online donation"

    def test_suspicious_check_number_warning(self, capsys):
        """Test warning for suspicious check numbers."""
        donations = [{"Check No.": "195", "Gift Amount": "100.00", "Donor Name": "Test Donor"}]  # Suspiciously short

        DeduplicationService.deduplicate_donations([], donations)

        captured = capsys.readouterr()
        assert "WARNING: Suspicious check number '195'" in captured.out

    def test_generate_unique_key_check_donation(self):
        """Test unique key generation for check donations."""
        donation = {
            "Check No.": "001234",  # Leading zeros
            "Gift Amount": "$1,234.56",  # Formatted amount
            "Donor Name": "Test Donor",
        }

        key = DeduplicationService._generate_unique_key(donation)

        assert key == "CHECK_1234_1234.56"

    def test_generate_unique_key_non_check_donation(self):
        """Test unique key generation for non-check donations."""
        donation = {
            "Donor Name": "John O'Brien",  # Special characters
            "Gift Amount": "100",
            "Gift Date": "2024-01-15",
            "Check No.": "",
        }

        key = DeduplicationService._generate_unique_key(donation)

        assert key == "OTHER_john obrien_100.00_2024-01-15"

    def test_generate_unique_key_insufficient_data(self):
        """Test unique key generation with insufficient data."""
        donation = {
            "Donor Name": "Test",
            # Missing amount
        }

        key = DeduplicationService._generate_unique_key(donation)

        assert key is None

    def test_merge_donation_data_basic(self):
        """Test basic donation data merging."""
        existing = {
            "Check No.": "1001",
            "Gift Amount": "100.00",
            "Donor Name": "John Doe",
            "Address - Line 1": "",  # Empty
            "qbCustomerStatus": "New",
        }
        new = {
            "Check No.": "1001",
            "Gift Amount": "100.00",
            "Donor Name": "John Doe",
            "Address - Line 1": "123 Main St",  # Has value
            "City": "Anytown",
            "qbCustomerStatus": "New",
        }

        with patch("src.services.deduplication.logger") as mock_logger:
            result = DeduplicationService.merge_donation_data(existing, new)

        assert result["Address - Line 1"] == "123 Main St"
        assert result["City"] == "Anytown"
        assert "mergeHistory" in result

    def test_merge_donation_data_memo_concatenation(self):
        """Test memo field concatenation during merge."""
        existing = {"Memo": "First memo", "Check No.": "1001", "Gift Amount": "100.00"}
        new = {"Memo": "Second memo", "Check No.": "1001", "Gift Amount": "100.00"}

        with patch("src.services.deduplication.logger") as mock_logger:
            result = DeduplicationService.merge_donation_data(existing, new)

        assert result["Memo"] == "First memo; Second memo"

    def test_merge_customer_fields_existing_matched(self):
        """Test customer field merging when existing has match."""
        existing = {"qbCustomerStatus": "Matched", "qboCustomerId": "QB123", "matchConfidence": 85}
        new = {"qbCustomerStatus": "New"}

        merged = {}
        DeduplicationService._merge_customer_fields(merged, existing, new)

        assert merged["qbCustomerStatus"] == "Matched"
        assert merged["qboCustomerId"] == "QB123"

    def test_merge_customer_fields_new_matched(self):
        """Test customer field merging when new has match."""
        existing = {"qbCustomerStatus": "New"}
        new = {"qbCustomerStatus": "Matched", "qboCustomerId": "QB456", "matchConfidence": 90}

        merged = {}
        DeduplicationService._merge_customer_fields(merged, existing, new)

        assert merged["qbCustomerStatus"] == "Matched"
        assert merged["qboCustomerId"] == "QB456"

    def test_merge_customer_fields_both_matched_higher_confidence(self):
        """Test customer field merging when both matched, new has higher confidence."""
        existing = {"qbCustomerStatus": "Matched", "qboCustomerId": "QB123", "matchConfidence": 75}
        new = {"qbCustomerStatus": "Matched", "qboCustomerId": "QB456", "matchConfidence": 95}

        merged = {}
        DeduplicationService._merge_customer_fields(merged, existing, new)

        assert merged["qbCustomerStatus"] == "Matched"
        assert merged["qboCustomerId"] == "QB456"  # Higher confidence wins

    def test_internal_id_assignment(self):
        """Test that internal IDs are assigned to donations without them."""
        donations = [
            {"Check No.": "1001", "Gift Amount": "100"},
            {"Check No.": "1002", "Gift Amount": "200", "internalId": "existing_id"},
            {"Check No.": "1003", "Gift Amount": "300"},
        ]

        result = DeduplicationService.deduplicate_donations(donations, [])

        # Check all have internal IDs
        for donation in result:
            assert "internalId" in donation
            assert donation["internalId"] is not None

        # Check existing ID is preserved
        existing_id_donation = next(d for d in result if d["Check No."] == "1002")
        assert existing_id_donation["internalId"] == "existing_id"

    def test_merge_history_tracking(self):
        """Test that merge history is properly tracked."""
        existing = [{"Check No.": "1001", "Gift Amount": "100.00", "Donor Name": "John Doe"}]
        new = [
            {"Check No.": "1001", "Gift Amount": "100.00", "Donor Name": "John Doe", "Address - Line 1": "123 Main St"}
        ]

        with patch("src.services.deduplication.logger") as mock_logger:
            result = DeduplicationService.deduplicate_donations(existing, new)

        donation = result[0]
        assert "mergeHistory" in donation
        assert len(donation["mergeHistory"]) == 1

        history_entry = donation["mergeHistory"][0]
        assert "timestamp" in history_entry
        assert "mergedFields" in history_entry
        assert "Address - Line 1" in history_entry["mergedFields"]
        assert history_entry["sourceData"]["checkNo"] == "1001"
        assert donation.get("isMerged") is True
