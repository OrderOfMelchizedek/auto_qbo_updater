#!/usr/bin/env python3
"""
Complete end-to-end test using actual dummy files with full enrichment.
Tests the entire pipeline from file extraction to final enriched JSON output.
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Set environment to use enriched format
os.environ["USE_LEGACY_FORMAT"] = "false"

# Import required modules
from utils.enhanced_file_processor import EnhancedFileProcessor
from utils.gemini_service import GeminiService
from utils.qbo_data_enrichment import QBODataEnrichment


class MockGeminiServiceWithEnrichment(GeminiService):
    """Mock Gemini service that returns rich test data."""

    def __init__(self, api_key=None, model_name=None):
        # Initialize with dummy values
        self.api_key = api_key or "mock-api-key"
        self.model_name = model_name or "mock-model"
        self.extraction_count = 0

    def extract_donation_data(self, file_path, custom_prompt=None):
        """Return test data based on file type."""
        self.extraction_count += 1

        if "pdf" in file_path.lower():
            # Return multiple donations for PDF
            return [
                {
                    "Donor Name": "John Smith",
                    "First Name": "John",
                    "Last Name": "Smith",
                    "Gift Amount": "100.00",
                    "Check No.": "1234",
                    "Check Date": "2024-01-15",
                    "Address - Line 1": "123 Main St",
                    "City": "Anytown",
                    "State": "CA",
                    "ZIP": "90210",
                    "Email": "john.smith@example.com",
                    "Phone": "(555) 123-4567",
                    "Deposit Date": "2024-01-20",
                    "Memo": "Annual contribution",
                },
                {
                    "Donor Name": "Acme Corporation",
                    "Organization Name": "Acme Corporation",
                    "Gift Amount": "500.00",
                    "Check No.": "9999",
                    "Check Date": "2024-01-16",
                    "Address - Line 1": "123 New Address Lane",  # Different from QBO
                    "City": "New City",  # Different from QBO
                    "State": "TX",
                    "ZIP": "75002",  # Different from QBO
                    "Email": "newemail@acmecorp.com",  # New email
                    "Phone": "(555) 111-2222",  # New phone
                    "Deposit Date": "2024-01-20",
                    "Memo": "Corporate donation",
                },
            ]
        else:
            # Return single donation for image
            return {
                "Donor Name": "Jane Doe",
                "First Name": "Jane",
                "Last Name": "Doe",
                "Gift Amount": "250.00",
                "Check No.": "5678",
                "Check Date": "2024-01-16",
                "Address - Line 1": "456 Oak Ave",
                "City": "Somewhere",
                "State": "NY",
                "ZIP": "10001",
                "Email": "jane.doe@email.com",
                "Phone": "(212) 555-1234",
                "Deposit Date": "2024-01-20",
                "Memo": "General donation",
            }

    def verify_customer_match(self, donation, customer):
        """Verify customer match with enrichment scenarios."""
        donor_name = donation.get("Donor Name", "").lower()
        customer_name = customer.get("DisplayName", "").lower()

        if donor_name == customer_name:
            # Check if addresses are different
            if donor_name == "acme corporation":
                return {
                    "validMatch": True,
                    "matchConfidence": "high",
                    "addressMateriallyDifferent": True,
                    "mismatchReason": None,
                }
            else:
                return {
                    "validMatch": True,
                    "matchConfidence": "high",
                    "addressMateriallyDifferent": False,
                    "mismatchReason": None,
                }

        return {"validMatch": False, "matchConfidence": "low", "mismatchReason": "Names don't match"}


class MockQBOServiceWithEnrichment:
    """Mock QBO service with rich customer data."""

    def __init__(self):
        self.customers = {
            "1": {
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
            },
            "2": {
                "Id": "2",
                "SyncToken": "1",
                "DisplayName": "Acme Corporation",
                "GivenName": "",
                "FamilyName": "",
                "FullyQualifiedName": "Acme Corporation",
                "CompanyName": "Acme Corporation",
                "BillAddr": {
                    "Line1": "789 Business Blvd",  # Different from extracted
                    "City": "Old City",  # Different from extracted
                    "CountrySubDivisionCode": "TX",
                    "PostalCode": "75001",
                },
                "PrimaryEmailAddr": {"Address": "info@acmecorp.com"},
                "PrimaryPhone": {"FreeFormNumber": "(800) 555-ACME"},
                "Mobile": {"FreeFormNumber": "(555) 999-8888"},
            },
        }
        self.auth_service = Mock()
        self.auth_service.is_token_valid.return_value = True
        self.auth_service.redis_client = None
        self.access_token = "mock-token"
        self.realm_id = "mock-realm"

    def find_customer(self, lookup_value):
        """Find customer by name."""
        lookup_lower = lookup_value.lower()

        for customer in self.customers.values():
            if customer["DisplayName"].lower() == lookup_lower:
                return customer
            if customer.get("PrimaryEmailAddr", {}).get("Address", "").lower() == lookup_lower:
                return customer

        return None

    def find_customers_batch(self, lookup_values):
        """Batch find customers."""
        results = {}
        for value in lookup_values:
            results[value] = self.find_customer(value)
        return results

    def get_customer_by_id(self, customer_id):
        """Get customer by ID with full data."""
        return self.customers.get(str(customer_id))

    def get_all_customers(self, use_cache=True):
        """Get all customers."""
        return list(self.customers.values())


def setup_logging():
    """Set up logging for the test."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create directories
    base_dir = Path(__file__).parent
    log_dir = base_dir / "logs"
    output_dir = base_dir / "test_results"
    log_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)

    # Configure logging
    log_file = log_dir / f"e2e_complete_test_{timestamp}.log"

    # Clear any existing handlers
    logger = logging.getLogger()
    logger.handlers = []

    # Set up new handlers
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
    )

    return timestamp, str(log_file), output_dir


