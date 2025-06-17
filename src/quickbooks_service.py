"""QuickBooks API service for customer operations."""
import json
import logging
import re
from typing import Any, Dict, List, Optional

import requests

from .config import Config
from .quickbooks_auth import QuickBooksAuth
from .quickbooks_utils import QuickBooksError

logger = logging.getLogger(__name__)


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
            raise QuickBooksError("Session not authenticated", status_code=401)

        company_id = auth_status.get("realm_id")
        if not company_id:
            raise QuickBooksError("No company ID found in session", status_code=400)

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
            raise QuickBooksError("No access token found", status_code=401)

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
                raise QuickBooksError("Token refresh failed", status_code=401)

        # Check for errors
        if response.status_code >= 400:
            try:
                error_detail = response.json()
            except Exception:
                error_detail = {"raw_response": response.text}

            raise QuickBooksError(
                f"API request failed ({response.status_code}): {response.text}",
                status_code=response.status_code,
                detail=error_detail,
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

    def _build_full_name(self, customer: Dict[str, Any]) -> str:
        """
        Build a properly formatted full name from QuickBooks customer data.

        Handles:
        - Individual names with salutations (Mr. John Smith)
        - Married couples (Mr. & Mrs. John Smith)
        - Unmarried couples (John Smith and Mary Jones)
        - Organizations (returns CompanyName)

        Args:
            customer: QuickBooks customer data

        Returns:
            Properly formatted full name
        """
        # If it's a company/organization, return the company name
        company_name = (customer.get("CompanyName") or "").strip()
        if company_name:
            return company_name

        # Extract name components
        title = (customer.get("Title") or "").strip()
        given_name = (customer.get("GivenName") or "").strip()
        middle_name = (customer.get("MiddleName") or "").strip()
        family_name = (customer.get("FamilyName") or "").strip()
        suffix = (customer.get("Suffix") or "").strip()
        display_name = (customer.get("DisplayName") or "").strip()

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
                name = (
                    f"{title} {given_name} {middle_name} {family_name} "
                    f"and {partner_info}"
                )
                return name.replace("  ", " ").strip()
            else:
                # Same last name
                return f"Mr. & Mrs. {given_name} {middle_name} {family_name}".replace(
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

        # Add middle name
        if middle_name:
            name_parts.append(middle_name)

        # Add family name
        if family_name:
            name_parts.append(family_name)

        # Add suffix if present
        if suffix:
            name_parts.append(suffix)

        # If we have name parts, join them
        if name_parts:
            return " ".join(name_parts)

        # Fallback to DisplayName if no name components
        return display_name

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

    def create_customer(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new customer in QuickBooks.

        Args:
            customer_data: Dictionary containing customer information.
                           Expected keys: DisplayName, GivenName, FamilyName,
                           CompanyName, PrimaryEmailAddr, PrimaryPhone, BillAddr.

        Returns:
            The created customer data from the API response.

        Raises:
            ValueError: If DisplayName is missing.
            QuickBooksError: If API request fails.
        """
        if not customer_data.get("DisplayName"):
            raise ValueError("DisplayName is required to create a customer.")

        payload = {
            "DisplayName": customer_data["DisplayName"],
            "GivenName": customer_data.get("GivenName"),
            "FamilyName": customer_data.get("FamilyName"),
            "CompanyName": customer_data.get("CompanyName"),
        }

        if customer_data.get("PrimaryEmailAddr"):
            payload["PrimaryEmailAddr"] = {"Address": customer_data["PrimaryEmailAddr"]}

        if customer_data.get("PrimaryPhone"):
            payload["PrimaryPhone"] = {"FreeFormNumber": customer_data["PrimaryPhone"]}

        bill_addr = customer_data.get("BillAddr")
        if bill_addr and isinstance(bill_addr, dict):
            payload["BillAddr"] = {
                "Line1": bill_addr.get("Line1"),
                "City": bill_addr.get("City"),
                "CountrySubDivisionCode": bill_addr.get("CountrySubDivisionCode"),
                "PostalCode": bill_addr.get("PostalCode"),
            }

        # Remove keys with None values to keep payload clean
        payload = {k: v for k, v in payload.items() if v is not None}

        try:
            response = self._make_request("POST", "/customer", json=payload)
            # QuickBooks API typically returns the created object under a key
            # like "Customer" in the JSON response.
            return response.json().get("Customer", response.json())
        except QuickBooksError as e:
            logger.error(f"Failed to create customer: {e}")
            # Re-raise the error to be handled by the caller
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during customer creation: {e}")
            raise QuickBooksError(f"Network error: {e}")
        except ValueError as e:  # Handles JSON decoding errors
            logger.error(f"Error decoding JSON response from customer creation: {e}")
            raise QuickBooksError(f"JSON decode error: {e}")

    def list_accounts(self, search_term: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all accounts from QuickBooks.

        Args:
            search_term: Optional search term to filter accounts by name

        Returns:
            List of account dictionaries

        Raises:
            QuickBooksError: If API request fails
        """
        try:
            # Query all accounts including system accounts with increased limit
            # Undeposited Funds is a system account that might need special handling
            # MAXRESULTS 1000 ensures we get more accounts than the default 100
            query = "SELECT * FROM Account MAXRESULTS 1000 ORDER BY Name"
            response = self._make_request("GET", "/query", params={"query": query})
            data = response.json()

            # Extract accounts from QueryResponse
            accounts = data.get("QueryResponse", {}).get("Account", [])

            # Log account types to debug Undeposited Funds issue
            logger.info(f"Found {len(accounts)} accounts from QuickBooks")

            # Log all Other Current Assets accounts and potential Undeposited Funds
            for account in accounts:
                account_type = account.get("AccountType", "")
                account_subtype = account.get("AccountSubType", "")
                account_name = account.get("Name", "")

                # Log Other Current Assets accounts
                if "other current" in account_type.lower():
                    logger.info(
                        f"Other Current Asset account: Name={account_name}, "
                        f"AccountType={account_type}, "
                        f"AccountSubType={account_subtype}, "
                        f"Id={account.get('Id')}"
                    )

                # Look for Undeposited Funds (with or without account numbers)
                # Matches: "12000 Undeposited Funds", "Undeposited Funds", etc.
                undeposited_pattern = re.compile(
                    r"\d*\s*undeposited\s*funds", re.IGNORECASE
                )
                if (
                    undeposited_pattern.search(account_name)
                    or account_subtype == "UndepositedFunds"
                    or undeposited_pattern.search(account.get("FullyQualifiedName", ""))
                ):
                    logger.info(
                        f"*** UNDEPOSITED FUNDS FOUND: Name={account_name}, "
                        f"AccountType={account_type}, "
                        f"AccountSubType={account_subtype}, "
                        f"FullyQualifiedName={account.get('FullyQualifiedName')}, "
                        f"Id={account.get('Id')}"
                    )

            # Also log a summary of account types
            account_types: Dict[str, int] = {}
            for account in accounts:
                acc_type = account.get("AccountType", "Unknown")
                account_types[acc_type] = account_types.get(acc_type, 0) + 1
            logger.info(f"Account type summary: {account_types}")

            # Filter to only return active accounts OR the Undeposited Funds account
            # (Undeposited Funds might be inactive but we still need it)
            filtered_accounts = []
            undeposited_pattern = re.compile(
                r"\d*\s*undeposited\s*funds", re.IGNORECASE
            )

            for account in accounts:
                is_active = account.get("Active", True)
                account_name = account.get("Name", "")
                fully_qualified_name = account.get("FullyQualifiedName", "")

                is_undeposited = (
                    undeposited_pattern.search(account_name)
                    or account.get("AccountSubType") == "UndepositedFunds"
                    or undeposited_pattern.search(fully_qualified_name)
                )

                if is_active or is_undeposited:
                    filtered_accounts.append(account)
                    if is_undeposited and not is_active:
                        logger.warning(
                            "Undeposited Funds account is inactive: "
                            f"{account.get('Name')}"
                        )

            # Apply search filtering if search_term is provided
            if search_term:
                search_lower = search_term.lower()
                filtered_accounts = [
                    acc
                    for acc in filtered_accounts
                    if search_lower in (acc.get("Name", "") or "").lower()
                    or search_lower in (acc.get("FullyQualifiedName", "") or "").lower()
                ]
                logger.info(
                    f"Filtered to {len(filtered_accounts)} accounts "
                    f"matching '{search_term}'"
                )

            return filtered_accounts

        except QuickBooksError:
            raise
        except Exception as e:
            logger.error(f"Error fetching accounts: {e}")
            raise QuickBooksError(f"Failed to fetch accounts: {e}")

    def list_items(self) -> List[Dict[str, Any]]:
        """
        List all items (products/services) from QuickBooks.

        Returns:
            List of item dictionaries

        Raises:
            QuickBooksError: If API request fails
        """
        try:
            # Query all active items
            query = "SELECT * FROM Item WHERE Active = true"
            response = self._make_request("GET", "/query", params={"query": query})
            data = response.json()

            # Extract items from QueryResponse
            items = data.get("QueryResponse", {}).get("Item", [])
            return items

        except QuickBooksError:
            raise
        except Exception as e:
            logger.error(f"Error fetching items: {e}")
            raise QuickBooksError(f"Failed to fetch items: {e}")

    def list_payment_methods(self) -> List[Dict[str, Any]]:
        """
        List all payment methods from QuickBooks.

        Returns:
            List of payment method dictionaries

        Raises:
            QuickBooksError: If API request fails
        """
        try:
            # Query all active payment methods
            query = "SELECT * FROM PaymentMethod WHERE Active = true"
            response = self._make_request("GET", "/query", params={"query": query})
            data = response.json()

            # Extract payment methods from QueryResponse
            payment_methods = data.get("QueryResponse", {}).get("PaymentMethod", [])
            return payment_methods

        except QuickBooksError:
            raise
        except Exception as e:
            logger.error(f"Error fetching payment methods: {e}")
            raise QuickBooksError(f"Failed to fetch payment methods: {e}")

    def create_sales_receipt(
        self, sales_receipt_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a sales receipt in QuickBooks.

        Args:
            sales_receipt_data: Dictionary containing sales receipt information.
                Required keys:
                - CustomerRef: {"value": "customer_id"}
                - Line: List of line items with ItemRef or AccountRef
                - DepositToAccountRef: {"value": "account_id"}
                Optional keys:
                - TxnDate: Transaction date (defaults to today)
                - PaymentMethodRef: Payment method reference
                - DocNumber: Document number (sales receipt number)
                - PaymentRefNum: Payment reference number (e.g., check number)
                - PrivateNote: Private note/memo

        Returns:
            The created sales receipt data from the API response.

        Raises:
            ValueError: If required fields are missing.
            QuickBooksError: If API request fails.
        """
        # Validate required fields
        if not sales_receipt_data.get("CustomerRef"):
            raise ValueError("CustomerRef is required to create a sales receipt.")
        if not sales_receipt_data.get("Line"):
            raise ValueError("At least one Line item is required.")
        if not sales_receipt_data.get("DepositToAccountRef"):
            raise ValueError("DepositToAccountRef is required.")

        # Build the sales receipt payload
        payload = {
            "CustomerRef": sales_receipt_data["CustomerRef"],
            "Line": sales_receipt_data["Line"],
            "DepositToAccountRef": sales_receipt_data["DepositToAccountRef"],
        }

        # Add optional fields if provided
        if sales_receipt_data.get("TxnDate"):
            payload["TxnDate"] = sales_receipt_data["TxnDate"]

        if sales_receipt_data.get("PaymentMethodRef"):
            payload["PaymentMethodRef"] = sales_receipt_data["PaymentMethodRef"]

        if sales_receipt_data.get("DocNumber"):
            payload["DocNumber"] = sales_receipt_data["DocNumber"]

        if sales_receipt_data.get("PrivateNote"):
            payload["PrivateNote"] = sales_receipt_data["PrivateNote"]

        if sales_receipt_data.get("PaymentRefNum"):
            payload["PaymentRefNum"] = sales_receipt_data["PaymentRefNum"]

        # Remove keys with None values
        payload = {k: v for k, v in payload.items() if v is not None}

        # Log the final payload being sent to QuickBooks
        logger.info(
            f"Final QuickBooks sales receipt payload: {json.dumps(payload, indent=2)}"
        )

        try:
            response = self._make_request("POST", "/salesreceipt", json=payload)
            # QuickBooks API returns the created object under "SalesReceipt" key
            return response.json().get("SalesReceipt", response.json())
        except QuickBooksError as e:
            logger.error(f"Failed to create sales receipt: {e}")
            raise
        except Exception as e:
            logger.error(f"Error creating sales receipt: {e}")
            raise QuickBooksError(f"Failed to create sales receipt: {e}")
