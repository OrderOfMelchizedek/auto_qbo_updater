#!/usr/bin/env python3
"""
Test structured extraction without legacy fallback.
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

# Import components
from src.utils.gemini_adapter import create_gemini_service


def test_no_fallback():
    """Test structured extraction without fallback."""

    # Initialize services
    gemini_service = create_gemini_service(
        api_key=os.getenv("GEMINI_API_KEY"), model_name="gemini-2.5-flash-preview-04-17"
    )

    file_processor = FileProcessor(gemini_service=gemini_service)

    # Test files
    test_dir = Path(__file__).parent / "tests" / "e2e" / "dummy files"
    files = [
        (str(test_dir / "2025-05-17 12.50.27-1.jpg"), ".jpg", "JPG (deposit slip)"),
        (str(test_dir / "2025-05-17-12-48-17.pdf"), ".pdf", "PDF (18 pages)"),
    ]

    print("Testing structured extraction WITHOUT legacy fallback...")
    print("=" * 60)

    for file_path, file_ext, description in files:
        print(f"\nTesting {description}:")
        print("-" * 40)

        try:
            result = file_processor.process(file_path, file_ext)

            if isinstance(result, list):
                print(f"✅ Successfully extracted {len(result)} donations")

                # Show summary
                total = 0
                for i, donation in enumerate(result):
                    amount = float(donation.get("Gift Amount", 0))
                    total += amount
                    donor = donation.get("Donor Name", "Unknown")
                    check_no = donation.get("Check No.", "N/A")
                    print(f"   {i+1}. {donor} - ${amount:.2f} (Check: {check_no})")

                print(f"   Total: ${total:.2f}")

            else:
                print(f"❌ Unexpected result type: {type(result)}")

        except Exception as e:
            print(f"❌ Extraction failed: {e}")
            print(f"   Error type: {type(e).__name__}")

            # Show if it's a validation error
            if "validation error" in str(e):
                print("   This is a Pydantic validation error")

    print("\n" + "=" * 60)
    print("Summary:")
    print("Structured extraction is now running without legacy fallback.")
    print("Any errors shown above need to be fixed in the structured extraction.")


if __name__ == "__main__":
    test_no_fallback()