def find_dummy_files():
    """Find all dummy files in the test directory."""
    dummy_dir = Path(__file__).parent / "dummy files"
    if not dummy_dir.exists():
        return []

    files = []
    for file_path in dummy_dir.iterdir():
        if file_path.is_file() and not file_path.name.startswith("."):
            ext = file_path.suffix.lower()
            if ext in [".pdf", ".jpg", ".jpeg", ".png"]:
                files.append((str(file_path), ext))

    return files


def run_complete_pipeline_test():
    """Run the complete end-to-end test."""
    timestamp, log_file, output_dir = setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("=" * 80)
    logger.info("Starting Complete End-to-End Pipeline Test")
    logger.info("=" * 80)

    # Find dummy files
    test_files = find_dummy_files()
    logger.info(f"\nFound {len(test_files)} test files:")
    for file_path, ext in test_files:
        logger.info(f"  - {Path(file_path).name} ({ext})")

    if not test_files:
        logger.error("No test files found! Please add files to tests/e2e/dummy files/")
        return None

    # Create mock services
    mock_gemini = MockGeminiServiceWithEnrichment()
    mock_qbo = MockQBOServiceWithEnrichment()

    # Create enhanced file processor
    processor = EnhancedFileProcessor(mock_gemini, mock_qbo)

    logger.info("\n" + "-" * 60)
    logger.info("Phase 1: Processing Files with Full Enrichment")
    logger.info("-" * 60)

    # Process all files
    all_payments, errors = processor.process_files_concurrently(test_files, "complete_test")

    logger.info(f"\nProcessed {len(all_payments)} payments")
    if errors:
        logger.warning(f"Encountered {len(errors)} errors:")
        for error in errors:
            logger.warning(f"  - {error}")

    # Analyze results
    logger.info("\n" + "-" * 60)
    logger.info("Phase 2: Enrichment Analysis")
    logger.info("-" * 60)

    stats = {
        "total": len(all_payments),
        "matched": 0,
        "new": 0,
        "address_updates": 0,
        "emails_added": 0,
        "phones_added": 0,
    }

    for payment in all_payments:
        payer_info = payment.get("payer_info", {})
        payment_info = payment.get("payment_info", {})

        logger.info(f"\nPayment: {payer_info.get('customer_lookup', 'Unknown')}")
        logger.info(f"  Amount: ${payment_info.get('amount', 0):.2f}")
        logger.info(f"  Check/Ref: {payment_info.get('check_no_or_payment_ref', 'N/A')}")
        logger.info(f"  Status: {payment.get('match_status', 'Unknown')}")

        # Update statistics
        if payment.get("match_status") == "New":
            stats["new"] += 1
        else:
            stats["matched"] += 1

        # Check enrichment features
        if payer_info.get("address_needs_update"):
            stats["address_updates"] += 1
            logger.info("  🏠 ADDRESS UPDATE NEEDED:")
            logger.info(
                f"    QBO: {payer_info.get('qb_address_line_1')}, {payer_info.get('qb_city')}, {payer_info.get('qb_state')} {payer_info.get('qb_zip')}"
            )
            extracted = payer_info.get("extracted_address", {})
            logger.info(
                f"    New: {extracted.get('line_1')}, {extracted.get('city')}, {extracted.get('state')} {extracted.get('zip')}"
            )
            if payer_info.get("address_differences"):
                for diff in payer_info["address_differences"]:
                    logger.info(f"    - {diff}")

        # Check email updates
        emails = payer_info.get("qb_email", [])
        if payer_info.get("email_updated"):
            stats["emails_added"] += 1
            logger.info(f"  ✉️  EMAIL UPDATED: {emails}")
        elif emails:
            logger.info(f"  Email(s): {emails}")

        # Check phone updates
        phones = payer_info.get("qb_phone", [])
        if payer_info.get("phone_updated"):
            stats["phones_added"] += 1
            logger.info(f"  📞 PHONE UPDATED: {phones}")
        elif phones:
            logger.info(f"  Phone(s): {phones}")

        # Show full name info
        if payer_info.get("first_name") or payer_info.get("last_name"):
            logger.info(f"  Name: {payer_info.get('first_name', '')} {payer_info.get('last_name', '')}")

        if payer_info.get("qb_organization_name"):
            logger.info(f"  Organization: {payer_info.get('qb_organization_name')}")

    # Export results
    logger.info("\n" + "-" * 60)
    logger.info("Phase 3: Exporting Results")
    logger.info("-" * 60)

    output_file = output_dir / f"e2e_complete_results_{timestamp}.json"

    export_data = {
        "timestamp": timestamp,
        "test_type": "complete_pipeline",
        "files_processed": [Path(f[0]).name for f in test_files],
        "summary": stats,
        "payments": all_payments,
        "errors": errors,
        "api_calls": {"gemini_extractions": mock_gemini.extraction_count},
    }

    with open(output_file, "w") as f:
        json.dump(export_data, f, indent=2, default=str)

    logger.info(f"\nResults exported to: {output_file}")
    logger.info(f"Log file: {log_file}")

    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("Test Summary")
    logger.info("=" * 60)
    logger.info(f"Total Payments: {stats['total']}")
    logger.info(f"Matched: {stats['matched']}")
    logger.info(f"New Customers: {stats['new']}")
    logger.info(f"Address Updates Needed: {stats['address_updates']}")
    logger.info(f"Emails Added: {stats['emails_added']}")
    logger.info(f"Phones Added: {stats['phones_added']}")
    logger.info("\n✅ Complete Pipeline Test Finished Successfully!")

    return export_data


if __name__ == "__main__":
    # Ensure we're using the enriched format
    os.environ["USE_LEGACY_FORMAT"] = "false"

    # Run the test
    results = run_complete_pipeline_test()

    if results:
        print(f"\n📊 Quick Stats:")
        print(f"   Processed: {results['summary']['total']} payments")
        print(f"   Files: {len(results['files_processed'])}")
        print(f"   Updates needed: {results['summary']['address_updates']}")
    else:
        print("\n❌ Test failed - check logs for details")
