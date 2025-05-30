"""
QuickBooks Online Sales Receipt Service.

This module handles creation and management of sales receipts.
"""

import logging
import re
from typing import Any, Dict, Optional
from urllib.parse import quote

from ..exceptions import QBOAPIException
from .base import QBOBaseService

logger = logging.getLogger(__name__)


class QBOSalesReceiptService(QBOBaseService):
    """Service for managing QuickBooks Online sales receipts."""

    def find_sales_receipt(self, check_no: str, check_date: str, customer_id: str) -> Optional[Dict[str, Any]]:
        """Find existing sales receipt by check number, date, and customer.

        Args:
            check_no: Check number to search for
            check_date: Check date (YYYY-MM-DD format)
            customer_id: QBO Customer ID

        Returns:
            Sales receipt data if found, None otherwise
        """
        if not self.auth_service.is_token_valid():
            logger.warning("Not authenticated with QBO")
            return None

        try:
            # Query for sales receipts matching the criteria
            # Using PaymentRefNum for check number and CustomerRef for customer
            escaped_check_no = self._escape_query_value(check_no)
            escaped_date = self._escape_query_value(check_date)
            escaped_customer_id = self._escape_query_value(customer_id)

            query = f"SELECT * FROM SalesReceipt WHERE PaymentRefNum = '{escaped_check_no}' AND TxnDate = '{escaped_date}' AND CustomerRef = '{escaped_customer_id}'"  # nosec B608
            encoded_query = quote(query)

            response = self._make_qbo_request("GET", f"query?query={encoded_query}")

            if response.get("QueryResponse", {}).get("SalesReceipt"):
                receipts = response["QueryResponse"]["SalesReceipt"]
                logger.info(f"Found {len(receipts)} matching sales receipt(s)")
                return receipts[0] if receipts else None

            return None

        except Exception as e:
            logger.error(f"Exception in find_sales_receipt: {str(e)}")
            return None

    def create_sales_receipt(self, sales_receipt_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a sales receipt in QBO with enhanced error handling.

        Args:
            sales_receipt_data: Sales receipt data dictionary

        Returns:
            Created sales receipt data if successful, or error details
        """
        if not self.auth_service.is_token_valid():
            logger.warning("Not authenticated with QBO")
            return {"error": True, "message": "Not authenticated with QBO"}

        try:
            response = self._make_qbo_request("POST", "salesreceipt", data=sales_receipt_data)
            return response.get("SalesReceipt")

        except QBOAPIException as e:
            # Parse the QBO error to provide actionable information
            error_data = {
                "error": True,
                "message": e.user_message or str(e),
                "detail": e.response_text,
            }

            # Try to parse specific error types
            if e.response_text:
                try:
                    import json

                    error_json = json.loads(e.response_text)
                    error_data.update(self._parse_qbo_error(error_json))
                except Exception:
                    pass

            logger.error(f"Error creating sales receipt: {error_data}")
            return error_data

        except Exception as e:
            logger.error(f"Exception in create_sales_receipt: {str(e)}")
            import traceback

            traceback.print_exc()
            return {"error": True, "message": str(e)}

    def _parse_qbo_error(self, error_json: Dict[str, Any]) -> Dict[str, Any]:
        """Parse QBO error response to extract actionable information.

        Args:
            error_json: Error response from QBO API

        Returns:
            Dictionary with parsed error information
        """
        error_data = {}

        if "Fault" in error_json:
            # Get error details from response
            errors = error_json["Fault"].get("Error", [])
            if isinstance(errors, dict):
                errors = [errors]

            if errors:
                error = errors[0]
                error_detail = error.get("Detail", "")
                error_message = error.get("Message", "")
                error_code = error.get("code", "")

                error_data["detail"] = error_detail
                error_data["message"] = error_message
                error_data["code"] = error_code

                # Check for specific reference errors
                if "Invalid Reference Id" in error_message:
                    # Account reference errors
                    if "Accounts element id" in error_detail or "Account id" in error_detail:
                        account_match = re.search(r"Accounts element id (\d+)", error_detail)
                        if not account_match:
                            account_match = re.search(r"Account id (\d+)", error_detail)

                        if account_match:
                            account_id = account_match.group(1)
                            error_data["setupType"] = "account"
                            error_data["invalidId"] = account_id
                            error_data["requiresSetup"] = True
                            logger.info(f"Detected invalid account reference: {account_id}")

                    # Item reference errors
                    elif (
                        "Item elements id" in error_detail
                        or "Item elements Id" in error_detail
                        or "Item id" in error_detail
                    ):
                        item_match = re.search(r"Item elements id (\d+)", error_detail)
                        if not item_match:
                            item_match = re.search(r"Item elements Id (\d+)", error_detail)
                        if not item_match:
                            item_match = re.search(r"Item id (\d+)", error_detail)

                        if item_match:
                            item_id = item_match.group(1)
                            error_data["setupType"] = "item"
                            error_data["invalidId"] = item_id
                            error_data["requiresSetup"] = True
                            logger.info(f"Detected invalid item reference: {item_id}")

                    # Payment method reference errors
                    elif "PaymentMethod id" in error_detail:
                        payment_method_match = re.search(r"PaymentMethod id (\w+)", error_detail)
                        payment_method_id = payment_method_match.group(1) if payment_method_match else "CHECK"

                        error_data["setupType"] = "paymentMethod"
                        error_data["invalidId"] = payment_method_id
                        error_data["requiresSetup"] = True
                        logger.info(f"Detected invalid payment method reference: {payment_method_id}")

                # Handle validation errors (non-reference errors)
                elif "Object is not valid" in error_message:
                    error_data["validationError"] = True
                    # Try to extract the validation details
                    validation_details = []
                    if "Object validation failed" in error_detail:
                        # Parse validation failures
                        validation_lines = error_detail.split("\n")
                        for line in validation_lines:
                            if ":" in line and line.strip():
                                validation_details.append(line.strip())

                    error_data["validationDetails"] = validation_details
                    logger.info(f"Detected validation error: {validation_details}")

                # Check for duplicate document number
                elif "Duplicate" in error_message and "DocNumber" in error_detail:
                    error_data["duplicateError"] = True
                    error_data["duplicateField"] = "DocNumber"
                    logger.info("Detected duplicate document number error")

        return error_data
