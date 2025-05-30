"""
Service for enriching payment data with QuickBooks customer information.
Handles pulling all customer fields and comparing addresses.
"""

import logging
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class QBODataEnrichment:
    """Service for enriching payment data with QBO customer information."""

    @staticmethod
    def extract_qbo_customer_data(customer: Dict[str, Any]) -> Dict[str, Any]:
        """Extract all relevant customer data from QBO customer object.

        Args:
            customer: QBO customer object

        Returns:
            Dictionary with all QBO customer fields
        """
        # Extract billing address
        bill_addr = customer.get("BillAddr", {})

        # Extract email - handle both single and list formats
        email_data = customer.get("PrimaryEmailAddr", {})
        qb_email = []
        if email_data and email_data.get("Address"):
            qb_email.append(email_data.get("Address"))

        # Extract phone - handle both single and list formats
        phone_data = customer.get("PrimaryPhone", {})
        qb_phone = []
        if phone_data and phone_data.get("FreeFormNumber"):
            qb_phone.append(phone_data.get("FreeFormNumber"))

        # Add mobile phone if different
        mobile_data = customer.get("Mobile", {})
        if mobile_data and mobile_data.get("FreeFormNumber"):
            mobile_num = mobile_data.get("FreeFormNumber")
            if mobile_num not in qb_phone:
                qb_phone.append(mobile_num)

        return {
            "customer_lookup": customer.get("DisplayName", ""),
            "first_name": customer.get("GivenName", ""),
            "last_name": customer.get("FamilyName", ""),
            "full_name": customer.get("FullyQualifiedName", ""),
            "qb_organization_name": customer.get("CompanyName", ""),
            "qb_address_line_1": bill_addr.get("Line1", ""),
            "qb_city": bill_addr.get("City", ""),
            "qb_state": bill_addr.get("CountrySubDivisionCode", ""),
            "qb_zip": normalize_zip(bill_addr.get("PostalCode", "")),
            "qb_email": qb_email,
            "qb_phone": qb_phone,
            "qbo_customer_id": customer.get("Id"),
            "qbo_sync_token": customer.get("SyncToken"),
        }

    @staticmethod
    def compare_addresses(extracted_addr: Dict[str, Any], qbo_addr: Dict[str, Any]) -> Dict[str, Any]:
        """Compare extracted address with QBO address to determine if update needed.

        Args:
            extracted_addr: Address from extracted payment data
            qbo_addr: Address from QuickBooks customer

        Returns:
            Dictionary with comparison results
        """
        # Normalize addresses for comparison
        extracted_line1 = (extracted_addr.get("address_line_1") or "").strip().lower()
        extracted_city = (extracted_addr.get("city") or "").strip().lower()
        extracted_state = (extracted_addr.get("state") or "").strip().upper()
        extracted_zip = normalize_zip(extracted_addr.get("zip") or "")

        qbo_line1 = (qbo_addr.get("qb_address_line_1") or "").strip().lower()
        qbo_city = (qbo_addr.get("qb_city") or "").strip().lower()
        qbo_state = (qbo_addr.get("qb_state") or "").strip().upper()
        qbo_zip = normalize_zip(qbo_addr.get("qb_zip") or "")

        # Check if addresses are materially different
        address_needs_update = False
        differences = []

        # Compare address line 1 - calculate character difference
        if extracted_line1 and qbo_line1:
            # Calculate similarity ratio
            similarity = calculate_string_similarity(extracted_line1, qbo_line1)
            if similarity < 0.5:  # Less than 50% similar
                address_needs_update = True
                differences.append(
                    f"Address line differs: '{extracted_addr.get('address_line_1')}' vs '{qbo_addr.get('qb_address_line_1')}'"
                )
        elif extracted_line1 and not qbo_line1:
            # QBO missing address
            address_needs_update = True
            differences.append("QBO missing address line 1")

        # Compare city
        if extracted_city and extracted_city != qbo_city:
            differences.append(f"City differs: '{extracted_addr.get('city')}' vs '{qbo_addr.get('qb_city')}'")
            if not address_needs_update and extracted_city:
                address_needs_update = True

        # Compare state
        if extracted_state and extracted_state != qbo_state:
            differences.append(f"State differs: '{extracted_state}' vs '{qbo_state}'")
            if not address_needs_update:
                address_needs_update = True

        # Compare ZIP
        if extracted_zip and extracted_zip != qbo_zip:
            differences.append(f"ZIP differs: '{extracted_zip}' vs '{qbo_zip}'")
            # ZIP alone doesn't trigger update unless other fields differ

        return {
            "address_needs_update": address_needs_update,
            "differences": differences,
            "similarity_score": (
                calculate_string_similarity(extracted_line1, qbo_line1) if extracted_line1 and qbo_line1 else 0.0
            ),
        }

    @staticmethod
    def merge_email_phone_lists(
        extracted_email: Optional[str], extracted_phone: Optional[str], qbo_emails: List[str], qbo_phones: List[str]
    ) -> Dict[str, Any]:
        """Merge extracted email/phone with QBO lists intelligently.

        Args:
            extracted_email: Email from extraction
            extracted_phone: Phone from extraction
            qbo_emails: List of emails from QBO
            qbo_phones: List of phones from QBO

        Returns:
            Dictionary with updated email/phone lists and flags
        """
        result = {
            "emails": qbo_emails.copy() if qbo_emails else [],
            "phones": qbo_phones.copy() if qbo_phones else [],
            "email_added": False,
            "phone_added": False,
        }

        # Handle email
        if extracted_email:
            extracted_email = extracted_email.strip().lower()
            # Check if email already exists (case-insensitive)
            existing_emails_lower = [e.lower() for e in result["emails"]]

            if not existing_emails_lower:
                # QBO has no email, add extracted
                result["emails"].append(extracted_email)
                result["email_added"] = True
            elif extracted_email not in existing_emails_lower:
                # Email is different, add to list
                result["emails"].append(extracted_email)
                result["email_added"] = True

        # Handle phone
        if extracted_phone:
            # Normalize phone for comparison
            extracted_phone_normalized = normalize_phone(extracted_phone)
            existing_phones_normalized = [normalize_phone(p) for p in result["phones"]]

            if not existing_phones_normalized:
                # QBO has no phone, add extracted
                result["phones"].append(extracted_phone)
                result["phone_added"] = True
            elif extracted_phone_normalized not in existing_phones_normalized:
                # Phone is different, add to list
                result["phones"].append(extracted_phone)
                result["phone_added"] = True

        return result


