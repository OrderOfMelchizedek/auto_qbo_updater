#!/usr/bin/env python3
"""
Test the V2 refactored workflow with real dummy files and CSV customer data.
This uses the new components that work with PaymentRecord objects and aliases.
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
    """Test V2 workflow with real files."""

    # Import V2 components
    from src.utils.alias_matcher import AliasMatcher
    from src.utils.enhanced_file_processor_v2 import EnhancedFileProcessorV2
    from src.utils.gemini_adapter_v2 import GeminiAdapterV2

    # Check for API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY not set!")
        return

    # Create Gemini V2 service
    gemini_service = GeminiAdapterV2(api_key)

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
    if not csv_path.exists():
        logger.error(f"CSV file not found: {csv_path}")
        logger.info("Creating sample customers instead...")
        customers = [
            {
                "Id": "1",
                "SyncToken": "0",
                "DisplayName": "Lang, John D. & Esther A.",
                "GivenName": "John",
                "FamilyName": "Lang",
                "FullyQualifiedName": "Lang, John D. & Esther A.",
                "CompanyName": "",
                "BillAddr": {
                    "Line1": "123 Main St",
                    "City": "Springfield",
                    "CountrySubDivisionCode": "IL",
                    "PostalCode": "62701",
                },
                "PrimaryEmailAddr": {"Address": "jlang@example.com"},
                "PrimaryPhone": {"FreeFormNumber": "555-0123"},
            },
            {
                "Id": "2",
                "SyncToken": "0",
                "DisplayName": "Collins, Jonelle",
                "GivenName": "Jonelle",
                "FamilyName": "Collins",
                "FullyQualifiedName": "Collins, Jonelle",
                "CompanyName": "",
                "BillAddr": {
                    "Line1": "456 Oak Ave",
                    "City": "Chicago",
                    "CountrySubDivisionCode": "IL",
                    "PostalCode": "60601",
                },
                "PrimaryEmailAddr": {"Address": "jcollins@example.com"},
                "PrimaryPhone": {"FreeFormNumber": "555-0456"},
            },
        ]
    else:
        customers = load_csv_customers(csv_path)
        logger.info(f"Loaded {len(customers)} customers from CSV")

    qbo_service = CSVQBOService(customers)

    # Create V2 processor
    processor = EnhancedFileProcessorV2(gemini_service, qbo_service)

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
    logger.info("PROCESSING WITH V2 WORKFLOW (ALIASES + NO VERIFICATION)")
    logger.info("=" * 80)

    # Process files
    try:
        enriched_payments, errors = processor.process_files(files)
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        import traceback

        traceback.print_exc()
        # If structured extraction isn't working, show what we would expect
        logger.info("\nDemonstrating expected behavior with mock data...")
        demonstrate_expected_behavior()
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

    for payment in enriched_payments:
        payer = payment["payer_info"]
        logger.info(f"\nCustomer: {payer['customer_lookup']}")
        logger.info(f"  Status: {payment['match_status']}")
        if payment["match_status"] == "Matched":
            logger.info(f"  Matched to: {payer.get('full_name', 'N/A')}")
            logger.info(f"  QBO ID: {payment.get('qbo_customer_id')}")


def demonstrate_expected_behavior():
    """Show what the expected behavior would be."""
    logger.info("\n" + "=" * 80)
    logger.info("EXPECTED BEHAVIOR WITH COMPREHENSIVE ALIASES")
    logger.info("=" * 80)

    examples = [
        {
            "extracted": "J. Lang",
            "expected_aliases": ["J. Lang", "Lang, J."],
            "would_match": ["Lang, John D. & Esther A.", "Lang, J.", "J. Lang & Associates"],
            "explanation": "Matches because 'Lang, J.' pattern fits 'Lang, John...'",
        },
        {
            "extracted": "J. Collins",
            "expected_aliases": ["J. Collins", "Collins, J."],
            "would_match": ["Collins, Jonelle", "Collins, J.", "J. Collins Trust"],
            "explanation": "Matches because last name Collins + initial J matches Jonelle",
        },
        {
            "extracted": "John A. Smith",
            "expected_aliases": [
                "John Smith",
                "J. Smith",
                "Smith, John",
                "Smith, J.",
                "John A. Smith",
                "Smith, John A.",
            ],
            "would_match": ["Smith, John", "John Smith", "Smith, J.", "Smith, John Anthony"],
            "explanation": "Multiple aliases increase match probability",
        },
    ]

    for ex in examples:
        logger.info(f"\nExtracted: '{ex['extracted']}'")
        logger.info(f"Aliases: {ex['expected_aliases']}")
        logger.info(f"Would match: {ex['would_match']}")
        logger.info(f"Why: {ex['explanation']}")


if __name__ == "__main__":
    main()
