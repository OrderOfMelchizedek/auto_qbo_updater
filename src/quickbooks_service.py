"""QuickBooks API service for customer operations."""
import logging
from typing import Any, Dict, List

import requests

from .config import Config
from .quickbooks_auth import QuickBooksAuth

logger = logging.getLogger(__name__)


class QuickBooksError(Exception):
    """QuickBooks API error."""

    pass


class QuickBooksClient:
    """Client for interacting with QuickBooks API."""

    def __init__(self, session_id: str):
        """
        Initialize QuickBooks client.

        Args:
            session_id: Session ID for authentication
        """
        self.session_id = session_id
        self.auth = QuickBooksAuth()

        # Get auth status to retrieve company ID
        auth_status = self.auth.get_auth_status(session_id)
        if not auth_status.get("authenticated"):
            raise QuickBooksError("Session not authenticated")

        company_id = auth_status.get("realm_id")
        if not company_id:
            raise QuickBooksError("No company ID found in session")

        # Set base URL based on environment
        if Config.QBO_ENVIRONMENT == "production":
            self.base_url = f"https://quickbooks.api.intuit.com/v3/company/{company_id}"
        else:
            self.base_url = (
                f"https://sandbox-quickbooks.api.intuit.com/v3/company/{company_id}"
            )

    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """
        Make authenticated request to QuickBooks API.

        Args:
            method: HTTP method
            endpoint: API endpoint
            **kwargs: Additional request parameters

        Returns:
            Response object

        Raises:
            QuickBooksError: If API request fails
        """
        # Get access token
        access_token = self.auth.get_valid_access_token(self.session_id)
        if not access_token:
            raise QuickBooksError("No access token found")

        # Set headers
        headers = kwargs.get("headers", {})
        headers["Authorization"] = f"Bearer {access_token}"
        headers["Accept"] = "application/json"
        headers["Content-Type"] = "application/json"
        kwargs["headers"] = headers

        # Make request
        url = f"{self.base_url}{endpoint}"
        response = requests.request(method, url, **kwargs)

        # Handle 401 - try token refresh
        if response.status_code == 401:
            logger.info("Got 401, attempting token refresh")
            try:
                self.auth.refresh_access_token(self.session_id)
                # Retry with new token
                access_token = self.auth.get_valid_access_token(self.session_id)
                headers["Authorization"] = f"Bearer {access_token}"
                response = requests.request(method, url, **kwargs)
            except Exception:
                raise QuickBooksError("Token refresh failed")

        # Check for errors
        if response.status_code >= 400:
            raise QuickBooksError(
                f"API request failed ({response.status_code}): {response.text}"
            )

        return response

    def search_customer(self, search_term: str) -> List[Dict[str, Any]]:
        """
        Search for customers by name or organization.

        Args:
            search_term: Name or organization to search for

        Returns:
            List of matching customers
        """
        # Escape special characters for QuickBooks query
        # QuickBooks uses backslash to escape single quotes
        escaped_term = search_term.replace("'", "\\'")

        # Build query - search in DisplayName field
        query = f"select * from Customer where DisplayName like '%{escaped_term}%'"

        logger.debug(f"QuickBooks query: {query}")

        # Make request
        response = self._make_request("GET", "/query", params={"query": query})

        # Extract customers from response
        data = response.json()
        customers = data.get("QueryResponse", {}).get("Customer", [])

        return customers

    def get_customer(self, customer_id: str) -> Dict[str, Any]:
        """
        Get full customer details by ID.

        Args:
            customer_id: QuickBooks customer ID

        Returns:
            Customer data
        """
        response = self._make_request("GET", f"/customer/{customer_id}")
        data = response.json()
        return data["Customer"]

    def format_customer_data(self, customer: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format QuickBooks customer data to PRD structure.

        Args:
            customer: Raw customer data from QuickBooks

        Returns:
            Formatted customer data matching PRD spec
        """
        # Extract customer reference info
        customer_ref = {
            "id": customer.get("Id", ""),
            "first_name": customer.get("GivenName"),
            "last_name": customer.get("FamilyName"),
            "full_name": customer.get("DisplayName", ""),
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

        # Extract email (as list to support multiple)
        qb_email = []
        if customer.get("PrimaryEmailAddr", {}).get("Address"):
            qb_email.append(customer["PrimaryEmailAddr"]["Address"])

        # Extract phone (as list to support multiple)
        qb_phone = []
        if customer.get("PrimaryPhone", {}).get("FreeFormNumber"):
            qb_phone.append(customer["PrimaryPhone"]["FreeFormNumber"])

        return {
            "customer_ref": customer_ref,
            "qb_address": qb_address,
            "qb_email": qb_email,
            "qb_phone": qb_phone,
        }

    def _format_zip_code(self, zip_code: str) -> str:
        """
        Format ZIP code - remove +4 extension, preserve leading zeros.

        Args:
            zip_code: Raw ZIP code

        Returns:
            Formatted 5-digit ZIP
        """
        if not zip_code:
            return ""

        # Remove +4 extension if present
        if "-" in zip_code:
            zip_code = zip_code.split("-")[0]

        # Ensure it's 5 digits with leading zeros preserved
        return zip_code.strip()
