"""
QuickBooks Online Entity Service.

This module handles management of QBO entities like accounts, items, and payment methods.
"""

import logging
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from .base import QBOBaseService

logger = logging.getLogger(__name__)


class QBOEntityService(QBOBaseService):
    """Service for managing QuickBooks Online entities (accounts, items, payment methods)."""

    def create_account(self, account_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new account in QBO.

        Args:
            account_data: Account data dictionary with required fields:
                - Name: Account name
                - AccountType: Account type (e.g., Bank, Other Current Asset)
                - AccountSubType: Optional sub-type

        Returns:
            Created account data if successful, None otherwise
        """
        if not self.auth_service.is_token_valid():
            logger.warning("Not authenticated with QBO")
            return None

        try:
            # Make sure required fields are present
            if "Name" not in account_data or "AccountType" not in account_data:
                logger.error("Missing required fields for account creation")
                return None

            response = self._make_qbo_request("POST", "account", data=account_data)
            account = response.get("Account")
            if account:
                logger.info(f"Successfully created account: {account.get('Name')} (ID: {account.get('Id')})")
            return account

        except Exception as e:
            logger.error(f"Exception in create_account: {str(e)}")
            import traceback

            traceback.print_exc()
            return None

    def create_item(self, item_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new item (product/service) in QBO.

        Args:
            item_data: Item data dictionary with required fields:
                - Name: Item name
                - Type: Service, Inventory, etc.
                - IncomeAccountRef: Reference to income account

        Returns:
            Created item data if successful, None otherwise
        """
        if not self.auth_service.is_token_valid():
            logger.warning("Not authenticated with QBO")
            return None

        try:
            # Make sure required fields are present
            if "Name" not in item_data:
                logger.error("Missing required Name field for item creation")
                return None

            # Default to Service type if not specified
            if "Type" not in item_data:
                item_data["Type"] = "Service"

            # Default to Non-inventory if type is Item
            if item_data.get("Type") == "Item" and "ItemType" not in item_data:
                item_data["ItemType"] = "Non-inventory"

            response = self._make_qbo_request("POST", "item", data=item_data)
            item = response.get("Item")
            if item:
                logger.info(f"Successfully created item: {item.get('Name')} (ID: {item.get('Id')})")
            return item

        except Exception as e:
            logger.error(f"Exception in create_item: {str(e)}")
            import traceback

            traceback.print_exc()
            return None

    def create_payment_method(self, payment_method_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new payment method in QBO.

        Args:
            payment_method_data: Payment method data dictionary with required fields:
                - Name: Payment method name

        Returns:
            Created payment method data if successful, None otherwise
        """
        if not self.auth_service.is_token_valid():
            logger.warning("Not authenticated with QBO")
            return None

        try:
            # Make sure required fields are present
            if "Name" not in payment_method_data:
                logger.error("Missing required Name field for payment method creation")
                return None

            response = self._make_qbo_request("POST", "paymentmethod", data=payment_method_data)
            payment_method = response.get("PaymentMethod")
            if payment_method:
                logger.info(
                    f"Successfully created payment method: {payment_method.get('Name')} (ID: {payment_method.get('Id')})"
                )
            return payment_method

        except Exception as e:
            logger.error(f"Exception in create_payment_method: {str(e)}")
            import traceback

            traceback.print_exc()
            return None

    def get_all_items(self) -> List[Dict[str, Any]]:
        """Fetch the complete list of items/products/services from QBO.

        Returns:
            List of all item data dictionaries
        """
        if not self.auth_service.is_token_valid():
            logger.warning("Not authenticated with QBO - Missing access_token or realm_id")
            return []

        try:
            logger.info("==== STARTING ITEM RETRIEVAL FROM QUICKBOOKS ====")

            items = []
            start_position = 1
            max_results = 1000  # QBO API limit per query
            batch_count = 0

            while True:
                batch_count += 1
                # Query for a batch of items
                query = f"SELECT * FROM Item STARTPOSITION {start_position} MAXRESULTS {max_results}"  # nosec B608
                encoded_query = quote(query)

                logger.info(f"Batch {batch_count}: Requesting items at position {start_position}")

                response = self._make_qbo_request("GET", f"query?query={encoded_query}")
                batch = response.get("QueryResponse", {}).get("Item", [])

                # If no more items, break the loop
                if not batch:
                    logger.info(f"Batch {batch_count}: No more items found")
                    break

                # Add this batch to our collection
                items.extend(batch)
                logger.info(f"Batch {batch_count}: Retrieved {len(batch)} items (running total: {len(items)})")

                # If we got fewer items than the max, we're done
                if len(batch) < max_results:
                    logger.info(f"Batch {batch_count}: Less than max results, finished retrieving")
                    break

                # Otherwise, update the start position for the next batch
                start_position += max_results

            logger.info(f"==== ITEM RETRIEVAL SUMMARY ====")
            logger.info(f"Successfully retrieved {len(items)} items in {batch_count} batches")

            # Log a few item names for verification
            if items:
                logger.info("Sample of retrieved items:")
                for i, item in enumerate(items[:5]):
                    logger.info(f"  {i+1}. {item.get('Name', 'Unknown')}")
                logger.info("  ...")

            return items

        except Exception as e:
            logger.error(f"Exception in get_all_items: {str(e)}")
            import traceback

            traceback.print_exc()
            return []

    def get_all_accounts(self) -> List[Dict[str, Any]]:
        """Fetch the complete list of accounts from QBO.

        Returns:
            List of all account data dictionaries
        """
        if not self.auth_service.is_token_valid():
            logger.warning("Not authenticated with QBO - Missing access_token or realm_id")
            return []

        try:
            logger.info("==== STARTING ACCOUNT RETRIEVAL FROM QUICKBOOKS ====")

            accounts = []
            start_position = 1
            max_results = 1000  # QBO API limit per query
            batch_count = 0

            while True:
                batch_count += 1
                # Query for a batch of accounts
                query = f"SELECT * FROM Account STARTPOSITION {start_position} MAXRESULTS {max_results}"  # nosec B608
                encoded_query = quote(query)

                logger.info(f"Batch {batch_count}: Requesting accounts at position {start_position}")

                response = self._make_qbo_request("GET", f"query?query={encoded_query}")
                batch = response.get("QueryResponse", {}).get("Account", [])

                # If no more accounts, break the loop
                if not batch:
                    logger.info(f"Batch {batch_count}: No more accounts found")
                    break

                # Add this batch to our collection
                accounts.extend(batch)
                logger.info(f"Batch {batch_count}: Retrieved {len(batch)} accounts (running total: {len(accounts)})")

                # If we got fewer accounts than the max, we're done
                if len(batch) < max_results:
                    logger.info(f"Batch {batch_count}: Less than max results, finished retrieving")
                    break

                # Otherwise, update the start position for the next batch
                start_position += max_results

            logger.info(f"==== ACCOUNT RETRIEVAL SUMMARY ====")
            logger.info(f"Successfully retrieved {len(accounts)} accounts in {batch_count} batches")

            # Sort accounts by name for easier selection in the UI
            accounts.sort(key=lambda x: x.get("Name", "").lower())

            return accounts

        except Exception as e:
            logger.error(f"Exception in get_all_accounts: {str(e)}")
            import traceback

            traceback.print_exc()
            return []

    def get_all_payment_methods(self) -> List[Dict[str, Any]]:
        """Fetch the complete list of payment methods from QBO.

        Returns:
            List of all payment method data dictionaries
        """
        if not self.auth_service.is_token_valid():
            logger.warning("Not authenticated with QBO - Missing access_token or realm_id")
            return []

        try:
            logger.info("==== STARTING PAYMENT METHOD RETRIEVAL FROM QUICKBOOKS ====")

            payment_methods = []
            start_position = 1
            max_results = 1000  # QBO API limit per query
            batch_count = 0

            while True:
                batch_count += 1
                # Query for a batch of payment methods
                query = (
                    f"SELECT * FROM PaymentMethod STARTPOSITION {start_position} MAXRESULTS {max_results}"  # nosec B608
                )
                encoded_query = quote(query)

                logger.info(f"Batch {batch_count}: Requesting payment methods at position {start_position}")

                response = self._make_qbo_request("GET", f"query?query={encoded_query}")
                batch = response.get("QueryResponse", {}).get("PaymentMethod", [])

                # If no more payment methods, break the loop
                if not batch:
                    logger.info(f"Batch {batch_count}: No more payment methods found")
                    break

                # Add this batch to our collection
                payment_methods.extend(batch)
                logger.info(
                    f"Batch {batch_count}: Retrieved {len(batch)} payment methods (running total: {len(payment_methods)})"
                )

                # If we got fewer payment methods than the max, we're done
                if len(batch) < max_results:
                    logger.info(f"Batch {batch_count}: Less than max results, finished retrieving")
                    break

                # Otherwise, update the start position for the next batch
                start_position += max_results

            logger.info(f"==== PAYMENT METHOD RETRIEVAL SUMMARY ====")
            logger.info(f"Successfully retrieved {len(payment_methods)} payment methods in {batch_count} batches")

            # Sort payment methods by name for easier selection in the UI
            payment_methods.sort(key=lambda x: x.get("Name", "").lower())

            return payment_methods

        except Exception as e:
            logger.error(f"Exception in get_all_payment_methods: {str(e)}")
            import traceback

            traceback.print_exc()
            return []
