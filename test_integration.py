#!/usr/bin/env python3
"""
Integration test for structured extraction with real files.
"""

import json
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.models.payment import PaymentRecord
from src.utils.gemini_adapter import create_gemini_service


def test_with_real_image():
    """Test structured extraction with a real image file."""
    # Get API key from environment
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Skipping integration test - GEMINI_API_KEY not set")
        print("To run this test, set your API key: export GEMINI_API_KEY='your-key-here'")
        return

    # Find a test image
    test_images = [
        "uploads/20250411_205258.jpg",
        "uploads/20250328_195721.jpg",
    ]

    test_image = None
    for img_path in test_images:
        if os.path.exists(img_path):
            test_image = img_path
            break

    if not test_image:
        print("No test images found in uploads/ directory")
        return

    print(f"\nTesting with image: {test_image}")

    # Create service with structured extraction
    gemini_service = create_gemini_service(api_key)

    # Test 1: Legacy extraction mode
    print("\nTest 1: Legacy extraction mode")
    gemini_service.set_use_structured(False)

    try:
        legacy_result = gemini_service.extract_donation_data(test_image)
        print("Legacy extraction successful!")
        if legacy_result:
            if isinstance(legacy_result, list):
                print(f"Found {len(legacy_result)} donations")
                for i, donation in enumerate(legacy_result[:2]):  # Show first 2
                    print(f"\nDonation {i+1}:")
                    print(f"  Donor: {donation.get('Donor Name', 'N/A')}")
                    print(f"  Amount: {donation.get('Gift Amount', 'N/A')}")
                    print(f"  Check No: {donation.get('Check No.', 'N/A')}")
            else:
                print(f"Donor: {legacy_result.get('Donor Name', 'N/A')}")
                print(f"Amount: {legacy_result.get('Gift Amount', 'N/A')}")
                print(f"Check No: {legacy_result.get('Check No.', 'N/A')}")
        else:
            print("No donations found")
    except Exception as e:
        print(f"Legacy extraction error: {e}")
        import traceback

        traceback.print_exc()

    # Test 2: Structured extraction mode
    print("\n\nTest 2: Structured extraction mode")
    gemini_service.set_use_structured(True)

    try:
        structured_result = gemini_service.extract_donation_data(test_image)
        print("Structured extraction successful!")
        if structured_result:
            if isinstance(structured_result, list):
                print(f"Found {len(structured_result)} payments")
                for i, payment in enumerate(structured_result[:2]):  # Show first 2
                    print(f"\nPayment {i+1}:")
                    print(f"  Payer: {payment.get('Donor Name', 'N/A')}")
                    print(f"  Amount: {payment.get('Gift Amount', 'N/A')}")
                    print(f"  Check No: {payment.get('Check No.', 'N/A')}")

                    # Try to convert to PaymentRecord
                    try:
                        payment_record = PaymentRecord.from_legacy_format(payment)
                        print(f"  Payment Method: {payment_record.payment_info.payment_method}")
                        print("  ✓ Successfully converted to PaymentRecord")
                    except Exception as e:
                        print(f"  ✗ Error converting to PaymentRecord: {e}")
            else:
                print(f"Payer: {structured_result.get('Donor Name', 'N/A')}")
                print(f"Amount: {structured_result.get('Gift Amount', 'N/A')}")
                print(f"Check No: {structured_result.get('Check No.', 'N/A')}")
        else:
            print("No payments found")
    except Exception as e:
        print(f"Structured extraction error: {e}")
        import traceback

        traceback.print_exc()

    print("\n\nIntegration test complete!")


def test_deduplication_with_payment_ref():
    """Test deduplication with new payment_ref field."""
    print("\n\nTest 3: Deduplication with payment references")

    from src.services.deduplication import DeduplicationService

    # Test data with online payments
    existing = [{"Donor Name": "John Smith", "Gift Amount": "100.00", "Check No.": "1234", "Check Date": "2025-05-01"}]

    new_donations = [
        # Duplicate check payment
        {
            "Donor Name": "John Smith",
            "Gift Amount": "100.00",
            "Check No.": "1234",
            "Check Date": "2025-05-01",
            "Memo": "Additional info",
        },
        # Online payment with payment ref
        {"Donor Name": "Jane Doe", "Gift Amount": "50.00", "Payment Ref": "TXN-12345", "Gift Date": "2025-05-02"},
        # Duplicate online payment
        {
            "Donor Name": "Jane Doe",
            "Gift Amount": "50.00",
            "Payment Ref": "TXN-12345",
            "Gift Date": "2025-05-02",
            "Email": "jane@example.com",
        },
    ]

    result = DeduplicationService.deduplicate_donations(existing, new_donations)

    print(f"Initial donations: {len(existing) + len(new_donations)}")
    print(f"After deduplication: {len(result)}")
    print(f"Expected: 2 (one check, one online payment)")

    # Verify results
    check_found = False
    online_found = False

    for donation in result:
        if donation.get("Check No.") == "1234":
            check_found = True
            print(f"\n✓ Check payment preserved: {donation.get('Donor Name')} - ${donation.get('Gift Amount')}")
            if donation.get("Memo"):
                print("  ✓ Additional info merged")
        elif donation.get("Payment Ref") == "TXN-12345":
            online_found = True
            print(f"\n✓ Online payment preserved: {donation.get('Donor Name')} - ${donation.get('Gift Amount')}")
            if donation.get("Email"):
                print("  ✓ Email info merged")

    if check_found and online_found:
        print("\n✅ Deduplication with payment_ref working correctly!")
    else:
        print("\n❌ Deduplication test failed")


if __name__ == "__main__":
    print("Running integration tests for structured extraction...")

    # Test with real image
    test_with_real_image()

    # Test deduplication
    test_deduplication_with_payment_ref()
