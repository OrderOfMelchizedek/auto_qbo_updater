#!/usr/bin/env python3
"""
Test structured extraction with BOTH files together (JPG + PDF).
This simulates a user uploading multiple files at once.
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


def test_both_files_together():
    """Test processing both JPG and PDF files together."""
    # Initialize services
    gemini_service = create_gemini_service(
        api_key=os.getenv("GEMINI_API_KEY"), model_name="gemini-2.5-flash-preview-04-17"
    )

    # Test files
    test_dir = Path(__file__).parent / "tests" / "e2e" / "dummy files"
    files = [str(test_dir / "2025-05-17 12.50.27-1.jpg"), str(test_dir / "2025-05-17-12-48-17.pdf")]

    print("Testing BOTH files together (simulating user upload)...")
    print("=" * 60)
    print(f"Files to process:")
    for f in files:
        print(f"  - {Path(f).name}")
    print()

    try:
        # Process files using FileProcessor
        print("Processing files...")
        file_processor = FileProcessor(gemini_service)
        results = []
        for file_path in files:
            _, ext = os.path.splitext(file_path)
            result = file_processor.process(file_path, ext)
            results.append(result)

        print(f"\nProcessed {len(results)} files")
        print("-" * 60)

        all_donations = []
        for i, result in enumerate(results):
            file_name = Path(files[i]).name
            print(f"\nFile: {file_name}")

            if isinstance(result, list):
                print(f"  ✅ Extracted {len(result)} donations")
                all_donations.extend(result)
                for j, donation in enumerate(result):
                    print(f"     Donation {j+1}: {donation.get('Donor Name')} - ${donation.get('Gift Amount')}")
            elif isinstance(result, dict) and result.get("success"):
                donations = result.get("donations", [])
                print(f"  ✅ Extracted {len(donations)} donations")
                all_donations.extend(donations)
            else:
                print(f"  ❌ Error: {result}")

        # Summary
        print("\n" + "=" * 60)
        print("TOTAL SUMMARY:")
        print("-" * 60)
        print(f"Total donations extracted: {len(all_donations)}")

        total_amount = 0
        for donation in all_donations:
            amount = float(donation.get("Gift Amount", 0))
            total_amount += amount

        print(f"Total amount: ${total_amount:.2f}")

        # Show all donations
        print("\nAll donations:")
        for i, donation in enumerate(all_donations):
            print(f"\n{i+1}. {donation.get('Donor Name', 'Unknown')}")
            print(f"   Check/Ref: {donation.get('Check No.') or donation.get('Payment Ref', 'N/A')}")
            print(f"   Amount: ${donation.get('Gift Amount')}")
            print(f"   Date: {donation.get('Check Date') or donation.get('Deposit Date', 'N/A')}")
            if donation.get("Address - Line 1"):
                print(f"   Address: {donation.get('Address - Line 1')}")
                if donation.get("City"):
                    print(f"            {donation.get('City')}, {donation.get('State')} {donation.get('ZIP')}")

    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback

        traceback.print_exc()


def test_direct_structured_extraction():
    """Test structured extraction directly with both files."""
    print("\n" + "=" * 60)
    print("Testing direct structured extraction with both files...")
    print("=" * 60)

    try:
        from src.utils.gemini_structured import GeminiStructuredService

        api_key = os.getenv("GEMINI_API_KEY")
        gemini_service = GeminiStructuredService(api_key=api_key)

        test_dir = Path(__file__).parent / "tests" / "e2e" / "dummy files"
        files = [str(test_dir / "2025-05-17 12.50.27-1.jpg"), str(test_dir / "2025-05-17-12-48-17.pdf")]

        # Try processing both files together
        print("\nAttempting to process both files in one call...")
        try:
            payment_records = gemini_service.extract_payment_structured(image_paths=files, document_type="batch")

            if payment_records:
                records = payment_records if isinstance(payment_records, list) else [payment_records]
                print(f"✅ Extracted {len(records)} payment records")
                for r in records:
                    print(
                        f"   - {r.payer_info.aliases[0] if r.payer_info.aliases else r.payer_info.organization_name}: ${r.payment_info.amount}"
                    )

        except Exception as e:
            print(f"❌ Error processing both files together: {e}")

            # Try processing individually
            print("\nProcessing files individually...")
            for file_path in files:
                print(f"\nFile: {Path(file_path).name}")
                try:
                    # Skip PDF for now if it fails
                    if file_path.endswith(".pdf"):
                        print("  ⚠️  Skipping PDF (PIL can't handle PDFs directly)")
                        continue

                    records = gemini_service.extract_payment_structured(image_paths=[file_path], document_type="batch")
                    if records:
                        records = records if isinstance(records, list) else [records]
                        print(f"  ✅ Extracted {len(records)} records")
                except Exception as e:
                    print(f"  ❌ Error: {e}")

    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_both_files_together()
    test_direct_structured_extraction()
