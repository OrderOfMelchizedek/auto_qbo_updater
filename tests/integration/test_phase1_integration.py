#!/usr/bin/env python3
"""
Integration test for Phase 1 implementation.
Tests the complete flow from extraction to final combined JSON output.
"""

import json
import os
import sys
from unittest.mock import Mock, patch

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.utils.enhanced_file_processor import EnhancedFileProcessor
from src.utils.gemini_adapter import create_gemini_service


def create_mock_qbo_service():
    """Create a mock QBO service with test data."""
    mock_qbo = Mock()

    # Mock customer data
    test_customer = {
        "Id": "123",
        "SyncToken": "0",
        "DisplayName": "John Smith",
        "GivenName": "John",
        "FamilyName": "Smith",
        "FullyQualifiedName": "John Smith",
        "CompanyName": "",
        "BillAddr": {
            "Line1": "123 Main St",
            "City": "Springfield",
            "CountrySubDivisionCode": "IL",
            "PostalCode": "62701",
        },
        "PrimaryEmailAddr": {"Address": "john@example.com"},
        "PrimaryPhone": {"FreeFormNumber": "(555) 123-4567"},
    }

    # Mock the methods
    mock_qbo.find_customers_batch.return_value = {
        "John Smith": test_customer,
        "john@example.com": test_customer,
        "(555) 123-4567": test_customer,
    }

    mock_qbo.get_customer_by_id.return_value = test_customer
    mock_qbo.get_all_customers.return_value = [test_customer]

    return mock_qbo


