#!/usr/bin/env python3
"""
Simple test for structured extraction with real files.
This test uses the real Gemini API without mocking dependencies.
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


def test_structured_extraction():
    """Test structured extraction with real files."""

    # Check for API key
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not found in environment")
        return

    # Setup test files
    test_dir = Path(__file__).parent / "tests" / "e2e" / "dummy files"
    jpg_file = test_dir / "2025-05-17 12.50.27-1.jpg"
    pdf_file = test_dir / "2025-05-17-12-48-17.pdf"

    print(f"Testing with files from: {test_dir}")
    print(f"JPG file exists: {jpg_file.exists()}")
    print(f"PDF file exists: {pdf_file.exists()}")

    # Create GeminiStructuredService directly
    gemini_service = GeminiStructuredService(api_key=api_key)

    # Test JPG file (check image)
    print("\n" + "=" * 50)
    print("Testing JPG file (check image)...")
    print("=" * 50)

    if jpg_file.exists():
        try:
            # Extract payment data
            payment_records = gemini_service.extract_payment_structured(
                image_paths=[str(jpg_file)], document_type="check"
            )

            if payment_records:
                record = payment_records[0] if isinstance(payment_records, list) else payment_records

                print("\nExtracted Structured Data:")
                print(f"Payment Info:")
                print(f"  - Payment Method: {record.payment_info.payment_method}")
                print(f"  - Check Number: {record.payment_info.check_no}")
                print(f"  - Amount: ${record.payment_info.amount}")
                print(f"  - Payment Date: {record.payment_info.payment_date}")
                print(f"  - Memo: {record.payment_info.memo}")

                print(f"\nPayer Info:")
                if record.payer_info.aliases:
                    print(f"  - Aliases: {', '.join(record.payer_info.aliases)}")
                if record.payer_info.organization_name:
                    print(f"  - Organization: {record.payer_info.organization_name}")
                print(f"  - Salutation: {record.payer_info.salutation}")

                print(f"\nContact Info:")
                print(f"  - Address: {record.contact_info.address_line_1}")
                print(f"  - City: {record.contact_info.city}")
                print(f"  - State: {record.contact_info.state}")
                print(f"  - ZIP: {record.contact_info.zip}")
                print(f"  - Email: {record.contact_info.email}")
                print(f"  - Phone: {record.contact_info.phone}")

                # Convert to legacy format
                print("\nLegacy Format Conversion:")
                legacy = record.to_legacy_format()
                print(json.dumps(legacy, indent=2))

        except Exception as e:
            print(f"Error processing JPG: {e}")
            import traceback

            traceback.print_exc()

    # Test PDF file
    print("\n" + "=" * 50)
    print("Testing PDF file...")
    print("=" * 50)

    if pdf_file.exists():
        try:
            # Extract payment data
            payment_records = gemini_service.extract_payment_structured(
                image_paths=[str(pdf_file)], document_type="check"
            )

            if payment_records:
                # Handle single or multiple records
                records = payment_records if isinstance(payment_records, list) else [payment_records]

                for i, record in enumerate(records):
                    print(f"\n--- Record {i+1} ---")
                    print(f"Payment Method: {record.payment_info.payment_method}")
                    print(f"Check/Ref: {record.payment_info.check_no or record.payment_info.payment_ref}")
                    print(f"Amount: ${record.payment_info.amount}")
                    print(
                        f"Payer: {record.payer_info.aliases[0] if record.payer_info.aliases else record.payer_info.organization_name}"
                    )

        except Exception as e:
            print(f"Error processing PDF: {e}")
            import traceback

            traceback.print_exc()

    # Test backward compatibility
    print("\n" + "=" * 50)
    print("Testing GeminiAdapter with structured extraction...")
    print("=" * 50)

    try:
        from src.utils.gemini_adapter import GeminiAdapter

        # Create adapter
        adapter = GeminiAdapter(api_key=api_key)

        if jpg_file.exists():
            result = adapter.extract_donation_data(str(jpg_file))
            print("\nGeminiAdapter Result (should be in legacy format):")
            print(json.dumps(result, indent=2))

            # Verify it's in legacy format
            if result:
                print("\nLegacy Format Verification:")
                print(f"✓ Has 'Donor Name': {'Donor Name' in result}")
                print(f"✓ Has 'Check No.': {'Check No.' in result}")
                print(f"✓ Has 'Gift Amount': {'Gift Amount' in result}")
                print(f"✓ Has 'Address - Line 1': {'Address - Line 1' in result}")

    except Exception as e:
        print(f"Error testing GeminiAdapter: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_structured_extraction()
