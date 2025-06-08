"""Donation processor that pipes extraction through validation and matching."""
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .customer_matcher import CustomerMatcher
from .final_display_merger import merge_all_donations_for_display
from .geminiservice import extract_donations_from_documents
from .validation import DonationValidator

logger = logging.getLogger(__name__)


def process_donation_documents(
    file_paths: List[Union[str, Path]],
    session_id: Optional[str] = None,
    csv_path: Optional[Path] = None,
    progress_callback=None,
) -> Tuple[List[Dict[str, Any]], Dict[str, int], List[Dict[str, Any]]]:
    """
    Process donation documents: extract, validate, deduplicate, and match.

    Args:
        file_paths: List of paths to document files
        session_id: Optional session ID for QuickBooks matching
        csv_path: Optional path to CSV file for testing

    Returns:
        Tuple of (processed_donations, metadata_dict, display_donations)
        metadata_dict contains: raw_count, valid_count, duplicate_count, matched_count
        display_donations: List of donations formatted for UI display
    """
    # Extract donations from documents
    raw_donations = extract_donations_from_documents(file_paths)
    raw_count = len(raw_donations)

    # Validate and deduplicate
    validator = DonationValidator()
    processed_donations = validator.process_donations(raw_donations)
    valid_count = len(processed_donations)

    # Calculate duplicate count
    duplicate_count = raw_count - valid_count

    # Match with QuickBooks if session provided
    matched_count = 0
    new_customer_count = 0
    matching_errors = []

    if session_id or csv_path:
        if csv_path:
            logger.info(f"Starting customer matching using CSV: {csv_path}")
        else:
            logger.info(f"Starting QuickBooks matching for session {session_id}")
        try:
            matcher = CustomerMatcher(session_id=session_id, csv_path=csv_path)
            logger.info(
                f"CustomerMatcher initialized successfully for "
                f"{len(processed_donations)} donations"
            )

            for i, donation in enumerate(processed_donations):
                try:
                    # Extract payer info for logging
                    payer_info = donation.get("PayerInfo", {})
                    payer_name = (
                        payer_info.get("Aliases", ["Unknown"])[0]
                        if payer_info.get("Aliases")
                        else payer_info.get("Organization_Name", "Unknown")
                    )
                    payment_ref = donation.get("PaymentInfo", {}).get(
                        "Payment_Ref", "Unknown"
                    )

                    logger.info(
                        f"Attempting to match donation {i+1}/"
                        f"{len(processed_donations)}: "
                        f"{payer_name} (Ref: {payment_ref})"
                    )

                    match_result = matcher.match_donation_to_customer(donation)
                    donation["match_data"] = match_result

                    if match_result["match_status"] == "matched":
                        matched_count += 1
                        logger.info(
                            f"✓ Matched {payer_name} to QuickBooks customer ID: "
                            f"{match_result['customer_ref']['id']}"
                        )
                    elif match_result["match_status"] == "new_customer":
                        new_customer_count += 1
                        logger.info(
                            f"✗ No match found for {payer_name} - "
                            "marked as new customer"
                        )

                except Exception as e:
                    error_msg = (
                        f"Failed to match donation {i+1} ({payer_name}): {str(e)}"
                    )
                    logger.error(error_msg)
                    matching_errors.append(error_msg)
                    # Add error info to donation
                    donation["match_data"] = {
                        "match_status": "error",
                        "error": str(e),
                        "customer_ref": None,
                        "qb_address": None,
                        "qb_email": [],
                        "qb_phone": [],
                        "updates_needed": {},
                    }

            logger.info(
                f"Matching complete: {matched_count} matched, "
                f"{new_customer_count} new customers, "
                f"{len(matching_errors)} errors"
            )

        except Exception as e:
            error_msg = f"Failed to initialize CustomerMatcher: {str(e)}"
            logger.error(error_msg)
            matching_errors.append(error_msg)
            # Mark all donations as having matching errors
            for donation in processed_donations:
                donation["match_data"] = {
                    "match_status": "error",
                    "error": "Matching service unavailable",
                    "customer_ref": None,
                    "qb_address": None,
                    "qb_email": [],
                    "qb_phone": [],
                    "updates_needed": {},
                }
    else:
        logger.info("No session_id or csv_path provided - skipping customer matching")

    metadata: Dict[str, int] = {
        "raw_count": raw_count,
        "valid_count": valid_count,
        "duplicate_count": duplicate_count,
        "matched_count": matched_count,
    }

    # Create display-ready versions of donations
    display_donations = merge_all_donations_for_display(processed_donations)

    return processed_donations, metadata, display_donations
