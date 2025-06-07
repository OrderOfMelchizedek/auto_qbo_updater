"""Customer matching logic for QuickBooks integration."""
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from .customer_data_source import create_customer_data_source
from .quickbooks_service import QuickBooksError

logger = logging.getLogger(__name__)


def compare_addresses(extracted: Dict[str, str], qb: Dict[str, str]) -> Dict[str, Any]:
    """
    Compare extracted address with QuickBooks address.

    Args:
        extracted: Extracted address data
        qb: QuickBooks address data

    Returns:
        Dict with match_percentage and should_update flag
    """
    # Get address line 1 for comparison
    extracted_line1 = extracted.get("line1", "").strip()
    qb_line1 = qb.get("line1", "").strip()

    # If QB has no address but extracted does, update
    if extracted_line1 and not qb_line1:
        return {"match_percentage": 0, "should_update": True}

    # If extracted has no address, don't update
    if not extracted_line1:
        return {"match_percentage": 100, "should_update": False}

    # Calculate character-level match percentage
    if extracted_line1.lower() == qb_line1.lower():
        match_percentage = 100
    else:
        # Count matching characters
        matches = sum(
            1 for a, b in zip(extracted_line1.lower(), qb_line1.lower()) if a == b
        )
        max_len = max(len(extracted_line1), len(qb_line1))
        match_percentage = int((matches / max_len * 100)) if max_len > 0 else 0

    # Update if less than 50% match
    should_update = match_percentage < 50

    return {"match_percentage": match_percentage, "should_update": should_update}


def calculate_match_score(donation: Dict[str, Any], customer: Dict[str, Any]) -> float:
    """
    Calculate match score between donation and customer.

    Args:
        donation: Extracted donation data
        customer: QuickBooks customer data

    Returns:
        Match score (0-100)
    """
    # Initial score

    # Get payer info
    payer_info = donation.get("PayerInfo", {})

    # For individuals - check aliases
    aliases = payer_info.get("Aliases", [])
    display_name = customer.get("DisplayName", "").lower()

    # Also check component names
    given_name = (customer.get("GivenName") or "").lower()
    family_name = (customer.get("FamilyName") or "").lower()

    for alias in aliases:
        alias_lower = alias.lower()

        # Exact match
        if alias_lower == display_name:
            return 100.0

        # Check if first and last name match (ignoring middle initial/name)
        alias_parts = alias_lower.split()
        if len(alias_parts) >= 2 and given_name and family_name:
            # Check first and last name
            if alias_parts[0] == given_name and alias_parts[-1] == family_name:
                return 95.0  # High score for first/last match

            # Check "Last, First" format
            if ", " in alias_lower:
                last_first = alias_lower.split(", ")
                if (
                    len(last_first) == 2
                    and last_first[0] == family_name
                    and last_first[1].startswith(given_name)
                ):
                    return 95.0

        # Partial name matching - all significant words present
        if (
            given_name
            and family_name
            and given_name in alias_lower
            and family_name in alias_lower
        ):
            return 90.0

    # For organizations
    org_name = payer_info.get("Organization_Name", "")
    company_name = customer.get("CompanyName", "")

    if org_name and company_name:
        org_lower = org_name.lower()
        company_lower = company_name.lower()

        # Exact match
        if org_lower == company_lower:
            return 100.0

        # Check if one contains the other
        if org_lower in company_lower or company_lower in org_lower:
            return 85.0

        # Check if all significant words match
        org_words = {word for word in org_lower.split() if len(word) > 3}
        company_words = {word for word in company_lower.split() if len(word) > 3}
        if org_words and company_words:
            common_words = org_words.intersection(company_words)
            if len(common_words) >= 2:  # At least 2 significant words match
                return 80.0

    return 0.0


