"""Test batch 1 and display JSON output."""
import json
import os
from pathlib import Path

from src.donation_processor import process_donation_documents


def test_batch_1_display_output():
    """Process batch 1 files and display the JSON output."""
    # Check if API key is available
    if not os.getenv("GEMINI_API_KEY"):
        print("GEMINI_API_KEY not set - using mock data")
        # Mock output for demonstration
        mock_output = {
            "donations": [
                {
                    "PaymentInfo": {
                        "Payment_Ref": "1234",
                        "Amount": 100.00,
                        "Payment_Method": "printed check",
                        "Payment_Date": "2025-05-17",
                    },
                    "PayerInfo": {"Aliases": ["John Smith"], "Salutation": "Mr."},
                    "ContactInfo": {
                        "Address_Line_1": "123 Main St",
                        "City": "Springfield",
                        "State": "CA",
                        "ZIP": "94025",
                    },
                },
                {
                    "PaymentInfo": {
                        "Payment_Ref": "5678",
                        "Amount": 250.00,
                        "Payment_Method": "printed check",
                        "Payment_Date": "2025-05-17",
                    },
                    "PayerInfo": {"Organization_Name": "Smith Foundation"},
                    "ContactInfo": {
                        "Address_Line_1": "456 Corporate Blvd",
                        "City": "San Francisco",
                        "State": "CA",
                        "ZIP": "94105",
                    },
                },
            ],
            "metadata": {
                "files_processed": 2,
                "raw_count": 2,
                "valid_count": 2,
                "duplicate_count": 0,
                "matched_count": 0,
            },
        }
        print("\n" + "=" * 80)
        print("MOCK OUTPUT (GEMINI_API_KEY not set)")
        print("=" * 80)
        print(json.dumps(mock_output, indent=2))
        return

    # Get test files
    test_files_dir = Path(__file__).parent / "test_files"
    file_paths = [
        test_files_dir / "test_batch_1" / "2025-05-17 12.50.27-1.jpg",
        test_files_dir / "test_batch_1" / "2025-05-17-12-48-17.pdf",
    ]

    # Verify files exist
    for path in file_paths:
        if not path.exists():
            print(f"Error: Test file not found: {path}")
            return

    print("\n" + "=" * 80)
    print("PROCESSING TEST BATCH 1")
    print("=" * 80)
    print("Input files:")
    for path in file_paths:
        print(f"  - {path.name}")

    try:
        # Process the documents
        donations, metadata, _ = process_donation_documents(file_paths)

        # Create output structure
        output = {"donations": donations, "metadata": metadata}

        print("\n" + "-" * 80)
        print("JSON OUTPUT:")
        print("-" * 80)
        print(json.dumps(output, indent=2))

        print("\n" + "-" * 80)
        print("SUMMARY:")
        print("-" * 80)
        print(f"Total donations processed: {len(donations)}")
        print(f"Raw entries extracted: {metadata['raw_count']}")
        print(f"Valid entries after processing: {metadata['valid_count']}")
        print(f"Duplicates removed: {metadata['duplicate_count']}")

        if donations:
            print("\nSample donation details:")
            for i, donation in enumerate(donations[:3]):  # Show first 3
                payment = donation.get("PaymentInfo", {})
                payer = donation.get("PayerInfo", {})
                contact = donation.get("ContactInfo", {})

                print(f"\nDonation {i+1}:")
                print(f"  Payment Ref: {payment.get('Payment_Ref')}")
                print(f"  Amount: ${payment.get('Amount', 0):.2f}")
                print(f"  Method: {payment.get('Payment_Method')}")

                if payer.get("Aliases"):
                    print(f"  Payer: {payer['Aliases'][0]}")
                elif payer.get("Organization_Name"):
                    print(f"  Organization: {payer['Organization_Name']}")

                if contact:
                    print(f"  Address: {contact.get('Address_Line_1', '')}")
                    print(
                        f"           {contact.get('City', '')}, "
                        f"{contact.get('State', '')} {contact.get('ZIP', '')}"
                    )

    except Exception as e:
        print(f"\nError processing files: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_batch_1_display_output()
