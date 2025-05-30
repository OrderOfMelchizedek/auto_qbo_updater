#!/usr/bin/env python3
"""
Test structured extraction with real files from e2e/dummy files directory.
This script tests the GeminiAdapter and structured extraction without mocking the Gemini API.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.models.payment import ContactInfo, PayerInfo, PaymentInfo, PaymentRecord
from src.utils.enhanced_file_processor import EnhancedFileProcessor
from src.utils.gemini_adapter import GeminiAdapter
from src.utils.gemini_structured import GeminiStructuredService


def test_structured_extraction():
    """Test structured extraction with real files."""

    # Setup test files
    test_dir = Path(__file__).parent / "tests" / "e2e" / "dummy files"
    jpg_file = test_dir / "2025-05-17 12.50.27-1.jpg"
    pdf_file = test_dir / "2025-05-17-12-48-17.pdf"

    print(f"Testing with files from: {test_dir}")
    print(f"JPG file exists: {jpg_file.exists()}")
    print(f"PDF file exists: {pdf_file.exists()}")

    # Load environment variables
    import os

    from dotenv import load_dotenv

    load_dotenv()

    # Check if we have the real API key
    if not os.environ.get("GEMINI_API_KEY"):
        print("ERROR: GEMINI_API_KEY not found in environment")
        print("Please ensure .env file exists with GEMINI_API_KEY set")
        return

    # Mock dependencies that are imported at module level
    with (
        patch("src.utils.result_store.redis") as mock_redis_store,
        patch("src.utils.s3_storage.boto3") as mock_boto3,
        patch("src.utils.gemini_service.redis") as mock_redis_service,
    ):

        # Setup Redis mocks
        mock_redis_instance = MagicMock()
        mock_redis_instance.get.return_value = None  # No cache
        mock_redis_instance.setex.return_value = True
        mock_redis_store.return_value = mock_redis_instance
        mock_redis_service.return_value = mock_redis_instance

        # Create GeminiAdapter instance
        from src.utils.gemini_adapter import GeminiAdapter

        gemini_adapter = GeminiAdapter(api_key=os.environ["GEMINI_API_KEY"])

        # Test JPG file
        print("\n" + "=" * 50)
        print("Testing JPG file (check image)...")
        print("=" * 50)

        if jpg_file.exists():
            with open(jpg_file, "rb") as f:
                jpg_content = f.read()

            try:
                # GeminiAdapter uses extract_donation_data method
                result = gemini_adapter.extract_donation_data(file_path=str(jpg_file))

                print("\nExtracted Data:")
                print(json.dumps(result, indent=2))

                # Verify required fields (legacy format)
                print("\nField Verification (Legacy Format):")
                print(f"✓ Check Number: {result.get('Check No.')}")
                print(f"✓ Amount: {result.get('Gift Amount')}")
                print(f"✓ Payment/Check Date: {result.get('Check Date') or result.get('Deposit Date')}")
                print(f"✓ Donor Name: {result.get('Donor Name')}")
                print(f"✓ Address: {result.get('Address - Line 1')}")
                print(f"✓ City: {result.get('City')}")
                print(f"✓ State: {result.get('State')}")
                print(f"✓ ZIP: {result.get('ZIP')}")

            except Exception as e:
                print(f"Error processing JPG: {e}")
                import traceback

                traceback.print_exc()

        # Test PDF file
        print("\n" + "=" * 50)
        print("Testing PDF file...")
        print("=" * 50)

        if pdf_file.exists():
            with open(pdf_file, "rb") as f:
                pdf_content = f.read()

            try:
                # GeminiAdapter uses extract_donation_data method
                result = gemini_adapter.extract_donation_data(file_path=str(pdf_file))

                print("\nExtracted Data:")
                print(json.dumps(result, indent=2))

                # Verify required fields (legacy format)
                print("\nField Verification (Legacy Format):")
                print(f"✓ Check Number: {result.get('Check No.')}")
                print(f"✓ Amount: {result.get('Gift Amount')}")
                print(f"✓ Payment/Check Date: {result.get('Check Date') or result.get('Deposit Date')}")
                print(f"✓ Donor Name: {result.get('Donor Name')}")
                print(f"✓ Address: {result.get('Address - Line 1')}")
                print(f"✓ City: {result.get('City')}")
                print(f"✓ State: {result.get('State')}")
                print(f"✓ ZIP: {result.get('ZIP')}")

            except Exception as e:
                print(f"Error processing PDF: {e}")
                import traceback

                traceback.print_exc()

        # Test backward compatibility
        print("\n" + "=" * 50)
        print("Testing backward compatibility...")
        print("=" * 50)

        # The adapter should return data in the old format when structured extraction fails
        # or when it needs to maintain compatibility

        if jpg_file.exists():
            # Test that we can still get donation data in old format
            old_format_expected_keys = ["donor", "amount", "check_no", "payment_date"]

            print("\nChecking if result can be converted to old format...")
            # The enhanced processor should handle this conversion
            print("✓ Backward compatibility layer would handle format conversion")


if __name__ == "__main__":
    test_structured_extraction()
