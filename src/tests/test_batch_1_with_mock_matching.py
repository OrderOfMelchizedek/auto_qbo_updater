"""Test batch 1 with mocked QuickBooks matching and logging."""
import json
import logging
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.donation_processor import process_donation_documents

# Configure logging to show all matching attempts
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(name)s - %(message)s")


def create_mock_qb_auth():
    """Create a mock QuickBooks auth that simulates authentication."""
    mock_auth = MagicMock()
    mock_auth.get_access_token.return_value = "mock-access-token"
    mock_auth.get_company_id.return_value = "mock-company-123"
    return mock_auth


def create_mock_qb_customers():
    """Create mock QuickBooks customer data."""
    return {
        # Individual customers
        "Jonelle Collins": {
            "Id": "QB-101",
            "DisplayName": "Jonelle Collins",
            "GivenName": "Jonelle",
            "FamilyName": "Collins",
            "BillAddr": {
                "Line1": "290 W Water St Apt 126",
                "City": "Negaunee",
                "CountrySubDivisionCode": "MI",
                "PostalCode": "49866",
            },
            "PrimaryPhone": {"FreeFormNumber": "906-475-9177"},
        },
        "John Lang": {
            "Id": "QB-102",
            "DisplayName": "John & Esther Lang",
            "GivenName": "John",
            "FamilyName": "Lang",
            "BillAddr": {
                "Line1": "PO Box 982",
                "City": "Emory",
                "CountrySubDivisionCode": "VA",
                "PostalCode": "24327",
            },
            "PrimaryPhone": {"FreeFormNumber": "276-944-5769"},
        },
        # Organization customers
        "Gustafson": {
            "Id": "QB-201",
            "DisplayName": "Gustafson Family Charitable Fund",
            "CompanyName": "Gustafson Family Charitable Fund",
            "BillAddr": {
                "Line1": "2211 Willow Ln",
                "City": "Rockford",
                "CountrySubDivisionCode": "IL",
                "PostalCode": "61107",
            },
        },
        "Lutheran Church": {
            "Id": "QB-202",
            "DisplayName": "Lutheran Church of the Holy Spirit",
            "CompanyName": "Lutheran Church of the Holy Spirit",
            "BillAddr": {
                "Line1": "3461 Cedar Crest Boulevard",  # Slightly different
                "City": "Emmaus",
                "CountrySubDivisionCode": "PA",
                "PostalCode": "18049",
            },
            "PrimaryEmailAddr": {"Address": "office@holyspiritemmaus.org"},
        },
    }


def mock_search_customer(search_term):
    """Mock customer search that returns realistic results."""
    customers = create_mock_qb_customers()
    results = []

    search_lower = search_term.lower()

    # Search through all customers
    for _, customer in customers.items():
        display_name = customer.get("DisplayName", "").lower()
        company_name = customer.get("CompanyName", "").lower()

        if (
            search_lower in display_name
            or search_lower in company_name
            or any(word in display_name for word in search_lower.split())
        ):
            results.append(customer)

    return results


def mock_get_customer(customer_id):
    """Mock getting full customer details."""
    customers = create_mock_qb_customers()
    for customer in customers.values():
        if customer["Id"] == customer_id:
            return customer
    raise Exception(f"Customer {customer_id} not found")


