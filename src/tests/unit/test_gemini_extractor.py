"""Tests for Gemini extraction service."""
import base64
import json
from unittest.mock import MagicMock, patch

import pytest

from src.models.document import GeminiExtractionResponse
from src.services.extraction.gemini_extractor import (
    GeminiExtractionError,
    GeminiExtractor,
)


@pytest.fixture
def mock_genai():
    """Mock Google Generative AI module."""
    with patch("src.services.extraction.gemini_extractor.genai") as mock:
        yield mock


@pytest.fixture
def sample_extraction_response():
    """Sample extraction response data."""
    return {
        "payment_info": {
            "payment_method": "check",
            "check_no": "1234",
            "amount": 100.00,
            "payment_date": "2025-01-15",
        },
        "payer_info": {
            "aliases": ["John Doe", "J. Doe"],
            "salutation": "Mr.",
        },
        "contact_info": {
            "address_line_1": "123 Main St",
            "city": "Anytown",
            "state": "CA",
            "zip": "12345",
            "email": "john@example.com",
        },
        "confidence_scores": {
            "amount": 1.0,
            "check_no": 0.95,
            "payer_name": 0.9,
        },
        "document_type": "check",
    }


class TestGeminiExtractor:
    """Test Gemini extractor functionality."""

    def test_init_with_api_key(self, mock_genai):
        """Test initialization with API key."""
        api_key = "test-api-key"
        extractor = GeminiExtractor(api_key=api_key)

        assert extractor.api_key == api_key
        mock_genai.configure.assert_called_once_with(api_key=api_key)

    @patch("src.services.extraction.gemini_extractor.settings")
    def test_init_from_settings(self, mock_settings, mock_genai):
        """Test initialization from settings."""
        mock_settings.GEMINI_API_KEY = "settings-api-key"
        extractor = GeminiExtractor()

        assert extractor.api_key == "settings-api-key"
        mock_genai.configure.assert_called_once_with(api_key="settings-api-key")

    @patch("src.services.extraction.gemini_extractor.settings")
    def test_init_missing_api_key(self, mock_settings):
        """Test initialization fails without API key."""
        mock_settings.GEMINI_API_KEY = None

        with pytest.raises(GeminiExtractionError) as exc_info:
            GeminiExtractor()

        assert "GEMINI_API_KEY not configured" in str(exc_info.value)

    def test_extract_from_image_success(self, mock_genai, sample_extraction_response):
        """Test successful image extraction."""
        # Setup mock
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps(sample_extraction_response)
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        # Create extractor
        extractor = GeminiExtractor(api_key="test-key")

        # Test extraction
        image_data = b"fake image data"
        result = extractor.extract_from_image(image_data, document_type="check")

        # Verify result
        assert isinstance(result, GeminiExtractionResponse)
        assert result.payment_info["amount"] == 100.00
        assert result.payment_info["check_no"] == "1234"
        assert result.document_type == "check"
        assert result.confidence_scores is not None

        # Verify API call
        mock_model.generate_content.assert_called_once()
        call_args = mock_model.generate_content.call_args[0][0]
        assert len(call_args) == 2  # Prompt and image
        assert "Extract donation information" in call_args[0]
        assert call_args[1]["mime_type"] == "image/png"
        assert call_args[1]["data"] == base64.b64encode(image_data).decode("utf-8")

    def test_extract_without_confidence(self, mock_genai):
        """Test extraction without confidence scores."""
        # Setup mock
        mock_model = MagicMock()
        mock_response = MagicMock()
        response_data = {
            "payment_info": {
                "payment_method": "cash",
                "amount": 50.00,
            }
        }
        mock_response.text = json.dumps(response_data)
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        # Create extractor
        extractor = GeminiExtractor(api_key="test-key")

        # Test extraction
        result = extractor.extract_from_image(b"image data", include_confidence=False)

        assert result.confidence_scores is None
        assert result.payment_info["amount"] == 50.00

    def test_extract_with_document_type_hint(self, mock_genai):
        """Test extraction with document type hint."""
        # Setup mock
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps(
            {"payment_info": {"amount": 75, "payment_method": "check"}}
        )
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        # Create extractor
        extractor = GeminiExtractor(api_key="test-key")

        # Test extraction
        extractor.extract_from_image(b"image data", document_type="envelope")

        # Check that document type hint was included in prompt
        call_args = mock_model.generate_content.call_args[0][0]
        assert "Document type hint: envelope" in call_args[0]

    def test_extract_api_error(self, mock_genai):
        """Test handling of API errors."""
        # Setup mock to raise error
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception("API Error")
        mock_genai.GenerativeModel.return_value = mock_model

        # Create extractor
        extractor = GeminiExtractor(api_key="test-key")

        # Test extraction
        with pytest.raises(GeminiExtractionError) as exc_info:
            extractor.extract_from_image(b"image data")

        assert "Failed to extract data" in str(exc_info.value)

    def test_extract_invalid_json_response(self, mock_genai):
        """Test handling of invalid JSON response."""
        # Setup mock with invalid JSON
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "invalid json"
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        # Create extractor
        extractor = GeminiExtractor(api_key="test-key")

        # Test extraction
        with pytest.raises(GeminiExtractionError):
            extractor.extract_from_image(b"image data")

    def test_build_extraction_prompt(self, mock_genai):
        """Test prompt building."""
        extractor = GeminiExtractor(api_key="test-key")

        # Test basic prompt
        prompt = extractor._build_extraction_prompt(None, False)
        assert "Extract donation information" in prompt
        assert "confidence scores" not in prompt

        # Test with confidence
        prompt = extractor._build_extraction_prompt(None, True)
        assert "confidence scores" in prompt
        assert "0-1" in prompt

        # Test with document type
        prompt = extractor._build_extraction_prompt("check", False)
        assert "Document type hint: check" in prompt

    def test_get_response_schema(self, mock_genai):
        """Test response schema generation."""
        extractor = GeminiExtractor(api_key="test-key")
        schema = extractor._get_response_schema()

        # Verify schema structure
        assert schema["type"] == "object"
        assert "payment_info" in schema["properties"]
        assert "payer_info" in schema["properties"]
        assert "contact_info" in schema["properties"]

        # Verify payment_info requirements
        payment_info = schema["properties"]["payment_info"]
        assert "payment_method" in payment_info["properties"]
        assert "amount" in payment_info["properties"]
        assert payment_info["required"] == ["payment_method", "amount"]

        # Verify enums
        payment_method = payment_info["properties"]["payment_method"]
        assert payment_method["enum"] == ["check", "cash", "online", "other"]

    def test_extract_from_csv_not_implemented(self, mock_genai):
        """Test CSV extraction raises NotImplementedError."""
        extractor = GeminiExtractor(api_key="test-key")

        with pytest.raises(NotImplementedError):
            extractor.extract_from_csv("csv content")
