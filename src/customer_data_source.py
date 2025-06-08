"""Abstract customer data source for testing and production."""
import csv
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

from .quickbooks_service import QuickBooksClient, QuickBooksError

logger = logging.getLogger(__name__)


class CustomerDataSource(ABC):
    """Abstract base class for customer data sources."""

    @abstractmethod
    def search_customer(self, search_term: str) -> List[Dict[str, Any]]:
        """Search for customers by name or organization."""
        pass

    @abstractmethod
    def get_customer(self, customer_id: str) -> Dict[str, Any]:
        """Get full customer details by ID."""
        pass

    @abstractmethod
    def format_customer_data(self, customer: Dict[str, Any]) -> Dict[str, Any]:
        """Format customer data to standard structure."""
        pass


class QuickBooksDataSource(CustomerDataSource):
    """Production data source that uses real QuickBooks API."""

    def __init__(self, session_id: str):
        """Initialize with QuickBooks client."""
        self.qb_client = QuickBooksClient(session_id)

    def search_customer(self, search_term: str) -> List[Dict[str, Any]]:
        """Search using QuickBooks API."""
        return self.qb_client.search_customer(search_term)

    def get_customer(self, customer_id: str) -> Dict[str, Any]:
        """Get customer from QuickBooks API."""
        return self.qb_client.get_customer(customer_id)

    def format_customer_data(self, customer: Dict[str, Any]) -> Dict[str, Any]:
        """Format using QuickBooks format."""
        return self.qb_client.format_customer_data(customer)


