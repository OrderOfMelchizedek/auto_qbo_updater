"""Service for QuickBooks sales receipt operations."""
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import requests
from authlib.integrations.requests_client import OAuth2Session

from src.config.settings import settings
from src.models.donation import DonationEntry
from src.models.quickbooks import QuickBooksSalesReceipt, SalesReceiptLine
from src.utils.exceptions import QuickBooksIntegrationError

logger = logging.getLogger(__name__)


class SalesReceiptService:
    """Service for managing QuickBooks sales receipts."""

    def __init__(self, oauth_token: Dict[str, Any]):
        """
        Initialize the sales receipt service.

        Args:
            oauth_token: OAuth token dictionary with access_token and realm_id
        """
        self.oauth_token = oauth_token
        self.realm_id = oauth_token.get("realm_id")
        self.base_url = f"{settings.QUICKBOOKS_BASE_URL}/v3/company/{self.realm_id}"

        # Create OAuth session
        self.session = OAuth2Session(
            client_id=settings.QUICKBOOKS_CLIENT_ID,
            token=oauth_token,
        )

        # Cache for commonly used items and accounts
        self._donation_item_id: Optional[str] = None
        self._deposit_account_id: Optional[str] = None

    def create_sales_receipt(
        self,
        donation: DonationEntry,
        customer_id: str,
        deposit_account_id: Optional[str] = None,
    ) -> QuickBooksSalesReceipt:
        """
        Create a sales receipt for a donation.

        Args:
            donation: Donation entry with payment information
            customer_id: QuickBooks customer ID
            deposit_account_id: Optional deposit account ID
                (uses default if not provided)

        Returns:
            Created sales receipt details
        """
        try:
            if not donation.payment_info:
                raise ValueError("Donation must have payment information")

            # Get or create donation item
            donation_item_id = self._get_or_create_donation_item()

            # Get deposit account
            if not deposit_account_id:
                deposit_account_id = self._get_default_deposit_account()

            # Build sales receipt data
            receipt_data = {
                "CustomerRef": {"value": customer_id},
                "TxnDate": (
                    donation.payment_info.payment_date.isoformat()
                    if donation.payment_info.payment_date
                    else datetime.now().date().isoformat()
                ),
                "Line": [
                    {
                        "DetailType": "SalesItemLineDetail",
                        "Amount": float(donation.payment_info.amount),
                        "SalesItemLineDetail": {
                            "ItemRef": {"value": donation_item_id},
                        },
                    }
                ],
                "DepositToAccountRef": {"value": deposit_account_id},
            }

            # Add payment method if available
            if donation.payment_info.payment_method:
                payment_method_ref = self._get_payment_method_ref(
                    donation.payment_info.payment_method
                )
                if payment_method_ref:
                    receipt_data["PaymentMethodRef"] = payment_method_ref

            # Add check number if available
            if donation.payment_info.check_number:
                receipt_data["PaymentRefNum"] = donation.payment_info.check_number

            # Add memo if available
            if donation.payment_info.memo:
                receipt_data["PrivateNote"] = donation.payment_info.memo

            # Add custom fields for tracking
            receipt_data["CustomField"] = [
                {
                    "DefinitionId": "1",  # Assuming custom field for source documents
                    "Name": "Source Documents",
                    "Type": "StringType",
                    "StringValue": ", ".join(
                        donation.source_documents[:5]
                    ),  # Limit to 5
                }
            ]

            # Create the sales receipt
            response = self.session.post(
                f"{self.base_url}/salesreceipt",
                json=receipt_data,
            )
            response.raise_for_status()

            data = response.json()
            created_receipt = data.get("SalesReceipt", {})

            logger.info(
                f"Created sales receipt: {created_receipt.get('Id')} "
                f"for amount ${donation.payment_info.amount}"
            )

            return self._parse_sales_receipt(created_receipt)

        except requests.RequestException as e:
            logger.error(f"Failed to create sales receipt: {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"Response body: {e.response.text}")
            raise QuickBooksIntegrationError(
                f"Sales receipt creation failed: {str(e)}", details={"error": str(e)}
            )

    def _get_or_create_donation_item(self) -> str:
        """Get or create the donation item in QuickBooks."""
        if self._donation_item_id:
            return self._donation_item_id

        # Search for existing donation item
        query = "SELECT * FROM Item WHERE Name = 'Donation' AND Active = true"
        items = self._execute_query(query, "Item")

        if items:
            self._donation_item_id = items[0]["Id"]
            return self._donation_item_id or ""

        # Create donation item if not found
        income_account_id = self._get_income_account()

        item_data = {
            "Name": "Donation",
            "Type": "Service",
            "IncomeAccountRef": {"value": income_account_id},
            "Active": True,
            "Description": "Charitable donation",
        }

        response = self.session.post(
            f"{self.base_url}/item",
            json=item_data,
        )
        response.raise_for_status()

        data = response.json()
        created_item = data.get("Item", {})
        self._donation_item_id = created_item.get("Id")

        logger.info(f"Created donation item: {self._donation_item_id}")
        return self._donation_item_id or ""

    def _get_income_account(self) -> str:
        """Get the income account for donations."""
        # Search for donation income account
        query = (
            "SELECT * FROM Account WHERE "
            "AccountType = 'Income' AND "
            "Name LIKE '%Donation%' AND "
            "Active = true"
        )
        accounts = self._execute_query(query, "Account")

        if accounts:
            return accounts[0]["Id"]

        # If not found, get the first income account
        query = "SELECT * FROM Account WHERE AccountType = 'Income' AND Active = true"
        accounts = self._execute_query(query, "Account")

        if accounts:
            return accounts[0]["Id"]

        raise QuickBooksIntegrationError("No income account found")

    def _get_default_deposit_account(self) -> str:
        """Get the default deposit account."""
        if self._deposit_account_id:
            return self._deposit_account_id

        # Get undeposited funds account (standard QB account)
        query = (
            "SELECT * FROM Account WHERE "
            "AccountType = 'Other Current Asset' AND "
            "Name = 'Undeposited Funds' AND "
            "Active = true"
        )
        accounts = self._execute_query(query, "Account")

        if accounts:
            self._deposit_account_id = accounts[0]["Id"]
            return self._deposit_account_id or ""

        # Fallback to any bank account
        query = (
            "SELECT * FROM Account WHERE "
            "AccountType IN ('Bank', 'Other Current Asset') AND "
            "Active = true"
        )
        accounts = self._execute_query(query, "Account")

        if accounts:
            self._deposit_account_id = accounts[0]["Id"]
            return self._deposit_account_id or ""

        raise QuickBooksIntegrationError("No deposit account found")

    def _get_payment_method_ref(self, payment_method: str) -> Optional[Dict[str, str]]:
        """Get payment method reference based on payment type."""
        # Map our payment methods to QuickBooks payment methods
        method_mapping = {
            "check": "Check",
            "cash": "Cash",
            "credit_card": "Credit Card",
            "electronic": "EFT",
            "other": "Other",
        }

        qb_method_name = method_mapping.get(payment_method, "Other")

        # Search for payment method
        query = f"SELECT * FROM PaymentMethod WHERE Name = '{qb_method_name}'"
        methods = self._execute_query(query, "PaymentMethod")

        if methods:
            return {"value": methods[0]["Id"]}

        return None

    def _execute_query(self, query: str, entity_type: str) -> List[Dict[str, Any]]:
        """Execute a QuickBooks query."""
        try:
            response = self.session.get(
                f"{self.base_url}/query",
                params={"query": query},
            )
            response.raise_for_status()

            data = response.json()
            return data.get("QueryResponse", {}).get(entity_type, [])

        except requests.RequestException as e:
            logger.error(f"Query execution failed: {e}")
            return []

    def get_sales_receipt(self, receipt_id: str) -> QuickBooksSalesReceipt:
        """
        Get a sales receipt by ID.

        Args:
            receipt_id: QuickBooks sales receipt ID

        Returns:
            Sales receipt details
        """
        try:
            response = self.session.get(f"{self.base_url}/salesreceipt/{receipt_id}")
            response.raise_for_status()

            data = response.json()
            receipt_data = data.get("SalesReceipt", {})

            return self._parse_sales_receipt(receipt_data)

        except requests.RequestException as e:
            logger.error(f"Failed to get sales receipt {receipt_id}: {e}")
            raise QuickBooksIntegrationError(
                f"Failed to get sales receipt: {str(e)}", details={"error": str(e)}
            )

    def batch_create_sales_receipts(
        self, donations_with_customers: List[Tuple[DonationEntry, str]]
    ) -> List[Dict[str, Any]]:
        """
        Create multiple sales receipts in batch.

        Args:
            donations_with_customers: List of (donation, customer_id) tuples

        Returns:
            List of results with receipt IDs or errors
        """
        results = []

        for donation, customer_id in donations_with_customers:
            try:
                receipt = self.create_sales_receipt(donation, customer_id)
                results.append(
                    {
                        "success": True,
                        "receipt_id": receipt.id,
                        "donation": donation,
                        "customer_id": customer_id,
                    }
                )
            except Exception as e:
                logger.error(
                    f"Failed to create receipt for customer {customer_id}: {e}"
                )
                results.append(
                    {
                        "success": False,
                        "error": str(e),
                        "donation": donation,
                        "customer_id": customer_id,
                    }
                )

        # Log summary
        successful = sum(1 for r in results if r["success"])
        logger.info(
            f"Batch created {successful}/{len(donations_with_customers)} "
            f"sales receipts"
        )

        return results

    def _parse_sales_receipt(
        self, receipt_data: Dict[str, Any]
    ) -> QuickBooksSalesReceipt:
        """Parse QuickBooks sales receipt data into our model."""
        # Parse line items
        lines = []
        for line_data in receipt_data.get("Line", []):
            if line_data.get("DetailType") == "SalesItemLineDetail":
                line = SalesReceiptLine(
                    id=line_data.get("Id"),
                    line_num=line_data.get("LineNum"),
                    amount=Decimal(str(line_data.get("Amount", 0))),
                    description=line_data.get("Description"),
                    item_ref=line_data.get("SalesItemLineDetail", {})
                    .get("ItemRef", {})
                    .get("value"),
                )
                lines.append(line)

        return QuickBooksSalesReceipt(
            id=receipt_data.get("Id"),
            sync_token=receipt_data.get("SyncToken"),
            doc_number=receipt_data.get("DocNumber"),
            txn_date=receipt_data.get("TxnDate"),
            customer_ref=receipt_data.get("CustomerRef", {}).get("value"),
            total_amt=Decimal(str(receipt_data.get("TotalAmt", 0))),
            payment_method_ref=receipt_data.get("PaymentMethodRef", {}).get("value"),
            payment_ref_num=receipt_data.get("PaymentRefNum"),
            deposit_to_account_ref=receipt_data.get("DepositToAccountRef", {}).get(
                "value"
            ),
            private_note=receipt_data.get("PrivateNote"),
            lines=lines,
        )
