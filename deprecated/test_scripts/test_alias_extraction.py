#!/usr/bin/env python3
"""
Test to verify that aliases are being extracted and used for matching.
"""

import json
import logging
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load environment
from dotenv import load_dotenv

load_dotenv()


def test_extraction_with_aliases():
    """Test that Gemini extraction includes aliases."""
    from src.utils.gemini_adapter import GeminiAdapter

    # Create Gemini service
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY not set!")
        return

    gemini_service = GeminiAdapter(api_key=api_key)

    # Find a test image
    dummy_dir = Path(__file__).parent / "tests" / "e2e" / "dummy files"
    jpg_file = None
    for f in dummy_dir.iterdir():
        if f.suffix.lower() == ".jpg":
            jpg_file = str(f)
            break

    if not jpg_file:
        logger.error("No JPG file found in dummy files")
        return

    logger.info(f"Extracting from: {jpg_file}")

    # Extract
    result = gemini_service.extract_donation_data(jpg_file)

    logger.info(f"\nExtracted {len(result)} payments")

    # Check for aliases
    for i, payment in enumerate(result):
        print(f"\n{'='*60}")
        print(f"PAYMENT {i+1}")
        print(f"{'='*60}")
        print(f"Donor Name: {payment.get('Donor Name')}")
        print(f"First Name: {payment.get('First Name')}")
        print(f"Last Name: {payment.get('Last Name')}")

        # Check if structured extraction is being used
        if hasattr(gemini_service, "use_structured") and gemini_service.use_structured:
            print("\n✅ Using STRUCTURED extraction")
            # The structured extraction should have created a PaymentRecord
            # which would have aliases in the payer_info
        else:
            print("\n❌ Using LEGACY extraction")

        # Look for aliases in the raw response
        print(f"\nFull payment data:")
        print(json.dumps(payment, indent=2))

        # Check how the name would be used for matching
        donor_name = payment.get("Donor Name", "")
        print(f"\nName used for matching: '{donor_name}'")

        # Show what aliases SHOULD have been generated
        if payment.get("Last Name") == "Lang":
            print("\nExpected aliases for J. Lang:")
            print("- J. Lang")
            print("- Lang, J.")
            print("- John Lang (if we knew the full first name)")
            print("- Lang, John")


if __name__ == "__main__":
    test_extraction_with_aliases()
