"""Customer matching logic for QuickBooks integration."""
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .customer_data_source import create_customer_data_source
from .quickbooks_service import QuickBooksError

logger = logging.getLogger(__name__)


def normalize_name(name: str) -> str:
    """
    Normalize a name by removing punctuation and extra spaces.

    Args:
        name: Name to normalize

    Returns:
        Normalized name
    """
    # Remove periods after single letters (initials)
    name = re.sub(r"\b(\w)\.", r"\1", name)

    # Remove other punctuation except spaces and hyphens
    name = re.sub(r"[^\w\s\-]", " ", name)

    # Normalize multiple spaces to single space
    name = " ".join(name.split())

    return name.strip()


def generate_search_variations(aliases: List[str], org_name: str = "") -> List[str]:
    """
    Generate search variations for better matching.

    Args:
        aliases: List of name aliases
        org_name: Organization name if applicable

    Returns:
        List of search terms to try
    """
    variations = []
    seen = set()

    # Process individual name aliases
    for alias in aliases:
        # Add original
        if alias and alias not in seen:
            variations.append(alias)
            seen.add(alias)

        # Normalize and add
        normalized = normalize_name(alias)
        if normalized and normalized not in seen:
            variations.append(normalized)
            seen.add(normalized)

        # Split name parts
        parts = normalized.split()

        if len(parts) >= 2:
            # Try without middle name/initial
            if len(parts) >= 3:
                # First + Last
                name_no_middle = f"{parts[0]} {parts[-1]}"
                if name_no_middle not in seen:
                    variations.append(name_no_middle)
                    seen.add(name_no_middle)

            # Last name only
            last_name = parts[-1]
            if last_name not in seen and len(last_name) > 2:
                variations.append(last_name)
                seen.add(last_name)

            # Handle "Last, First" format
            if "," in alias:
                # Already handled by normalization
                pass

    # Process organization name
    if org_name:
        # Add original
        if org_name not in seen:
            variations.append(org_name)
            seen.add(org_name)

        # Normalize
        normalized_org = normalize_name(org_name)
        if normalized_org and normalized_org not in seen:
            variations.append(normalized_org)
            seen.add(normalized_org)

        # Extract significant words (longer than 3 chars)
        org_words = [word for word in normalized_org.split() if len(word) > 3]

        # Common words to skip
        skip_words = {"the", "and", "inc", "llc", "corp", "corporation", "company"}
        org_words = [w for w in org_words if w.lower() not in skip_words]

        # Try significant word combinations
        if len(org_words) >= 2:
            # First two significant words
            two_words = " ".join(org_words[:2])
            if two_words not in seen:
                variations.append(two_words)
                seen.add(two_words)

            # Most significant single word
            if org_words[0] not in seen and len(org_words[0]) > 4:
                variations.append(org_words[0])
                seen.add(org_words[0])

        # Handle special cases like "DAFgiving360"
        # Split on case changes
        case_split = re.sub(r"([A-Z]+)([a-z])", r"\1 \2", org_name)
        case_split = re.sub(r"([a-z])([A-Z])", r"\1 \2", case_split)
        if case_split != org_name and case_split not in seen:
            variations.append(case_split)
            seen.add(case_split)

    return variations


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
    # Get payer info
    payer_info = donation.get("PayerInfo", {})

    # Get customer info in lowercase for comparison
    display_name = customer.get("DisplayName", "").lower()
    given_name = (customer.get("GivenName") or "").lower()
    family_name = (customer.get("FamilyName") or "").lower()
    company_name = (customer.get("CompanyName") or "").lower()

    # Normalize display name for better matching
    normalized_display = normalize_name(display_name).lower()

    # For individuals - check aliases
    aliases = payer_info.get("Aliases", [])
    best_score = 0.0

    for alias in aliases:
        alias_lower = alias.lower()
        normalized_alias = normalize_name(alias).lower()

        # Exact match (after normalization)
        if normalized_alias == normalized_display:
            best_score = max(best_score, 100.0)
            continue

        # Original exact match
        if alias_lower == display_name:
            best_score = max(best_score, 98.0)
            continue

        # Check component names
        alias_parts = normalized_alias.split()

        if len(alias_parts) >= 2 and given_name and family_name:
            # Exact first and last name match
            if alias_parts[0] == given_name and alias_parts[-1] == family_name:
                best_score = max(best_score, 95.0)
                continue

            # Last name exact match with partial first name
            if alias_parts[-1] == family_name and given_name.startswith(alias_parts[0]):
                best_score = max(best_score, 90.0)
                continue

            # Both names present anywhere
            if given_name in normalized_alias and family_name in normalized_alias:
                best_score = max(best_score, 85.0)
                continue

        # Check if customer name contains the search term
        if normalized_alias in normalized_display:
            best_score = max(best_score, 80.0)
            continue

        # Check last name only match
        if len(alias_parts) >= 2 and family_name and alias_parts[-1] == family_name:
            best_score = max(best_score, 75.0)
            continue

        # Partial match - any significant word matches
        if len(alias_parts) >= 2:
            for part in alias_parts:
                if len(part) > 2 and part in normalized_display:
                    best_score = max(best_score, 60.0)
                    break

    # For organizations
    org_name = payer_info.get("Organization_Name", "")

    if org_name and (company_name or (not aliases and display_name)):
        org_lower = org_name.lower()
        normalized_org = normalize_name(org_name).lower()

        # Use company name if available, otherwise display name
        compare_name = company_name if company_name else display_name
        normalized_compare = normalize_name(compare_name).lower()

        # Exact match after normalization
        if normalized_org == normalized_compare:
            best_score = max(best_score, 100.0)

        # Original exact match
        elif org_lower == compare_name:
            best_score = max(best_score, 98.0)

        # One contains the other
        elif (
            normalized_org in normalized_compare or normalized_compare in normalized_org
        ):
            best_score = max(best_score, 85.0)

        # Significant word matching
        else:
            # Extract significant words
            skip_words = {
                "the",
                "and",
                "inc",
                "llc",
                "corp",
                "corporation",
                "company",
                "of",
                "a",
            }

            org_words = {
                word
                for word in normalized_org.split()
                if len(word) > 2 and word not in skip_words
            }
            compare_words = {
                word
                for word in normalized_compare.split()
                if len(word) > 2 and word not in skip_words
            }

            if org_words and compare_words:
                common_words = org_words.intersection(compare_words)

                # Multiple significant words match
                if len(common_words) >= 2:
                    best_score = max(best_score, 80.0)

                # Single important word matches (longer words weighted higher)
                elif len(common_words) == 1:
                    word = list(common_words)[0]
                    if len(word) >= 5:  # Longer word = more significant
                        best_score = max(best_score, 70.0)
                    else:
                        best_score = max(best_score, 60.0)

    return best_score


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
        aliases = payer_info.get("Aliases", [])
        org_name = payer_info.get("Organization_Name", "")

        # Generate search variations
        search_variations = generate_search_variations(aliases, org_name)
        logger.info(f"Generated search variations: {search_variations}")

        # Search for customer using variations
        search_results = []
        searched_ids = set()  # Track customer IDs to avoid duplicates

        for search_term in search_variations:
            try:
                logger.debug(f"Searching for: '{search_term}'")
                results = self.data_source.search_customer(search_term)

                # Add unique results
                for customer in results:
                    customer_id = customer.get("Id")
                    if customer_id and customer_id not in searched_ids:
                        search_results.append(customer)
                        searched_ids.add(customer_id)

                logger.debug(f"Found {len(results)} results for '{search_term}'")

            except QuickBooksError as e:
                logger.error(f"QuickBooks search failed for '{search_term}': {e}")
                raise

        # If no search results, return new customer
        if not search_results:
            logger.info(
                "No QuickBooks customers found for search variations: "
                f"{search_variations}"
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
