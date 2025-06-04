"""Unit tests for custom exceptions."""
import pytest

from src.utils.exceptions import (
    DonationProcessingError,
    GeminiExtractionError,
    QuickBooksIntegrationError,
)


def test_donation_processing_error():
    """Test DonationProcessingError base exception."""
    with pytest.raises(DonationProcessingError) as exc_info:
        raise DonationProcessingError("Test error")

    assert str(exc_info.value) == "Test error"
    assert isinstance(exc_info.value, Exception)


def test_gemini_extraction_error_inheritance():
    """Test that GeminiExtractionError inherits from DonationProcessingError."""
    error = GeminiExtractionError("Extraction failed")

    assert isinstance(error, DonationProcessingError)
    assert isinstance(error, Exception)
    assert str(error) == "Extraction failed"


def test_quickbooks_integration_error_inheritance():
    """Test that QuickBooksIntegrationError inherits from DonationProcessingError."""
    error = QuickBooksIntegrationError("QB sync failed")

    assert isinstance(error, DonationProcessingError)
    assert isinstance(error, Exception)
    assert str(error) == "QB sync failed"


def test_exception_with_details():
    """Test exceptions can carry additional details."""
    details = {"document_id": "123", "error_code": "INVALID_FORMAT"}
    error = GeminiExtractionError("Invalid document format", details=details)

    assert hasattr(error, "details")
    assert error.details == details
