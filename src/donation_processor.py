"""Simple donation processor that pipes extraction output to validation."""
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

from .geminiservice import extract_donations_from_documents
from .validation import DonationValidator


def process_donation_documents(
    file_paths: List[Union[str, Path]]
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """
    Process donation documents: extract, validate, and deduplicate.

    Args:
        file_paths: List of paths to document files

    Returns:
        Tuple of (processed_donations, metadata_dict)
        metadata_dict contains: raw_count, valid_count, duplicate_count
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

    metadata = {
        "raw_count": raw_count,
        "valid_count": valid_count,
        "duplicate_count": duplicate_count,
    }

    return processed_donations, metadata
