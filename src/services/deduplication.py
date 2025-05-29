"""
Deduplication service for merging and managing duplicate donation records.

This module handles the logic for identifying and merging duplicate donations
based on check numbers, amounts, and other identifying information.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .validation import (
    normalize_amount,
    normalize_check_number,
    normalize_date,
    normalize_donor_name,
)

logger = logging.getLogger(__name__)


class DeduplicationService:
    """Service for handling donation deduplication and merging."""

    @staticmethod
    def deduplicate_donations(
        existing_donations: List[Dict[str, Any]], new_donations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Strict deduplication using Check No. + Amount as unique key.

        This ensures NO duplicates can exist with the same check number and amount.
        All data is merged into the single record for each unique key.

        Args:
            existing_donations: List of existing donation records
            new_donations: List of new donation records to merge

        Returns:
            List of deduplicated donation records
        """
        # Convert existing donations list to a dictionary with unique keys
        unique_donations = {}

        # First, add all existing donations to the unique dictionary
        for donation in existing_donations:
            unique_key = DeduplicationService._generate_unique_key(donation)
            if not unique_key:
                print(f"Skipping donation without sufficient identifying info: {donation}")
                continue

            # Store in dictionary (will overwrite if duplicate key exists)
            if unique_key in unique_donations:
                print(f"WARNING: Duplicate key found in existing donations: {unique_key}")
            unique_donations[unique_key] = donation

        # Now process new donations
        merge_count = 0
        new_count = 0

        for new_donation in new_donations:
            unique_key = DeduplicationService._generate_unique_key(new_donation)
            if not unique_key:
                print(f"Skipping new donation without sufficient identifying info: {new_donation}")
                continue

            # Check for suspicious check numbers
            check_no = normalize_check_number(new_donation.get("Check No.", ""))
            if check_no and len(check_no) <= 3 and check_no.isdigit():
                # Check numbers like "195" are suspicious - real checks are usually 4+ digits
                print(
                    f"WARNING: Suspicious check number '{check_no}' - may be a page number or reference"
                )
                # Still process it but log the warning

            # Check if this key already exists
            if unique_key in unique_donations:
                # Merge with existing donation
                logger.info(f"Merging donation with key: {unique_key}")
                logger.info(
                    f"  Existing: {unique_donations[unique_key].get('Donor Name')} - "
                    f"Status: {unique_donations[unique_key].get('qbCustomerStatus')} - "
                    f"ID: {unique_donations[unique_key].get('qboCustomerId')}"
                )
                logger.info(
                    f"  New: {new_donation.get('Donor Name')} - "
                    f"Status: {new_donation.get('qbCustomerStatus')} - "
                    f"ID: {new_donation.get('qboCustomerId')}"
                )
                unique_donations[unique_key] = DeduplicationService.merge_donation_data(
                    unique_donations[unique_key], new_donation
                )
                merge_count += 1
            else:
                # Add as new donation
                logger.info(f"Adding new donation with key: {unique_key}")
                logger.info(
                    f"  New: {new_donation.get('Donor Name')} - "
                    f"Status: {new_donation.get('qbCustomerStatus')} - "
                    f"ID: {new_donation.get('qboCustomerId')}"
                )
                unique_donations[unique_key] = new_donation
                new_count += 1

        # Convert back to list
        result = list(unique_donations.values())

        # Ensure internal IDs are unique
        for i, donation in enumerate(result):
            if "internalId" not in donation or not donation["internalId"]:
                donation["internalId"] = f"donation_{i}"

        logger.info(
            f"Deduplication complete: {len(result)} unique donations "
            f"(merged {merge_count}, added {new_count})"
        )

        # Log final customer match status
        matched_count = sum(
            1
            for d in result
            if d.get("qbCustomerStatus")
            in ["Matched", "Matched-AddressMismatch", "Matched-AddressNeedsReview"]
        )
        logger.info(
            f"Customer matches in final result: {matched_count} out of {len(result)} donations"
        )

        return result

    @staticmethod
    def _generate_unique_key(donation: Dict[str, Any]) -> Optional[str]:
        """
        Generate a unique key for a donation record.

        Args:
            donation: Donation record

        Returns:
            Unique key string or None if insufficient data
        """
        check_no = normalize_check_number(donation.get("Check No.", ""))
        amount = normalize_amount(donation.get("Gift Amount", ""))

        # Create unique key
        if check_no and amount:
            # Check donations use check number + amount as key
            return f"CHECK_{check_no}_{amount}"
        else:
            # Non-check donations use donor name + amount + date as key
            donor_name = normalize_donor_name(donation.get("Donor Name", ""))
            gift_date = normalize_date(donation.get("Gift Date", ""))

            if donor_name and amount:
                return f"OTHER_{donor_name}_{amount}_{gift_date}"
            else:
                # Not enough identifying information
                return None

    @staticmethod
    def merge_donation_data(existing: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
        """
        Intelligently merge two donation records, preserving the most complete information.

        Priority rules:
        1. Non-null values override null values
        2. Longer/more complete values override shorter ones
        3. Values from images override values from PDFs (generally more accurate)
        4. Specific fields have custom merge logic

        Args:
            existing: Existing donation record
            new: New donation record to merge

        Returns:
            Merged donation record
        """
        merged = existing.copy()

        # Debug logging
        logger.info(
            f"Merging donations - Existing status: {existing.get('qbCustomerStatus')}, "
            f"New status: {new.get('qbCustomerStatus')}"
        )

        # Initialize merge history if not present
        if "mergeHistory" not in merged:
            merged["mergeHistory"] = []

        # Track what fields are being merged
        merged_fields = []

        # Fields that should be merged by taking non-null or most complete value
        simple_merge_fields = [
            "Donor Name",
            "First Name",
            "Last Name",
            "Full Name",
            "Address - Line 1",
            "City",
            "State",
            "ZIP",
            "Organization Name",
            "Email",
            "Phone",
            "Check Date",
            "Deposit Date",
            "Deposit Method",
            "Gift Amount",
            "Check No.",
        ]

        for field in simple_merge_fields:
            existing_val = existing.get(field)
            new_val = new.get(field)

            # Take new value if existing is empty/null/N/A
            if (not existing_val or existing_val == "N/A") and new_val and new_val != "N/A":
                merged[field] = new_val
                merged_fields.append(field)
            # Take longer/more complete value for text fields
            elif (
                existing_val
                and new_val
                and isinstance(existing_val, str)
                and isinstance(new_val, str)
            ):
                # Safely strip whitespace
                existing_stripped = existing_val.strip() if existing_val else ""
                new_stripped = new_val.strip() if new_val else ""

                # Also replace N/A with actual values
                if existing_val == "N/A" and new_val != "N/A":
                    merged[field] = new_val
                    merged_fields.append(field)
                elif len(new_stripped) > len(existing_stripped) and new_val != "N/A":
                    merged[field] = new_val
                    merged_fields.append(field)

        # Special handling for memo - concatenate if different
        existing_memo = existing.get("Memo") or ""
        new_memo = new.get("Memo") or ""
        existing_memo = existing_memo.strip() if existing_memo else ""
        new_memo = new_memo.strip() if new_memo else ""

        if new_memo and new_memo not in existing_memo:
            if existing_memo:
                merged["Memo"] = f"{existing_memo}; {new_memo}"
            else:
                merged["Memo"] = new_memo

        # Preserve QBO-related fields - intelligently merge to keep the best match
        DeduplicationService._merge_customer_fields(merged, existing, new)

        # Other QBO fields - simple merge
        other_qbo_fields = ["qbSyncStatus", "internalId"]
        for field in other_qbo_fields:
            if field in existing and existing[field]:
                merged[field] = existing[field]
            elif field in new and new[field]:
                merged[field] = new[field]

        # Data source tracking
        if "dataSource" in existing and "dataSource" in new:
            if existing["dataSource"] != new["dataSource"]:
                merged["dataSource"] = "Mixed"

        # Add merge history entry if fields were merged
        if merged_fields:
            merged["mergeHistory"].append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "mergedFields": merged_fields,
                    "sourceData": {
                        "checkNo": new.get("Check No.", ""),
                        "amount": new.get("Gift Amount", ""),
                        "donor": new.get("Donor Name", ""),
                    },
                }
            )
            merged["isMerged"] = True

        # Log the final merged result
        logger.info(
            f"Merge complete - Result status: {merged.get('qbCustomerStatus')} - "
            f"ID: {merged.get('qboCustomerId')}"
        )

        return merged

    @staticmethod
    def _merge_customer_fields(
        merged: Dict[str, Any], existing: Dict[str, Any], new: Dict[str, Any]
    ) -> None:
        """
        Merge customer-related fields intelligently.

        Args:
            merged: The merged record to update
            existing: Existing donation record
            new: New donation record
        """
        customer_fields = ["qboCustomerId", "customerLookup", "matchMethod", "matchConfidence"]

        # Check if either record has a successful match
        existing_matched = existing.get("qbCustomerStatus") in [
            "Matched",
            "Matched-AddressMismatch",
            "Matched-AddressNeedsReview",
        ]
        new_matched = new.get("qbCustomerStatus") in [
            "Matched",
            "Matched-AddressMismatch",
            "Matched-AddressNeedsReview",
        ]

        if existing_matched and not new_matched:
            # Existing has a match, new doesn't - keep existing
            for field in customer_fields:
                if field in existing:
                    merged[field] = existing[field]
            merged["qbCustomerStatus"] = existing.get("qbCustomerStatus")
        elif new_matched and not existing_matched:
            # New has a match, existing doesn't - take new
            for field in customer_fields:
                if field in new:
                    merged[field] = new[field]
            merged["qbCustomerStatus"] = new.get("qbCustomerStatus")
        elif existing_matched and new_matched:
            # Both have matches - prefer existing unless new has higher confidence
            existing_confidence = existing.get("matchConfidence", 0)
            new_confidence = new.get("matchConfidence", 0)
            if new_confidence > existing_confidence:
                for field in customer_fields:
                    if field in new:
                        merged[field] = new[field]
                merged["qbCustomerStatus"] = new.get("qbCustomerStatus")
            else:
                for field in customer_fields:
                    if field in existing:
                        merged[field] = existing[field]
                merged["qbCustomerStatus"] = existing.get("qbCustomerStatus")
        else:
            # Neither has a match - preserve any existing data
            for field in customer_fields:
                if field in existing and existing[field]:
                    merged[field] = existing[field]
                elif field in new and new[field]:
                    merged[field] = new[field]
            if "qbCustomerStatus" in existing:
                merged["qbCustomerStatus"] = existing["qbCustomerStatus"]
            elif "qbCustomerStatus" in new:
                merged["qbCustomerStatus"] = new["qbCustomerStatus"]
