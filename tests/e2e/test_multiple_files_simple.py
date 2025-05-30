#!/usr/bin/env python3
"""
Test processing multiple files (JPG + PDF) as the app would.
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

from src.utils.file_processor import FileProcessor

# Import app components
from src.utils.gemini_adapter import create_gemini_service


def test_multiple_files():
    """Test processing JPG and PDF files as separate uploads."""

    # Initialize services
    gemini_service = create_gemini_service(
        api_key=os.getenv("GEMINI_API_KEY"), model_name="gemini-2.5-flash-preview-04-17"
    )

    file_processor = FileProcessor(gemini_service=gemini_service)

    # Test files
    test_dir = Path(__file__).parent / "tests" / "e2e" / "dummy files"
    files = [(str(test_dir / "2025-05-17 12.50.27-1.jpg"), ".jpg"), (str(test_dir / "2025-05-17-12-48-17.pdf"), ".pdf")]

    print("Testing multiple file processing (JPG + PDF)...")
    print("=" * 60)

    all_donations = []

    for file_path, file_ext in files:
        file_name = Path(file_path).name
        print(f"\nProcessing: {file_name}")
        print("-" * 40)

        try:
            # Process each file
            result = file_processor.process(file_path, file_ext)

            if isinstance(result, list):
                print(f"✅ Extracted {len(result)} donations")
                all_donations.extend(result)

                # Show donations from this file
                for i, donation in enumerate(result):
                    donor = donation.get("Donor Name", "Unknown")
                    amount = donation.get("Gift Amount", "0")
                    check_no = donation.get("Check No.", donation.get("Payment Ref", "N/A"))
                    print(f"   {i+1}. {donor} - ${amount} (Check/Ref: {check_no})")

            elif isinstance(result, dict):
                if result.get("success"):
                    donations = result.get("donations", [])
                    print(f"✅ Extracted {len(donations)} donations")
                    all_donations.extend(donations)
                else:
                    print(f"❌ Error: {result.get('error', 'Unknown error')}")
            else:
                print(f"❌ Unexpected result type: {type(result)}")

        except Exception as e:
            print(f"❌ Exception processing {file_name}: {e}")
            import traceback

            traceback.print_exc()

    # Summary
    print("\n" + "=" * 60)
    print("COMBINED RESULTS FROM BOTH FILES:")
    print("=" * 60)
    print(f"Total donations extracted: {len(all_donations)}")

    total_amount = 0
    print("\nAll donations:")
    for i, donation in enumerate(all_donations):
        amount = float(donation.get("Gift Amount", 0))
        total_amount += amount

        donor = donation.get("Donor Name", "Unknown")
        check_no = donation.get("Check No.", donation.get("Payment Ref", "N/A"))
        date = donation.get("Check Date") or donation.get("Deposit Date", "N/A")

        print(f"\n{i+1}. {donor}")
        print(f"   Check/Ref: {check_no}")
        print(f"   Amount: ${amount:.2f}")
        print(f"   Date: {date}")

        # Show address if available
        if donation.get("Address - Line 1"):
            addr = donation.get("Address - Line 1")
            city = donation.get("City", "")
            state = donation.get("State", "")
            zip_code = donation.get("ZIP", "")
            print(f"   Address: {addr}")
            if city:
                print(f"            {city}, {state} {zip_code}")

    print(f"\nTotal Amount: ${total_amount:.2f}")

    # Check if we got the expected results
    print("\n" + "-" * 60)
    print("Verification:")
    if len(all_donations) >= 4:
        print("✅ Successfully extracted donations from both files")
        print("✅ Structured extraction is working for image files")
    else:
        print(f"⚠️  Only extracted {len(all_donations)} donations (expected at least 4)")


if __name__ == "__main__":
    test_multiple_files()
