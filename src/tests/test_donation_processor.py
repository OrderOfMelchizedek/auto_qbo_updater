"""Tests for donation processor pipeline."""
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.donation_processor import process_donation_documents


class TestDonationProcessor:
    """Test donation processing pipeline."""

    @patch("src.donation_processor.extract_donations_from_documents")
    @patch("src.donation_processor.DonationValidator")
    def test_process_donation_documents(self, mock_validator_class, mock_extract):
        """Test that extraction output is piped to validation."""
        # Mock extraction output
        raw_donations = [
            {
                "PaymentInfo": {
                    "Payment_Ref": "001234",
                    "Amount": "100.00",
                    "Payment_Method": "printed check",
                },
                "PayerInfo": {"Aliases": ["JOHN SMITH"]},
            },
            {
                "PaymentInfo": {
                    "Payment_Ref": "001234",  # Duplicate
                    "Amount": "100.00",
                    "Payment_Date": "2024-01-15",
                }
            },
        ]
        mock_extract.return_value = raw_donations

        # Mock validator
        mock_validator = MagicMock()
        mock_validator_class.return_value = mock_validator

        # Expected processed output
        processed_donations = [
            {
                "PaymentInfo": {
                    "Payment_Ref": "1234",
                    "Amount": 100.00,
                    "Payment_Method": "printed check",
                    "Payment_Date": "2024-01-15",
                },
                "PayerInfo": {"Aliases": ["John Smith"]},
            }
        ]
        mock_validator.process_donations.return_value = processed_donations

        # Run the processor
        file_paths = ["test1.pdf", "test2.jpg"]
        result, metadata = process_donation_documents(file_paths)

        # Verify extraction was called with file paths
        mock_extract.assert_called_once_with(file_paths)

        # Verify validation was called with extraction output
        mock_validator.process_donations.assert_called_once_with(raw_donations)

        # Verify result is the processed output
        assert result == processed_donations
        assert metadata["raw_count"] == 2
        assert metadata["valid_count"] == 1
        assert metadata["duplicate_count"] == 1


@pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY not set - skipping integration tests",
)
class TestDonationProcessorIntegration:
    """Integration tests for all test batches."""

    @pytest.fixture
    def test_files_dir(self):
        """Get the test files directory."""
        return Path(__file__).parent / "test_files"

    def test_batch_1(self, test_files_dir):
        """Test batch 1 files."""
        file_paths = [
            test_files_dir / "test_batch_1" / "2025-05-17 12.50.27-1.jpg",
            test_files_dir / "test_batch_1" / "2025-05-17-12-48-17.pdf",
        ]

        results, metadata = process_donation_documents(file_paths)

        # Verify we got results
        assert len(results) > 0

        # Verify each result has required fields
        for donation in results:
            assert "PaymentInfo" in donation
            assert "Payment_Ref" in donation["PaymentInfo"]
            assert "Amount" in donation["PaymentInfo"]
            assert donation["PaymentInfo"]["Amount"] > 0

    def test_batch_2(self, test_files_dir):
        """Test batch 2 files."""
        file_paths = [
            test_files_dir / "test_batch_2" / "20250411_205258.jpg",
            test_files_dir / "test_batch_2" / "20250411_205415.jpg",
        ]

        results = process_donation_documents(file_paths)

        assert len(results) > 0
        for donation in results:
            assert "PaymentInfo" in donation
            assert "Payment_Ref" in donation["PaymentInfo"]
            assert "Amount" in donation["PaymentInfo"]

    def test_batch_3(self, test_files_dir):
        """Test batch 3 files."""
        file_paths = [
            test_files_dir / "test_batch_3" / "2025-01-11-15-27-04.pdf",
            test_files_dir / "test_batch_3" / "2025-01-11-15-36-44.pdf",
        ]

        results = process_donation_documents(file_paths)

        assert len(results) > 0
        for donation in results:
            assert "PaymentInfo" in donation
            assert "Payment_Ref" in donation["PaymentInfo"]
            assert "Amount" in donation["PaymentInfo"]

    def test_batch_4(self, test_files_dir):
        """Test batch 4 files - largest batch with 7 files."""
        file_paths = [
            test_files_dir / "test_batch_4" / "2025-03-01-16-45-21.pdf",
            test_files_dir / "test_batch_4" / "20250207182439287.pdf",
            test_files_dir / "test_batch_4" / "20250328_195721.jpg",
            test_files_dir / "test_batch_4" / "20250328_195746.jpg",
            test_files_dir / "test_batch_4" / "20250328_195802.jpg",
            test_files_dir / "test_batch_4" / "20250328_195844.jpg",
            test_files_dir / "test_batch_4" / "20250328_195901.jpg",
        ]

        results = process_donation_documents(file_paths)

        assert len(results) > 0
        for donation in results:
            assert "PaymentInfo" in donation
            assert "Payment_Ref" in donation["PaymentInfo"]
            assert "Amount" in donation["PaymentInfo"]

    def test_all_batches_summary(self, test_files_dir, capsys):
        """Test all batches and print summary."""
        batches = {
            "Batch 1": [
                test_files_dir / "test_batch_1" / "2025-05-17 12.50.27-1.jpg",
                test_files_dir / "test_batch_1" / "2025-05-17-12-48-17.pdf",
            ],
            "Batch 2": [
                test_files_dir / "test_batch_2" / "20250411_205258.jpg",
                test_files_dir / "test_batch_2" / "20250411_205415.jpg",
            ],
            "Batch 3": [
                test_files_dir / "test_batch_3" / "2025-01-11-15-27-04.pdf",
                test_files_dir / "test_batch_3" / "2025-01-11-15-36-44.pdf",
            ],
            "Batch 4": [
                test_files_dir / "test_batch_4" / "2025-03-01-16-45-21.pdf",
                test_files_dir / "test_batch_4" / "20250207182439287.pdf",
                test_files_dir / "test_batch_4" / "20250328_195721.jpg",
                test_files_dir / "test_batch_4" / "20250328_195746.jpg",
                test_files_dir / "test_batch_4" / "20250328_195802.jpg",
                test_files_dir / "test_batch_4" / "20250328_195844.jpg",
                test_files_dir / "test_batch_4" / "20250328_195901.jpg",
            ],
        }

        all_results = {}
        total_donations = 0

        print("\n" + "=" * 60)
        print("PROCESSING ALL TEST BATCHES")
        print("=" * 60)

        for batch_name, file_paths in batches.items():
            print(f"\n{batch_name}:")
            print(f"  Files: {len(file_paths)}")

            try:
                results = process_donation_documents(file_paths)
                all_results[batch_name] = results
                total_donations += len(results)

                print(f"  Processed donations: {len(results)}")

                # Show sample data from first donation
                if results:
                    donation = results[0]
                    payment = donation.get("PaymentInfo", {})
                    print(
                        f"  Sample - Ref: {payment.get('Payment_Ref')}, "
                        f"Amount: ${payment.get('Amount', 0):.2f}"
                    )

            except Exception as e:
                print(f"  Error: {str(e)}")
                all_results[batch_name] = []

        print(f"\nTOTAL DONATIONS PROCESSED: {total_donations}")

        # Assertions
        assert len(all_results) == 4
        assert all(batch_name in all_results for batch_name in batches.keys())
        assert total_donations > 0

    def test_batch_with_validation_details(self, test_files_dir):
        """Test batch with detailed validation and deduplication analysis."""
        from src.geminiservice import extract_donations_from_documents
        from src.validation import DonationValidator

        # Use batch 1 for detailed analysis
        file_paths = [
            test_files_dir / "test_batch_1" / "2025-05-17 12.50.27-1.jpg",
            test_files_dir / "test_batch_1" / "2025-05-17-12-48-17.pdf",
        ]

        print("\n" + "=" * 60)
        print("DETAILED VALIDATION AND DEDUPLICATION ANALYSIS")
        print("=" * 60)

        # Step 1: Raw extraction
        print("\n1. RAW EXTRACTION:")
        raw_donations = extract_donations_from_documents(file_paths)
        print(f"   Found {len(raw_donations)} raw entries")

        # Step 2: Process through validation and deduplication
        print("\n2. AFTER VALIDATION & DEDUPLICATION:")
        processed_donations = process_donation_documents(file_paths)
        print(f"   Resulted in {len(processed_donations)} valid entries")

        removed = len(raw_donations) - len(processed_donations)
        if removed > 0:
            print(f"   Removed {removed} entries (duplicates or invalid)")

        # Step 3: Show validation changes
        print("\n3. VALIDATION CHANGES:")
        validator = DonationValidator()

        for i, raw in enumerate(raw_donations):
            print(f"\n   Entry {i+1}:")
            validated = validator.validate_entry(raw)

            # Check payment ref changes
            raw_payment = raw.get("PaymentInfo", {})
            val_payment = validated.get("PaymentInfo", {})

            if raw_payment.get("Payment_Ref") != val_payment.get("Payment_Ref"):
                print(
                    f"     Check number: '{raw_payment.get('Payment_Ref')}' → "
                    f"'{val_payment.get('Payment_Ref')}'"
                )

            # Check text case changes
            raw_payer = raw.get("PayerInfo", {})
            val_payer = validated.get("PayerInfo", {})

            if raw_payer.get("Organization_Name") != val_payer.get("Organization_Name"):
                print(
                    f"     Organization: '{raw_payer.get('Organization_Name')}' → "
                    f"'{val_payer.get('Organization_Name')}'"
                )

            # Check aliases
            raw_aliases = raw_payer.get("Aliases", [])
            val_aliases = val_payer.get("Aliases", [])
            if raw_aliases != val_aliases:
                print(f"     Aliases: {raw_aliases} → {val_aliases}")

            # Check address changes
            raw_contact = raw.get("ContactInfo", {})
            val_contact = validated.get("ContactInfo", {})

            if raw_contact.get("Address_Line_1") != val_contact.get("Address_Line_1"):
                print(
                    f"     Address: '{raw_contact.get('Address_Line_1')}' → "
                    f"'{val_contact.get('Address_Line_1')}'"
                )

            if raw_contact.get("ZIP") != val_contact.get("ZIP"):
                print(
                    f"     ZIP: '{raw_contact.get('ZIP')}' → '{val_contact.get('ZIP')}'"
                )

        # Assertions
        assert len(processed_donations) > 0
        assert all("PaymentInfo" in d for d in processed_donations)
        assert all("Payment_Ref" in d["PaymentInfo"] for d in processed_donations)
        assert all("Amount" in d["PaymentInfo"] for d in processed_donations)
