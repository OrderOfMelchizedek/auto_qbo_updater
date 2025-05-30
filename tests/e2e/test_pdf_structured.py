#!/usr/bin/env python3
"""
Test structured extraction specifically for PDF files.
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

from src.utils.gemini_adapter import GeminiAdapter

# Import components
from src.utils.gemini_structured import GeminiStructuredService


def test_pdf_structured():
    """Test PDF processing with structured extraction."""

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not found")
        return

    # Test file
    test_dir = Path(__file__).parent / "tests" / "e2e" / "dummy files"
    pdf_file = test_dir / "2025-05-17-12-48-17.pdf"

    print("Testing PDF with structured extraction...")
    print("=" * 60)

    # Test 1: Direct structured extraction
    print("\n1. Testing GeminiStructuredService directly:")
    print("-" * 40)

    try:
        gemini_service = GeminiStructuredService(api_key=api_key)

        payment_records = gemini_service.extract_payment_structured(image_paths=[str(pdf_file)], document_type="batch")

        if payment_records:
            records = payment_records if isinstance(payment_records, list) else [payment_records]
            print(f"✅ Extracted {len(records)} payment records from PDF")

            for i, record in enumerate(records):
                print(f"\n   Record {i+1}:")
                print(f"   - Check #: {record.payment_info.check_no}")
                print(f"   - Amount: ${record.payment_info.amount}")
                print(f"   - Date: {record.payment_info.payment_date}")
                print(
                    f"   - Payer: {', '.join(record.payer_info.aliases) if record.payer_info.aliases else record.payer_info.organization_name}"
                )

                if record.contact_info.address_line_1:
                    print(f"   - Address: {record.contact_info.address_line_1}")
                    if record.contact_info.city:
                        print(
                            f"              {record.contact_info.city}, {record.contact_info.state} {record.contact_info.zip}"
                        )

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()

    # Test 2: Through GeminiAdapter
    print("\n\n2. Testing through GeminiAdapter:")
    print("-" * 40)

    try:
        adapter = GeminiAdapter(api_key=api_key)

        # Check if it uses structured extraction
        print(f"Adapter using structured extraction: {adapter.use_structured}")

        result = adapter.extract_donation_data(str(pdf_file))

        if isinstance(result, list):
            print(f"✅ Extracted {len(result)} donations from PDF")

            # Check if we have the detailed info that comes from structured extraction
            has_addresses = any(d.get("Address - Line 1") for d in result)
            has_dates = any(d.get("Check Date") or d.get("Deposit Date") for d in result)

            print(f"   Has addresses: {has_addresses}")
            print(f"   Has dates: {has_dates}")

            if has_addresses or has_dates:
                print("   ✅ Appears to be using structured extraction!")
            else:
                print("   ⚠️  May be using legacy extraction")

            # Show first donation as example
            if result:
                print(f"\n   Example (first donation):")
                d = result[0]
                print(f"   - Donor: {d.get('Donor Name')}")
                print(f"   - Check #: {d.get('Check No.')}")
                print(f"   - Amount: ${d.get('Gift Amount')}")
                print(f"   - Date: {d.get('Check Date') or d.get('Deposit Date', 'N/A')}")
                if d.get("Address - Line 1"):
                    print(f"   - Address: {d.get('Address - Line 1')}")

        else:
            print(f"❌ Unexpected result type: {type(result)}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_pdf_structured()
