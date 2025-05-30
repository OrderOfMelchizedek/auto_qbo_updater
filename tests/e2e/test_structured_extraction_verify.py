#!/usr/bin/env python3
"""
Test script to verify structured extraction is working correctly.
This script tests the extraction with a sample image to ensure all required fields are extracted.
"""

import json
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.utils.gemini_adapter import create_gemini_service


def test_structured_extraction():
    """Test the structured extraction with a sample file."""

    # Initialize the Gemini service
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY environment variable not set")
        return False

    print("Initializing Gemini service...")
    gemini_service = create_gemini_service(api_key)

    # Check if structured mode is enabled
    if hasattr(gemini_service, "use_structured"):
        print(f"Structured extraction enabled: {gemini_service.use_structured}")
    else:
        print("WARNING: Service doesn't have use_structured attribute")

    # Find a test file
    test_files = []
    uploads_dir = Path("uploads")
    if uploads_dir.exists():
        # Look for image files
        for ext in [".jpg", ".jpeg", ".png"]:
            test_files.extend(uploads_dir.glob(f"*{ext}"))

    if not test_files:
        print("No test files found in uploads directory")
        print("Please upload a check image to test extraction")
        return False

    # Test with the first file found
    test_file = str(test_files[0])
    print(f"\nTesting extraction with: {test_file}")

    try:
        # Extract data
        result = gemini_service.extract_donation_data(test_file)

        if result:
            print("\nExtraction successful!")
            print(f"Type of result: {type(result)}")

            # Handle both single and multiple results
            results = result if isinstance(result, list) else [result]

            for i, donation in enumerate(results):
                print(f"\n--- Donation {i+1} ---")
                print(json.dumps(donation, indent=2))

                # Check for required fields
                print("\nChecking required fields:")

                # Payment fields
                payment_fields = {
                    "Check No.": donation.get("Check No."),
                    "Gift Amount": donation.get("Gift Amount"),
                    "Check Date": donation.get("Check Date"),
                    "Payment Date": donation.get("Payment Date"),
                    "Deposit Date": donation.get("Deposit Date"),
                    "Memo": donation.get("Memo"),
                }

                # Payer fields
                payer_fields = {
                    "Donor Name": donation.get("Donor Name"),
                    "Organization Name": donation.get("Organization Name"),
                    "First Name": donation.get("First Name"),
                    "Last Name": donation.get("Last Name"),
                    "Salutation": donation.get("Salutation"),
                }

                # Contact fields
                contact_fields = {
                    "Address - Line 1": donation.get("Address - Line 1"),
                    "City": donation.get("City"),
                    "State": donation.get("State"),
                    "ZIP": donation.get("ZIP"),
                    "Email": donation.get("Email"),
                    "Phone": donation.get("Phone"),
                }

                print("\nPayment Info:")
                for field, value in payment_fields.items():
                    status = "✓" if value else "✗"
                    print(f"  {status} {field}: {value}")

                print("\nPayer Info:")
                for field, value in payer_fields.items():
                    status = "✓" if value else "✗"
                    print(f"  {status} {field}: {value}")

                print("\nContact Info:")
                for field, value in contact_fields.items():
                    status = "✓" if value else "✗"
                    print(f"  {status} {field}: {value}")

                # Check if this looks like structured extraction worked
                # The adapter should have converted from structured to legacy format
                if donation.get("Donor Name") and donation.get("Gift Amount"):
                    print("\n✅ Basic extraction working correctly")
                else:
                    print("\n❌ Missing critical fields")

            return True
        else:
            print("Extraction returned None")
            return False

    except Exception as e:
        print(f"Error during extraction: {e}")
        import traceback

        traceback.print_exc()
        return False


def check_structured_models():
    """Check if the structured models are properly configured."""
    print("\nChecking structured models...")

    try:
        from src.models.payment import ContactInfo, PayerInfo, PaymentInfo, PaymentRecord

        print("✓ Payment models imported successfully")

        # Test creating a sample payment record
        sample_payment = PaymentRecord(
            payment_info=PaymentInfo(
                payment_method="handwritten_check", check_no="1234", amount=100.00, payment_date="2025-05-30"
            ),
            payer_info=PayerInfo(aliases=["John Doe"], salutation="Mr."),
            contact_info=ContactInfo(address_line_1="123 Main St", city="Springfield", state="IL", zip="62701"),
        )

        # Test conversion to legacy format
        legacy = sample_payment.to_legacy_format()
        print("✓ Sample payment record created and converted to legacy format")
        print(f"  Legacy donor name: {legacy.get('Donor Name')}")
        print(f"  Legacy amount: {legacy.get('Gift Amount')}")

        return True

    except Exception as e:
        print(f"✗ Error with structured models: {e}")
        return False


if __name__ == "__main__":
    print("=== Structured Extraction Verification ===")

    # Check models first
    models_ok = check_structured_models()

    # Test extraction
    extraction_ok = test_structured_extraction()

    if models_ok and extraction_ok:
        print("\n✅ Structured extraction is working correctly!")
    else:
        print("\n❌ Issues found with structured extraction")
        print("Please check the configuration and try again")
