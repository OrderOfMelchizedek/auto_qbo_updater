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

    # Add organization name first if present
    if org_name and org_name not in seen:
        variations.append(org_name)
        seen.add(org_name)
        return variations  # For organizations, just use the org name

    # Process individual name aliases
    for alias in aliases:
        if not alias:
            continue

        # Add original alias
        if alias not in seen:
            variations.append(alias)
            seen.add(alias)

        # Parse name components
        parts = alias.split()
        if len(parts) >= 2:
            # Generate "Lastname, Firstname" variations
            first_name = parts[0]
            last_name = parts[-1]
            middle_parts = parts[1:-1] if len(parts) > 2 else []

            # "Smith, John" from "John Smith"
            lastname_firstname = f"{last_name}, {first_name}"
            if lastname_firstname not in seen:
                variations.append(lastname_firstname)
                seen.add(lastname_firstname)

            # "Smith, John A." from "John A. Smith"
            if middle_parts:
                full_reversed = f"{last_name}, {' '.join([first_name] + middle_parts)}"
                if full_reversed not in seen:
                    variations.append(full_reversed)
                    seen.add(full_reversed)

            # Just last name for broader search
            if last_name not in seen and len(last_name) > 2:
                variations.append(last_name)
                seen.add(last_name)

            # First initial variations
            if len(first_name) > 0:
                # "J. Smith" from "John Smith"
                initial_last = f"{first_name[0]}. {last_name}"
                if initial_last not in seen:
                    variations.append(initial_last)
                    seen.add(initial_last)

                # "Smith, J." from "John Smith"
                lastname_initial = f"{last_name}, {first_name[0]}."
                if lastname_initial not in seen:
                    variations.append(lastname_initial)
                    seen.add(lastname_initial)

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

        # Split both alias and display name into parts for flexible matching
        alias_parts = normalized_alias.split()
        display_parts = normalized_display.split()

        # Handle "Last, First" format in display name
        if "," in display_name:
            # QuickBooks often uses "Last, First" format
            comma_parts = display_name.split(",")
            if len(comma_parts) == 2:
                qb_last = normalize_name(comma_parts[0]).lower()
                qb_first = normalize_name(comma_parts[1]).lower()

                # Check if alias matches this format
                if len(alias_parts) >= 2:
                    # First Last format in alias vs Last, First in QB
                    if alias_parts[0] == qb_first and alias_parts[-1] == qb_last:
                        best_score = max(best_score, 95.0)
                        continue

                    # Handle middle initials/names
                    if (alias_parts[0] == qb_first or alias_parts[-1] == qb_last) and (
                        qb_first.startswith(alias_parts[0])
                        or alias_parts[0].startswith(qb_first)
                    ):
                        best_score = max(best_score, 90.0)
                        continue

        # Check component names if we have them
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

        # Check if all parts of alias are in display name (any order)
        if len(alias_parts) >= 2 and len(display_parts) >= 2:
            alias_set = set(alias_parts)
            display_set = set(display_parts)

            # All alias parts found in display
            if alias_set.issubset(display_set):
                best_score = max(best_score, 90.0)
                continue

            # Most alias parts found (allow for middle names/initials)
            common_parts = alias_set.intersection(display_set)
            if len(common_parts) >= min(2, len(alias_parts)):
                best_score = max(best_score, 85.0)
                continue

        # Check if customer name contains the search term
        if normalized_alias in normalized_display:
            best_score = max(best_score, 80.0)
            continue

        # Check last name only match
        if len(alias_parts) >= 2:
            # Check against family name
            if family_name and alias_parts[-1] == family_name:
                best_score = max(best_score, 75.0)
                continue

            # Check against last part of display name
            if len(display_parts) >= 2 and alias_parts[-1] == display_parts[-1]:
                best_score = max(best_score, 75.0)
                continue

        # Partial match - any significant word matches
        if len(alias_parts) >= 2:
            for part in alias_parts:
                if len(part) > 2:
                    # Check in display name parts
                    for display_part in display_parts:
                        if (
                            part == display_part
                            or display_part.startswith(part)
                            or part.startswith(display_part)
                        ):
                            best_score = max(best_score, 70.0)
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
        self.data_source = create_customer_data_source(
            session_id=session_id, csv_path=csv_path
        )

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
        logger.info(
            f"Generated {len(search_variations)} search variations from "
            f"aliases {aliases}: {search_variations}"
        )

        # Search for customer using variations
        searched_ids = set()  # Track customer IDs to avoid duplicates
        best_match = None
        best_score = 0.0

        for search_term in search_variations:
            try:
                logger.info(f"Searching for: '{search_term}'")
                results = self.data_source.search_customer(search_term)
                logger.info(f"Found {len(results)} results for '{search_term}'")

                # Score results immediately to potentially stop early
                for customer in results:
                    customer_id = customer.get("Id")
                    if customer_id and customer_id not in searched_ids:
                        searched_ids.add(customer_id)

                        # Score this customer
                        score = calculate_match_score(donation, customer)
                        logger.info(
                            f"Customer '{customer.get('DisplayName')}' "
                            f"(ID: {customer_id}) scored {score} "
                            f"for search term '{search_term}'"
                        )

                        if score > best_score:
                            best_score = score
                            best_match = customer

                        # If we found a good match, stop searching
                        if score >= 85:
                            logger.info(
                                f"Found good match: "
                                f"'{customer.get('DisplayName')}' "
                                f"with score {score}. Stopping search."
                            )
                            break

                # Stop outer loop if we found a good match
                if best_score >= 85:
                    break

            except QuickBooksError as e:
                logger.error(f"QuickBooks search failed for '{search_term}': {e}")
                raise

        # If no match found, return new customer
        if not best_match or best_score < 50:
            logger.info(
                f"No good match found (best score: {best_score}) for "
                f"search variations: {search_variations}"
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
            "qb_customer_id": qb_customer["customer_ref"].get(
                "id"
            ),  # Include customer ID
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
            # Store original QuickBooks address before updating
            result["original_qb_address"] = qb_customer["qb_address"].copy()
            logger.info(f"Storing original_qb_address: {result['original_qb_address']}")
            # Update with extracted address
            result["qb_address"] = extracted_address
            logger.info(f"Updated to new address: {result['qb_address']}")

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
