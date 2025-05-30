#!/usr/bin/env python3
"""
Enhanced end-to-end test that specifically tests the enrichment features.
This test includes address comparison, email/phone list management, and
the final combined JSON output format.
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Import required modules
from utils.enhanced_file_processor import EnhancedFileProcessor
from utils.gemini_adapter import GeminiAdapter
from utils.payment_combiner import PaymentCombiner
from utils.qbo_data_enrichment import QBODataEnrichment


class EnhancedMockQBOService:
    """Enhanced mock QBO service with rich customer data."""

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

    def find_customer(self, lookup_value):
        """Find customer by name or other field."""
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
        """Get customer by ID."""
        return self.customers.get(str(customer_id))

    def get_all_customers(self, use_cache=True):
        """Get all customers."""
        return list(self.customers.values())


def setup_test_environment():
    """Set up test directories and logging."""
    # Create necessary directories
    base_dir = Path(__file__).parent
    (base_dir / "logs").mkdir(exist_ok=True)
    (base_dir / "output").mkdir(exist_ok=True)
    (base_dir / "test_results").mkdir(exist_ok=True)

    # Set up logging
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = base_dir / "logs" / f"e2e_enrichment_test_{timestamp}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
    )

    return timestamp, str(log_file)


def create_test_extractions():
    """Create test extraction data with various scenarios."""
    return [
        {
            # John Smith - will match, same address
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
            "Email": "john.smith@example.com",  # Same as QBO
            "Phone": "(555) 123-4567",  # Same as QBO
            "Deposit Date": "2024-01-20",
        },
        {
            # Acme Corporation - will match, different address
            "Donor Name": "Acme Corporation",
            "Organization Name": "Acme Corporation",
            "Gift Amount": "500.00",
            "Check No.": "9999",
            "Check Date": "2024-01-16",
            "Address - Line 1": "123 New Address Lane",  # Different!
            "City": "New City",  # Different!
            "State": "TX",
            "ZIP": "75002",  # Different!
            "Email": "newemail@acmecorp.com",  # New email!
            "Phone": "(555) 111-2222",  # New phone!
            "Deposit Date": "2024-01-20",
        },
        {
            # Jane Doe - no match, new customer
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
        },
    ]


def run_enrichment_test():
    """Run the enhanced end-to-end test."""
    logger = logging.getLogger(__name__)
    timestamp, log_file = setup_test_environment()

    logger.info("=" * 80)
    logger.info("Starting Enhanced End-to-End Pipeline Test with Enrichment")
    logger.info("=" * 80)

    # Create mock services
    mock_gemini = Mock(spec=GeminiAdapter)
    mock_gemini.use_structured = True
    mock_qbo = EnhancedMockQBOService()

    # Create test data
    test_extractions = create_test_extractions()

    # Mock Gemini to return our test data
    mock_gemini.extract_donation_data.return_value = test_extractions

    # Mock verification results
    def mock_verify(donation, customer):
        if donation.get("Donor Name") == "John Smith":
            return {"validMatch": True, "matchConfidence": "high", "addressMateriallyDifferent": False}
        elif donation.get("Donor Name") == "Acme Corporation":
            return {
                "validMatch": True,
                "matchConfidence": "high",
                "addressMateriallyDifferent": True,  # Address differs!
            }
        return {"validMatch": False}

    mock_gemini.verify_customer_match.side_effect = mock_verify

    # Create enhanced file processor
    processor = EnhancedFileProcessor(mock_gemini, mock_qbo)

    # Disable legacy format to get enriched output
    os.environ["USE_LEGACY_FORMAT"] = "false"

    logger.info("\n" + "-" * 60)
    logger.info("Phase 1: Processing with Enrichment")
    logger.info("-" * 60)

    # Process files (simulated as already extracted)
    enriched_data, errors = processor.process_files_concurrently_with_enrichment(
        [("dummy.pdf", ".pdf")], task_id="test_enrichment"  # Dummy file reference
    )

    logger.info(f"\nProcessed {len(enriched_data)} payments with enrichment")

    # Log enriched results
    logger.info("\n" + "-" * 60)
    logger.info("Phase 2: Enrichment Results")
    logger.info("-" * 60)

    for payment in enriched_data:
        payer_info = payment.get("payer_info", {})
        payment_info = payment.get("payment_info", {})

        logger.info(f"\nPayer: {payer_info.get('customer_lookup', 'Unknown')}")
        logger.info(f"  Match Status: {payment.get('match_status')}")
        logger.info(f"  Amount: ${payment_info.get('amount', 0)}")
        logger.info(f"  Check #: {payment_info.get('check_no_or_payment_ref')}")

        # Check enrichment features
        if payer_info.get("address_needs_update"):
            logger.info("  ⚠️  ADDRESS NEEDS UPDATE")
            logger.info(f"    Current: {payer_info.get('qb_address_line_1')}, {payer_info.get('qb_city')}")
            extracted = payer_info.get("extracted_address", {})
            logger.info(f"    New: {extracted.get('line_1')}, {extracted.get('city')}")

        if payer_info.get("email_updated"):
            logger.info("  ✉️  NEW EMAIL ADDED")
            logger.info(f"    Emails: {payer_info.get('qb_email', [])}")

        if payer_info.get("phone_updated"):
            logger.info("  📞  NEW PHONE ADDED")
            logger.info(f"    Phones: {payer_info.get('qb_phone', [])}")

    # Export results
    logger.info("\n" + "-" * 60)
    logger.info("Phase 3: Exporting Results")
    logger.info("-" * 60)

    output_dir = Path(__file__).parent / "test_results"
    output_file = output_dir / f"e2e_enrichment_results_{timestamp}.json"

    # Create summary
    summary = {
        "timestamp": timestamp,
        "test_type": "enrichment_pipeline",
        "summary": {
            "total_payments": len(enriched_data),
            "matched": sum(1 for p in enriched_data if p.get("match_status") != "New"),
            "new_customers": sum(1 for p in enriched_data if p.get("match_status") == "New"),
            "address_updates_needed": sum(
                1 for p in enriched_data if p.get("payer_info", {}).get("address_needs_update")
            ),
            "emails_added": sum(1 for p in enriched_data if p.get("payer_info", {}).get("email_updated")),
            "phones_added": sum(1 for p in enriched_data if p.get("payer_info", {}).get("phone_updated")),
        },
        "payments": enriched_data,
        "errors": errors,
    }

    with open(output_file, "w") as f:
        json.dump(summary, f, indent=2)

    logger.info(f"\nResults exported to: {output_file}")
    logger.info(f"Log file: {log_file}")

    # Test backward compatibility
    logger.info("\n" + "-" * 60)
    logger.info("Phase 4: Testing Backward Compatibility")
    logger.info("-" * 60)

    # Enable legacy format
    os.environ["USE_LEGACY_FORMAT"] = "true"

    # Process again with legacy format
    legacy_data, _ = processor.process_files_concurrently([("dummy.pdf", ".pdf")], task_id="test_legacy")

    logger.info(f"\nLegacy format test: {len(legacy_data)} donations")

    # Check that enrichment data is still present in legacy format
    for donation in legacy_data[:1]:  # Just check first one
        logger.info(f"\nLegacy format sample:")
        logger.info(f"  Donor Name: {donation.get('Donor Name')}")
        logger.info(f"  Address Needs Update: {donation.get('addressNeedsUpdate')}")
        logger.info(f"  Email Updated: {donation.get('emailUpdated')}")
        logger.info(f"  Phone Updated: {donation.get('phoneUpdated')}")

    logger.info("\n" + "=" * 80)
    logger.info("Enhanced End-to-End Test Complete!")
    logger.info("=" * 80)

    return summary


if __name__ == "__main__":
    # Mock the extract_donation_data to use our test data
    with patch.object(GeminiAdapter, "extract_donation_data", return_value=create_test_extractions()):
        summary = run_enrichment_test()

        # Print final statistics
        stats = summary["summary"]
        print(f"\nFinal Statistics:")
        print(f"  Total Payments: {stats['total_payments']}")
        print(f"  Matched: {stats['matched']}")
        print(f"  New Customers: {stats['new_customers']}")
        print(f"  Address Updates Needed: {stats['address_updates_needed']}")
        print(f"  Emails Added: {stats['emails_added']}")
        print(f"  Phones Added: {stats['phones_added']}")
