"""Test batch 1 with CSV-based customer matching."""
import json
import logging
import os
from pathlib import Path

from src.donation_processor import process_donation_documents

# Configure logging to show all matching attempts
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(name)s - %(message)s")


def test_batch_1_with_csv_matching():
    """Process batch 1 files with CSV-based customer matching."""
    print("\n" + "=" * 80)
    print("PROCESSING BATCH 1 WITH CSV CUSTOMER MATCHING")
    print("=" * 80)

    # Get paths
    test_files_dir = Path(__file__).parent / "test_files"
    csv_path = test_files_dir / "customer_contact_list.csv"

    if not csv_path.exists():
        print(f"Error: CSV file not found: {csv_path}")
        return

    file_paths = [
        test_files_dir / "test_batch_1" / "2025-05-17 12.50.27-1.jpg",
        test_files_dir / "test_batch_1" / "2025-05-17-12-48-17.pdf",
    ]

    # Check if we have real files and API key
    use_real_files = all(path.exists() for path in file_paths) and os.getenv(
        "GEMINI_API_KEY"
    )

    if use_real_files:
        print("Using real test files with Gemini extraction")
    else:
        print("Using mock donation data (no GEMINI_API_KEY or files missing)")
        # Mock the extraction
        from unittest.mock import patch

        with patch(
            "src.donation_processor.extract_donations_from_documents"
        ) as mock_extract:
            mock_extract.return_value = [
                {
                    "PaymentInfo": {
                        "Payment_Ref": "1848",
                        "Amount": "50.00",
                        "Payment_Method": "handwritten check",
                        "Payment_Date": "2025-04-07",
                    },
                    "PayerInfo": {
                        "Aliases": [
                            "Jonelle R. Collins",
                            "Jonelle Collins",
                            "J. Collins",
                        ],
                        "Salutation": "Ms.",
                    },
                    "ContactInfo": {
                        "Address_Line_1": "290 W Water St Apt 126",
                        "City": "Negaunee",
                        "State": "MI",
                        "ZIP": "49866",
                        "Phone": "9064759177",
                    },
                },
                {
                    "PaymentInfo": {
                        "Payment_Ref": "8117",
                        "Amount": "100.00",
                        "Payment_Method": "handwritten check",
                        "Payment_Date": "2025-04-02",
                    },
                    "PayerInfo": {
                        "Aliases": [
                            "John D. Lang",
                            "Esther A. Lang",
                            "John & Esther Lang",
                        ],
                        "Salutation": "Mr. & Mrs.",
                    },
                    "ContactInfo": {
                        "Address_Line_1": "PO Box 982",
                        "City": "Emory",
                        "State": "VA",
                        "ZIP": "24327",
                        "Phone": "2769445769",
                    },
                },
                {
                    "PaymentInfo": {
                        "Payment_Ref": "3517031",
                        "Amount": "600.00",
                        "Payment_Method": "printed check",
                        "Payment_Date": "2025-05-07",
                    },
                    "PayerInfo": {
                        "Organization_Name": "Gustafson Family Charitable Fund"
                    },
                    "ContactInfo": {
                        "Address_Line_1": "2211 Willow Ln",
                        "City": "Rockford",
                        "State": "IL",
                        "ZIP": "61107",
                    },
                },
                {
                    "PaymentInfo": {
                        "Payment_Ref": "13967",
                        "Amount": "500.00",
                        "Payment_Method": "printed check",
                        "Payment_Date": "2025-05-06",
                    },
                    "PayerInfo": {
                        "Organization_Name": "The Lutheran Church Of The Holy Spirit"
                    },
                    "ContactInfo": {
                        "Address_Line_1": "3461 Cedar Crest Blvd.",
                        "City": "Emmaus",
                        "State": "PA",
                        "ZIP": "18049",
                    },
                },
                # Add a donation that should match someone in the CSV
                {
                    "PaymentInfo": {
                        "Payment_Ref": "5555",
                        "Amount": "75.00",
                        "Payment_Method": "handwritten check",
                        "Payment_Date": "2025-05-01",
                    },
                    "PayerInfo": {"Aliases": ["Joyce Anderson"], "Salutation": "Ms."},
                    "ContactInfo": {
                        "Address_Line_1": "8203 Mill Creek Dr.",
                        "City": "Madison",
                        "State": "WI",
                        "ZIP": "53719",
                    },
                },
            ]
            file_paths = ["mock1.jpg", "mock2.pdf"]

    # Process with CSV matching
    print(f"\nProcessing donations with CSV customer data from: {csv_path.name}")
    print("-" * 80)

    try:
        results, metadata = process_donation_documents(file_paths, csv_path=csv_path)

        print("\n" + "-" * 80)
        print("MATCHING RESULTS:")
        print("-" * 80)

        # Display results
        for i, donation in enumerate(results):
            payment = donation.get("PaymentInfo", {})
            payer = donation.get("PayerInfo", {})
            contact = donation.get("ContactInfo", {})
            match_data = donation.get("match_data", {})

            # Get payer name
            if payer.get("Aliases"):
                payer_name = payer["Aliases"][0]
            elif payer.get("Organization_Name"):
                payer_name = payer["Organization_Name"]
            else:
                payer_name = "Unknown"

            print(f"\nDonation {i+1}: {payer_name}")
            print(f"  Payment Ref: {payment.get('Payment_Ref')}")
            print(f"  Amount: ${payment.get('Amount', 0):.2f}")

            # Show extracted address
            if contact:
                print(f"  Extracted Address: {contact.get('Address_Line_1', '')}")
                print(
                    f"                     {contact.get('City', '')}, "
                    f"{contact.get('State', '')} {contact.get('ZIP', '')}"
                )

            if match_data:
                print(f"  Match Status: {match_data.get('match_status')}")
                if match_data.get("customer_ref"):
                    print(f"  CSV Customer ID: {match_data['customer_ref']['id']}")
                    print(f"  CSV Name: {match_data['customer_ref']['full_name']}")
                    if match_data.get("qb_address", {}).get("line1"):
                        print(f"  CSV Address: {match_data['qb_address']['line1']}")
                        print(
                            f"               {match_data['qb_address']['city']}, "
                            f"{match_data['qb_address']['state']} "
                            f"{match_data['qb_address']['zip']}"
                        )

                if match_data.get("updates_needed"):
                    updates = match_data["updates_needed"]
                    if any(updates.values()):
                        print("  Updates needed:")
                        if updates.get("address"):
                            print("    - Address differs significantly")
                        if updates.get("email_added"):
                            print("    - Email will be added")
                        if updates.get("phone_added"):
                            print("    - Phone will be added")
            else:
                print("  Match Status: No matching attempted")

        print("\n" + "-" * 80)
        print("METADATA:")
        print("-" * 80)
        print(json.dumps(metadata, indent=2))

        print("\n" + "-" * 80)
        print("SUMMARY:")
        print("-" * 80)
        print(f"Total donations processed: {len(results)}")
        print(f"Matched to existing customers: {metadata.get('matched_count', 0)}")
        print(f"New customers: {metadata.get('new_customer_count', 0)}")
        print(f"Matching errors: {len(metadata.get('matching_errors', []))}")

        if metadata.get("matching_errors"):
            print("\nMatching errors:")
            for error in metadata["matching_errors"]:
                print(f"  - {error}")

    except Exception as e:
        print(f"\nError processing files: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_batch_1_with_csv_matching()
