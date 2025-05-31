"""
Payment combiner V2 that works directly with PaymentRecord objects.
Creates the final JSON structure without using legacy format.
"""

import logging
from typing import Any, Dict, Optional

from models.payment import PaymentRecord

from .check_normalizer import normalize_check_number
from .qbo_data_enrichment import QBODataEnrichment, normalize_zip

logger = logging.getLogger(__name__)


class PaymentCombinerV2:
    """Service for combining PaymentRecord with QBO data into final format."""

    def __init__(self, qbo_enrichment: Optional[QBODataEnrichment] = None):
        """Initialize the payment combiner.

        Args:
            qbo_enrichment: Optional QBO enrichment service instance
        """
        self.qbo_enrichment = qbo_enrichment or QBODataEnrichment()

    def combine_payment_data(
        self, payment_record: PaymentRecord, qbo_customer: Optional[Dict[str, Any]] = None, match_status: str = "New"
    ) -> Dict[str, Any]:
        """Combine PaymentRecord with QBO customer data.

        Args:
            payment_record: PaymentRecord object from extraction
            qbo_customer: QBO customer data if matched
            match_status: Customer match status

        Returns:
            Combined payment data in final format
        """
        # Extract payment info
        payment_info = self._extract_payment_info(payment_record)

        # Extract and enrich payer info
        payer_info = self._extract_payer_info(payment_record, qbo_customer)

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

        # Add match details if available
        if qbo_customer:
            combined["match_method"] = "alias_matching"
            combined["match_confidence"] = "high"

        return combined

    def _extract_payment_info(self, payment_record: PaymentRecord) -> Dict[str, Any]:
        """Extract payment information from PaymentRecord.

        Args:
            payment_record: PaymentRecord object

        Returns:
            Payment info in final format
        """
        payment = payment_record.payment_info

        # Determine check number or payment reference and normalize
        check_no_or_ref = normalize_check_number(payment.check_no) or payment.payment_ref or ""

        # Use payment_date if available, otherwise check_date
        payment_date = payment.payment_date or payment.check_date or ""

        return {
            "check_no_or_payment_ref": check_no_or_ref,
            "amount": payment.amount,
            "payment_date": payment_date,
            "deposit_date": payment.deposit_date or "",
            "deposit_method": payment.deposit_method or "ATM Deposit",
            "memo": payment.memo or "",
        }

    def _extract_payer_info(
        self, payment_record: PaymentRecord, qbo_customer: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Extract and combine payer information.

        Args:
            payment_record: PaymentRecord object
            qbo_customer: QBO customer data if available

        Returns:
            Payer info in final format
        """
        payer = payment_record.payer_info
        contact = payment_record.contact_info

        # Start with extracted data
        extracted_address = {
            "line_1": contact.address_line_1 or "",
            "city": contact.city or "",
            "state": contact.state or "",
            "zip": normalize_zip(contact.zip or ""),
        }

        if qbo_customer:
            # Extract QBO customer data
            qbo_data = self.qbo_enrichment.extract_qbo_customer_data(qbo_customer)

            # Compare addresses
            address_comparison = self.qbo_enrichment.compare_addresses(extracted_address, qbo_data)

            # Handle email/phone updates
            email_phone_result = self.qbo_enrichment.merge_email_phone_lists(
                contact.email, contact.phone, qbo_data.get("qb_email", []), qbo_data.get("qb_phone", [])
            )

            # Determine customer lookup name
            # For matched customers, use QBO display name
            customer_lookup = qbo_data.get("customer_lookup", "")

            # Build payer info with QBO data
            payer_info = {
                "customer_lookup": customer_lookup,
                "salutation": payer.salutation or "",
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

            # Add update flags and details
            if address_comparison["address_needs_update"]:
                payer_info["address_differences"] = address_comparison["differences"]

            if email_phone_result["email_added"]:
                payer_info["email_updated"] = True

            if email_phone_result["phone_added"]:
                payer_info["phone_updated"] = True

        else:
            # No QBO match - use extracted data
            # Determine customer lookup from aliases or organization
            if payer.organization_name:
                customer_lookup = payer.organization_name
            elif payer.aliases and len(payer.aliases) > 0:
                # Use the most complete alias as customer lookup
                customer_lookup = payer.aliases[0]
            else:
                customer_lookup = ""

            payer_info = {
                "customer_lookup": customer_lookup,
                "salutation": payer.salutation or "",
                "first_name": "",  # Will be populated when customer is created
                "last_name": "",
                "full_name": customer_lookup,
                "qb_organization_name": payer.organization_name or "",
                "qb_address_line_1": extracted_address["line_1"],
                "qb_city": extracted_address["city"],
                "qb_state": extracted_address["state"],
                "qb_zip": extracted_address["zip"],
                "qb_email": [contact.email] if contact.email else [],
                "qb_phone": [contact.phone] if contact.phone else [],
                "address_needs_update": False,
                "extracted_address": extracted_address,
            }

        return payer_info
