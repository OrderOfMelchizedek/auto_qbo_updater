"""Merge extracted donation data with QuickBooks match data for final display."""
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def merge_donation_for_display(
    donation: Dict[str, Any], match_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Merge extracted donation data with QuickBooks match data for final display.

    Args:
        donation: Extracted donation data from Gemini
        match_data: QuickBooks match data from CustomerMatcher

    Returns:
        Merged data in the format specified by PRD item 13
    """
    # Extract base information from donation
    payer_info = donation.get("PayerInfo", {})
    payment_info = donation.get("PaymentInfo", {})
    contact_info = donation.get("ContactInfo", {})

    # Initialize the final display structure
    display_data = {
        "payer_info": {
            "customer_ref": {
                "salutation": "",
                "first_name": "",
                "last_name": "",
                "full_name": "",
                "display_name": "",
            },
            "qb_organization_name": "",
            "qb_address": {
                "line1": "",
                "city": "",
                "state": "",
                "zip": "",
            },
            "previous_address": None,  # Track previous address for updates
            "address_update_source": None,  # Track source of address update
            "qb_email": "",
            "qb_phone": "",
        },
        "payment_info": {
            "payment_ref": payment_info.get("Payment_Ref", ""),
            "amount": payment_info.get("Amount", ""),
            "payment_date": payment_info.get("Payment_Date", ""),
            "deposit_date": payment_info.get("Deposit_Date", ""),
            "deposit_method": payment_info.get("Deposit_Method", ""),
            "memo": payment_info.get("Memo", ""),
        },
        "status": {
            "matched": False,
            "new_customer": False,
            "sent_to_qb": False,
            "address_updated": False,
            "edited": False,
        },
    }

    # If we have match data, use QuickBooks customer info
    if match_data and match_data.get("match_status") == "matched":
        logger.info(
            f"Processing matched customer with match_data keys: "
            f"{list(match_data.keys())}"
        )
        customer_ref = match_data.get("customer_ref", {})

        # Set customer reference info
        display_data["payer_info"]["customer_ref"] = {
            "salutation": payer_info.get("Salutation", ""),
            "first_name": customer_ref.get("first_name", ""),
            "last_name": customer_ref.get("last_name", ""),
            "full_name": customer_ref.get("full_name", ""),
            "display_name": customer_ref.get("display_name", ""),
        }

        # Set organization name if present
        display_data["payer_info"]["qb_organization_name"] = customer_ref.get(
            "company_name", ""
        )

        # Use QuickBooks address
        qb_address = match_data.get("qb_address", {})
        display_data["payer_info"]["qb_address"] = {
            "line1": qb_address.get("line1", ""),
            "city": qb_address.get("city", ""),
            "state": qb_address.get("state", ""),
            "zip": qb_address.get("zip", ""),
        }

        # Set email and phone (using first if multiple)
        qb_emails = match_data.get("qb_email", [])
        display_data["payer_info"]["qb_email"] = qb_emails[0] if qb_emails else ""

        qb_phones = match_data.get("qb_phone", [])
        display_data["payer_info"]["qb_phone"] = qb_phones[0] if qb_phones else ""

        # Set status flags
        display_data["status"]["matched"] = True

        # Include QuickBooks customer ID if available
        if match_data.get("qb_customer_id"):
            display_data["status"]["qbo_customer_id"] = match_data["qb_customer_id"]

        # Check if address was updated
        updates_needed = match_data.get("updates_needed", {})
        if updates_needed.get("address"):
            display_data["status"]["address_updated"] = True
            logger.info(
                f"Address update detected for customer: "
                f"{customer_ref.get('display_name', 'Unknown')}"
            )
            logger.info(f"Match data keys: {list(match_data.keys())}")

            # Check if we have the original QB address stored
            if "original_qb_address" in match_data:
                # Use the stored original address as previous address
                original_addr = match_data["original_qb_address"]
                display_data["payer_info"]["previous_address"] = {
                    "line1": original_addr.get("line1", ""),
                    "city": original_addr.get("city", ""),
                    "state": original_addr.get("state", ""),
                    "zip": original_addr.get("zip", ""),
                }
                logger.info(
                    f"Set previous_address from original_qb_address: "
                    f"{display_data['payer_info']['previous_address']}"
                )
            else:
                # Fallback: qb_address might already be the new address
                # In this case, we can't determine the previous address
                display_data["payer_info"]["previous_address"] = None
                logger.warning(
                    f"No original_qb_address found in match_data. "
                    f"Available keys: {list(match_data.keys())}"
                )

            # Use the extracted address as the new address
            display_data["payer_info"]["qb_address"] = {
                "line1": contact_info.get("Address_Line_1", ""),
                "city": contact_info.get("City", ""),
                "state": contact_info.get("State", ""),
                "zip": contact_info.get("ZIP", ""),
            }

            # Mark the source as extracted
            display_data["payer_info"]["address_update_source"] = "extracted"

            # Store the original QuickBooks address as previous address
            display_data["payer_info"]["previous_address"] = {
                "line1": qb_address.get("line1", ""),
                "city": qb_address.get("city", ""),
                "state": qb_address.get("state", ""),
                "zip": qb_address.get("zip", ""),
            }

            # Use the extracted address as the new address
            display_data["payer_info"]["qb_address"] = {
                "line1": contact_info.get("Address_Line_1", ""),
                "city": contact_info.get("City", ""),
                "state": contact_info.get("State", ""),
                "zip": contact_info.get("ZIP", ""),
            }

            # Mark the source as extracted
            display_data["payer_info"]["address_update_source"] = "extracted"

    else:
        # No match or new customer - use extracted data
        # Try to parse name from aliases
        aliases = payer_info.get("Aliases", [])
        if aliases:
            # Use first alias as full name
            full_name = aliases[0]
            display_data["payer_info"]["customer_ref"]["full_name"] = full_name

            # Try to split into first/last (simple split)
            name_parts = full_name.split()
            if len(name_parts) >= 2:
                display_data["payer_info"]["customer_ref"]["first_name"] = name_parts[0]
                display_data["payer_info"]["customer_ref"]["last_name"] = name_parts[-1]

        # Set salutation from extracted data
        display_data["payer_info"]["customer_ref"]["salutation"] = payer_info.get(
            "Salutation", ""
        )

        # Use organization name if present
        display_data["payer_info"]["qb_organization_name"] = payer_info.get(
            "Organization_Name", ""
        )

        # Use extracted address
        display_data["payer_info"]["qb_address"] = {
            "line1": contact_info.get("Address_Line_1", ""),
            "city": contact_info.get("City", ""),
            "state": contact_info.get("State", ""),
            "zip": contact_info.get("ZIP", ""),
        }

        # Use extracted contact info
        display_data["payer_info"]["qb_email"] = contact_info.get("Email", "")
        display_data["payer_info"]["qb_phone"] = contact_info.get("Phone", "")

        # Set status as new customer if no match
        if match_data and match_data.get("match_status") == "new_customer":
            display_data["status"]["new_customer"] = True

    # Add match metadata for debugging/reference
    if match_data is not None:
        display_data["_match_data"] = match_data

    # Log final display data for debugging
    if display_data["status"]["address_updated"]:
        logger.info(
            f"Final display data has address_updated=True, "
            f"previous_address={display_data['payer_info'].get('previous_address')}"
        )

    return display_data


def merge_all_donations_for_display(
    donations: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Merge all donations with their match data for display.

    Args:
        donations: List of donations with match_data included

    Returns:
        List of merged donations ready for display
    """
    display_donations = []

    for donation in donations:
        # Extract match data if present
        match_data = donation.get("match_data")

        # Create display version
        display_donation = merge_donation_for_display(donation, match_data)

        # Preserve original donation ID if present
        if "_id" in donation:
            display_donation["_id"] = donation["_id"]

        display_donations.append(display_donation)

    logger.info(f"Merged {len(display_donations)} donations for display")
    return display_donations
