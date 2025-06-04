"""Gemini API integration for document extraction."""
import base64
import json
import logging
from typing import Any, Dict, Optional

import google.generativeai as genai

from src.config.settings import settings
from src.models.document import GeminiExtractionResponse
from src.utils.exceptions import DonationProcessingError

logger = logging.getLogger(__name__)


class GeminiExtractionError(DonationProcessingError):
    """Exception raised for Gemini extraction errors."""

    pass


class GeminiExtractor:
    """Service for extracting donation information using Google Gemini API."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini extractor.

        Args:
            api_key: Optional API key (defaults to settings)
        """
        self.api_key = api_key or settings.GEMINI_API_KEY
        if not self.api_key:
            raise GeminiExtractionError(
                "GEMINI_API_KEY not configured", details={"config": "missing_api_key"}
            )

        # Configure the API
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel("gemini-1.5-flash")

    def extract_from_image(
        self,
        image_data: bytes,
        document_type: Optional[str] = None,
        include_confidence: bool = True,
    ) -> GeminiExtractionResponse:
        """
        Extract donation information from an image.

        Args:
            image_data: Image bytes
            document_type: Hint about document type (check, envelope, etc.)
            include_confidence: Whether to include confidence scores

        Returns:
            GeminiExtractionResponse with extracted data

        Raises:
            GeminiExtractionError: If extraction fails
        """
        try:
            # Prepare the extraction prompt
            prompt = self._build_extraction_prompt(document_type, include_confidence)

            # Prepare image for API
            encoded_image = base64.b64encode(image_data).decode("utf-8")

            # Create the request content
            response = self.model.generate_content(
                [
                    prompt,
                    {
                        "mime_type": "image/png",
                        "data": encoded_image,
                    },
                ],
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=self._get_response_schema(),
                ),
            )

            # Parse the response
            result = json.loads(response.text)

            # Create response object
            extraction_response = GeminiExtractionResponse(
                payment_info=result.get("payment_info"),
                payer_info=result.get("payer_info"),
                contact_info=result.get("contact_info"),
                confidence_scores=result.get("confidence_scores")
                if include_confidence
                else None,
                document_type=result.get("document_type") or document_type,
                raw_response=result,
            )

            logger.info(f"Extracted data from {document_type or 'unknown'} document")
            return extraction_response

        except Exception as e:
            logger.error(f"Gemini extraction failed: {str(e)}")
            raise GeminiExtractionError(
                f"Failed to extract data: {str(e)}", details={"error": str(e)}
            )

    def _build_extraction_prompt(
        self, document_type: Optional[str], include_confidence: bool
    ) -> str:
        """
        Build the extraction prompt for Gemini.

        Args:
            document_type: Type of document
            include_confidence: Whether to request confidence scores

        Returns:
            Prompt string
        """
        base_prompt = """Extract donation information from this document.

Rules:
1. Extract all visible text related to donations, payments, and contact information
2. For checks: Use the numeric amount box for the amount, check number from top right
3. For envelopes: Use return address as the authoritative donor address
4. Strip leading zeros from check numbers if they're longer than 4 digits
5. Validate that amounts are positive numbers
6. Parse dates in any common format and return as YYYY-MM-DD
7. For addresses, ensure proper formatting with city, state, and ZIP
8. If information is unclear or partially visible, still attempt extraction
9. Identify the document type (check, envelope, receipt, etc.)
"""

        if document_type:
            base_prompt += f"\nDocument type hint: {document_type}"

        if include_confidence:
            base_prompt += """
10. Include confidence scores (0-1) for each extracted field
11. Use 1.0 for clearly visible, 0.8-0.9 for slightly unclear, 0.5-0.7 for guessed
"""

        return base_prompt

    def _get_response_schema(self) -> Dict[str, Any]:
        """
        Get the JSON schema for Gemini response.

        Returns:
            Response schema dictionary
        """
        return {
            "type": "object",
            "properties": {
                "payment_info": {
                    "type": "object",
                    "properties": {
                        "payment_method": {
                            "type": "string",
                            "enum": ["check", "cash", "online", "other"],
                        },
                        "check_no": {"type": "string", "nullable": True},
                        "payment_ref": {"type": "string", "nullable": True},
                        "amount": {"type": "number"},
                        "payment_date": {
                            "type": "string",
                            "format": "date",
                            "nullable": True,
                        },
                        "check_date": {
                            "type": "string",
                            "format": "date",
                            "nullable": True,
                        },
                        "postmark_date": {
                            "type": "string",
                            "format": "date",
                            "nullable": True,
                        },
                        "deposit_date": {
                            "type": "string",
                            "format": "date",
                            "nullable": True,
                        },
                        "deposit_method": {"type": "string", "nullable": True},
                        "memo": {"type": "string", "nullable": True},
                    },
                    "required": ["payment_method", "amount"],
                },
                "payer_info": {
                    "type": "object",
                    "properties": {
                        "aliases": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "salutation": {"type": "string", "nullable": True},
                        "organization_name": {"type": "string", "nullable": True},
                    },
                },
                "contact_info": {
                    "type": "object",
                    "properties": {
                        "address_line_1": {"type": "string", "nullable": True},
                        "city": {"type": "string", "nullable": True},
                        "state": {
                            "type": "string",
                            "pattern": "^[A-Z]{2}$",
                            "nullable": True,
                        },
                        "zip": {
                            "type": "string",
                            "pattern": r"^\d{5}(-\d{4})?$",
                            "nullable": True,
                        },
                        "email": {
                            "type": "string",
                            "format": "email",
                            "nullable": True,
                        },
                        "phone": {"type": "string", "nullable": True},
                    },
                },
                "confidence_scores": {
                    "type": "object",
                    "additionalProperties": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                    },
                    "nullable": True,
                },
                "document_type": {"type": "string", "nullable": True},
            },
            "required": ["payment_info"],
        }

    def extract_from_csv(self, csv_content: str) -> Dict[str, Any]:
        """
        Extract donation information from CSV content.

        Args:
            csv_content: CSV file content as string

        Returns:
            Dictionary with extracted data

        Note:
            CSV extraction doesn't use Gemini API, it's handled separately
        """
        # CSV extraction is handled differently - this is a placeholder
        # The actual implementation would parse CSV and map columns
        raise NotImplementedError(
            "CSV extraction should be handled by a separate service"
        )
