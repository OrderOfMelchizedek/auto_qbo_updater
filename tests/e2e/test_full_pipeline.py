#!/usr/bin/env python3
"""
Comprehensive End-to-End Test Script for FOM to QBO Automation Pipeline

This script:
1. Finds dummy files in the tests/e2e/dummy files directory
2. Mocks all external dependencies (Redis, Celery, S3, QBO API)
3. Processes files through the entire pipeline using EnhancedFileProcessor
4. Captures all logs to a timestamped log file
5. Exports the final JSON results to a timestamped JSON file
6. Simulates QBO authentication and customer matching
7. Tests the full enrichment pipeline including address comparison
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from unittest.mock import MagicMock, Mock, patch

# Add the src directory to the Python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# Mock the problematic imports before importing anything else
sys.modules["src.models"] = MagicMock()
sys.modules["src.models.payment"] = MagicMock()
sys.modules["utils.gemini_adapter"] = MagicMock()
sys.modules["utils.gemini_structured"] = MagicMock()
sys.modules["celery"] = MagicMock()
sys.modules["redis"] = MagicMock()
sys.modules["boto3"] = MagicMock()

# Import application modules
from src.utils.file_processor import FileProcessor
from src.utils.gemini_service import GeminiService
from src.utils.progress_logger import ProgressLogger
from src.utils.prompt_manager import PromptManager
from src.utils.qbo_service import QBOService
from src.utils.qbo_service.auth import QBOAuthService
from src.utils.qbo_service.customers import QBOCustomerService
from src.utils.qbo_service.sales_receipts import QBOSalesReceiptService

# Configure logging
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
# Use the main logs directory
log_dir = Path(__file__).parent.parent.parent / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"e2e_test_{timestamp}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


class MockGeminiService:
    """Mock Gemini service for testing."""

    def __init__(self):
        self.api_key = "mock-api-key"
        self.model_name = "gemini-test-model"
        self.prompt_manager = PromptManager(prompt_dir="docs/prompts_archive")
        self._rate_limiter = MagicMock()
        self.extraction_count = 0

    def extract_donation_data(self, file_path: str, custom_prompt: str = None) -> Optional[Dict[str, Any]]:
        """Mock extraction of donation data from a file."""
        self.extraction_count += 1

        # Simulate different responses based on file type
        if file_path.endswith(".jpg"):
            logger.info(f"Mock extracting from image: {file_path}")
            # Return Acme for the first image extraction to test address mismatch
            if self.extraction_count == 1:
                return [
                    {
                        "Donor Name": "Acme Corporation",
                        "Gift Amount": "500.00",
                        "Check No.": "9999",
                        "Check Date": "2024-01-17",
                        "Address - Line 1": "789 Corporate Blvd",
                        "City": "Business City",  # Different from QBO's Austin
                        "State": "TX",
                        "ZIP": "75001",
                        "Deposit Date": "2024-01-20",
                    }
                ]
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
                    "Phone": "555-1234",
                    "Deposit Date": "2024-01-20",
                },
                {
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
                    "Deposit Date": "2024-01-20",
                },
            ]
        elif file_path.endswith(".pdf"):
            logger.info(f"Mock extracting from PDF: {file_path}")
            return [
                {
                    "Donor Name": "Acme Corporation",
                    "Gift Amount": "500.00",
                    "Check No.": "9999",
                    "Check Date": "2024-01-17",
                    "Address - Line 1": "789 Corporate Blvd",
                    "City": "Business City",  # Different from QBO's Austin
                    "State": "TX",
                    "ZIP": "75001",
                    "Deposit Date": "2024-01-20",
                },
                {
                    "Donor Name": "Bob Wilson",
                    "First Name": "Bob",
                    "Last Name": "Wilson",
                    "Gift Amount": "75.00",
                    "Check No.": "2468",
                    "Check Date": "2024-01-18",
                    "Address - Line 1": "321 Elm St",
                    "City": "Springfield",
                    "State": "IL",
                    "ZIP": "62701",
                    "Email": "bob@wilson.com",
                    "Deposit Date": "2024-01-20",
                },
            ]
        else:
            return None

    def extract_text_data(self, prompt_text: str) -> Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]:
        """Mock text extraction."""
        return {"extracted": "text_data"}

    def extract_donation_data_from_content(
        self, content: Any, prompt: str = None, file_type: str = None
    ) -> Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]:
        """Mock extraction from content."""
        self.extraction_count += 1
        # Return Acme Corp for PDF batch processing
        return [
            {
                "Donor Name": "Acme Corporation",
                "Gift Amount": "500.00",
                "Check No.": "9999",
                "Check Date": "2024-01-17",
                "Address - Line 1": "789 Corporate Blvd",
                "City": "Business City",  # Different from QBO's Austin
                "State": "TX",
                "ZIP": "75001",
                "Deposit Date": "2024-01-20",
            }
        ]

    def verify_customer_match(self, extracted_donor: Dict[str, Any], qbo_customer: Dict[str, Any]) -> Dict[str, Any]:
        """Mock customer verification."""
        logger.info(
            f"Mock verifying match between {extracted_donor.get('Donor Name')} and {qbo_customer.get('DisplayName')}"
        )

        # Simulate different verification scenarios
        donor_name = extracted_donor.get("Donor Name", "").lower()
        qbo_name = qbo_customer.get("DisplayName", "").lower()

        # Check if names are similar
        if donor_name in qbo_name or qbo_name in donor_name:
            # Check if address is different
            if extracted_donor.get("City", "").lower() != qbo_customer.get("BillAddr", {}).get("City", "").lower():
                return {
                    "validMatch": True,
                    "matchConfidence": "high",
                    "addressMateriallyDifferent": True,
                    "enhancedData": extracted_donor,
                }
            else:
                return {
                    "validMatch": True,
                    "matchConfidence": "high",
                    "addressMateriallyDifferent": False,
                    "enhancedData": {
                        **extracted_donor,
                        "Address - Line 1": qbo_customer.get("BillAddr", {}).get(
                            "Line1", extracted_donor.get("Address - Line 1")
                        ),
                        "City": qbo_customer.get("BillAddr", {}).get("City", extracted_donor.get("City")),
                        "State": qbo_customer.get("BillAddr", {}).get(
                            "CountrySubDivisionCode", extracted_donor.get("State")
                        ),
                        "ZIP": qbo_customer.get("BillAddr", {}).get("PostalCode", extracted_donor.get("ZIP")),
                    },
                }
        else:
            return {"validMatch": False, "matchConfidence": "low", "mismatchReason": "Names do not match"}


class MockQBOService:
    """Mock QBO service for testing."""

    def __init__(self):
        self.auth_service = MagicMock()
        self.auth_service.is_token_valid.return_value = True
        self.customers = QBOCustomerService(self.auth_service)

        # Mock customer database
        self.mock_customers = [
            {
                "Id": "1",
                "DisplayName": "John Smith",
                "GivenName": "John",
                "FamilyName": "Smith",
                "PrimaryEmailAddr": {"Address": "john.smith@example.com"},
                "BillAddr": {
                    "Line1": "123 Main St",
                    "City": "Anytown",
                    "CountrySubDivisionCode": "CA",
                    "PostalCode": "90210",
                },
            },
            {
                "Id": "2",
                "DisplayName": "Acme Corp",
                "CompanyName": "Acme Corporation",
                "BillAddr": {
                    "Line1": "789 Corporate Blvd",
                    "City": "Austin",  # Different city from extracted data
                    "CountrySubDivisionCode": "TX",
                    "PostalCode": "78701",
                },
            },
            {
                "Id": "3",
                "DisplayName": "Bob Wilson",
                "GivenName": "Robert",
                "FamilyName": "Wilson",
                "PrimaryEmailAddr": {"Address": "bob@wilson.com"},
                "BillAddr": {
                    "Line1": "321 Elm St",
                    "City": "Springfield",
                    "CountrySubDivisionCode": "IL",
                    "PostalCode": "62701",
                },
            },
        ]

    def find_customer(self, customer_lookup: str) -> Optional[Dict[str, Any]]:
        """Mock customer search."""
        logger.info(f"Mock searching for customer: {customer_lookup}")

        lookup_lower = customer_lookup.lower()
        for customer in self.mock_customers:
            if (
                lookup_lower in customer.get("DisplayName", "").lower()
                or lookup_lower in customer.get("CompanyName", "").lower()
                or lookup_lower in customer.get("PrimaryEmailAddr", {}).get("Address", "").lower()
                or customer.get("DisplayName", "").lower() in lookup_lower
            ):
                logger.info(f"Found customer: {customer['DisplayName']}")
                return customer

        logger.info(f"No customer found for: {customer_lookup}")
        return None

    def find_customers_batch(self, customer_lookups: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
        """Mock batch customer search."""
        results = {}
        for lookup in customer_lookups:
            results[lookup] = self.find_customer(lookup)
        return results

    def get_all_customers(self, use_cache: bool = True) -> List[Dict[str, Any]]:
        """Mock get all customers."""
        return self.mock_customers


def find_dummy_files() -> List[Tuple[str, str]]:
    """Find all dummy files in the test directory."""
    dummy_dir = Path(__file__).parent / "dummy files"
    files = []

    if dummy_dir.exists():
        for file_path in dummy_dir.iterdir():
            if file_path.is_file():
                ext = file_path.suffix.lower()
                if ext in [".jpg", ".jpeg", ".png", ".pdf", ".csv"]:
                    files.append((str(file_path), ext))
                    logger.info(f"Found dummy file: {file_path.name}")
    else:
        logger.warning(f"Dummy files directory not found: {dummy_dir}")

    return files


def process_pipeline(files: List[Tuple[str, str]]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Process files through the entire pipeline."""
    logger.info("=" * 80)
    logger.info("Starting End-to-End Pipeline Test")
    logger.info("=" * 80)

    # Initialize mocked services
    gemini_service = MockGeminiService()
    qbo_service = MockQBOService()
    progress_logger = ProgressLogger()

    # Create file processor with mocked services
    file_processor = FileProcessor(
        gemini_service=gemini_service, qbo_service=qbo_service, progress_logger=progress_logger
    )

    # Mock external dependencies - they're already mocked in sys.modules
    # No need to patch since we've already mocked the modules

    logger.info("\n" + "-" * 60)
    logger.info("Phase 1: Individual File Processing")
    logger.info("-" * 60)

    # Process individual files
    all_donations = []
    all_errors = []

    for file_path, file_ext in files:
        logger.info(f"\nProcessing file: {Path(file_path).name}")
        try:
            result = file_processor.process(file_path, file_ext)
            if result:
                if isinstance(result, list):
                    logger.info(f"Extracted {len(result)} donations from {Path(file_path).name}")
                    all_donations.extend(result)
                else:
                    logger.info(f"Extracted 1 donation from {Path(file_path).name}")
                    all_donations.append(result)
            else:
                error_msg = f"Failed to extract donations from {Path(file_path).name}"
                logger.error(error_msg)
                all_errors.append(error_msg)
        except Exception as e:
            error_msg = f"Error processing {Path(file_path).name}: {str(e)}"
            logger.error(error_msg)
            all_errors.append(error_msg)

    logger.info(f"\nTotal donations extracted: {len(all_donations)}")

    logger.info("\n" + "-" * 60)
    logger.info("Phase 2: Concurrent Batch Processing")
    logger.info("-" * 60)

    # Test concurrent processing
    batch_donations, batch_errors = file_processor.process_files_concurrently(files)

    logger.info(f"\nBatch processing results:")
    logger.info(f"  - Donations: {len(batch_donations)}")
    logger.info(f"  - Errors: {len(batch_errors)}")

    # Use batch results as they include deduplication and matching
    if batch_donations:
        all_donations = batch_donations

    logger.info("\n" + "-" * 60)
    logger.info("Phase 3: Customer Matching Results")
    logger.info("-" * 60)

    # Analyze customer matching results
    status_counts = {}
    for donation in all_donations:
        status = donation.get("qbCustomerStatus", "Unknown")
        status_counts[status] = status_counts.get(status, 0) + 1

        logger.info(f"\nDonor: {donation.get('Donor Name')}")
        logger.info(f"  Status: {status}")
        logger.info(f"  Amount: ${donation.get('Gift Amount')}")
        logger.info(f"  Check #: {donation.get('Check No.')}")

        if status.startswith("Matched"):
            logger.info(f"  QBO Customer: {donation.get('customerLookup')}")
            logger.info(f"  Match Method: {donation.get('matchMethod')}")
            logger.info(f"  Match Confidence: {donation.get('matchConfidence')}")

            if donation.get("addressMateriallyDifferent"):
                logger.info("  ⚠️  Address needs review:")
                logger.info(
                    f"    Extracted: {donation.get('Address - Line 1')}, {donation.get('City')}, {donation.get('State')} {donation.get('ZIP')}"
                )
                qbo_addr = donation.get("qboAddress", {})
                logger.info(
                    f"    QBO: {qbo_addr.get('Line1')}, {qbo_addr.get('City')}, {qbo_addr.get('State')} {qbo_addr.get('ZIP')}"
                )
        elif status == "New":
            if donation.get("matchRejectionReason"):
                logger.info(f"  Rejection Reason: {donation.get('matchRejectionReason')}")

    logger.info("\n" + "-" * 60)
    logger.info("Summary Statistics")
    logger.info("-" * 60)
    logger.info(f"\nCustomer Status Distribution:")
    for status, count in sorted(status_counts.items()):
        logger.info(f"  {status}: {count}")

    logger.info(f"\nGemini API Calls: {gemini_service.extraction_count}")

    return all_donations, all_errors


def export_results(donations: List[Dict[str, Any]], errors: List[str]):
    """Export results to JSON file."""
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"e2e_results_{timestamp}.json"

    results = {
        "timestamp": timestamp,
        "summary": {
            "total_donations": len(donations),
            "total_errors": len(errors),
            "matched_customers": sum(1 for d in donations if d.get("qbCustomerStatus", "").startswith("Matched")),
            "new_customers": sum(1 for d in donations if d.get("qbCustomerStatus") == "New"),
            "needs_review": sum(1 for d in donations if d.get("addressMateriallyDifferent", False)),
        },
        "donations": donations,
        "errors": errors,
    }

    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    logger.info(f"\nResults exported to: {output_file}")
    logger.info(f"Log file: {log_file}")

    return output_file


def main():
    """Main entry point."""
    try:
        # Find dummy files
        files = find_dummy_files()

        if not files:
            logger.error("No dummy files found to process!")
            return 1

        # Process through pipeline
        donations, errors = process_pipeline(files)

        # Export results
        output_file = export_results(donations, errors)

        logger.info("\n" + "=" * 80)
        logger.info("End-to-End Test Complete!")
        logger.info("=" * 80)

        return 0

    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
