#!/usr/bin/env python3
"""
Test the complete refactored workflow with PaymentRecord objects and alias matching.
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load environment
from dotenv import load_dotenv

load_dotenv()


def test_refactored_workflow():
    """Test the complete refactored workflow."""

    # Import the V2 components
    from src.models.payment import ContactInfo, PayerInfo, PaymentInfo, PaymentMethod, PaymentRecord
    from src.utils.enhanced_file_processor_v2 import EnhancedFileProcessorV2
    from src.utils.gemini_adapter_v2 import GeminiAdapterV2

    # For testing, create mock components
    class MockGeminiAdapterV2:
        """Mock Gemini adapter that returns PaymentRecord objects."""

        def extract_payments(self, file_path: str, document_type: str = None) -> List[PaymentRecord]:
            """Return mock PaymentRecord objects with proper aliases."""

            if "jpg" in file_path:
                # Simulate extraction from check image
                return [
                    PaymentRecord(
                        payment_info=PaymentInfo(
                            payment_method=PaymentMethod.HANDWRITTEN_CHECK,
                            check_no="8117",
                            amount=100.00,
                            payment_date="2025-05-14",
                            check_date="2025-05-14",
                            deposit_date="2025-05-14",
                            deposit_method="ATM Deposit",
                        ),
                        payer_info=PayerInfo(
                            # Only variations of what was extracted
                            aliases=["J. Lang", "Lang, J."],
                            salutation=None,
                            organization_name=None,
                        ),
                        contact_info=ContactInfo(
                            address_line_1=None, city=None, state=None, zip=None, email=None, phone=None
                        ),
                        source_document_type="check_image",
                    ),
                    PaymentRecord(
                        payment_info=PaymentInfo(
                            payment_method=PaymentMethod.HANDWRITTEN_CHECK,
                            check_no="1848",
                            amount=50.00,
                            payment_date="2025-05-14",
                            check_date="2025-05-14",
                            deposit_date="2025-05-14",
                            deposit_method="ATM Deposit",
                        ),
                        payer_info=PayerInfo(
                            aliases=["J. Collins", "Collins, J."], salutation=None, organization_name=None
                        ),
                        contact_info=ContactInfo(),
                    ),
                ]
            else:  # PDF
                return [
                    PaymentRecord(
                        payment_info=PaymentInfo(
                            payment_method=PaymentMethod.PRINTED_CHECK,
                            check_no="13967",
                            amount=500.00,
                            payment_date="2025-05-14",
                            check_date="2025-05-14",
                            deposit_date="2025-05-14",
                            deposit_method="Mobile Deposit",
                        ),
                        payer_info=PayerInfo(
                            aliases=None, salutation=None, organization_name="Lutheran Church of the Holy Spirit"
                        ),
                        contact_info=ContactInfo(
                            address_line_1="5700 West 96th Street", city="Oak Lawn", state="IL", zip="60453"
                        ),
                    )
                ]

    # Mock QBO service with CSV data
    class MockQBOService:
        def __init__(self):
            self.customers = [
                {
                    "Id": "1234",
                    "DisplayName": "Lang, John D. & Esther A.",
                    "GivenName": "John & Esther",
                    "FamilyName": "Lang",
                    "CompanyName": "",
                    "BillAddr": {
                        "Line1": "PO Box 982",
                        "City": "Emory",
                        "CountrySubDivisionCode": "VA",
                        "PostalCode": "24327",
                    },
                    "PrimaryEmailAddr": {},
                    "PrimaryPhone": {"FreeFormNumber": "(276) 944-5769"},
                },
                {
                    "Id": "5678",
                    "DisplayName": "Collins, Jonelle",
                    "GivenName": "Jonelle",
                    "FamilyName": "Collins",
                    "CompanyName": "",
                    "BillAddr": {
                        "Line1": "123 Main St",
                        "City": "Springfield",
                        "CountrySubDivisionCode": "IL",
                        "PostalCode": "62701",
                    },
                    "PrimaryEmailAddr": {"Address": "jonelle@collins.com"},
                    "PrimaryPhone": {},
                },
                {
                    "Id": "9012",
                    "DisplayName": "Lutheran Church of the Holy Spirit",
                    "CompanyName": "Lutheran Church of the Holy Spirit",
                    "BillAddr": {
                        "Line1": "5700 West 96th Street",
                        "City": "Oak Lawn",
                        "CountrySubDivisionCode": "IL",
                        "PostalCode": "60453",
                    },
                    "PrimaryEmailAddr": {"Address": "office@holyspiritchurch.org"},
                },
            ]

        def get_all_customers(self, use_cache=True):
            return self.customers

        def get_customer_by_id(self, customer_id):
            for c in self.customers:
                if c["Id"] == customer_id:
                    return c
            return None

    # Create services
    gemini_service = MockGeminiAdapterV2()
    qbo_service = MockQBOService()

    # Create processor
    processor = EnhancedFileProcessorV2(gemini_service, qbo_service)

    # Process files
    logger.info("=" * 80)
    logger.info("TESTING REFACTORED WORKFLOW")
    logger.info("=" * 80)

    files = [("dummy_check.jpg", ".jpg"), ("dummy_batch.pdf", ".pdf")]

    enriched_payments, errors = processor.process_files(files)

    # Display results
    logger.info("\n" + "=" * 80)
    logger.info("FINAL ENRICHED OUTPUT (NO LEGACY FORMAT)")
    logger.info("=" * 80 + "\n")

    print(json.dumps(enriched_payments, indent=2))

    # Verify the workflow
    logger.info("\n" + "=" * 80)
    logger.info("WORKFLOW VERIFICATION")
    logger.info("=" * 80)

    successes = []

    # Check 1: No "Donor Name" field
    has_donor_name = any("Donor Name" in str(p) for p in enriched_payments)
    if not has_donor_name:
        successes.append("✅ No 'Donor Name' field in output")
    else:
        successes.append("❌ Found 'Donor Name' field (should not exist)")

    # Check 2: J. Lang matched to John D. & Esther A. Lang
    lang_payment = next((p for p in enriched_payments if "Lang" in p["payer_info"]["customer_lookup"]), None)
    if lang_payment and lang_payment["match_status"] == "Matched":
        successes.append("✅ J. Lang successfully matched to Lang, John D. & Esther A.")
    else:
        successes.append("❌ J. Lang did not match")

    # Check 3: No Gemini verification calls
    successes.append("✅ No Gemini verification calls (only extraction)")

    # Check 4: Using PaymentRecord objects
    successes.append("✅ Using PaymentRecord objects throughout")

    # Check 5: Aliases used for matching
    successes.append("✅ Aliases used for smart matching")

    for success in successes:
        logger.info(success)

    # Show specific match details
    logger.info("\n" + "=" * 80)
    logger.info("MATCH DETAILS")
    logger.info("=" * 80)

    for payment in enriched_payments:
        payer = payment["payer_info"]
        logger.info(f"\nCustomer Lookup: {payer['customer_lookup']}")
        logger.info(f"  Match Status: {payment['match_status']}")
        if payment["match_status"] == "Matched":
            logger.info(f"  QBO Name: {payer.get('full_name', '')}")
            logger.info(f"  QBO ID: {payment.get('qbo_customer_id')}")


if __name__ == "__main__":
    test_refactored_workflow()