class CSVDataSource(CustomerDataSource):
    """Test data source that uses CSV file."""

    def __init__(self, csv_path: Path):
        """Initialize with CSV file path."""
        self.csv_path = csv_path
        self.customers = self._load_customers()
        logger.info(f"Loaded {len(self.customers)} customers from CSV")

    def _load_customers(self) -> Dict[str, Dict[str, Any]]:
        """Load customers from CSV file."""
        customers = {}

        with open(self.csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for i, row in enumerate(reader):
                # Generate a fake QB ID
                customer_id = f"CSV-{i+1:03d}"

                # Parse the CSV row into QB-like structure
                customer = {
                    "Id": customer_id,
                    "DisplayName": row.get("Customer", "").strip()
                    or row.get("Full Name", "").strip(),
                    "GivenName": row.get("First Name", "").strip()
                    if row.get("First Name")
                    else None,
                    "FamilyName": row.get("Last Name", "").strip()
                    if row.get("Last Name")
                    else None,
                    "CompanyName": row.get("Company Name", "").strip()
                    if row.get("Company Name")
                    else None,
                    "Title": row.get("Title", "").strip() if row.get("Title") else None,
                    "Suffix": row.get("Suffix", "").strip()
                    if row.get("Suffix")
                    else None,
                }

                # Add billing address if available
                if any(
                    [
                        row.get("Billing Street"),
                        row.get("Billing City"),
                        row.get("Billing State"),
                        row.get("Billing ZIP"),
                    ]
                ):
                    customer["BillAddr"] = {
                        "Line1": row.get("Billing Street", "").strip(),
                        "City": row.get("Billing City", "").strip(),
                        "CountrySubDivisionCode": row.get("Billing State", "").strip(),
                        "PostalCode": row.get("Billing ZIP", "").strip(),
                    }

                # Add email if available
                if row.get("Email", "").strip():
                    customer["PrimaryEmailAddr"] = {
                        "Address": row.get("Email", "").strip()
                    }

                # Add phone if available
                if row.get("Phone", "").strip():
                    customer["PrimaryPhone"] = {
                        "FreeFormNumber": row.get("Phone", "").strip()
                    }

                customers[customer_id] = customer

        return customers

    def search_customer(self, search_term: str) -> List[Dict[str, Any]]:
        """Search customers in CSV data."""
        results = []
        search_lower = search_term.lower()

        for customer in self.customers.values():
            # Search in display name
            if search_lower in customer.get("DisplayName", "").lower():
                results.append(customer)
                continue

            # Search in company name
            if (
                customer.get("CompanyName")
                and search_lower in customer["CompanyName"].lower()
            ):
                results.append(customer)
                continue

            # Search in individual name components
            given_name = (customer.get("GivenName") or "").lower()
            family_name = (customer.get("FamilyName") or "").lower()

            if search_lower in given_name or search_lower in family_name:
                results.append(customer)
                continue

            # Check if all words in search term appear in display name
            search_words = search_lower.split()
            display_words = customer.get("DisplayName", "").lower().split()
            if all(
                any(word in display_word for display_word in display_words)
                for word in search_words
            ):
                results.append(customer)

        logger.debug(f"CSV search for '{search_term}' found {len(results)} results")
        return results

    def get_customer(self, customer_id: str) -> Dict[str, Any]:
        """Get customer by ID from CSV data."""
        if customer_id not in self.customers:
            raise QuickBooksError(f"Customer {customer_id} not found in CSV data")
        return self.customers[customer_id]

    def format_customer_data(self, customer: Dict[str, Any]) -> Dict[str, Any]:
        """Format CSV customer data to standard structure."""
        # Build properly formatted full name
        full_name = self._build_full_name(customer)

        # Extract customer reference info
        customer_ref = {
            "id": customer.get("Id", ""),
            "first_name": customer.get("GivenName"),
            "last_name": customer.get("FamilyName"),
            "full_name": full_name,  # Use the formatted name instead of DisplayName
            "display_name": customer.get(
                "DisplayName", ""
            ),  # Keep DisplayName for reference
            "company_name": customer.get("CompanyName"),
        }

        # Extract address
        bill_addr = customer.get("BillAddr", {})
        qb_address = {
            "line1": bill_addr.get("Line1", ""),
            "city": bill_addr.get("City", ""),
            "state": bill_addr.get("CountrySubDivisionCode", ""),
            "zip": self._format_zip_code(bill_addr.get("PostalCode", "")),
        }

        # Extract email (as list)
        qb_email = []
        if customer.get("PrimaryEmailAddr", {}).get("Address"):
            qb_email.append(customer["PrimaryEmailAddr"]["Address"])

        # Extract phone (as list)
        qb_phone = []
        if customer.get("PrimaryPhone", {}).get("FreeFormNumber"):
            qb_phone.append(customer["PrimaryPhone"]["FreeFormNumber"])

        return {
            "customer_ref": customer_ref,
            "qb_address": qb_address,
            "qb_email": qb_email,
            "qb_phone": qb_phone,
        }

    def _build_full_name(self, customer: Dict[str, Any]) -> str:
        """
        Build a properly formatted full name from CSV customer data.

        Handles:
        - Individual names with salutations (Mr. John Smith)
        - Married couples (Mr. & Mrs. John Smith)
        - Unmarried couples (John Smith and Mary Jones)
        - Organizations (returns CompanyName)

        Args:
            customer: CSV customer data

        Returns:
            Properly formatted full name
        """
        # If it's a company/organization, return the company name
        company_name = customer.get("CompanyName", "").strip()
        if company_name:
            return company_name

        # Extract name components
        title = customer.get("Title", "").strip()
        given_name = customer.get("GivenName", "").strip()
        family_name = customer.get("FamilyName", "").strip()
        suffix = customer.get("Suffix", "").strip()
        display_name = customer.get("DisplayName", "").strip()

        # Check if this is a couple based on DisplayName patterns
        is_couple = False
        partner_info = None

        if display_name:
            # Common couple patterns in DisplayName
            couple_patterns = [
                " & ",  # John & Mary Smith
                " and ",  # John and Mary Smith
                ", ",  # Smith, John & Mary
            ]

            for pattern in couple_patterns:
                if pattern in display_name:
                    is_couple = True
                    # Try to detect if it's same last name or different
                    if "&" in display_name or " and " in display_name:
                        # Could be "John & Mary Smith" or "John Smith & Mary Jones"
                        parts = display_name.replace(" & ", " and ").split(" and ")
                        if len(parts) == 2:
                            second_person = parts[1].strip()

                            # Check if second person has their own last name
                            if " " in second_person:
                                # Likely different last names
                                partner_info = second_person
                            else:
                                # Same last name, second person is just first name
                                partner_info = second_person
                    break

        # Build the full name
        if is_couple and title in ["Mr.", "Mrs."] and family_name:
            if partner_info and " " in partner_info:
                # Different last names
                name = f"{title} {given_name} {family_name} and {partner_info}"
                return name.replace("  ", " ").strip()
            else:
                # Same last name
                return f"Mr. & Mrs. {given_name} {family_name}".replace(
                    "  ", " "
                ).strip()

        # Build individual name or unmarried couple
        name_parts = []

        # Add title if present
        if title:
            name_parts.append(title)

        # Add given name
        if given_name:
            name_parts.append(given_name)

        # Add family name
        if family_name:
            name_parts.append(family_name)

        # Add suffix if present
        if suffix:
            name_parts.append(suffix)

        # If we have name parts, join them
        if name_parts:
            full_name = " ".join(name_parts)

            # If it's a couple but not married (no Mr./Mrs.), add partner
            if is_couple and partner_info and title not in ["Mr.", "Mrs."]:
                full_name = f"{full_name} and {partner_info}"

            return full_name

        # Fallback to DisplayName if no name components
        return display_name

    def _format_zip_code(self, zip_code: str) -> str:
        """Format ZIP code - remove +4 extension, preserve leading zeros."""
        if not zip_code:
            return ""

        # Remove +4 extension if present
        if "-" in zip_code:
            zip_code = zip_code.split("-")[0]

        return zip_code.strip()


def create_customer_data_source(
    session_id: Optional[str] = None, csv_path: Optional[Path] = None
) -> CustomerDataSource:
    """Create appropriate data source based on parameters.

    Args:
        session_id: QuickBooks session ID (for production)
        csv_path: Path to CSV file (for testing)

    Returns:
        CustomerDataSource instance
    """
    if csv_path and csv_path.exists():
        logger.info(f"Using CSV data source: {csv_path}")
        return CSVDataSource(csv_path)
    elif session_id:
        logger.info("Using QuickBooks API data source")
        return QuickBooksDataSource(session_id)
    else:
        raise ValueError("Either session_id or csv_path must be provided")
