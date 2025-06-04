"""File handling utilities."""
import os
from typing import Optional

from src.models.document import FileType


def validate_file_type(filename: str) -> Optional[str]:
    """
    Validate file type based on extension.

    Args:
        filename: Name of the file

    Returns:
        File type if valid, None otherwise
    """
    if not filename:
        return None

    extension = os.path.splitext(filename)[1].lower().lstrip(".")

    valid_extensions = {
        "jpg": FileType.JPG,
        "jpeg": FileType.JPEG,
        "png": FileType.PNG,
        "pdf": FileType.PDF,
        "csv": FileType.CSV,
    }

    return valid_extensions.get(extension)


def validate_file_size(size_bytes: int, max_mb: int = 20) -> bool:
    """
    Validate file size.

    Args:
        size_bytes: File size in bytes
        max_mb: Maximum allowed size in megabytes

    Returns:
        True if valid, False otherwise
    """
    max_bytes = max_mb * 1024 * 1024
    return 0 < size_bytes <= max_bytes


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe storage.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    # Remove path components
    filename = os.path.basename(filename)

    # Replace problematic characters
    invalid_chars = '<>:"|?*'
    for char in invalid_chars:
        filename = filename.replace(char, "_")

    # Limit length
    name, ext = os.path.splitext(filename)
    if len(name) > 100:
        name = name[:100]

    return name + ext


def get_mime_type(filename: str) -> str:
    """
    Get MIME type based on file extension.

    Args:
        filename: Name of the file

    Returns:
        MIME type string
    """
    extension = os.path.splitext(filename)[1].lower().lstrip(".")

    mime_types = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "pdf": "application/pdf",
        "csv": "text/csv",
    }

    return mime_types.get(extension, "application/octet-stream")
