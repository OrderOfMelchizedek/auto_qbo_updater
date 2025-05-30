#!/usr/bin/env python3
"""
Debug PDF structured extraction to see what's being returned.
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

# Import components
from src.utils.gemini_adapter import GeminiAdapter


def test_pdf_debug():
    """Debug PDF extraction."""

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not found")
        return

    # Test file
    test_dir = Path(__file__).parent / "tests" / "e2e" / "dummy files"
    pdf_file = test_dir / "2025-05-17-12-48-17.pdf"

    print("Testing PDF extraction...")
    print("=" * 60)

    # Use GeminiAdapter
    adapter = GeminiAdapter(api_key=api_key)

    try:
        result = adapter.extract_donation_data(str(pdf_file))

        print(f"\nExtraction returned type: {type(result)}")

        if isinstance(result, list):
            print(f"Number of donations: {len(result)}")

            if result:
                # Show first donation
                print("\nFirst donation raw data:")
                print(json.dumps(result[0], indent=2))

                # Check what fields we have
                print("\nAvailable fields in first donation:")
                for key, value in result[0].items():
                    print(f"  - {key}: {type(value).__name__} = {repr(value)[:50]}")

        else:
            print("Result is not a list")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_pdf_debug()
