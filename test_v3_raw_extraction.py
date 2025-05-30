#!/usr/bin/env python3
"""
Test V3 raw extraction to see what Gemini returns with unified batching.
"""

import json
import logging
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load environment
from dotenv import load_dotenv

load_dotenv()


def main():
    """Test V3 raw extraction."""

    # Import V3 components
    from src.utils.gemini_adapter_v3 import GeminiAdapterV3

    # Check for API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY not set!")
        return

    # Create Gemini V3 service
    gemini_service = GeminiAdapterV3(api_key)

    # Test with the dummy files
    files = ["tests/e2e/dummy files/2025-05-17-12-48-17.pdf", "tests/e2e/dummy files/2025-05-17 12.50.27-1.jpg"]

    logger.info("=" * 80)
    logger.info("V3 UNIFIED BATCH EXTRACTION (ALL FILES TOGETHER)")
    logger.info("=" * 80)

    try:
        # Extract all together
        payments = gemini_service.extract_payments_batch(files)
        logger.info(f"\nExtracted {len(payments)} payments total")

        # Convert to dict for display
        payments_data = []
        for p in payments:
            payment_dict = {
                "payment_info": {
                    "payment_method": p.payment_info.payment_method,
                    "check_no": p.payment_info.check_no,
                    "payment_ref": p.payment_info.payment_ref,
                    "amount": p.payment_info.amount,
                    "check_date": p.payment_info.check_date,
                    "deposit_date": p.payment_info.deposit_date,
                    "memo": p.payment_info.memo,
                },
                "payer_info": {"aliases": p.payer_info.aliases, "organization_name": p.payer_info.organization_name},
                "contact_info": {
                    "address_line_1": p.contact_info.address_line_1,
                    "city": p.contact_info.city,
                    "state": p.contact_info.state,
                    "zip": p.contact_info.zip,
                },
            }
            payments_data.append(payment_dict)

        print("\nFull extraction results:")
        print(json.dumps(payments_data, indent=2))

        # Look for the DAFgiving payment
        print("\n" + "=" * 80)
        print("CHECKING DAFgiving EXTRACTION:")
        print("=" * 80)

        for i, p in enumerate(payments):
            if "3517031" in str(p.payment_info.check_no or "") or "3517031" in str(p.payment_info.payment_ref or ""):
                print(f"\nPayment {i+1} has ref/check 0003517031:")
                print(f"  Organization: {p.payer_info.organization_name}")
                print(f"  Aliases: {p.payer_info.aliases}")
                print(f"  Memo: {p.payment_info.memo}")

                if p.payer_info.organization_name and "SGO" in p.payer_info.organization_name:
                    print("  ✅ CORRECTLY extracted as DAFgivingSGOs!")
                else:
                    print("  ❌ Organization name not correctly extracted")

    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
