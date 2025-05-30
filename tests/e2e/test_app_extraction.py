#!/usr/bin/env python3
"""
Test structured extraction through the actual app flow.
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


def test_app_flow():
    """Test extraction through the actual app flow."""

    # Initialize services like the app does
    gemini_service = create_gemini_service(
        api_key=os.getenv("GEMINI_API_KEY"), model_name="gemini-2.5-flash-preview-04-17"
    )

    # Create file processor
    file_processor = FileProcessor(gemini_service=gemini_service)

    # Test file
    test_dir = Path(__file__).parent / "tests" / "e2e" / "dummy files"
    jpg_file = test_dir / "2025-05-17 12.50.27-1.jpg"

    print("Testing app flow with structured extraction...")
    print("=" * 60)

    try:
        # Process file through app's file processor
        print(f"\nProcessing: {jpg_file.name}")
        result = file_processor.process(str(jpg_file), ".jpg")

        if isinstance(result, list):
            donations = result
            print(f"\n✅ Successfully processed file")
            print(f"✅ Extracted {len(donations)} donations")

            # Show summary
            total = 0
            for i, donation in enumerate(donations):
                amount = float(donation.get("Gift Amount", 0))
                total += amount
                print(f"\nDonation {i+1}:")
                print(f"  Donor: {donation.get('Donor Name')}")
                print(f"  Check No: {donation.get('Check No.')}")
                print(f"  Amount: ${amount:.2f}")
                print(f"  Method: {donation.get('Deposit Method', 'Unknown')}")

            print(f"\nTotal Amount: ${total:.2f}")

            # Verify structured extraction was used
            print("\n" + "-" * 60)
            print("Checking if structured extraction was used...")

            # Check log output or adapter state
            if hasattr(gemini_service, "use_structured"):
                print(f"✅ Adapter configured for structured extraction: {gemini_service.use_structured}")

            # Check if we got all 4 checks
            if len(donations) == 4:
                print("✅ All 4 checks were extracted (structured extraction working!)")
            else:
                print(f"⚠️  Only {len(donations)} check(s) extracted (might be using legacy)")

        else:
            print(f"❌ Error: {result.get('error')}")

    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_app_flow()