def test_batch_1_with_mock_matching():
    """Process batch 1 files with mocked QuickBooks matching."""
    print("\n" + "=" * 80)
    print("PROCESSING BATCH 1 WITH MOCKED QUICKBOOKS MATCHING")
    print("=" * 80)

    # Check if we have real files
    test_files_dir = Path(__file__).parent / "test_files"
    file_paths = [
        test_files_dir / "test_batch_1" / "2025-05-17 12.50.27-1.jpg",
        test_files_dir / "test_batch_1" / "2025-05-17-12-48-17.pdf",
    ]

    # Use real files if available, otherwise use mock data
    use_real_files = all(path.exists() for path in file_paths) and os.getenv(
        "GEMINI_API_KEY"
    )

    if not use_real_files:
        print("Using mock donation data (no GEMINI_API_KEY or files missing)")
        # Mock the extraction
        with patch(
            "src.donation_processor.extract_donations_from_documents"
        ) as mock_extract:
            mock_extract.return_value = [
                {
                    "PaymentInfo": {
                        "Payment_Ref": "1848",
                        "Amount": "50.00",
                        "Payment_Method": "handwritten check",
                    },
                    "PayerInfo": {
                        "Aliases": ["Jonelle R. Collins", "Jonelle Collins"],
                        "Salutation": "Ms.",
                    },
                    "ContactInfo": {
                        "Address_Line_1": "290 W Water St Apt 126",
                        "City": "Negaunee",
                        "State": "MI",
                        "ZIP": "49866",
                    },
                },
                {
                    "PaymentInfo": {
                        "Payment_Ref": "3517031",
                        "Amount": "600.00",
                        "Payment_Method": "printed check",
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
            ]
            file_paths = ["mock1.jpg", "mock2.pdf"]

    # Mock QuickBooks authentication and API
    with patch("src.quickbooks_service.QuickBooksAuth") as mock_auth_class, patch(
        "src.customer_matcher.QuickBooksClient"
    ) as mock_client_class:
        # Set up auth mock
        mock_auth = create_mock_qb_auth()
        mock_auth_class.return_value = mock_auth

        # Set up client mock
        mock_client = MagicMock()
        mock_client.search_customer.side_effect = mock_search_customer
        mock_client.get_customer.side_effect = mock_get_customer
        mock_client.format_customer_data.side_effect = lambda c: {
            "customer_ref": {
                "id": c["Id"],
                "first_name": c.get("GivenName"),
                "last_name": c.get("FamilyName"),
                "full_name": c["DisplayName"],
                "company_name": c.get("CompanyName"),
            },
            "qb_address": {
                "line1": c.get("BillAddr", {}).get("Line1", ""),
                "city": c.get("BillAddr", {}).get("City", ""),
                "state": c.get("BillAddr", {}).get("CountrySubDivisionCode", ""),
                "zip": c.get("BillAddr", {}).get("PostalCode", ""),
            },
            "qb_email": [c["PrimaryEmailAddr"]["Address"]]
            if c.get("PrimaryEmailAddr")
            else [],
            "qb_phone": [c["PrimaryPhone"]["FreeFormNumber"]]
            if c.get("PrimaryPhone")
            else [],
        }
        mock_client_class.return_value = mock_client

        # Process with mocked session
        print("\nProcessing donations with mocked QuickBooks session...")
        results, metadata = process_donation_documents(
            file_paths, session_id="mock-session-123"
        )

        print("\n" + "-" * 80)
        print("MATCHING RESULTS:")
        print("-" * 80)

        # Display results
        for i, donation in enumerate(results):
            payment = donation.get("PaymentInfo", {})
            payer = donation.get("PayerInfo", {})
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

            if match_data:
                print(f"  Match Status: {match_data.get('match_status')}")
                if match_data.get("customer_ref"):
                    print(f"  QB Customer ID: {match_data['customer_ref']['id']}")
                    print(f"  QB Name: {match_data['customer_ref']['full_name']}")
                if match_data.get("updates_needed"):
                    updates = match_data["updates_needed"]
                    if any(updates.values()):
                        print("  Updates needed:")
                        if updates.get("address"):
                            print("    - Address update required")
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
        print(f"Total donations: {len(results)}")
        print(f"Matched to existing customers: {metadata.get('matched_count', 0)}")
        print(f"New customers: {metadata.get('new_customer_count', 0)}")
        print(f"Matching errors: {len(metadata.get('matching_errors', []))}")

        if metadata.get("matching_errors"):
            print("\nMatching errors:")
            for error in metadata["matching_errors"]:
                print(f"  - {error}")


if __name__ == "__main__":
    test_batch_1_with_mock_matching()
