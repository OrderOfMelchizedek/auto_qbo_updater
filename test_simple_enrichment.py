#!/usr/bin/env python3
"""
Simple test to demonstrate the enrichment pipeline with mock extraction data.
"""

import json
import logging
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Set environment to not use legacy format
os.environ["USE_LEGACY_FORMAT"] = "false"

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def create_test_extraction_with_addresses():
    """Create test extraction data that includes addresses."""
    return [
        {
            "Donor Name": "Gustafson, Karen",
            "First Name": "Karen",
            "Last Name": "Gustafson",
            "Gift Amount": "600.00",
            "Check No.": "3517037",
            "Check Date": "2025-05-14",
            "Deposit Date": "2025-05-14",
            "Deposit Method": "ATM Deposit",
            # Add address that differs from QBO
            "Address - Line 1": "123 New Street",
            "City": "Chicago",
            "State": "IL",
            "ZIP": "60601",
            "Email": "karen.new@email.com",  # New email
            "Phone": "(312) 555-1234",  # New phone
        },
        {
            "Donor Name": "Collins, Jonelle",
            "First Name": "Jonelle",
            "Last Name": "Collins",
            "Gift Amount": "50.00",
            "Check No.": "1848",
            "Check Date": "2025-05-14",
            "Deposit Date": "2025-05-14",
            # No address - should keep QBO data
        },
        {
            "Donor Name": "Lutheran Church of the Holy Spirit",
            "Organization Name": "Lutheran Church of the Holy Spirit",
            "Gift Amount": "500.00",
            "Check No.": "13967",
            "Check Date": "2025-05-14",
            "Deposit Date": "2025-05-14",
            # Same address as QBO
            "Address - Line 1": "789 Church Blvd",
            "City": "Austin",
            "State": "TX",
            "ZIP": "78701",
        },
    ]


def main():
    """Run simple enrichment test."""
    from src.utils.enhanced_file_processor import EnhancedFileProcessor
    from src.utils.payment_combiner import PaymentCombiner
    from src.utils.qbo_data_enrichment import QBODataEnrichment

    # Mock services
    class MockGeminiService:
        def extract_donation_data(self, *args, **kwargs):
            return create_test_extraction_with_addresses()

    class MockQBOService:
        def __init__(self):
            self.customers = {
                "1": {
                    "Id": "1",
                    "SyncToken": "0",
                    "DisplayName": "Gustafson, Karen",
                    "GivenName": "Karen",
                    "FamilyName": "Gustafson",
                    "FullyQualifiedName": "Karen Gustafson",
                    "CompanyName": "",
                    "BillAddr": {
                        "Line1": "387 Selborne Road",
                        "City": "Riverside",
                        "CountrySubDivisionCode": "IL",
                        "PostalCode": "60546",
                    },
                    "PrimaryEmailAddr": {"Address": "karen@gustafson.com"},
                    "PrimaryPhone": {"FreeFormNumber": "(708) 555-9876"},
                },
                "2": {
                    "Id": "2",
                    "SyncToken": "1",
                    "DisplayName": "Collins, Jonelle",
                    "GivenName": "Jonelle",
                    "FamilyName": "Collins",
                    "FullyQualifiedName": "Jonelle Collins",
                    "CompanyName": "",
                    "BillAddr": {
                        "Line1": "456 Oak Street",
                        "City": "Springfield",
                        "CountrySubDivisionCode": "IL",
                        "PostalCode": "62701",
                    },
                    "PrimaryEmailAddr": {"Address": "jonelle@collins.com"},
                },
                "3": {
                    "Id": "3",
                    "SyncToken": "2",
                    "DisplayName": "Lutheran Church of the Holy Spirit",
                    "CompanyName": "Lutheran Church of the Holy Spirit",
                    "FullyQualifiedName": "Lutheran Church of the Holy Spirit",
                    "BillAddr": {
                        "Line1": "789 Church Blvd",
                        "City": "Austin",
                        "CountrySubDivisionCode": "TX",
                        "PostalCode": "78701",
                    },
                    "PrimaryEmailAddr": {"Address": "info@holyspiritchurch.org"},
                },
            }

        def find_customer(self, name):
            for cust in self.customers.values():
                if name.lower() in cust["DisplayName"].lower():
                    return cust
            return None

        def find_customers_batch(self, names):
            return {name: self.find_customer(name) for name in names}

        def get_customer_by_id(self, customer_id):
            return self.customers.get(customer_id)

        def get_all_customers(self, use_cache=True):
            return list(self.customers.values())

    # Create processor
    gemini_service = MockGeminiService()
    qbo_service = MockQBOService()
    processor = EnhancedFileProcessor(gemini_service, qbo_service)

    logger.info("Processing test data with enrichment...")

    # Process test data directly through the pipeline
    # First get the raw extractions
    test_extractions = create_test_extraction_with_addresses()

    # Process through dedupe and matching
    from src.services.deduplication import DeduplicationService

    deduplicated = DeduplicationService.deduplicate_donations([], test_extractions)

    # Match with QBO
    matched = processor.match_donations_with_qbo_customers_batch_enhanced(deduplicated)

    # Convert to final format
    enrichment = QBODataEnrichment()
    combiner = PaymentCombiner(enrichment)
    enriched_data = combiner.process_batch(matched)

    # Display results
    print("\n" + "=" * 80)
    print("FINAL ENRICHED JSON OUTPUT")
    print("=" * 80 + "\n")

    print(json.dumps(enriched_data, indent=2))

    # Detailed analysis
    print("\n" + "=" * 80)
    print("ANALYSIS OF ENRICHMENT FEATURES")
    print("=" * 80)

    for i, payment in enumerate(enriched_data):
        payer_info = payment.get("payer_info", {})

        print(f"\n{'='*60}")
        print(f"PAYMENT {i+1}: {payer_info.get('customer_lookup')}")
        print(f"{'='*60}")

        # Check address update status
        if payer_info.get("address_needs_update"):
            print("\n⚠️  ADDRESS UPDATE NEEDED:")
            print(
                f"  Current QBO Address: {payer_info.get('qb_address_line_1')}, "
                f"{payer_info.get('qb_city')}, {payer_info.get('qb_state')} {payer_info.get('qb_zip')}"
            )
            extracted = payer_info.get("extracted_address", {})
            print(
                f"  New Address: {extracted.get('line_1')}, "
                f"{extracted.get('city')}, {extracted.get('state')} {extracted.get('zip')}"
            )
        else:
            print("\n✅ Address is current")

        # Check email/phone updates
        if payer_info.get("email_updated"):
            print(f"\n📧 EMAIL ADDED: {payer_info.get('qb_email')}")

        if payer_info.get("phone_updated"):
            print(f"\n📱 PHONE ADDED: {payer_info.get('qb_phone')}")

        # Show all QB data
        print("\nQUICKBOOKS DATA:")
        print(f"  Full Name: {payer_info.get('full_name')}")
        print(f"  Organization: {payer_info.get('qb_organization_name') or 'N/A'}")
        print(f"  Email List: {payer_info.get('qb_email')}")
        print(f"  Phone List: {payer_info.get('qb_phone')}")


if __name__ == "__main__":
    main()
