#!/usr/bin/env python3
"""
Test PDF with legacy extraction only.
"""

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
from src.utils.gemini_adapter import GeminiAdapter


def test_pdf_legacy():
    """Test PDF with legacy extraction."""

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not found")
        return

    # Test file
    test_dir = Path(__file__).parent / "tests" / "e2e" / "dummy files"
    pdf_file = test_dir / "2025-05-17-12-48-17.pdf"

    print("Testing PDF with legacy extraction...")
    print("=" * 60)

    # Create adapter and disable structured extraction
    adapter = GeminiAdapter(api_key=api_key)
    adapter.use_structured = False

    print(f"Structured extraction disabled: {not adapter.use_structured}")

    # Create file processor
    file_processor = FileProcessor(gemini_service=adapter)

    try:
        result = file_processor.process(str(pdf_file), ".pdf")

        if isinstance(result, list):
            print(f"\n✅ Extracted {len(result)} donations with legacy extraction")

            for i, donation in enumerate(result):
                donor = donation.get("Donor Name", "Unknown")
                amount = donation.get("Gift Amount", "0")
                check_no = donation.get("Check No.", "N/A")
                address = donation.get("Address - Line 1", "N/A")

                print(f"\n{i+1}. {donor}")
                print(f"   Check #: {check_no}")
                print(f"   Amount: ${amount}")
                if address != "N/A":
                    print(f"   Address: {address}")

        else:
            print(f"Unexpected result type: {type(result)}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_pdf_legacy()
