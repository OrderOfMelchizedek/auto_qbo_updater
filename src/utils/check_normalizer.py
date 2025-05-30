"""
Check number normalization utility.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def normalize_check_number(check_no: Optional[str]) -> Optional[str]:
    """Normalize check number according to rules:
    - 3-4 digit check numbers: keep leading zeros
    - >4 digit check numbers: remove leading zeros

    Examples:
        079 -> 079
        0026 -> 0026
        0000095214 -> 95214

    Args:
        check_no: Original check number

    Returns:
        Normalized check number
    """
    if not check_no:
        return check_no

    # Convert to string and strip whitespace
    check_str = str(check_no).strip()

    if not check_str:
        return check_str

    # If check number is longer than 4 digits and starts with zeros, remove them
    if len(check_str) > 4 and check_str.startswith("0"):
        normalized = check_str.lstrip("0")
        # Make sure we don't remove all zeros
        if not normalized:
            normalized = "0"
        logger.debug(f"Normalized check number: {check_str} -> {normalized}")
        return normalized

    # For 3-4 digit checks or checks without leading zeros, return as-is
    return check_str
