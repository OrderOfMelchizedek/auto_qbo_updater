"""Custom exceptions for the application."""
from typing import Any, Dict, Optional


class DonationProcessingError(Exception):
    """Base exception for all donation processing errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize exception with message and optional details.

        Args:
            message: Error message
            details: Optional dictionary with additional error details
        """
        super().__init__(message)
        self.details = details or {}


class GeminiExtractionError(DonationProcessingError):
    """Exception raised for errors during Gemini API extraction."""

    pass


class QuickBooksIntegrationError(DonationProcessingError):
    """Exception raised for errors during QuickBooks integration."""

    pass
