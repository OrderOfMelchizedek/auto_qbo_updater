"""Tests for final display merger."""
from src.final_display_merger import (
    merge_all_donations_for_display,
    merge_donation_for_display,
)


class TestFinalDisplayMerger:
    """Test the final display merger functionality."""

    def test_merge_donation_without_match(self):
        """Test merging donation with no match data."""
        donation = {
            "PaymentInfo": {
                "Payment_Ref": "1234",
                "Amount": 100.00,
                "Payment_Date": "2024-01-01",
                "Deposit_Date": "2024-01-02",
                "Deposit_Method": "Check",
                "Memo": "Test donation",
            },
            "PayerInfo": {
                "Aliases": ["John Smith"],
                "Salutation": "Mr.",
                "Organization_Name": "",
            },
            "ContactInfo": {
                "Address_Line_1": "123 Main St",
                "City": "Springfield",
                "State": "CA",
                "ZIP": "94025",
                "Email": "john@example.com",
                "Phone": "555-1234",
            },
        }

        result = merge_donation_for_display(donation)

        # Check payment info
        assert result["payment_info"]["payment_ref"] == "1234"
        assert result["payment_info"]["amount"] == 100.00
        assert result["payment_info"]["payment_date"] == "2024-01-01"
        assert result["payment_info"]["memo"] == "Test donation"

        # Check payer info
        assert result["payer_info"]["customer_ref"]["salutation"] == "Mr."
        assert result["payer_info"]["customer_ref"]["full_name"] == "John Smith"
        assert result["payer_info"]["customer_ref"]["first_name"] == "John"
        assert result["payer_info"]["customer_ref"]["last_name"] == "Smith"

        # Check address
        assert result["payer_info"]["qb_address"]["line1"] == "123 Main St"
        assert result["payer_info"]["qb_address"]["city"] == "Springfield"
        assert result["payer_info"]["qb_address"]["state"] == "CA"
        assert result["payer_info"]["qb_address"]["zip"] == "94025"

        # Check contact
        assert result["payer_info"]["qb_email"] == "john@example.com"
        assert result["payer_info"]["qb_phone"] == "555-1234"

        # Check status
        assert result["status"]["matched"] is False
        assert result["status"]["new_customer"] is False

    def test_merge_donation_with_match(self):
        """Test merging donation with match data."""
        donation = {
            "PaymentInfo": {
                "Payment_Ref": "1234",
                "Amount": 100.00,
            },
            "PayerInfo": {"Aliases": ["John Smith"], "Salutation": "Mr."},
            "ContactInfo": {"Email": "john@example.com", "Phone": "555-1234"},
        }

        match_data = {
            "match_status": "matched",
            "customer_ref": {
                "id": "QB-001",
                "first_name": "John",
                "last_name": "Smith",
                "full_name": "John Smith",
                "company_name": None,
            },
            "qb_address": {
                "line1": "456 Oak Ave",
                "city": "San Francisco",
                "state": "CA",
                "zip": "94105",
            },
            "qb_email": ["john.smith@company.com"],
            "qb_phone": ["555-9999"],
            "updates_needed": {
                "address": True,
                "email_added": False,
                "phone_added": False,
            },
        }

        result = merge_donation_for_display(donation, match_data)

        # Check customer ref from match
        assert result["payer_info"]["customer_ref"]["first_name"] == "John"
        assert result["payer_info"]["customer_ref"]["last_name"] == "Smith"
        assert (
            result["payer_info"]["customer_ref"]["salutation"] == "Mr."
        )  # From donation

        # Check QB data
        assert result["payer_info"]["qb_address"]["line1"] == "456 Oak Ave"
        assert result["payer_info"]["qb_address"]["city"] == "San Francisco"
        assert result["payer_info"]["qb_email"] == "john.smith@company.com"
        assert result["payer_info"]["qb_phone"] == "555-9999"

        # Check status
        assert result["status"]["matched"] is True
        assert result["status"]["address_updated"] is True
        assert result["status"]["new_customer"] is False

    def test_merge_donation_organization(self):
        """Test merging donation for organization."""
        donation = {
            "PaymentInfo": {
                "Payment_Ref": "5678",
                "Amount": 500.00,
            },
            "PayerInfo": {"Organization_Name": "Smith Foundation"},
            "ContactInfo": {},
        }

        match_data = {
            "match_status": "matched",
            "customer_ref": {
                "id": "QB-002",
                "first_name": None,
                "last_name": None,
                "full_name": "Smith Foundation",
                "company_name": "Smith Foundation",
            },
            "qb_address": {},
            "qb_email": ["info@smithfoundation.org"],
            "qb_phone": [],
            "updates_needed": {},
        }

        result = merge_donation_for_display(donation, match_data)

        assert result["payer_info"]["qb_organization_name"] == "Smith Foundation"
        assert result["payer_info"]["customer_ref"]["full_name"] == "Smith Foundation"
        assert result["payer_info"]["qb_email"] == "info@smithfoundation.org"

    def test_merge_donation_new_customer(self):
        """Test merging donation marked as new customer."""
        donation = {
            "PaymentInfo": {"Payment_Ref": "9999", "Amount": 50.00},
            "PayerInfo": {"Aliases": ["Jane Doe"]},
            "ContactInfo": {},
        }

        match_data = {
            "match_status": "new_customer",
            "customer_ref": None,
            "qb_address": None,
            "qb_email": [],
            "qb_phone": [],
            "updates_needed": {},
        }

        result = merge_donation_for_display(donation, match_data)

        assert result["payer_info"]["customer_ref"]["full_name"] == "Jane Doe"
        assert result["status"]["new_customer"] is True
        assert result["status"]["matched"] is False

    def test_merge_all_donations(self):
        """Test merging multiple donations."""
        donations = [
            {
                "PaymentInfo": {"Payment_Ref": "1", "Amount": 100},
                "PayerInfo": {"Aliases": ["John Smith"]},
                "ContactInfo": {},
                "match_data": {
                    "match_status": "matched",
                    "customer_ref": {"full_name": "John Smith"},
                    "qb_address": {},
                    "qb_email": [],
                    "qb_phone": [],
                },
            },
            {
                "PaymentInfo": {"Payment_Ref": "2", "Amount": 200},
                "PayerInfo": {"Aliases": ["Jane Doe"]},
                "ContactInfo": {},
                "match_data": {
                    "match_status": "new_customer",
                    "customer_ref": None,
                    "qb_address": None,
                    "qb_email": [],
                    "qb_phone": [],
                },
            },
        ]

        results = merge_all_donations_for_display(donations)

        assert len(results) == 2
        assert results[0]["status"]["matched"] is True
        assert results[1]["status"]["new_customer"] is True
        assert results[0]["payment_info"]["payment_ref"] == "1"
        assert results[1]["payment_info"]["payment_ref"] == "2"
