#!/usr/bin/env python3
"""
Test structured extraction with batch processing for multiple checks in one image.
"""

import json
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Load environment variables
from dotenv import load_dotenv

load_dotenv()

# Import after environment is set up
from src.utils.gemini_structured import GeminiStructuredService


def test_batch_extraction():
    """Test extraction of multiple checks from a single image."""

    # Check for API key
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not found in environment")
        return

    # Setup test file
    test_dir = Path(__file__).parent / "tests" / "e2e" / "dummy files"
    jpg_file = test_dir / "2025-05-17 12.50.27-1.jpg"

    if not jpg_file.exists():
        print(f"Test file not found: {jpg_file}")
        return

    # Create GeminiStructuredService
    gemini_service = GeminiStructuredService(api_key=api_key)

    print("Testing batch extraction (multiple checks in one image)...")
    print("=" * 60)

    try:
        # Force batch mode by setting document_type to "batch"
        payment_records = gemini_service.extract_payment_structured(
            image_paths=[str(jpg_file)], document_type="batch"  # This forces expect_list = True
        )

        if payment_records:
            records = payment_records if isinstance(payment_records, list) else [payment_records]

            print(f"\nExtracted {len(records)} payment record(s):")
            print("-" * 60)

            for i, record in enumerate(records):
                print(f"\n--- Check #{i+1} ---")
                print(f"Check Number: {record.payment_info.check_no}")
                print(f"Amount: ${record.payment_info.amount}")
                print(f"Payment Method: {record.payment_info.payment_method}")
                print(f"Payment Date: {record.payment_info.payment_date}")

                if record.payer_info.aliases:
                    print(f"Payer: {', '.join(record.payer_info.aliases)}")
                elif record.payer_info.organization_name:
                    print(f"Organization: {record.payer_info.organization_name}")

                # Show address if available
                if record.contact_info.address_line_1:
                    print(f"Address: {record.contact_info.address_line_1}")
                    if record.contact_info.city:
                        print(
                            f"         {record.contact_info.city}, {record.contact_info.state} {record.contact_info.zip}"
                        )

            # Test conversion to legacy format
            print("\n" + "=" * 60)
            print("Legacy Format Conversion Test:")
            print("-" * 60)

            legacy_records = []
            for record in records:
                legacy = record.to_legacy_format()
                legacy_records.append(legacy)

            print(json.dumps(legacy_records, indent=2))

            # Summary
            print(f"\n✅ Successfully extracted {len(records)} checks")
            total_amount = sum(r.payment_info.amount for r in records)
            print(f"✅ Total amount: ${total_amount:.2f}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


def test_gemini_adapter_batch():
    """Test GeminiAdapter with batch extraction."""
    print("\n" + "=" * 60)
    print("Testing GeminiAdapter with batch mode...")
    print("=" * 60)

    try:
        from src.utils.gemini_adapter import GeminiAdapter

        api_key = os.environ.get("GEMINI_API_KEY")
        adapter = GeminiAdapter(api_key=api_key)

        test_dir = Path(__file__).parent / "tests" / "e2e" / "dummy files"
        jpg_file = test_dir / "2025-05-17 12.50.27-1.jpg"

        # Test extraction
        result = adapter.extract_donation_data(str(jpg_file))

        if isinstance(result, list):
            print(f"✅ Extracted {len(result)} donations")
            for i, donation in enumerate(result):
                print(f"\nDonation {i+1}:")
                print(f"  Donor: {donation.get('Donor Name')}")
                print(f"  Check No: {donation.get('Check No.')}")
                print(f"  Amount: ${donation.get('Gift Amount')}")
        else:
            print("❌ Expected list but got single record")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_batch_extraction()
    test_gemini_adapter_batch()
