#!/usr/bin/env python3
"""
Debug test to see what JSON is being returned by Gemini.
"""

import logging
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Set up logging to see debug output
logging.basicConfig(level=logging.INFO)

# Load environment variables
from dotenv import load_dotenv

load_dotenv()

# Import components
from src.utils.gemini_structured import GeminiStructuredService


def test_debug_json():
    """Debug what JSON is being returned."""

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not found")
        return

    # Test file
    test_dir = Path(__file__).parent / "tests" / "e2e" / "dummy files"
    jpg_file = test_dir / "2025-05-17 12.50.27-1.jpg"

    print("Debug test for JSON extraction...")
    print("=" * 60)

    # Create service
    service = GeminiStructuredService(api_key=api_key)

    try:
        # Test with JPG
        payment_records = service.extract_payment_structured(image_paths=[str(jpg_file)], document_type="batch")

        print(f"\nSuccess! Extracted {len(payment_records) if isinstance(payment_records, list) else 1} records")

    except Exception as e:
        print(f"\nError occurred: {e}")
        print("\nCheck the logs above to see what JSON was extracted")


if __name__ == "__main__":
    test_debug_json()
