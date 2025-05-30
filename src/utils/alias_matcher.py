"""
Alias-based customer matching service for the refactored workflow.
Matches payments to QBO customers using the aliases list.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from ..models.payment import PaymentRecord

logger = logging.getLogger(__name__)


class AliasMatcher:
    """Service for matching payments to customers using aliases."""

    def __init__(self, qbo_service):
        """Initialize with QBO service.

        Args:
            qbo_service: QBO service instance for customer lookups
        """
        self.qbo_service = qbo_service

    def match_payment_batch(
        self, payment_records: List[PaymentRecord]
    ) -> List[Tuple[PaymentRecord, Optional[Dict[str, Any]]]]:
        """Match a batch of payments to QBO customers using aliases.

        Args:
            payment_records: List of PaymentRecord objects to match

        Returns:
            List of tuples (PaymentRecord, matched_customer or None)
        """
        if not self.qbo_service:
            logger.warning("QBO service not available - returning unmatched payments")
            return [(record, None) for record in payment_records]

        logger.info(f"Matching {len(payment_records)} payments using aliases")

        # Preload customer cache for performance
        try:
            all_customers = self.qbo_service.get_all_customers(use_cache=True)
            logger.info(f"Loaded {len(all_customers)} customers from QBO")
        except Exception as e:
            logger.error(f"Failed to load customer cache: {e}")
            all_customers = []

        # Match each payment
        results = []
        for payment in payment_records:
            matched_customer = self._match_single_payment(payment, all_customers)
            results.append((payment, matched_customer))

        # Log summary
        matched_count = sum(1 for _, customer in results if customer is not None)
        logger.info(f"Matched {matched_count} of {len(payment_records)} payments")

        return results

    def _match_single_payment(
        self, payment: PaymentRecord, all_customers: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Match a single payment to a customer using aliases.

        Args:
            payment: PaymentRecord to match
            all_customers: List of all QBO customers

        Returns:
            Matched customer dict or None
        """
        payer_info = payment.payer_info

        # For organizations, try exact match on organization name
        if payer_info.organization_name:
            logger.debug(f"Matching organization: {payer_info.organization_name}")
            for customer in all_customers:
                if self._match_organization(payer_info.organization_name, customer):
                    logger.info(
                        f"Matched organization '{payer_info.organization_name}' to customer '{customer.get('DisplayName')}'"
                    )
                    return customer

        # For individuals, try each alias
        elif payer_info.aliases:
            logger.debug(f"Matching individual with aliases: {payer_info.aliases}")
            for alias in payer_info.aliases:
                for customer in all_customers:
                    if self._match_alias(alias, customer):
                        logger.info(f"Matched alias '{alias}' to customer '{customer.get('DisplayName')}'")
                        return customer

        # Also try matching by email or phone if available
        contact_info = payment.contact_info

        if contact_info.email:
            logger.debug(f"Trying email match: {contact_info.email}")
            for customer in all_customers:
                if self._match_email(contact_info.email, customer):
                    logger.info(f"Matched email '{contact_info.email}' to customer '{customer.get('DisplayName')}'")
                    return customer

        if contact_info.phone:
            logger.debug(f"Trying phone match: {contact_info.phone}")
            for customer in all_customers:
                if self._match_phone(contact_info.phone, customer):
                    logger.info(f"Matched phone '{contact_info.phone}' to customer '{customer.get('DisplayName')}'")
                    return customer

        logger.debug(f"No match found for payment")
        return None

    def _match_organization(self, org_name: str, customer: Dict[str, Any]) -> bool:
        """Check if organization name matches customer.

        Args:
            org_name: Organization name from payment
            customer: QBO customer data

        Returns:
            True if match found
        """
        org_lower = org_name.lower().strip()

        # Check company name
        company_name = customer.get("CompanyName", "").lower().strip()
        if company_name and (org_lower == company_name or org_lower in company_name or company_name in org_lower):
            return True

        # Check display name
        display_name = customer.get("DisplayName", "").lower().strip()
        if org_lower == display_name or org_lower in display_name or display_name in org_lower:
            return True

        return False

    def _match_alias(self, alias: str, customer: Dict[str, Any]) -> bool:
        """Check if alias matches customer using smart matching.

        Args:
            alias: Name alias from payment
            customer: QBO customer data

        Returns:
            True if match found
        """
        alias_lower = alias.lower().strip()

        # Extract last name from alias
        alias_last = self._extract_last_name(alias)

        # Extract last name from customer
        customer_last = customer.get("FamilyName", "").lower().strip()

        # Check last name match
        if alias_last and customer_last and alias_last == customer_last:
            # Last names match - that's a good start
            # But we need more evidence for a match
            display_name = customer.get("DisplayName", "").lower()

            # Check if the full alias appears in display name
            if alias_lower in display_name:
                return True

            # For single last name aliases (e.g., "Lang"),
            # only match if it's the only name part
            alias_parts = alias.split()
            if len(alias_parts) == 1:
                # Single name - be more strict
                # Only match if customer has same single last name
                customer_parts = customer.get("DisplayName", "").split()
                if len(customer_parts) == 1 and customer_parts[0].lower() == alias_lower:
                    return True
            else:
                # Multi-part name - check if structure matches
                # "Lang, J." should match "Lang, John D. & Esther A."
                if "," in alias and "," in customer.get("DisplayName", ""):
                    return True

        # Check exact display name match
        display_name = customer.get("DisplayName", "").lower().strip()
        if alias_lower == display_name:
            return True

        # Check if alias is contained in display name
        # This helps with "Smith" matching "Smith, John and Jane"
        if len(alias_lower) > 2 and alias_lower in display_name:
            return True

        return False

    def _extract_last_name(self, name: str) -> str:
        """Extract last name from a name string.

        Args:
            name: Full name string

        Returns:
            Extracted last name (lowercase)
        """
        name = name.strip()

        # Handle "Last, First" format
        if "," in name:
            return name.split(",")[0].strip().lower()

        # Handle "First Last" format
        parts = name.split()
        if len(parts) >= 2:
            return parts[-1].lower()
        elif len(parts) == 1:
            # Single name - could be last name
            return parts[0].lower()

        return ""

    def _match_email(self, email: str, customer: Dict[str, Any]) -> bool:
        """Check if email matches customer.

        Args:
            email: Email from payment
            customer: QBO customer data

        Returns:
            True if match found
        """
        email_lower = email.lower().strip()

        # Check primary email
        primary_email = customer.get("PrimaryEmailAddr", {})
        if primary_email and primary_email.get("Address", "").lower().strip() == email_lower:
            return True

        return False

    def _match_phone(self, phone: str, customer: Dict[str, Any]) -> bool:
        """Check if phone matches customer.

        Args:
            phone: Phone from payment
            customer: QBO customer data

        Returns:
            True if match found
        """
        # Normalize phone for comparison (digits only)
        phone_digits = "".join(c for c in phone if c.isdigit())

        # Check primary phone
        primary_phone = customer.get("PrimaryPhone", {})
        if primary_phone:
            customer_phone = primary_phone.get("FreeFormNumber", "")
            customer_digits = "".join(c for c in customer_phone if c.isdigit())
            if phone_digits == customer_digits:
                return True

        # Check mobile phone
        mobile_phone = customer.get("Mobile", {})
        if mobile_phone:
            customer_phone = mobile_phone.get("FreeFormNumber", "")
            customer_digits = "".join(c for c in customer_phone if c.isdigit())
            if phone_digits == customer_digits:
                return True

        return False
