"""Validation and deduplication logic for donation entries."""
import re
from collections import defaultdict
from typing import Any, Dict, List, Optional


class DonationValidator:
    """Handles validation and deduplication of donation entries."""

    @staticmethod
    def convert_to_proper_case(text: str) -> str:
        """Convert ALL CAPS text to proper case, handling special cases."""
        if not text or not text.isupper():
            return text

        # Handle special cases like "PO Box", "LLC", etc.
        special_cases = {
            "PO": "PO",
            "LLC": "LLC",
            "INC": "Inc",
            "JR": "Jr",
            "SR": "Sr",
            "II": "II",
            "III": "III",
            "IV": "IV",
        }

        words = text.split()
        result = []

        for word in words:
            upper_word = word.upper()
            if upper_word in special_cases:
                result.append(special_cases[upper_word])
            else:
                # Title case the word
                result.append(word.capitalize())

        return " ".join(result)

    @staticmethod
    def clean_check_number(check_num: Optional[str]) -> Optional[str]:
        """Remove leading zeros from check numbers if > 5 digits and numeric."""
        if not check_num:
            return check_num

        # Only strip leading zeros if check number > 5 digits and is numeric
        if len(check_num) > 5 and check_num.isdigit():
            cleaned = check_num.lstrip("0")
            # If all zeros (after stripping), return single zero
            return cleaned if cleaned else "0"
        else:
            # For check numbers with 5 or fewer digits, or non-numeric, return as is
            return check_num

    @staticmethod
    def normalize_zip_code(zip_code: Optional[str]) -> Optional[str]:
        """Normalize ZIP codes - preserve leading zeros, ignore extensions."""
        if not zip_code:
            return zip_code

        # Remove any non-digit characters except dash
        cleaned = re.sub(r"[^\d-]", "", zip_code)

        # Split on dash to separate main ZIP from extension
        parts = cleaned.split("-")
        main_zip = parts[0]

        # Ensure 5 digits with leading zeros if needed
        if main_zip and len(main_zip) <= 5:
            main_zip = main_zip.zfill(5)

        return main_zip

    def validate_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and clean a single donation entry.

        Args:
            entry: Raw donation entry from Gemini extraction

        Returns:
            Validated and cleaned entry
        """
        validated = entry.copy()

        # Validate PaymentInfo
        if "PaymentInfo" in validated:
            payment = validated["PaymentInfo"]

            # Clean check number
            if "Payment_Ref" in payment and payment.get("Payment_Method") in [
                "handwritten check",
                "printed check",
            ]:
                payment["Payment_Ref"] = self.clean_check_number(payment["Payment_Ref"])

            # Ensure amount is a float
            if "Amount" in payment:
                try:
                    payment["Amount"] = float(payment["Amount"])
                except (ValueError, TypeError):
                    payment["Amount"] = None

        # Validate PayerInfo
        if "PayerInfo" in validated:
            payer = validated["PayerInfo"]

            # Convert ALL CAPS fields to proper case
            for field in ["Salutation", "Organization_Name"]:
                if field in payer and payer[field]:
                    payer[field] = self.convert_to_proper_case(payer[field])

            # Handle aliases
            if "Aliases" in payer and isinstance(payer["Aliases"], list):
                payer["Aliases"] = [
                    self.convert_to_proper_case(alias) for alias in payer["Aliases"]
                ]

        # Validate ContactInfo
        if "ContactInfo" in validated:
            contact = validated["ContactInfo"]

            # Convert address fields to proper case
            for field in ["Address_Line_1", "City"]:
                if field in contact and contact[field]:
                    contact[field] = self.convert_to_proper_case(contact[field])

            # Normalize ZIP code
            if "ZIP" in contact:
                contact["ZIP"] = self.normalize_zip_code(contact["ZIP"])

            # Clean phone number (basic - remove non-digits)
            if "Phone" in contact and contact["Phone"]:
                contact["Phone"] = re.sub(r"\D", "", contact["Phone"])

        return validated

    def is_valid_entry(self, entry: Dict[str, Any]) -> bool:
        """
        Check if entry has required fields (Payment_Ref and Amount).

        Args:
            entry: Donation entry to check

        Returns:
            True if entry has required fields, False otherwise
        """
        if "PaymentInfo" not in entry:
            return False

        payment = entry["PaymentInfo"]

        # Check required fields
        if not payment.get("Payment_Ref") or payment.get("Amount") is None:
            return False

        # Amount must be positive
        try:
            amount = float(payment.get("Amount", 0))
            if amount <= 0:
                return False
        except (ValueError, TypeError):
            return False

        return True

    def deduplicate_entries(
        self, entries: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Deduplicate donation entries using Payment_Ref + Amount as key.

        Merges duplicate entries to create most complete record.

        Args:
            entries: List of donation entries

        Returns:
            Deduplicated list of entries
        """
        # Group by unique key (Payment_Ref + Amount)
        grouped = defaultdict(list)

        for entry in entries:
            if not self.is_valid_entry(entry):
                continue

            payment = entry["PaymentInfo"]
            # Normalize payment ref for comparison (remove leading zeros)
            ref = payment["Payment_Ref"]
            if ref and ref.isdigit():
                ref = ref.lstrip("0") or "0"
            key = (ref, float(payment["Amount"]))
            grouped[key].append(entry)

        # Merge duplicates
        deduplicated = []
        for duplicates in grouped.values():
            if len(duplicates) == 1:
                deduplicated.append(duplicates[0])
            else:
                merged = self._merge_entries(duplicates)
                deduplicated.append(merged)

        return deduplicated

    def _merge_entries(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge multiple entries into one complete record.

        Later entries take precedence for non-empty values.

        Args:
            entries: List of duplicate entries to merge

        Returns:
            Merged entry with most complete data
        """
        merged = entries[0].copy()

        for entry in entries[1:]:
            # Merge PaymentInfo
            if "PaymentInfo" in entry:
                for key, value in entry["PaymentInfo"].items():
                    if value and (
                        key not in merged["PaymentInfo"]
                        or not merged["PaymentInfo"][key]
                    ):
                        merged["PaymentInfo"][key] = value

            # Merge PayerInfo
            if "PayerInfo" in entry:
                if "PayerInfo" not in merged:
                    merged["PayerInfo"] = {}

                for key, value in entry["PayerInfo"].items():
                    if key == "Aliases":
                        # Combine aliases lists
                        existing = set(merged.get("PayerInfo", {}).get("Aliases", []))
                        new = set(value) if isinstance(value, list) else {value}
                        merged["PayerInfo"]["Aliases"] = list(existing | new)
                    elif value and (
                        key not in merged["PayerInfo"] or not merged["PayerInfo"][key]
                    ):
                        merged["PayerInfo"][key] = value

            # Merge ContactInfo
            if "ContactInfo" in entry:
                if "ContactInfo" not in merged:
                    merged["ContactInfo"] = {}

                for key, value in entry["ContactInfo"].items():
                    if value and (
                        key not in merged["ContactInfo"]
                        or not merged["ContactInfo"][key]
                    ):
                        merged["ContactInfo"][key] = value

        return merged

    def process_donations(
        self, raw_entries: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Process donation entries through validation and deduplication.

        Args:
            raw_entries: List of raw donation entries from Gemini

        Returns:
            List of validated and deduplicated entries
        """
        # First validate and clean each entry
        validated_entries = [self.validate_entry(entry) for entry in raw_entries]

        # Then deduplicate (this already filters invalid entries)
        deduplicated = self.deduplicate_entries(validated_entries)

        return deduplicated
