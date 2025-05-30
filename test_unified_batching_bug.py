#!/usr/bin/env python3
"""
Test to reproduce the bug where payment data gets mixed up during unified batching.
This test will verify that check 3517031 is incorrectly matched to Fintel instead of Gustafson.
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
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG to see detailed matching logs
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
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
            # Use a stable ID based on customer name position
            customer_id = str(len(customers) + 1)

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
    """Test unified batching bug."""

    # Import V3 components
    from src.utils.enhanced_file_processor_v3_filtered import EnhancedFileProcessorV3
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
            # Create lookup maps
            self.gustafson_id = None
            self.fintel_id = None

            for c in customers:
                if "Gustafson" in c["DisplayName"]:
                    self.gustafson_id = c["Id"]
                    logger.info(f"Found Gustafson: {c['DisplayName']} (ID: {c['Id']})")
                if "Fintel" in c["DisplayName"]:
                    self.fintel_id = c["Id"]
                    logger.info(f"Found Fintel: {c['DisplayName']} (ID: {c['Id']})")

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

    # Create V3 processor with filtering
    processor = EnhancedFileProcessorV3(gemini_service, qbo_service)

    # Test with the dummy files
    files = [
        ("tests/e2e/dummy files/2025-05-17-12-48-17.pdf", ".pdf"),
        ("tests/e2e/dummy files/2025-05-17 12.50.27-1.jpg", ".jpg"),
    ]

    logger.info("\n" + "=" * 80)
    logger.info("TESTING UNIFIED BATCHING BUG")
    logger.info("=" * 80)
    logger.info("Expected: Check 3517031 should match to Gustafson")
    logger.info("Bug: Check 3517031 matches to Fintel instead")

    # Process files
    try:
        enriched_payments, errors = processor.process_files(files)
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        import traceback

        traceback.print_exc()
        return

    # Look for the problematic payment
    logger.info("\n" + "=" * 80)
    logger.info("CHECKING FOR BUG")
    logger.info("=" * 80)

    bug_found = False
    for payment in enriched_payments:
        check_ref = payment["payment_info"].get("check_no_or_payment_ref", "")

        # Look for check 3517031 (without leading zeros)
        if str(check_ref) == "3517031":
            payer_info = payment["payer_info"]
            customer_lookup = payer_info.get("customer_lookup", "")
            qbo_id = payment.get("qbo_customer_id", "")

            logger.info(f"\nFound check 3517031:")
            logger.info(f"  Customer lookup: {customer_lookup}")
            logger.info(f"  QBO ID: {qbo_id}")
            logger.info(f"  Expected: Should match Gustafson (ID: {qbo_service.gustafson_id})")
            logger.info(f"  Actual: Matched to ID {qbo_id}")

            # Check if it's the bug
            if "Fintel" in customer_lookup or qbo_id == qbo_service.fintel_id:
                logger.error("  ❌ BUG CONFIRMED: Check matched to Fintel instead of Gustafson!")
                bug_found = True
            elif "Gustafson" in customer_lookup or qbo_id == qbo_service.gustafson_id:
                logger.info("  ✅ CORRECT: Check properly matched to Gustafson")
            else:
                logger.warning(f"  ⚠️  UNEXPECTED: Check matched to {customer_lookup}")

    if not bug_found:
        # Also check for 0003517031 (with leading zeros)
        for payment in enriched_payments:
            check_ref = payment["payment_info"].get("check_no_or_payment_ref", "")

            if str(check_ref) == "0003517031":
                payer_info = payment["payer_info"]
                customer_lookup = payer_info.get("customer_lookup", "")

                logger.info(f"\nFound check 0003517031:")
                logger.info(f"  Customer lookup: {customer_lookup}")
                logger.info(f"  Note: This should be DAFgivingSGOs")

    # Also show raw extraction to understand the issue
    logger.info("\n" + "=" * 80)
    logger.info("RAW EXTRACTION DATA")
    logger.info("=" * 80)

    try:
        # Get raw extraction
        raw_payments = gemini_service.extract_payments_batch([f[0] for f in files])

        logger.info(f"\nTotal raw payments: {len(raw_payments)}")

        for i, p in enumerate(raw_payments):
            if "3517" in str(p.payment_info.check_no or ""):
                logger.info(f"\nRaw payment {i+1}:")
                logger.info(f"  Check no: {p.payment_info.check_no}")
                logger.info(f"  Amount: ${p.payment_info.amount}")
                logger.info(f"  Organization: {p.payer_info.organization_name}")
                logger.info(f"  Aliases: {p.payer_info.aliases}")

    except Exception as e:
        logger.error(f"Could not get raw extraction: {e}")

    return bug_found


if __name__ == "__main__":
    bug_found = main()
    if bug_found:
        sys.exit(1)  # Exit with error code if bug is found
    else:
        sys.exit(0)
