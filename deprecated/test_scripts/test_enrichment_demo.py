#!/usr/bin/env python3
"""
Demonstrate the enrichment pipeline with mock data.
This shows the final JSON structure after processing.
"""

import json
import logging
import os
import sys
from pathlib import Path
from unittest.mock import Mock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Set environment to not use legacy format
os.environ["USE_LEGACY_FORMAT"] = "false"

# Import required modules
from src.utils.enhanced_file_processor import EnhancedFileProcessor
from src.utils.payment_combiner import PaymentCombiner
from src.utils.qbo_data_enrichment import QBODataEnrichment

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class MockGeminiService:
    """Mock Gemini service that returns test extraction data."""

    def __init__(self):
        self.use_structured = True

    def extract_donation_data(self, file_path, custom_prompt=None):
        """Return mock extraction data based on file type."""
        if file_path.endswith(".jpg"):
            return [
                {
                    "Donor Name": "John Smith",
                    "First Name": "John",
                    "Last Name": "Smith",
                    "Salutation": "Mr.",
                    "Gift Amount": "250.00",
                    "Check No.": "1234",
                    "Check Date": "2024-12-15",
                    "Deposit Date": "2024-12-18",
                    "Deposit Method": "ATM Deposit",
                    "Address - Line 1": "456 Updated Street",  # Different from QBO!
                    "City": "New City",  # Different from QBO!
                    "State": "CA",
                    "ZIP": "90211",  # Slightly different
                    "Email": "john.new@example.com",  # New email!
                    "Phone": "(555) 999-8888",  # New phone!
                    "Memo": "Annual donation",
                }
            ]
        else:  # PDF
            return [
                {
                    "Donor Name": "Acme Corporation",
                    "Organization Name": "Acme Corporation",
                    "Gift Amount": "1000.00",
                    "Check No.": "5678",
                    "Check Date": "2024-12-16",
                    "Deposit Date": "2024-12-18",
                    "Deposit Method": "Mobile Deposit",
                    "Address - Line 1": "999 New Corporate Way",  # Very different!
                    "City": "Dallas",  # Different city!
                    "State": "TX",
                    "ZIP": "75201",  # Different ZIP
                    "Email": "accounting@acmecorp.com",  # New email
                    "Memo": "Q4 2024 contribution",
                },
                {
                    "Donor Name": "Jane Doe",
                    "First Name": "Jane",
                    "Last Name": "Doe",
                    "Gift Amount": "150.00",
                    "Check No.": "9012",
                    "Check Date": "2024-12-17",
                    "Deposit Date": "2024-12-18",
                    "Address - Line 1": "789 Pine Street",
                    "City": "Springfield",
                    "State": "IL",
                    "ZIP": "62701",
                    "Email": "jane.doe@email.com",
                    "Phone": "(217) 555-1234",
                },
            ]

    def verify_customer_match(self, donor, customer):
        """Mock verification."""
        return {"validMatch": True, "matchConfidence": "high"}


class MockQBOService:
    """Mock QBO service with rich customer data."""

    def __init__(self):
        self.customers_data = {
            "john smith": {
                "Id": "1",
                "SyncToken": "0",
                "DisplayName": "John Smith",
                "GivenName": "John",
                "FamilyName": "Smith",
                "FullyQualifiedName": "John Smith",
                "CompanyName": "",
                "BillAddr": {
                    "Line1": "123 Main St",
                    "City": "Anytown",
                    "CountrySubDivisionCode": "CA",
                    "PostalCode": "90210",
                },
                "PrimaryEmailAddr": {"Address": "john.smith@example.com"},
                "PrimaryPhone": {"FreeFormNumber": "(555) 123-4567"},
                "Mobile": {"FreeFormNumber": "(555) 987-6543"},
            },
            "acme corporation": {
                "Id": "2",
                "SyncToken": "1",
                "DisplayName": "Acme Corporation",
                "CompanyName": "Acme Corporation",
                "FullyQualifiedName": "Acme Corporation",
                "BillAddr": {
                    "Line1": "789 Corporate Blvd",
                    "City": "Austin",
                    "CountrySubDivisionCode": "TX",
                    "PostalCode": "78701",
                },
                "PrimaryEmailAddr": {"Address": "info@acmecorp.com"},
                "PrimaryPhone": {"FreeFormNumber": "(512) 555-0100"},
            },
        }

    def find_customer(self, search_term):
        """Find customer by name."""
        return self.customers_data.get(search_term.lower())

    def find_customers_batch(self, search_terms):
        """Batch search customers."""
        results = {}
        for term in search_terms:
            results[term] = self.find_customer(term)
        return results

    def get_customer_by_id(self, customer_id):
        """Get customer by ID."""
        for customer in self.customers_data.values():
            if customer["Id"] == customer_id:
                return customer
        return None


