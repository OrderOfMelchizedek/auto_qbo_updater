#!/usr/bin/env python3
"""
Test the V3 unified batching workflow with second-pass extraction.
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
    """Test V3 workflow with second-pass extraction."""

    # Import V3 components
    from src.utils.alias_matcher import AliasMatcher
    from src.utils.enhanced_file_processor_v3_second_pass import EnhancedFileProcessorV3
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

    # Create V3 processor with second-pass extraction
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
    logger.info("PROCESSING WITH V3 UNIFIED BATCHING + SECOND-PASS EXTRACTION")
    logger.info("=" * 80)
    logger.info("Payments without payer info will get a second extraction attempt")

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
    logger.info("FINAL ENRICHED JSON OUTPUT (WITH SECOND PASS)")
    logger.info("=" * 80 + "\n")

    print(json.dumps(enriched_payments, indent=2))

    # Analysis
    logger.info("\n" + "=" * 80)
    logger.info("ANALYSIS")
    logger.info("=" * 80)

    logger.info(f"\nTotal valid payments: {len(enriched_payments)}")
    logger.info("Expected: Hopefully 4 or more payments if second pass found missing payers")

    # List all payments
    for i, payment in enumerate(enriched_payments):
        payment_info = payment["payment_info"]
        payer_info = payment["payer_info"]
        logger.info(f"\nPayment {i+1}:")
        logger.info(f"  Check/Ref: {payment_info.get('check_no_or_payment_ref')}")
        logger.info(f"  Amount: ${payment_info.get('amount')}")
        logger.info(
            f"  Payer: {payer_info.get('customer_lookup') or payer_info.get('qb_organization_name') or 'Unknown'}"
        )
        logger.info(f"  Match status: {payment.get('match_status')}")


if __name__ == "__main__":
    main()