def normalize_zip(zip_code: str) -> str:
    """Normalize ZIP code to 5 digits, preserving leading zeros.

    Args:
        zip_code: ZIP code string

    Returns:
        5-digit ZIP code or empty string
    """
    if not zip_code:
        return ""

    # Remove non-numeric characters
    cleaned = "".join(c for c in str(zip_code) if c.isdigit())

    if len(cleaned) >= 5:
        # Take first 5 digits (ignore +4 extension)
        return cleaned[:5]
    elif len(cleaned) > 0:
        # Pad with leading zeros if needed
        return cleaned.zfill(5)

    return ""


def normalize_phone(phone: str) -> str:
    """Normalize phone number for comparison.

    Args:
        phone: Phone number string

    Returns:
        Normalized phone number (digits only)
    """
    if not phone:
        return ""

    # Extract only digits
    return "".join(c for c in phone if c.isdigit())


def calculate_string_similarity(str1: str, str2: str) -> float:
    """Calculate similarity ratio between two strings.

    Uses character-level comparison to determine how similar two strings are.

    Args:
        str1: First string
        str2: Second string

    Returns:
        Similarity ratio between 0.0 and 1.0
    """
    if not str1 or not str2:
        return 0.0

    # Simple character matching algorithm
    # Count matching characters in same positions
    matches = sum(c1 == c2 for c1, c2 in zip(str1, str2))

    # Also count characters that appear in both strings regardless of position
    str1_chars = set(str1)
    str2_chars = set(str2)
    common_chars = len(str1_chars & str2_chars)

    # Weighted average of position matches and common characters
    max_len = max(len(str1), len(str2))
    position_score = matches / max_len if max_len > 0 else 0
    common_score = common_chars / max(len(str1_chars), len(str2_chars)) if str1_chars or str2_chars else 0

    # Weight position matches more heavily
    return (position_score * 0.7) + (common_score * 0.3)
