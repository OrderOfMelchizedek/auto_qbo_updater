"""
Customer matching and data merging service for combining extracted data with QuickBooks customer data.
"""

import logging
import re
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

from src.models.payment import ContactInfo, PayerInfo, PaymentRecord
from src.models.qbo_customer import AddressComparison, ContactUpdate, CustomerMatchResult, QBCustomer
from src.models.ui_models import UIPayerInfo, UIPaymentInfo, UIPaymentRecord
from utils.qbo_service.customers import QBOCustomerService

logger = logging.getLogger(__name__)


class CustomerMatcher:
    """Service for matching extracted payment data with QuickBooks customers."""

    def __init__(self, qbo_customer_service: QBOCustomerService):
        """Initialize with QBO customer service.

        Args:
            qbo_customer_service: Service for interacting with QBO customers
        """
        self.qbo_service = qbo_customer_service

    def match_and_merge_payment(self, payment_record: PaymentRecord) -> UIPaymentRecord:
        """Match payment record with QBO customer and merge data for UI.

        Args:
            payment_record: Extracted payment record

        Returns:
            UIPaymentRecord with merged data ready for UI display
        """
        try:
            # Attempt to match customer
            match_result = self._match_customer(payment_record.payer_info)

            if match_result.matched and match_result.qb_customer:
                # Customer found - merge and update as needed
                ui_payer_info = self._merge_customer_data(
                    payment_record.payer_info, payment_record.contact_info, match_result.qb_customer
                )
                ui_payer_info.is_matched = True
                ui_payer_info.match_confidence = match_result.confidence_score

            else:
                # No match found - prepare for new customer creation
                ui_payer_info = self._prepare_new_customer_data(payment_record.payer_info, payment_record.contact_info)
                ui_payer_info.is_new_customer = True

            # Convert payment info
            ui_payment_info = self._convert_payment_info(payment_record.payment_info)

            # Create UI record
            ui_record = UIPaymentRecord(
                payer_info=ui_payer_info,
                payment_info=ui_payment_info,
                processing_status="processed",
                extraction_source=payment_record.source_document_type or "unknown",
            )

            return ui_record

        except Exception as e:
            logger.error(f"Error matching and merging payment: {e}")
            # Return basic UI record with error status
            return self._create_error_record(payment_record, str(e))

    def _match_customer(self, payer_info: PayerInfo) -> CustomerMatchResult:
        """Match payer information against QBO customers.

        Args:
            payer_info: Extracted payer information

        Returns:
            CustomerMatchResult with match details
        """
        try:
            # Get all QBO customers for matching
            qbo_customers = self.qbo_service.get_all_customers()

            if not qbo_customers:
                return CustomerMatchResult(
                    matched=False, confidence_score=0.0, match_method="no_customers_available", needs_new_customer=True
                )

            best_match = None
            best_score = 0.0
            alternatives = []

            # Prepare search terms from payer info
            search_terms = self._prepare_search_terms(payer_info)

            for customer in qbo_customers:
                score = self._calculate_match_score(search_terms, customer)

                if score > 0.5:  # Potential match
                    if score > best_score:
                        if best_match:
                            alternatives.append(best_match)
                        best_match = customer
                        best_score = score
                    else:
                        alternatives.append(customer)

            # Determine if match is strong enough
            matched = best_score >= 0.75
            match_method = "name_fuzzy_match" if matched else "no_strong_match"

            return CustomerMatchResult(
                matched=matched,
                confidence_score=best_score,
                qb_customer=best_match,
                match_method=match_method,
                alternatives=alternatives[:3],  # Top 3 alternatives
                needs_new_customer=not matched,
            )

        except Exception as e:
            logger.error(f"Error during customer matching: {e}")
            return CustomerMatchResult(
                matched=False, confidence_score=0.0, match_method="error", needs_new_customer=True
            )

    def _prepare_search_terms(self, payer_info: PayerInfo) -> List[str]:
        """Prepare search terms from payer information.

        Args:
            payer_info: Payer information

        Returns:
            List of search terms
        """
        terms = []

        # Add organization name if available
        if payer_info.organization_name:
            terms.append(payer_info.organization_name.strip().lower())

        # Add aliases if available
        if payer_info.aliases:
            for alias in payer_info.aliases:
                if alias and alias.strip():
                    terms.append(alias.strip().lower())

        return terms

    def _calculate_match_score(self, search_terms: List[str], customer: dict) -> float:
        """Calculate match score between search terms and QBO customer.

        Args:
            search_terms: Terms to search for
            customer: QBO customer data

        Returns:
            Match score between 0.0 and 1.0
        """
        if not search_terms:
            return 0.0

        # Prepare customer comparison terms
        customer_terms = []

        # Add customer name fields
        for field in ["name", "full_name", "display_name", "company_name"]:
            if field in customer and customer[field]:
                customer_terms.append(customer[field].lower())

        # Add first/last name combination
        first_name = customer.get("given_name", "") or customer.get("first_name", "")
        last_name = customer.get("family_name", "") or customer.get("last_name", "")
        if first_name and last_name:
            customer_terms.append(f"{first_name} {last_name}".lower())
            customer_terms.append(f"{last_name}, {first_name}".lower())

        if not customer_terms:
            return 0.0

        # Calculate best match score
        max_score = 0.0

        for search_term in search_terms:
            for customer_term in customer_terms:
                # Exact match gets highest score
                if search_term == customer_term:
                    return 1.0

                # Fuzzy match using sequence matcher
                score = SequenceMatcher(None, search_term, customer_term).ratio()

                # Bonus for last name matches (common for family donations)
                search_parts = search_term.split()
                customer_parts = customer_term.split()
                if len(search_parts) > 1 and len(customer_parts) > 1:
                    if search_parts[-1] == customer_parts[-1]:  # Last names match
                        score += 0.2

                max_score = max(max_score, score)

        return min(max_score, 1.0)  # Cap at 1.0

    def _merge_customer_data(self, payer_info: PayerInfo, contact_info: ContactInfo, qb_customer: dict) -> UIPayerInfo:
        """Merge extracted data with QBO customer data.

        Args:
            payer_info: Extracted payer information
            contact_info: Extracted contact information
            qb_customer: QBO customer data

        Returns:
            UIPayerInfo with merged data
        """
        # Start with QB customer data
        ui_payer = UIPayerInfo(
            customer_lookup=str(qb_customer.get("id", "")),
            first_name=qb_customer.get("given_name") or qb_customer.get("first_name"),
            last_name=qb_customer.get("family_name") or qb_customer.get("last_name"),
            full_name=qb_customer.get("name") or qb_customer.get("display_name"),
            qb_organization_name=qb_customer.get("company_name"),
            qb_address_line_1=self._get_qb_address_field(qb_customer, "line1"),
            qb_city=self._get_qb_address_field(qb_customer, "city"),
            qb_state=self._get_qb_address_field(qb_customer, "state"),
            qb_zip=self._get_qb_address_field(qb_customer, "postal_code"),
            qb_email=self._get_qb_email(qb_customer),
            qb_phone=self._get_qb_phone(qb_customer),
        )

        # Add salutation from extracted data if not in QB
        if payer_info.salutation and not ui_payer.salutation:
            ui_payer.salutation = payer_info.salutation

        # Check for address updates
        address_comparison = self._compare_addresses(contact_info, qb_customer)
        if address_comparison.needs_update:
            ui_payer.qb_address_line_1 = contact_info.address_line_1
            ui_payer.qb_city = contact_info.city
            ui_payer.qb_state = contact_info.state
            ui_payer.qb_zip = contact_info.zip
            ui_payer.address_updated = True

        # Check for contact updates
        contact_updates = self._check_contact_updates(contact_info, qb_customer)
        if contact_updates.email_updates:
            # Add new emails
            current_emails = ui_payer.qb_email
            if isinstance(current_emails, str):
                ui_payer.qb_email = [current_emails] + contact_updates.email_updates
            elif isinstance(current_emails, list):
                ui_payer.qb_email = current_emails + contact_updates.email_updates
            else:
                ui_payer.qb_email = contact_updates.email_updates
            ui_payer.contact_updated = True

        if contact_updates.phone_updates:
            # Add new phones
            current_phones = ui_payer.qb_phone
            if isinstance(current_phones, str):
                ui_payer.qb_phone = [current_phones] + contact_updates.phone_updates
            elif isinstance(current_phones, list):
                ui_payer.qb_phone = current_phones + contact_updates.phone_updates
            else:
                ui_payer.qb_phone = contact_updates.phone_updates
            ui_payer.contact_updated = True

        return ui_payer

    def _compare_addresses(self, extracted_contact: ContactInfo, qb_customer: dict) -> AddressComparison:
        """Compare extracted address with QB customer address.

        Args:
            extracted_contact: Extracted contact information
            qb_customer: QB customer data

        Returns:
            AddressComparison result
        """
        qb_address = self._get_qb_address_field(qb_customer, "line1") or ""
        extracted_address = extracted_contact.address_line_1 or ""

        if not extracted_address:
            # No extracted address to compare
            return AddressComparison(
                needs_update=False, similarity_score=1.0, differences=[], recommended_action="no_change"
            )

        if not qb_address:
            # QB has no address, use extracted
            return AddressComparison(
                needs_update=True,
                similarity_score=0.0,
                differences=["QB address is empty"],
                recommended_action="update_with_extracted",
            )

        # Calculate similarity
        similarity = SequenceMatcher(None, extracted_address.lower(), qb_address.lower()).ratio()

        # Check character difference threshold (>50% different)
        needs_update = similarity < 0.5

        differences = []
        if needs_update:
            differences.append(f"Address differs significantly: QB='{qb_address}' vs Extracted='{extracted_address}'")

        return AddressComparison(
            needs_update=needs_update,
            similarity_score=similarity,
            differences=differences,
            recommended_action="update_with_extracted" if needs_update else "keep_qb_address",
        )

    def _check_contact_updates(self, extracted_contact: ContactInfo, qb_customer: dict) -> ContactUpdate:
        """Check if contact information needs updates.

        Args:
            extracted_contact: Extracted contact information
            qb_customer: QB customer data

        Returns:
            ContactUpdate with recommended changes
        """
        email_updates = []
        phone_updates = []
        update_reason = ""

        # Check email
        qb_email = self._get_qb_email(qb_customer)
        extracted_email = extracted_contact.email

        if extracted_email:
            extracted_email = extracted_email.strip().lower()

            if not qb_email:
                # No QB email, add extracted
                email_updates.append(extracted_email)
                update_reason += "Added email (QB had none). "
            else:
                # Check if extracted email is different
                qb_emails = [qb_email] if isinstance(qb_email, str) else qb_email
                qb_emails_lower = [email.lower() for email in qb_emails]

                if extracted_email not in qb_emails_lower:
                    email_updates.append(extracted_email)
                    update_reason += "Added new email address. "

        # Check phone
        qb_phone = self._get_qb_phone(qb_customer)
        extracted_phone = extracted_contact.phone

        if extracted_phone:
            # Clean phone numbers for comparison
            extracted_clean = re.sub(r"[^\d]", "", extracted_phone)

            if not qb_phone:
                # No QB phone, add extracted
                phone_updates.append(extracted_phone)
                update_reason += "Added phone (QB had none). "
            else:
                # Check if extracted phone is different
                qb_phones = [qb_phone] if isinstance(qb_phone, str) else qb_phone
                qb_phones_clean = [re.sub(r"[^\d]", "", phone) for phone in qb_phones]

                if extracted_clean not in qb_phones_clean:
                    phone_updates.append(extracted_phone)
                    update_reason += "Added new phone number. "

        return ContactUpdate(
            email_updates=email_updates if email_updates else None,
            phone_updates=phone_updates if phone_updates else None,
            update_reason=update_reason.strip(),
        )

    def _prepare_new_customer_data(self, payer_info: PayerInfo, contact_info: ContactInfo) -> UIPayerInfo:
        """Prepare data for creating a new customer.

        Args:
            payer_info: Extracted payer information
            contact_info: Extracted contact information

        Returns:
            UIPayerInfo for new customer
        """
        # Determine name fields
        full_name = None
        first_name = None
        last_name = None

        if payer_info.aliases and len(payer_info.aliases) > 0:
            full_name = payer_info.aliases[0]  # Use first alias as primary name
            # Try to parse first/last name
            name_parts = full_name.split()
            if len(name_parts) >= 2:
                first_name = name_parts[0]
                last_name = name_parts[-1]

        return UIPayerInfo(
            salutation=payer_info.salutation,
            first_name=first_name,
            last_name=last_name,
            full_name=full_name,
            qb_organization_name=payer_info.organization_name,
            qb_address_line_1=contact_info.address_line_1,
            qb_city=contact_info.city,
            qb_state=contact_info.state,
            qb_zip=contact_info.zip,
            qb_email=contact_info.email,
            qb_phone=contact_info.phone,
            is_new_customer=True,
        )

    def _convert_payment_info(self, payment_info) -> UIPaymentInfo:
        """Convert PaymentInfo to UIPaymentInfo.

        Args:
            payment_info: Extracted payment information

        Returns:
            UIPaymentInfo for UI display
        """
        check_no_or_ref = payment_info.check_no or payment_info.payment_ref or "Unknown"

        return UIPaymentInfo(
            check_no_or_payment_ref=check_no_or_ref,
            amount=payment_info.amount,
            payment_date=payment_info.payment_date or "Unknown",
            deposit_date=payment_info.deposit_date,
            deposit_method=payment_info.deposit_method,
            memo=payment_info.memo,
        )

    def _create_error_record(self, payment_record: PaymentRecord, error_msg: str) -> UIPaymentRecord:
        """Create UI record for error cases.

        Args:
            payment_record: Original payment record
            error_msg: Error message

        Returns:
            UIPaymentRecord with error status
        """
        # Create basic UI structures
        ui_payer = UIPayerInfo(full_name="Error processing payer", is_matched=False)

        ui_payment = UIPaymentInfo(
            check_no_or_payment_ref="Error",
            amount=payment_record.payment_info.amount if payment_record.payment_info else 0.0,
            payment_date="Unknown",
        )

        return UIPaymentRecord(
            payer_info=ui_payer,
            payment_info=ui_payment,
            processing_status="error",
            warnings=[f"Processing error: {error_msg}"],
        )

    def _get_qb_address_field(self, qb_customer: dict, field: str) -> Optional[str]:
        """Extract address field from QB customer data.

        Args:
            qb_customer: QB customer data
            field: Address field name

        Returns:
            Address field value or None
        """
        # Check various possible address structures in QB data
        for addr_key in ["billing_address", "address", "primary_address"]:
            if addr_key in qb_customer and qb_customer[addr_key]:
                addr = qb_customer[addr_key]
                if field in addr and addr[field]:
                    return addr[field]

        # Check direct fields
        direct_field_map = {
            "line1": ["address_line_1", "address1", "street"],
            "city": ["city"],
            "state": ["state", "state_code"],
            "postal_code": ["zip", "zip_code", "postal_code"],
        }

        for possible_field in direct_field_map.get(field, [field]):
            if possible_field in qb_customer and qb_customer[possible_field]:
                return qb_customer[possible_field]

        return None

    def _get_qb_email(self, qb_customer: dict) -> Optional[str]:
        """Extract email from QB customer data.

        Args:
            qb_customer: QB customer data

        Returns:
            Email address or None
        """
        for field in ["email", "primary_email", "email_address"]:
            if field in qb_customer and qb_customer[field]:
                return qb_customer[field]
        return None

    def _get_qb_phone(self, qb_customer: dict) -> Optional[str]:
        """Extract phone from QB customer data.

        Args:
            qb_customer: QB customer data

        Returns:
            Phone number or None
        """
        for field in ["phone", "primary_phone", "phone_number", "mobile"]:
            if field in qb_customer and qb_customer[field]:
                return qb_customer[field]
        return None
