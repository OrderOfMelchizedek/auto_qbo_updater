"""Service for deduplicating donation entries."""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from src.models.donation import DonationEntry
from src.utils.exceptions import DonationProcessingError

logger = logging.getLogger(__name__)


class DeduplicationError(DonationProcessingError):
    """Exception raised for deduplication errors."""

    pass


class DonationDeduplicator:
    """Service for identifying and merging duplicate donation entries."""

    def __init__(self):
        """Initialize the deduplicator."""
        self.merge_log = []

    def deduplicate_donations(
        self, donations: List[Dict[str, Any]]
    ) -> Tuple[List[DonationEntry], List[Dict[str, Any]]]:
        """
        Deduplicate a list of donation entries.

        Args:
            donations: List of donation dictionaries with extracted data

        Returns:
            Tuple of (deduplicated donations, merge audit log)

        Raises:
            DeduplicationError: If deduplication fails
        """
        try:
            if not donations:
                return [], []

            # Convert to DataFrame for efficient processing
            df = pd.DataFrame(donations)

            # Prepare the data
            df = self._prepare_dataframe(df)

            # Find duplicates based on key (check_number + amount)
            df = self._identify_duplicates(df)

            # Merge duplicate entries
            merged_df, merge_log = self._merge_duplicates(df)

            # Convert back to DonationEntry objects
            deduplicated_donations = self._dataframe_to_donations(merged_df)

            logger.info(
                f"Deduplicated {len(donations)} donations to "
                f"{len(deduplicated_donations)}"
            )

            return deduplicated_donations, merge_log

        except Exception as e:
            logger.error(f"Deduplication failed: {str(e)}")
            raise DeduplicationError(
                f"Failed to deduplicate donations: {str(e)}", details={"error": str(e)}
            )

    def _prepare_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare the dataframe for deduplication.

        Args:
            df: Raw dataframe with donation data

        Returns:
            Prepared dataframe
        """
        # Extract nested fields if they exist
        if "payment_info" in df.columns:
            # Flatten payment_info
            payment_df = pd.json_normalize(df["payment_info"].fillna({}))
            df = pd.concat([df.drop("payment_info", axis=1), payment_df], axis=1)

        if "payer_info" in df.columns:
            # Flatten payer_info
            payer_df = pd.json_normalize(df["payer_info"].fillna({}))
            df = pd.concat([df.drop("payer_info", axis=1), payer_df], axis=1)

        if "contact_info" in df.columns:
            # Flatten contact_info
            contact_df = pd.json_normalize(df["contact_info"].fillna({}))
            df = pd.concat([df.drop("contact_info", axis=1), contact_df], axis=1)

        # Clean check numbers (strip leading zeros if > 4 digits)
        if "check_no" in df.columns:
            df["check_no"] = df["check_no"].apply(self._clean_check_number)

        # Ensure amount is numeric
        if "amount" in df.columns:
            df["amount"] = pd.to_numeric(df["amount"], errors="coerce")

        # Parse dates
        date_columns = ["payment_date", "check_date", "deposit_date", "postmark_date"]
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        return df

    def _clean_check_number(self, check_no: Any) -> Optional[str]:
        """
        Clean check number by stripping leading zeros if > 4 digits.

        Args:
            check_no: Raw check number

        Returns:
            Cleaned check number or None
        """
        if pd.isna(check_no) or check_no is None:
            return None

        check_str = str(check_no).strip()

        # Strip leading zeros if longer than 4 digits
        if len(check_str) > 4 and check_str.startswith("0"):
            check_str = check_str.lstrip("0")

        return check_str if check_str else None

    def _identify_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Identify duplicate entries based on check number and amount.

        Args:
            df: Prepared dataframe

        Returns:
            Dataframe with duplicate group identifiers
        """
        # Create duplicate key from check_no + amount
        # Only consider entries with both check_no and amount
        if "check_no" in df.columns and "amount" in df.columns:
            has_key = df["check_no"].notna() & df["amount"].notna()

            # Create a composite key for duplicates
            df.loc[has_key, "dup_key"] = (
                df.loc[has_key, "check_no"].astype(str)
                + "_"
                + df.loc[has_key, "amount"].astype(str)
            )

            # Assign group IDs to duplicates
            df["dup_group"] = df.groupby("dup_key").ngroup()

            # Mark entries without keys as unique (negative group IDs)
            df.loc[~has_key, "dup_group"] = -1 * (df.index[~has_key] + 1)
        else:
            # No check_no column, all entries are unique
            df["dup_group"] = -1 * (df.index + 1)

        return df

    def _merge_duplicates(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
        """
        Merge duplicate entries intelligently.

        Args:
            df: Dataframe with duplicate groups identified

        Returns:
            Tuple of (merged dataframe, merge audit log)
        """
        merge_log = []
        merged_rows = []

        # Group by duplicate group
        for dup_group, group_df in df.groupby("dup_group"):
            if len(group_df) == 1 or dup_group < 0:
                # Not a duplicate, keep as is
                merged_rows.append(group_df.iloc[0].to_dict())
            else:
                # Merge duplicates
                merged_row, log_entry = self._merge_group(group_df)
                merged_rows.append(merged_row)
                merge_log.append(log_entry)

        merged_df = pd.DataFrame(merged_rows)

        # Clean up temporary columns
        merged_df = merged_df.drop(columns=["dup_key", "dup_group"], errors="ignore")

        return merged_df, merge_log

    def _merge_group(
        self, group_df: pd.DataFrame
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Merge a group of duplicate entries.

        Args:
            group_df: Dataframe with duplicate entries

        Returns:
            Tuple of (merged row dict, audit log entry)
        """
        # Start with the most complete row
        completeness_scores = group_df.notna().sum(axis=1)
        base_idx = completeness_scores.idxmax()
        merged = group_df.loc[base_idx].to_dict()

        # Merge strategy for each field type
        for col in group_df.columns:
            if col in ["dup_key", "dup_group", "source_documents"]:
                continue

            # Special handling for list columns
            if col == "aliases":
                # Combine all aliases
                all_aliases = []
                for val in group_df[col].dropna():
                    if isinstance(val, list):
                        all_aliases.extend(val)
                    else:
                        all_aliases.append(str(val))
                merged[col] = list(set(all_aliases))
                continue

            # For non-list columns, get unique values
            try:
                values = group_df[col].dropna().unique()
            except TypeError:
                # If unhashable type, just take the first non-null value
                values = group_df[col].dropna().tolist()
                if values:
                    merged[col] = values[0]
                continue

            if len(values) == 0:
                continue
            elif len(values) == 1:
                merged[col] = values[0]
            else:
                # Multiple different values - apply merge rules
                if col in [
                    "payment_date",
                    "check_date",
                    "deposit_date",
                    "postmark_date",
                ]:
                    # Use earliest date
                    merged[col] = pd.to_datetime(values).min()

                elif col == "amount":
                    # All amounts should be the same (part of key)
                    merged[col] = values[0]

                elif col in ["address_line_1", "city", "state", "zip"]:
                    # Use longest/most complete address
                    longest = max(values, key=lambda x: len(str(x)))
                    merged[col] = longest

                else:
                    # Default: use most common or first non-null
                    value_counts = group_df[col].value_counts()
                    if len(value_counts) > 0:
                        merged[col] = value_counts.index[0]

        # Track source documents
        if "source_documents" in group_df.columns:
            all_sources = []
            for sources in group_df["source_documents"].dropna():
                if isinstance(sources, list):
                    all_sources.extend(sources)
                else:
                    all_sources.append(str(sources))
            merged["source_documents"] = list(set(all_sources))
        else:
            # If no source tracking, at least count the merges
            merged["source_documents"] = [f"merged_{i}" for i in range(len(group_df))]

        # Create audit log entry
        log_entry = {
            "merge_key": group_df.iloc[0]["dup_key"]
            if "dup_key" in group_df.columns
            else "unknown",
            "merged_count": len(group_df),
            "check_no": merged.get("check_no"),
            "amount": merged.get("amount"),
            "source_documents": merged.get("source_documents", []),
            "merge_timestamp": datetime.now().isoformat(),
        }

        return merged, log_entry

    def _is_not_null(self, value: Any) -> bool:
        """Check if a value is not null/None/NaN, handling various types."""
        if value is None:
            return False
        if isinstance(value, list):
            return len(value) > 0
        if isinstance(value, (str, int, float)):
            try:
                return pd.notna(value)
            except Exception:
                return True
        return True

    def _dataframe_to_donations(self, df: pd.DataFrame) -> List[DonationEntry]:
        """
        Convert dataframe back to DonationEntry objects.

        Args:
            df: Merged dataframe

        Returns:
            List of DonationEntry objects
        """
        donations = []

        for _, row in df.iterrows():
            # Reconstruct the nested structure
            row_dict = row.to_dict()

            # Group fields back into nested structures
            payment_fields = [
                "payment_method",
                "check_no",
                "payment_ref",
                "amount",
                "payment_date",
                "check_date",
                "postmark_date",
                "deposit_date",
                "deposit_method",
                "memo",
            ]
            payment_info = {
                k: v
                for k, v in row_dict.items()
                if k in payment_fields and self._is_not_null(v)
            }

            payer_fields = ["aliases", "salutation", "organization_name", "name"]
            payer_info = {
                k: v
                for k, v in row_dict.items()
                if k in payer_fields and self._is_not_null(v)
            }

            # If we have aliases but no name, use the first alias as name
            if "aliases" in payer_info and "name" not in payer_info:
                aliases = payer_info["aliases"]
                if isinstance(aliases, list) and len(aliases) > 0:
                    payer_info["name"] = aliases[0]

            # Handle contact info with nested address
            contact_info = {}

            # Extract address fields
            address_fields = {
                "street1": row_dict.get("address_line_1"),
                "city": row_dict.get("city"),
                "state": row_dict.get("state"),
                "postal_code": row_dict.get("zip"),
            }
            # Only include address if at least one field is present
            address_data = {
                k: v for k, v in address_fields.items() if self._is_not_null(v)
            }
            if address_data:
                contact_info["address"] = address_data

            # Add email and phone
            if self._is_not_null(row_dict.get("email")):
                contact_info["email"] = row_dict.get("email")
            if self._is_not_null(row_dict.get("phone")):
                contact_info["phone"] = row_dict.get("phone")

            # Create DonationEntry
            donation = DonationEntry(
                payment_info=payment_info if payment_info else None,
                payer_info=payer_info if payer_info else None,
                contact_info=contact_info if contact_info else None,
                source_documents=row_dict.get("source_documents", []),
                confidence_scores=row_dict.get("confidence_scores"),
            )

            donations.append(donation)

        return donations
