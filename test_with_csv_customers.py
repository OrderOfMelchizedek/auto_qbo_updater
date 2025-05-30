#!/usr/bin/env python3
"""
Test script to process the dummy files with enrichment using CSV customer data.
"""

import csv
import json
import logging
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Set environment to not use legacy format
os.environ["USE_LEGACY_FORMAT"] = "false"

# Import required modules
from src.utils.enhanced_file_processor import EnhancedFileProcessor
from src.utils.gemini_adapter import GeminiAdapter

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class CSVQBOService:
    """Mock QBO service that uses CSV data."""

    def __init__(self, csv_path):
        self.auth_service = None
        self.customers_data = []
        self.customers_by_name = {}
        self.load_csv_data(csv_path)

    def load_csv_data(self, csv_path):
        """Load customer data from CSV file."""
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Convert CSV row to QBO-like customer object
                customer = self.csv_to_qbo_format(row)
                self.customers_data.append(customer)

                # Index by various name forms for easy lookup
                display_name = customer["DisplayName"].lower()
                self.customers_by_name[display_name] = customer

                # Also index by last name if available
                if customer.get("FamilyName"):
                    self.customers_by_name[customer["FamilyName"].lower()] = customer

                # Index by company name if available
                if customer.get("CompanyName"):
                    self.customers_by_name[customer["CompanyName"].lower()] = customer

        logger.info(f"Loaded {len(self.customers_data)} customers from CSV")

    def csv_to_qbo_format(self, csv_row):
        """Convert CSV row to QBO customer format."""
        # Generate a unique ID based on customer name
        customer_name = csv_row.get("Customer", "")
        customer_id = str(hash(customer_name) % 10000)

        # Parse name components
        full_name = csv_row.get("Full name", "")
        first_name = csv_row.get("First name", "")
        last_name = csv_row.get("Last name", "")

        # Determine if it's a company
        company_name = csv_row.get("Company", "")

        return {
            "Id": customer_id,
            "SyncToken": "0",
            "DisplayName": customer_name,
            "GivenName": first_name,
            "FamilyName": last_name,
            "FullyQualifiedName": full_name or customer_name,
            "CompanyName": company_name,
            "BillAddr": {
                "Line1": csv_row.get("Bill street", ""),
                "City": csv_row.get("Bill city", ""),
                "CountrySubDivisionCode": csv_row.get("Bill state", ""),
                "PostalCode": csv_row.get("Bill zip", ""),
            },
            "PrimaryEmailAddr": {"Address": csv_row.get("Email", "")},
            "PrimaryPhone": {"FreeFormNumber": csv_row.get("Phone", "") or csv_row.get("Phone numbers", "")},
            # Store original CSV data for reference
            "_csv_data": csv_row,
        }

    def find_customer(self, search_term):
        """Find customer by name."""
        if not search_term:
            return None

        search_lower = search_term.lower().strip()

        # Direct match
        if search_lower in self.customers_by_name:
            return self.customers_by_name[search_lower]

        # Partial match - search in display names
        for name, customer in self.customers_by_name.items():
            if search_lower in name or name in search_lower:
                return customer

        # Try last name only
        for customer in self.customers_data:
            if customer.get("FamilyName", "").lower() == search_lower:
                return customer

        # Try searching in the full customer name
        for customer in self.customers_data:
            display_name = customer.get("DisplayName", "").lower()
            # Handle "Last, First" format
            if "," in display_name:
                parts = display_name.split(",")
                if parts[0].strip() == search_lower:  # Match last name
                    return customer

        logger.debug(f"No match found for: {search_term}")
        return None

    def find_customers_batch(self, search_terms):
        """Batch search customers."""
        results = {}
        for term in search_terms:
            results[term] = self.find_customer(term)
        return results

    def get_customer_by_id(self, customer_id):
        """Get customer by ID."""
        for customer in self.customers_data:
            if customer["Id"] == customer_id:
                return customer
        return None

    def get_all_customers(self, use_cache=True):
        """Get all customers."""
        return self.customers_data


def main():
    """Process dummy files and show enriched output."""

    # Find dummy files
    dummy_dir = Path(__file__).parent / "tests" / "e2e" / "dummy files"
    files = []

    for file_path in dummy_dir.iterdir():
        if file_path.suffix.lower() in [".jpg", ".pdf"]:
            files.append((str(file_path), file_path.suffix))
            logger.info(f"Found file: {file_path.name}")

    if not files:
        logger.error("No dummy files found!")
        return

    # Create services
    logger.info("\nInitializing services...")

    # Load environment variables
    from dotenv import load_dotenv

    load_dotenv()

    # Use real Gemini service with API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY not set!")
        return

    gemini_service = GeminiAdapter(api_key=api_key)

    # Use CSV-based QBO service
    csv_path = Path(__file__).parent / "Friends of Mwangaza_Customer Contact List - All Fields.csv"
    qbo_service = CSVQBOService(csv_path)

    # Create enhanced processor
    processor = EnhancedFileProcessor(gemini_service, qbo_service)

    logger.info(f"\nProcessing {len(files)} files with enrichment...")

    # Process files
    enriched_data, errors = processor.process_files_concurrently_with_enrichment(files)

    # Debug: Print raw enriched data length
    logger.info(f"Raw enriched data: {len(enriched_data)} items")

    if errors:
        logger.error(f"Errors during processing: {errors}")

    # Display results
    logger.info(f"\n{'='*80}")
    logger.info("FINAL ENRICHED JSON OUTPUT")
    logger.info(f"{'='*80}\n")

    # Pretty print the JSON
    print(json.dumps(enriched_data, indent=2))

    # Show detailed analysis
    print(f"\n{'='*80}")
    print("DETAILED ANALYSIS")
    print(f"{'='*80}")

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

    # Summary statistics
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
