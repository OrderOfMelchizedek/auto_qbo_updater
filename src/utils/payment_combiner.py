"""
Service for combining extracted payment data with QBO customer data.
Creates the final JSON structure for UI display.
"""

import logging
from typing import Any, Dict, List, Optional, Union

from .qbo_data_enrichment import QBODataEnrichment, normalize_zip

logger = logging.getLogger(__name__)


class PaymentCombiner:
    """Service for combining payment and QBO data into final format."""

    def __init__(self, qbo_enrichment: Optional[QBODataEnrichment] = None):
        """Initialize the payment combiner.

        Args:
            qbo_enrichment: Optional QBO enrichment service instance
        """
        self.qbo_enrichment = qbo_enrichment or QBODataEnrichment()

    def combine_payment_data(
        self,
        extracted_payment: Dict[str, Any],
        qbo_customer: Optional[Dict[str, Any]] = None,
        match_status: str = "New",
    ) -> Dict[str, Any]:
        """Combine extracted payment data with QBO customer data.

        Args:
            extracted_payment: Payment data from extraction (legacy format)
            qbo_customer: QBO customer data if matched
            match_status: Customer match status

        Returns:
            Combined payment data in final format
        """
        # Extract payment info
        payment_info = self._extract_payment_info(extracted_payment)

        # Extract payer info
        payer_info = self._extract_payer_info(extracted_payment, qbo_customer)

        # Combine into final structure
        combined = {
            "payer_info": payer_info,
            "payment_info": payment_info,
            "match_status": match_status,
            "qbo_customer_id": qbo_customer.get("Id") if qbo_customer else None,
        }

        # Add sync token if updating existing customer
        if qbo_customer and qbo_customer.get("SyncToken"):
            combined["qbo_sync_token"] = qbo_customer.get("SyncToken")

        return combined

    def _extract_payment_info(self, payment: Dict[str, Any]) -> Dict[str, Any]:
        """Extract payment information from legacy format.

        Args:
            payment: Payment data in legacy format

        Returns:
            Payment info in new format
        """
        # Determine check number or payment reference
        check_no_or_ref = payment.get("Check No.") or payment.get("Payment Ref") or ""

        # Extract amount, handling various formats
        amount_str = payment.get("Gift Amount", "0")
        try:
            amount = float(str(amount_str).replace("$", "").replace(",", ""))
        except ValueError:
            amount = 0.0

        # Determine payment date (prefer Check Date, fall back to Deposit Date)
        payment_date = payment.get("Check Date") or payment.get("Deposit Date") or ""

        return {
            "check_no_or_payment_ref": check_no_or_ref,
            "amount": amount,
            "payment_date": payment_date,
            "deposit_date": payment.get("Deposit Date", ""),
            "deposit_method": payment.get("Deposit Method", "ATM Deposit"),
            "memo": payment.get("Memo", ""),
        }

    def _extract_payer_info(self, payment: Dict[str, Any], qbo_customer: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract and combine payer information.

        Args:
            payment: Payment data in legacy format
            qbo_customer: QBO customer data if available

        Returns:
            Payer info in new format
        """
        # Start with extracted data
        extracted_address = {
            "line_1": payment.get("Address - Line 1", ""),
            "city": payment.get("City", ""),
            "state": payment.get("State", ""),
            "zip": normalize_zip(payment.get("ZIP", "")),
        }

        if qbo_customer:
            # Extract QBO customer data
            qbo_data = self.qbo_enrichment.extract_qbo_customer_data(qbo_customer)

            # Compare addresses
            address_comparison = self.qbo_enrichment.compare_addresses(extracted_address, qbo_data)

            # Handle email/phone updates
            extracted_email = payment.get("Email", "")
            extracted_phone = payment.get("Phone", "")
            email_phone_result = self.qbo_enrichment.merge_email_phone_lists(
                extracted_email, extracted_phone, qbo_data.get("qb_email", []), qbo_data.get("qb_phone", [])
            )

            # Build payer info with QBO data
            payer_info = {
                "customer_lookup": qbo_data.get("customer_lookup", ""),
                "salutation": payment.get("Salutation", ""),
                "first_name": qbo_data.get("first_name", ""),
                "last_name": qbo_data.get("last_name", ""),
                "full_name": qbo_data.get("full_name", ""),
                "qb_organization_name": qbo_data.get("qb_organization_name", ""),
                "qb_address_line_1": qbo_data.get("qb_address_line_1", ""),
                "qb_city": qbo_data.get("qb_city", ""),
                "qb_state": qbo_data.get("qb_state", ""),
                "qb_zip": qbo_data.get("qb_zip", ""),
                "qb_email": email_phone_result["emails"],
                "qb_phone": email_phone_result["phones"],
                "address_needs_update": address_comparison["address_needs_update"],
                "extracted_address": extracted_address,
            }

            # Add update flags
            if address_comparison["address_needs_update"]:
                payer_info["address_differences"] = address_comparison["differences"]

            if email_phone_result["email_added"]:
                payer_info["email_updated"] = True

            if email_phone_result["phone_added"]:
                payer_info["phone_updated"] = True

        else:
            # No QBO match - use extracted data
            payer_info = {
                "customer_lookup": payment.get("Donor Name", ""),
                "salutation": payment.get("Salutation", ""),
                "first_name": payment.get("First Name", ""),
                "last_name": payment.get("Last Name", ""),
                "full_name": payment.get("Donor Name", ""),
                "qb_organization_name": payment.get("Organization Name", ""),
                "qb_address_line_1": extracted_address["line_1"],
                "qb_city": extracted_address["city"],
                "qb_state": extracted_address["state"],
                "qb_zip": extracted_address["zip"],
                "qb_email": [payment.get("Email")] if payment.get("Email") else [],
                "qb_phone": [payment.get("Phone")] if payment.get("Phone") else [],
                "address_needs_update": False,
                "extracted_address": extracted_address,
            }

        return payer_info

    def process_batch(self, payments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process a batch of payments, combining with QBO data.

        Args:
            payments: List of payment dictionaries with QBO matching already done

        Returns:
            List of combined payment data
        """
        combined_payments = []

        for payment in payments:
            # Get match status
            match_status = payment.get("qbCustomerStatus", "New")

            # Get QBO customer if matched
            qbo_customer = None
            if match_status in ["Matched", "Matched-AddressMismatch", "Matched-AddressNeedsReview"]:
                # Customer data should be embedded in payment from matching process
                # Extract it from the payment data
                qbo_customer = self._extract_embedded_qbo_data(payment)

            # Combine data
            combined = self.combine_payment_data(payment, qbo_customer, match_status)

            # Preserve any additional fields from matching
            if payment.get("matchMethod"):
                combined["match_method"] = payment.get("matchMethod")
            if payment.get("matchConfidence"):
                combined["match_confidence"] = payment.get("matchConfidence")

            combined_payments.append(combined)

        return combined_payments

    def _extract_embedded_qbo_data(self, payment: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract embedded QBO customer data from matched payment.

        Args:
            payment: Payment with embedded QBO data

        Returns:
            QBO customer data or None
        """
        # Check if QBO data is embedded
        if not payment.get("qboCustomerId"):
            return None

        # Reconstruct QBO customer object from embedded data
        qbo_customer = {
            "Id": payment.get("qboCustomerId"),
            "DisplayName": payment.get("customerLookup", ""),
            "SyncToken": payment.get("qboSyncToken"),
        }

        # Add address if available
        if payment.get("qboAddress"):
            qbo_addr = payment["qboAddress"]
            qbo_customer["BillAddr"] = {
                "Line1": qbo_addr.get("Line1", ""),
                "City": qbo_addr.get("City", ""),
                "CountrySubDivisionCode": qbo_addr.get("State", ""),
                "PostalCode": qbo_addr.get("ZIP", ""),
            }

        # Note: Full customer data would need to be fetched from QBO
        # This is a placeholder structure
        return qbo_customer

    def convert_to_legacy_format(self, combined_payment: Dict[str, Any]) -> Dict[str, Any]:
        """Convert combined payment format back to legacy format for backward compatibility.

        Args:
            combined_payment: Payment in combined format

        Returns:
            Payment in legacy format
        """
        payer_info = combined_payment.get("payer_info", {})
        payment_info = combined_payment.get("payment_info", {})

        # Build legacy format
        legacy = {
            # Donor/customer fields
            "Donor Name": payer_info.get("customer_lookup", ""),
            "customerLookup": payer_info.get("customer_lookup", ""),
            "First Name": payer_info.get("first_name", ""),
            "Last Name": payer_info.get("last_name", ""),
            "Organization Name": payer_info.get("qb_organization_name", ""),
            "Salutation": payer_info.get("salutation", ""),
            # Address fields - use QBO address if available, else extracted
            "Address - Line 1": payer_info.get("qb_address_line_1")
            or payer_info.get("extracted_address", {}).get("line_1", ""),
            "City": payer_info.get("qb_city") or payer_info.get("extracted_address", {}).get("city", ""),
            "State": payer_info.get("qb_state") or payer_info.get("extracted_address", {}).get("state", ""),
            "ZIP": payer_info.get("qb_zip") or payer_info.get("extracted_address", {}).get("zip", ""),
            # Contact fields - use first from lists
            "Email": payer_info.get("qb_email", [""])[0] if payer_info.get("qb_email") else "",
            "Phone": payer_info.get("qb_phone", [""])[0] if payer_info.get("qb_phone") else "",
            # Payment fields
            "Check No.": payment_info.get("check_no_or_payment_ref", ""),
            "Gift Amount": str(payment_info.get("amount", 0)),
            "Check Date": payment_info.get("payment_date", ""),
            "Deposit Date": payment_info.get("deposit_date", ""),
            "Deposit Method": payment_info.get("deposit_method", ""),
            "Memo": payment_info.get("memo", ""),
            # QBO fields
            "qboCustomerId": combined_payment.get("qbo_customer_id"),
            "qbCustomerStatus": combined_payment.get("match_status", "New"),
            "matchMethod": combined_payment.get("match_method"),
            "matchConfidence": combined_payment.get("match_confidence"),
            # Add enrichment flags
            "addressNeedsUpdate": payer_info.get("address_needs_update", False),
            "emailUpdated": payer_info.get("email_updated", False),
            "phoneUpdated": payer_info.get("phone_updated", False),
        }

        # Add internal ID if needed
        if "internalId" not in legacy:
            import uuid

            legacy["internalId"] = str(uuid.uuid4())

        return legacy

    def process_batch_legacy_output(self, payments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process batch but return in legacy format for backward compatibility.

        Args:
            payments: List of payment dictionaries

        Returns:
            List of payments in legacy format
        """
        # First process to combined format
        combined_payments = self.process_batch(payments)

        # Then convert each back to legacy
        legacy_payments = []
        for combined in combined_payments:
            legacy = self.convert_to_legacy_format(combined)
            legacy_payments.append(legacy)

        return legacy_payments