def main():
    """Demonstrate the enrichment pipeline."""

    logger.info("=" * 80)
    logger.info("ENRICHMENT PIPELINE DEMONSTRATION")
    logger.info("=" * 80)

    # Create mock services
    gemini_service = MockGeminiService()
    qbo_service = MockQBOService()

    # Create enhanced processor
    processor = EnhancedFileProcessor(gemini_service, qbo_service)

    # Mock files to process
    files = [("/dummy/check.jpg", ".jpg"), ("/dummy/batch.pdf", ".pdf")]

    logger.info(f"\nProcessing {len(files)} files with enrichment...")

    # Process files
    enriched_data, errors = processor.process_files_concurrently_with_enrichment(files)

    # Display results
    logger.info(f"\n{'='*80}")
    logger.info("FINAL ENRICHED JSON OUTPUT")
    logger.info(f"{'='*80}\n")

    # Pretty print the JSON
    print(json.dumps(enriched_data, indent=2))

    # Detailed analysis
    logger.info(f"\n{'='*80}")
    logger.info("DETAILED ANALYSIS")
    logger.info(f"{'='*80}")

    for i, payment in enumerate(enriched_data):
        payer_info = payment.get("payer_info", {})
        payment_info = payment.get("payment_info", {})

        print(f"\n{'='*60}")
        print(f"PAYMENT {i+1}: {payer_info.get('customer_lookup', 'Unknown')}")
        print(f"{'='*60}")

        print("\nPAYER INFO:")
        print(f"  Customer Lookup: {payer_info.get('customer_lookup')}")
        print(f"  Salutation: {payer_info.get('salutation')}")
        print(f"  First Name: {payer_info.get('first_name')}")
        print(f"  Last Name: {payer_info.get('last_name')}")
        print(f"  Full Name: {payer_info.get('full_name')}")
        print(f"  QB Organization Name: {payer_info.get('qb_organization_name')}")
        print(f"  QB Address - Line 1: {payer_info.get('qb_address_line_1')}")
        print(f"  QB City: {payer_info.get('qb_city')}")
        print(f"  QB State: {payer_info.get('qb_state')}")
        print(f"  QB ZIP: {payer_info.get('qb_zip')}")
        print(f"  QB Email: {payer_info.get('qb_email')}")
        print(f"  QB Phone: {payer_info.get('qb_phone')}")

        print("\nPAYMENT INFO:")
        print(f"  Check No./Payment Ref: {payment_info.get('check_no_or_payment_ref')}")
        print(f"  Amount: ${payment_info.get('amount')}")
        print(f"  Payment Date: {payment_info.get('payment_date')}")
        print(f"  Deposit Date: {payment_info.get('deposit_date')}")
        print(f"  Deposit Method: {payment_info.get('deposit_method')}")
        print(f"  Memo: {payment_info.get('memo')}")

        print("\nMATCH STATUS:")
        print(f"  Status: {payment.get('match_status')}")
        print(f"  QBO Customer ID: {payment.get('qbo_customer_id')}")

        if payer_info.get("address_needs_update"):
            print("\n⚠️  ADDRESS UPDATE NEEDED:")
            print(f"  Extracted Address: {payer_info.get('extracted_address')}")
            print(f"  Differences: {payer_info.get('address_differences')}")

        if payer_info.get("email_updated"):
            print("\n✅ EMAIL ADDED/UPDATED")

        if payer_info.get("phone_updated"):
            print("\n✅ PHONE ADDED/UPDATED")

    # Summary
    logger.info(f"\n{'='*80}")
    logger.info("SUMMARY")
    logger.info(f"{'='*80}")
    logger.info(f"Total payments processed: {len(enriched_data)}")

    matched = sum(1 for p in enriched_data if p.get("match_status") != "New")
    logger.info(f"Matched to QBO customers: {matched}")

    needs_update = sum(1 for p in enriched_data if p.get("payer_info", {}).get("address_needs_update"))
    logger.info(f"Address updates needed: {needs_update}")

    emails_added = sum(1 for p in enriched_data if p.get("payer_info", {}).get("email_updated"))
    logger.info(f"Emails added: {emails_added}")

    phones_added = sum(1 for p in enriched_data if p.get("payer_info", {}).get("phone_updated"))
    logger.info(f"Phones added: {phones_added}")


if __name__ == "__main__":
    main()