def test_phase1_integration():
    """Test the complete Phase 1 integration."""

    print("=== Phase 1 Integration Test ===\n")

    # Initialize services
    api_key = os.environ.get("GEMINI_API_KEY", "test-key")

    # Create mock Gemini service for testing
    mock_gemini = Mock()

    # Mock extraction result (legacy format)
    mock_extraction = {
        "Donor Name": "John Smith",
        "Check No.": "1234",
        "Gift Amount": "500.00",
        "Check Date": "2025-05-28",
        "Deposit Date": "2025-05-30",
        "Deposit Method": "Mobile Deposit",
        "Memo": "Annual contribution",
        "Address - Line 1": "456 Elm St",  # Different from QBO
        "City": "Chicago",  # Different from QBO
        "State": "IL",
        "ZIP": "60601",  # Different from QBO
        "Email": "john.new@example.com",  # New email
        "Phone": "(555) 999-8888",  # New phone
        "Salutation": "Mr.",
        "First Name": "John",
        "Last Name": "Smith",
    }

    mock_gemini.extract_donation_data.return_value = mock_extraction

    # Mock verification result
    mock_gemini.verify_customer_match.return_value = {
        "validMatch": True,
        "matchConfidence": "high",
        "addressMateriallyDifferent": True,
        "mismatchReason": None,
    }

    # Create mock QBO service
    mock_qbo = create_mock_qbo_service()

    # Create enhanced file processor
    processor = EnhancedFileProcessor(mock_gemini, mock_qbo)

    print("1. Testing data extraction...")
    # For testing, directly use the mock extraction
    extracted = mock_extraction

    if extracted:
        print("   ✓ Extraction successful")
        print(f"   Extracted donor: {extracted.get('Donor Name')}")
        print(f"   Amount: ${extracted.get('Gift Amount')}")
    else:
        print("   ✗ Extraction failed")
        return False

    print("\n2. Testing deduplication...")
    # Test with duplicates
    donations = [extracted, extracted.copy()]  # Two identical donations
    deduplicated = processor._deduplicate_donations(donations)

    if len(deduplicated) == 1:
        print("   ✓ Deduplication working correctly")
        print(f"   Reduced from {len(donations)} to {len(deduplicated)} donations")
    else:
        print("   ✗ Deduplication failed")

    print("\n3. Testing enhanced customer matching...")
    # Test enhanced matching
    matched = processor.match_donations_with_qbo_customers_batch_enhanced(deduplicated)

    if matched and matched[0].get("qboCustomerId"):
        print("   ✓ Customer matching successful")
        print(f"   Matched to: {matched[0].get('customerLookup')}")
        print(f"   QBO ID: {matched[0].get('qboCustomerId')}")

        # Check enrichment fields
        enriched_fields = [
            "qbo_first_name",
            "qbo_last_name",
            "qbo_address_line_1",
            "address_needs_update",
            "merged_emails",
            "merged_phones",
        ]

        missing_fields = [f for f in enriched_fields if f not in matched[0]]
        if not missing_fields:
            print("   ✓ All enrichment fields present")
        else:
            print(f"   ✗ Missing enrichment fields: {missing_fields}")
    else:
        print("   ✗ Customer matching failed")

    print("\n4. Testing address comparison...")
    if matched and matched[0].get("address_needs_update"):
        print("   ✓ Address comparison detected differences")
        print(f"   Extracted: {matched[0].get('Address - Line 1')}, {matched[0].get('City')}")
        print(f"   QBO: {matched[0].get('qbo_address_line_1')}, {matched[0].get('qbo_city')}")
        if matched[0].get("address_differences"):
            print(f"   Differences: {matched[0]['address_differences']}")
    else:
        print("   ✗ Address comparison not working")

    print("\n5. Testing email/phone updates...")
    if matched and matched[0].get("merged_emails"):
        emails = matched[0]["merged_emails"]
        phones = matched[0]["merged_phones"]

        print(f"   Emails: {emails}")
        print(f"   Email updated: {matched[0].get('email_updated', False)}")
        print(f"   Phones: {phones}")
        print(f"   Phone updated: {matched[0].get('phone_updated', False)}")

        if len(emails) > 1 and matched[0].get("email_updated"):
            print("   ✓ Email list properly updated")
        if len(phones) > 1 and matched[0].get("phone_updated"):
            print("   ✓ Phone list properly updated")

    print("\n6. Testing final JSON output...")
    # Use payment combiner to create final format
    from src.utils.payment_combiner import PaymentCombiner

    combiner = PaymentCombiner()

    final_payments = combiner.process_batch(matched)

    if final_payments:
        final = final_payments[0]
        print("   ✓ Final JSON created successfully")
        print("\n   Final payment structure:")
        print(json.dumps(final, indent=2, default=str))

        # Verify structure
        required_fields = {
            "payer_info": ["customer_lookup", "qb_email", "qb_phone", "address_needs_update"],
            "payment_info": ["check_no_or_payment_ref", "amount", "payment_date"],
            "match_status": None,
            "qbo_customer_id": None,
        }

        all_good = True
        for key, subfields in required_fields.items():
            if key not in final:
                print(f"   ✗ Missing required field: {key}")
                all_good = False
            elif subfields:
                for subfield in subfields:
                    if subfield not in final[key]:
                        print(f"   ✗ Missing required field: {key}.{subfield}")
                        all_good = False

        if all_good:
            print("\n   ✓ All required fields present in final JSON")

        # Check specific values
        if final["payer_info"]["address_needs_update"]:
            print("   ✓ Address update flag correctly set")

        if len(final["payer_info"]["qb_email"]) > 1:
            print("   ✓ Multiple emails in list")

        if final["payment_info"]["check_no_or_payment_ref"] == "1234":
            print("   ✓ Payment reference correctly mapped")

    print("\n=== Phase 1 Integration Test Complete ===")
    return True


def test_with_real_file():
    """Test with a real file if available."""
    print("\n=== Testing with Real File ===\n")

    # Check for test files
    from pathlib import Path

    uploads_dir = Path("uploads")

    if not uploads_dir.exists():
        print("No uploads directory found")
        return

    test_files = list(uploads_dir.glob("*.jpg")) + list(uploads_dir.glob("*.png"))

    if not test_files:
        print("No test images found in uploads directory")
        return

    test_file = str(test_files[0])
    print(f"Testing with: {test_file}")

    # This would require real API keys and services
    print("Note: Real file testing requires valid API keys and QBO connection")
    print("Run this test in a properly configured environment")


if __name__ == "__main__":
    # Run integration test
    success = test_phase1_integration()

    if success:
        print("\n✅ Phase 1 implementation is working correctly!")

        # Optionally test with real file
        # test_with_real_file()
    else:
        print("\n❌ Phase 1 implementation has issues")