class CustomerMatcher:
    """Handles matching donations to QuickBooks customers."""

    def __init__(
        self, session_id: Optional[str] = None, csv_path: Optional[Path] = None
    ):
        """
        Initialize customer matcher.

        Args:
            session_id: Session ID for QuickBooks auth (production)
            csv_path: Path to CSV file for testing
        """
        self.data_source = create_customer_data_source(session_id, csv_path)

    def match_donation_to_customer(self, donation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Match donation to QuickBooks customer.

        Args:
            donation: Extracted donation data

        Returns:
            Matched customer data with update flags
        """
        # Get payer info
        payer_info = donation.get("PayerInfo", {})

        # Search for customer
        search_results = []
        search_terms = []

        # Search by aliases for individuals
        aliases = payer_info.get("Aliases", [])
        for alias in aliases:
            search_terms.append(alias)
            try:
                logger.debug(f"Searching for alias: '{alias}'")
                results = self.data_source.search_customer(alias)
                logger.debug(f"Found {len(results)} results for '{alias}'")
                search_results.extend(results)
            except QuickBooksError as e:
                logger.error(f"QuickBooks search failed for '{alias}': {e}")
                raise

        # Search by organization name
        org_name = payer_info.get("Organization_Name")
        if org_name:
            search_terms.append(org_name)
            try:
                logger.debug(f"Searching for organization: '{org_name}'")
                results = self.data_source.search_customer(org_name)
                logger.debug(f"Found {len(results)} results for '{org_name}'")
                search_results.extend(results)
            except QuickBooksError as e:
                logger.error(f"QuickBooks search failed for '{org_name}': {e}")
                raise

        # If no search results, return new customer
        if not search_results:
            logger.info(
                f"No QuickBooks customers found for search terms: {search_terms}"
            )
            return {
                "match_status": "new_customer",
                "customer_ref": None,
                "qb_address": None,
                "qb_email": [],
                "qb_phone": [],
                "updates_needed": {
                    "address": False,
                    "email_added": False,
                    "phone_added": False,
                },
            }

        # Score and find best match
        best_match = None
        best_score = 0.0

        logger.debug(f"Scoring {len(search_results)} potential matches")
        for customer in search_results:
            score = calculate_match_score(donation, customer)
            logger.debug(
                f"Customer '{customer.get('DisplayName')}' "
                f"(ID: {customer.get('Id')}) scored {score}"
            )
            if score > best_score:
                best_score = score
                best_match = customer

        # If no good match found
        if best_score < 50 or not best_match:
            logger.info(
                f"No good match found (best score: {best_score}). "
                "Marking as new customer"
            )
            return {
                "match_status": "new_customer",
                "customer_ref": None,
                "qb_address": None,
                "qb_email": [],
                "qb_phone": [],
                "updates_needed": {
                    "address": False,
                    "email_added": False,
                    "phone_added": False,
                },
            }

        # Get full customer details
        logger.info(
            f"Best match: '{best_match['DisplayName']}' "
            f"(ID: {best_match['Id']}) with score {best_score}"
        )
        try:
            full_customer = self.data_source.get_customer(best_match["Id"])
            formatted_customer = self.data_source.format_customer_data(full_customer)
        except QuickBooksError as e:
            logger.error(
                f"Failed to get full customer details for ID {best_match['Id']}: {e}"
            )
            raise

        # Merge with extracted data
        return self.merge_customer_data(donation, formatted_customer)

    def merge_customer_data(
        self, donation: Dict[str, Any], qb_customer: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge extracted donation data with QuickBooks customer data.

        Args:
            donation: Extracted donation data
            qb_customer: Formatted QuickBooks customer data

        Returns:
            Merged customer data with update flags
        """
        # Start with QB customer data
        result = {
            "match_status": "matched",
            "customer_ref": qb_customer["customer_ref"],
            "qb_address": qb_customer["qb_address"].copy(),
            "qb_email": qb_customer["qb_email"].copy(),
            "qb_phone": qb_customer["qb_phone"].copy(),
            "updates_needed": {
                "address": False,
                "email_added": False,
                "phone_added": False,
            },
        }

        # Get contact info from donation
        contact_info = donation.get("ContactInfo", {})

        # Check address updates
        extracted_address = {
            "line1": contact_info.get("Address_Line_1", ""),
            "city": contact_info.get("City", ""),
            "state": contact_info.get("State", ""),
            "zip": contact_info.get("ZIP", ""),
        }

        address_comparison = compare_addresses(
            extracted_address, qb_customer["qb_address"]
        )

        if address_comparison["should_update"]:
            result["updates_needed"]["address"] = True
            # Update with extracted address
            result["qb_address"] = extracted_address

        # Check email updates
        extracted_email = contact_info.get("Email") or ""
        if isinstance(extracted_email, str):
            extracted_email = extracted_email.strip()
        if extracted_email and (
            not qb_customer["qb_email"]
            or extracted_email not in qb_customer["qb_email"]
        ):
            # Add email
            result["qb_email"].append(extracted_email)
            result["updates_needed"]["email_added"] = True

        # Check phone updates
        extracted_phone = contact_info.get("Phone") or ""
        if isinstance(extracted_phone, str):
            extracted_phone = extracted_phone.strip()
        if extracted_phone and (
            not qb_customer["qb_phone"]
            or extracted_phone not in qb_customer["qb_phone"]
        ):
            # Add phone
            result["qb_phone"].append(extracted_phone)
            result["updates_needed"]["phone_added"] = True

        return result
