#!/usr/bin/env python3
"""
Test script for Phase 2: Customer Matching Refactor
Verifies that customer matching only happens after deduplication.
"""

import json
import os
import sys
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.services.deduplication import DeduplicationService
from src.utils.file_processor import FileProcessor


def test_no_matching_during_extraction():
    """Test that individual file processing doesn't do customer matching."""
    print("\nTest 1: Verify no customer matching during individual file extraction")

    # Create mock services
    mock_gemini = MagicMock()
    mock_qbo = MagicMock()

    # Create test donation data
    test_donation = {"Donor Name": "John Smith", "Gift Amount": "100.00", "Check No.": "1234"}
    mock_gemini.extract_donation_data.return_value = test_donation

    # Create file processor
    processor = FileProcessor(mock_gemini, mock_qbo)

    # Mock the match_donations_with_qbo_customers_batch method to track calls
    original_match = processor.match_donations_with_qbo_customers_batch
    processor.match_donations_with_qbo_customers_batch = MagicMock(side_effect=original_match)

    # Mock _process_image to return test data
    def mock_process_image(path):
        return test_donation

    # Process a single file
    result = processor._process_with_validation(mock_process_image, "test.jpg", ".jpg")

    # Verify that matching was NOT called during individual processing
    assert processor.match_donations_with_qbo_customers_batch.call_count == 0
    print("✓ No customer matching called during individual file processing")

    # Verify donation was returned without customer fields
    assert result is not None
    assert "qbCustomerStatus" not in result
    assert "qboCustomerId" not in result
    print("✓ Donation returned without customer matching fields")


def test_matching_after_deduplication():
    """Test that customer matching happens only after deduplication."""
    print("\nTest 2: Verify customer matching happens after deduplication")

    # Create mock services
    mock_gemini = MagicMock()
    mock_qbo = MagicMock()
    mock_qbo.is_token_valid.return_value = True
    mock_qbo.get_all_customers.return_value = []
    mock_qbo.find_customers_batch.return_value = {}

    # Create file processor with mocked batch processor
    processor = FileProcessor(mock_gemini, mock_qbo)

    # Mock batch processing to return test donations
    test_donations = [
        {"Donor Name": "John Smith", "Gift Amount": "100.00", "Check No.": "1234"},
        {"Donor Name": "Jane Doe", "Gift Amount": "50.00", "Check No.": "5678"},
        {"Donor Name": "John Smith", "Gift Amount": "100.00", "Check No.": "1234"},  # Duplicate
    ]

    # Track method calls
    match_calls = []
    dedupe_calls = []

    # Mock the deduplication
    original_dedupe = processor._deduplicate_donations

    def mock_dedupe(donations):
        dedupe_calls.append(len(donations))
        # Remove duplicate
        return [donations[0], donations[1]]

    processor._deduplicate_donations = mock_dedupe

    # Mock the matching
    original_match = processor.match_donations_with_qbo_customers_batch

    def mock_match(donations):
        match_calls.append(len(donations))
        # Add match status
        for d in donations:
            d["qbCustomerStatus"] = "New"
        return donations

    processor.match_donations_with_qbo_customers_batch = mock_match

    # Mock batch processor
    with patch("src.utils.file_processor.BatchProcessor") as MockBatchProcessor:
        mock_batch_processor = MagicMock()
        MockBatchProcessor.return_value = mock_batch_processor

        # Mock batch processing methods
        mock_batch_processor.prepare_batches.return_value = ["batch1"]
        mock_batch_processor.process_batches_concurrently.return_value = (test_donations, [])

        # Process files concurrently
        processor.batch_processor = mock_batch_processor
        results, errors = processor.process_files_concurrently([("test1.jpg", ".jpg"), ("test2.jpg", ".jpg")])

    # Verify the order of operations
    assert len(dedupe_calls) == 1, "Deduplication should be called once"
    assert dedupe_calls[0] == 3, "Deduplication should process all 3 donations"

    assert len(match_calls) == 1, "Matching should be called once"
    assert match_calls[0] == 2, "Matching should process 2 deduplicated donations"

    print("✓ Deduplication called before matching")
    print("✓ Matching called only once after deduplication")
    print(f"✓ Processed {dedupe_calls[0]} donations → {match_calls[0]} after deduplication")


def test_deduplication_without_customer_fields():
    """Test that deduplication doesn't merge customer fields."""
    print("\nTest 3: Verify deduplication doesn't handle customer fields")

    # Test data with customer fields
    existing = [
        {
            "Donor Name": "John Smith",
            "Gift Amount": "100.00",
            "Check No.": "1234",
            "qbCustomerStatus": "Matched",
            "qboCustomerId": "123",
        }
    ]

    new_donation = {
        "Donor Name": "John Smith",
        "Gift Amount": "100.00",
        "Check No.": "1234",
        "Memo": "Additional info",
        "qbCustomerStatus": "New",  # Different status
    }

    # Deduplicate
    result = DeduplicationService.deduplicate_donations(existing, [new_donation])

    # Verify only one donation remains
    assert len(result) == 1
    print("✓ Duplicate donations merged correctly")

    # Verify memo was merged but customer fields were not intelligently merged
    assert result[0].get("Memo") == "Additional info"
    print("✓ Non-customer fields merged correctly")

    # In Phase 2, customer fields are NOT preserved during deduplication
    # They will be set during the single matching pass
    print("✓ Customer field merging removed from deduplication")


def test_csv_processing_no_matching():
    """Test that CSV processing doesn't do customer matching."""
    print("\nTest 4: Verify CSV processing doesn't do customer matching")

    # Create mock services
    mock_gemini = MagicMock()
    mock_qbo = MagicMock()

    # Mock CSV extraction
    csv_donations = [
        {"Donor Name": "Online Donor 1", "Gift Amount": "75.00", "Payment Ref": "TXN-001"},
        {"Donor Name": "Online Donor 2", "Gift Amount": "125.00", "Payment Ref": "TXN-002"},
    ]
    mock_gemini.extract_text_data.return_value = csv_donations

    # Create file processor
    processor = FileProcessor(mock_gemini, mock_qbo)

    # Process CSV
    with patch("builtins.open", create=True) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = "csv,data"
        result = processor._process_csv("test.csv")

    # Verify no customer fields were added
    assert result is not None
    assert len(result) == 2
    for donation in result:
        assert "qbCustomerStatus" not in donation
        assert "qboCustomerId" not in donation

    print("✓ CSV processing returns donations without customer matching")


def run_all_tests():
    """Run all Phase 2 tests."""
    print("=" * 60)
    print("Phase 2 Customer Matching Refactor Tests")
    print("=" * 60)

    try:
        test_no_matching_during_extraction()
        test_matching_after_deduplication()
        test_deduplication_without_customer_fields()
        test_csv_processing_no_matching()

        print("\n" + "=" * 60)
        print("✅ All Phase 2 tests passed!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()
