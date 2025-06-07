"""Tests for donation processor with customer matching."""
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.donation_processor import process_donation_documents


class TestDonationProcessorWithMatching:
    """Test donation processing with customer matching."""

    @patch("src.donation_processor.extract_donations_from_documents")
    @patch("src.donation_processor.DonationValidator")
    @patch("src.donation_processor.CustomerMatcher")
    def test_process_with_matching(
        self, mock_matcher_class, mock_validator_class, mock_extract
    ):
        """Test processing with QuickBooks matching."""
        # Mock extraction output
        raw_donations = [
            {
                "PaymentInfo": {
                    "Payment_Ref": "001234",
                    "Amount": "100.00",
                    "Payment_Method": "printed check",
                },
                "PayerInfo": {"Aliases": ["JOHN SMITH"]},
                "ContactInfo": {
                    "Address_Line_1": "123 Main St",
                    "City": "Springfield",
                    "State": "CA",
                    "ZIP": "94025",
                },
            }
        ]
        mock_extract.return_value = raw_donations

        # Mock validator
        mock_validator = MagicMock()
        mock_validator_class.return_value = mock_validator
        processed_donations = [
            {
                "PaymentInfo": {
                    "Payment_Ref": "1234",
                    "Amount": 100.00,
                    "Payment_Method": "printed check",
                },
                "PayerInfo": {"Aliases": ["John Smith"]},
                "ContactInfo": {
                    "Address_Line_1": "123 Main St",
                    "City": "Springfield",
                    "State": "CA",
                    "ZIP": "94025",
                },
            }
        ]
        mock_validator.process_donations.return_value = processed_donations

        # Mock matcher
        mock_matcher = MagicMock()
        mock_matcher_class.return_value = mock_matcher
        match_result = {
            "match_status": "matched",
            "customer_ref": {"id": "1", "full_name": "John Smith"},
            "qb_address": {
                "line1": "123 Main St",
                "city": "Springfield",
                "state": "CA",
                "zip": "94025",
            },
            "qb_email": ["john@example.com"],
            "qb_phone": ["555-1234"],
            "updates_needed": {
                "address": False,
                "email_added": False,
                "phone_added": False,
            },
        }
        mock_matcher.match_donation_to_customer.return_value = match_result

        # Run processor with session ID
        results, metadata = process_donation_documents(
            ["test.pdf"], session_id="test-session"
        )

        # Verify matching was called
        mock_matcher_class.assert_called_once_with("test-session")
        mock_matcher.match_donation_to_customer.assert_called_once()

        # Verify results include match data
        assert len(results) == 1
        assert "match_data" in results[0]
        assert results[0]["match_data"]["match_status"] == "matched"
        assert results[0]["match_data"]["customer_ref"]["id"] == "1"

        # Verify metadata
        assert metadata["matched_count"] == 1

    @patch("src.donation_processor.extract_donations_from_documents")
    @patch("src.donation_processor.DonationValidator")
    def test_process_without_session(self, mock_validator_class, mock_extract):
        """Test processing without QuickBooks session."""
        raw_donations = [{"PaymentInfo": {"Payment_Ref": "1234", "Amount": "100"}}]
        mock_extract.return_value = raw_donations

        mock_validator = MagicMock()
        mock_validator_class.return_value = mock_validator
        mock_validator.process_donations.return_value = raw_donations

        # Run without session ID
        results, metadata = process_donation_documents(["test.pdf"])

        # Should not have match data
        assert len(results) == 1
        assert "match_data" not in results[0]
        assert metadata["matched_count"] == 0


@pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY not set - skipping integration tests",
)
class TestDonationProcessorRealFiles:
    """Integration tests with real test files."""

    @pytest.fixture
    def test_files_dir(self):
        """Get the test files directory."""
        return Path(__file__).parent / "test_files"

    @pytest.fixture
    def mock_qb_customers(self):
        """Mock QuickBooks customers for testing."""
        return [
            {
                "Id": "1",
                "DisplayName": "John Smith",
                "GivenName": "John",
                "FamilyName": "Smith",
                "BillAddr": {
                    "Line1": "123 Main St",
                    "City": "Springfield",
                    "CountrySubDivisionCode": "CA",
                    "PostalCode": "94025",
                },
            },
            {
                "Id": "2",
                "DisplayName": "Smith Foundation",
                "CompanyName": "Smith Foundation",
                "BillAddr": {
                    "Line1": "456 Corporate Blvd",
                    "City": "San Francisco",
                    "CountrySubDivisionCode": "CA",
                    "PostalCode": "94105",
                },
            },
        ]

    def test_batch_1_real_files(self, test_files_dir):
        """Test batch 1 with real files."""
        file_paths = [
            test_files_dir / "test_batch_1" / "2025-05-17 12.50.27-1.jpg",
            test_files_dir / "test_batch_1" / "2025-05-17-12-48-17.pdf",
        ]

        # Ensure files exist
        for path in file_paths:
            assert path.exists(), f"Test file not found: {path}"

        results, metadata = process_donation_documents(file_paths)

        # Verify we got results
        assert len(results) > 0
        assert metadata["raw_count"] >= len(results)
        assert metadata["valid_count"] == len(results)

        # Verify each result has required fields
        for donation in results:
            assert "PaymentInfo" in donation
            assert "Payment_Ref" in donation["PaymentInfo"]
            assert "Amount" in donation["PaymentInfo"]
            assert isinstance(donation["PaymentInfo"]["Amount"], (int, float))
            assert donation["PaymentInfo"]["Amount"] > 0

    def test_batch_2_real_files(self, test_files_dir):
        """Test batch 2 with real files."""
        file_paths = [
            test_files_dir / "test_batch_2" / "20250411_205258.jpg",
            test_files_dir / "test_batch_2" / "20250411_205415.jpg",
        ]

        for path in file_paths:
            assert path.exists(), f"Test file not found: {path}"

        results, metadata = process_donation_documents(file_paths)

        assert len(results) > 0
        for donation in results:
            assert "PaymentInfo" in donation
            assert donation["PaymentInfo"].get("Payment_Ref")
            assert donation["PaymentInfo"].get("Amount", 0) > 0

    def test_batch_3_real_files(self, test_files_dir):
        """Test batch 3 with real files."""
        file_paths = [
            test_files_dir / "test_batch_3" / "2025-01-11-15-27-04.pdf",
            test_files_dir / "test_batch_3" / "2025-01-11-15-36-44.pdf",
        ]

        for path in file_paths:
            assert path.exists(), f"Test file not found: {path}"

        results, metadata = process_donation_documents(file_paths)

        assert len(results) > 0
        for donation in results:
            assert "PaymentInfo" in donation
            assert donation["PaymentInfo"].get("Payment_Ref")
            assert donation["PaymentInfo"].get("Amount", 0) > 0

    def test_batch_4_real_files(self, test_files_dir):
        """Test batch 4 with all 7 files."""
        file_paths = [
            test_files_dir / "test_batch_4" / "2025-03-01-16-45-21.pdf",
            test_files_dir / "test_batch_4" / "20250207182439287.pdf",
            test_files_dir / "test_batch_4" / "20250328_195721.jpg",
            test_files_dir / "test_batch_4" / "20250328_195746.jpg",
            test_files_dir / "test_batch_4" / "20250328_195802.jpg",
            test_files_dir / "test_batch_4" / "20250328_195844.jpg",
            test_files_dir / "test_batch_4" / "20250328_195901.jpg",
        ]

        for path in file_paths:
            assert path.exists(), f"Test file not found: {path}"

        results, metadata = process_donation_documents(file_paths)

        assert len(results) > 0
        assert metadata["raw_count"] >= len(results)

        for donation in results:
            assert "PaymentInfo" in donation
            assert donation["PaymentInfo"].get("Payment_Ref")
            assert donation["PaymentInfo"].get("Amount", 0) > 0

    @patch("src.donation_processor.CustomerMatcher")
    def test_batch_with_mocked_matching(
        self, mock_matcher_class, test_files_dir, mock_qb_customers
    ):
        """Test real files with mocked QuickBooks matching."""
        # Use batch 1 files
        file_paths = [
            test_files_dir / "test_batch_1" / "2025-05-17 12.50.27-1.jpg",
            test_files_dir / "test_batch_1" / "2025-05-17-12-48-17.pdf",
        ]

        # Mock the matcher
        mock_matcher = MagicMock()
        mock_matcher_class.return_value = mock_matcher

        # Mock match results
        def mock_match(donation):
            # Simple matching based on aliases
            payer_info = donation.get("PayerInfo", {})
            aliases = payer_info.get("Aliases", [])

            for alias in aliases:
                if "smith" in alias.lower():
                    return {
                        "match_status": "matched",
                        "customer_ref": {"id": "1", "full_name": "John Smith"},
                        "qb_address": {
                            "line1": "123 Main St",
                            "city": "Springfield",
                            "state": "CA",
                            "zip": "94025",
                        },
                        "qb_email": ["john@example.com"],
                        "qb_phone": ["555-1234"],
                        "updates_needed": {
                            "address": False,
                            "email_added": False,
                            "phone_added": False,
                        },
                    }

            return {
                "match_status": "new_customer",
                "customer_ref": None,
                "qb_address": None,
                "qb_email": [],
                "qb_phone": [],
                "updates_needed": {
                    "address": False,
                    "email_added": False,
                    "phone_added": False,
                },
            }

        mock_matcher.match_donation_to_customer.side_effect = mock_match

        # Process with matching
        results, metadata = process_donation_documents(
            file_paths, session_id="test-session"
        )

        # Verify results
        assert len(results) > 0
        assert "match_data" in results[0]

        # Check if any were matched
        matched = [
            d
            for d in results
            if d.get("match_data", {}).get("match_status") == "matched"
        ]
        new_customers = [
            d
            for d in results
            if d.get("match_data", {}).get("match_status") == "new_customer"
        ]

        assert metadata["matched_count"] == len(matched)
        assert len(matched) + len(new_customers) == len(results)

    def test_all_batches_summary(self, test_files_dir):
        """Test all batches and print comprehensive summary."""
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
        total_raw = 0
        total_duplicates = 0

        print("\n" + "=" * 80)
        print("PROCESSING ALL TEST BATCHES WITH VALIDATION AND DEDUPLICATION")
        print("=" * 80)

        for batch_name, file_paths in batches.items():
            print(f"\n{batch_name}:")
            print(f"  Input files: {len(file_paths)}")

            try:
                results, metadata = process_donation_documents(file_paths)
                all_results[batch_name] = results
                total_donations += len(results)
                total_raw += metadata["raw_count"]
                total_duplicates += metadata["duplicate_count"]

                print(f"  Raw extracted: {metadata['raw_count']}")
                print(f"  After validation: {metadata['valid_count']}")
                print(f"  Duplicates removed: {metadata['duplicate_count']}")

                # Show sample data
                if results:
                    for i, donation in enumerate(results[:2]):  # Show first 2
                        payment = donation.get("PaymentInfo", {})
                        payer = donation.get("PayerInfo", {})
                        aliases = payer.get("Aliases", [])
                        org = payer.get("Organization_Name", "")
                        name = aliases[0] if aliases else org if org else "Unknown"

                        print(f"  Sample {i+1}: {name}")
                        print(f"    - Ref: {payment.get('Payment_Ref')}")
                        print(f"    - Amount: ${payment.get('Amount', 0):.2f}")

            except Exception as e:
                print(f"  Error: {str(e)}")
                all_results[batch_name] = []

        print("\n" + "-" * 80)
        print("SUMMARY:")
        print(f"  Total raw entries extracted: {total_raw}")
        print(f"  Total duplicates removed: {total_duplicates}")
        print(f"  Total valid donations: {total_donations}")
        print(
            f"  Deduplication rate: {(total_duplicates/total_raw*100):.1f}%"
            if total_raw > 0
            else "0%"
        )

        # Assertions
        assert len(all_results) == 4
        assert total_donations > 0
        assert total_raw >= total_donations  # Raw should be >= final count
