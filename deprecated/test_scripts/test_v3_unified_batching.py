#!/usr/bin/env python3
"""
Test the V3 unified batching workflow with batch size of 5.
"""

import csv
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


def load_csv_customers(csv_path):
    """Load customers from CSV file."""
    customers = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert CSV row to QBO-like format
            customer_name = row.get("Customer", "")
            customer_id = str(hash(customer_name) % 10000)

            customers.append(
                {
                    "Id": customer_id,
                    "SyncToken": "0",
                    "DisplayName": customer_name,
                    "GivenName": row.get("First name", ""),
                    "FamilyName": row.get("Last name", ""),
                    "FullyQualifiedName": row.get("Full name", "") or customer_name,
                    "CompanyName": row.get("Company", ""),
                    "BillAddr": {
                        "Line1": row.get("Bill street", ""),
                        "City": row.get("Bill city", ""),
                        "CountrySubDivisionCode": row.get("Bill state", ""),
                        "PostalCode": row.get("Bill zip", ""),
                    },
                    "PrimaryEmailAddr": {"Address": row.get("Email", "")},
                    "PrimaryPhone": {"FreeFormNumber": row.get("Phone", "") or row.get("Phone numbers", "")},
                }
            )

    return customers


def main():
    """Test V3 workflow with unified batching."""

    # Import V3 components
    from src.utils.alias_matcher import AliasMatcher
    from src.utils.enhanced_file_processor_v3 import EnhancedFileProcessorV3
    from src.utils.gemini_adapter_v3 import GeminiAdapterV3

    # Check for API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY not set!")
        return

    # Create Gemini V3 service
    gemini_service = GeminiAdapterV3(api_key)

    # Create mock QBO service with CSV data
    class CSVQBOService:
        def __init__(self, customers):
            self.customers = customers

        def get_all_customers(self, use_cache=True):
            return self.customers

        def get_customer_by_id(self, customer_id):
            for c in self.customers:
                if c["Id"] == customer_id:
                    return c
            return None

    # Load CSV customers
    csv_path = Path(__file__).parent / "Friends of Mwangaza_Customer Contact List - All Fields.csv"
    customers = load_csv_customers(csv_path)
    logger.info(f"Loaded {len(customers)} customers from CSV")

    qbo_service = CSVQBOService(customers)

    # Create V3 processor
    processor = EnhancedFileProcessorV3(gemini_service, qbo_service)

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

    logger.info("\n" + "=" * 80)
    logger.info("PROCESSING WITH V3 UNIFIED BATCHING (BATCH SIZE = 5)")
    logger.info("=" * 80)
    logger.info("Expected: 18 page PDF + 1 image = 19 items total")
    logger.info("Batches: 5 + 5 + 5 + 4 = 4 batches")

    # Process files
    try:
        enriched_payments, errors = processor.process_files(files)
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        return

    if errors:
        logger.error(f"Errors: {errors}")

    # Display results
    logger.info("\n" + "=" * 80)
    logger.info("FINAL ENRICHED JSON OUTPUT")
    logger.info("=" * 80 + "\n")

    print(json.dumps(enriched_payments, indent=2))

    # Analysis
    logger.info("\n" + "=" * 80)
    logger.info("ANALYSIS")
    logger.info("=" * 80)

    logger.info(f"\nTotal payments: {len(enriched_payments)}")

    # Look for the DAFgiving payment
    for payment in enriched_payments:
        check_no = payment["payment_info"].get("check_no_or_payment_ref", "")
        if "3517031" in str(check_no):
            payer = payment["payer_info"]
            logger.info(f"\nFound payment with ref 0003517031:")
            logger.info(f"  Organization: {payer.get('qb_organization_name', 'N/A')}")
            logger.info(f"  Customer lookup: {payer.get('customer_lookup', 'N/A')}")
            logger.info(f"  Match status: {payment.get('match_status', 'N/A')}")

            # Check if it's correctly identified as DAFgivingSGOs
            if "SGO" in str(payer.get("qb_organization_name", "")):
                logger.info("  ✅ CORRECTLY extracted as DAFgivingSGOs!")
            else:
                logger.info("  ❌ Still misread the organization name")


if __name__ == "__main__":
    main()
