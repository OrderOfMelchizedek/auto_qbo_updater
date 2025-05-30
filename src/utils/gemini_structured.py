"""
Enhanced Gemini service with structured output support using Pydantic models.
This module provides structured extraction capabilities while maintaining
backward compatibility with the existing extraction methods.
"""

import base64
import io
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Type, Union

import google.generativeai as genai
from PIL import Image
from pydantic import BaseModel

from src.models.payment import PaymentRecord

from .exceptions import GeminiAPIException, RetryableException
from .prompt_manager import PromptManager
from .rate_limiter import RateLimiter, RateLimitExceededException
from .retry import retry_on_failure

# Configure logger
logger = logging.getLogger(__name__)


class GeminiStructuredService:
    """Enhanced Gemini service with structured output support."""

    # Rate limiting configuration
    RATE_LIMIT_PER_MINUTE = int(os.environ.get("GEMINI_RATE_LIMIT_PER_MINUTE", "60"))
    RATE_LIMIT_PER_HOUR = int(os.environ.get("GEMINI_RATE_LIMIT_PER_HOUR", "1500"))

    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash-exp"):
        """Initialize the Gemini service with API key and model name.

        Args:
            api_key: Gemini API key
            model_name: Gemini model name (defaults to latest 2.0 flash)
        """
        self.api_key = api_key
        self.model_name = model_name
        genai.configure(api_key=api_key)

        # Initialize prompt managers for both old and new prompts
        self.prompt_manager = PromptManager(prompt_dir="docs/prompts_archive")
        self.structured_prompt_manager = PromptManager(prompt_dir="docs/prompts_structured")

        logger.info(f"Initialized Gemini structured service with model: {self.model_name}")

        # Initialize rate limiter
        self._rate_limiter = RateLimiter(
            per_minute_limit=self.RATE_LIMIT_PER_MINUTE,
            per_hour_limit=self.RATE_LIMIT_PER_HOUR,
        )

    def _check_rate_limit(self):
        """Check and enforce rate limits for Gemini API calls."""
        if not self._rate_limiter.check_rate_limit():
            wait_time = self._rate_limiter.get_wait_time()
            logger.warning(f"Rate limit reached. Waiting {wait_time} seconds before continuing...")
            raise RateLimitExceededException(f"Rate limit reached. Please wait {wait_time} seconds.")

    def _prepare_image_part(self, image_path: str):
        """Prepare an image for Gemini API by uploading it.

        Args:
            image_path: Path to the image file

        Returns:
            Uploaded file part for Gemini
        """
        # Determine MIME type based on file extension
        ext = os.path.splitext(image_path)[1].lower()
        mime_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".pdf": "application/pdf",
        }
        mime_type = mime_map.get(ext, "image/jpeg")

        # Upload file to Gemini
        uploaded_file = genai.upload_file(image_path, mime_type=mime_type)
        return uploaded_file

    @retry_on_failure(max_attempts=3)
    def extract_payment_structured(
        self,
        image_paths: List[str],
        document_type: str = "mixed",
        response_model: Type[BaseModel] = PaymentRecord,
    ) -> Union[PaymentRecord, List[PaymentRecord]]:
        """Extract payment information using structured output.

        Args:
            image_paths: List of paths to images (checks, envelopes, etc.)
            document_type: Type of documents ("check", "envelope", "mixed")
            response_model: Pydantic model for response structure

        Returns:
            Structured payment data as PaymentRecord(s)
        """
        self._check_rate_limit()

        # Prepare prompt based on document type
        prompt_key = f"{document_type}_extraction_prompt"
        prompt = self.structured_prompt_manager.get_prompt(
            prompt_key, default_prompt=self._get_default_structured_prompt(document_type)
        )

        # Prepare content parts
        content_parts = [prompt]

        # Upload and add images
        uploaded_files = []
        try:
            for image_path in image_paths:
                uploaded_file = self._prepare_image_part(image_path)
                uploaded_files.append(uploaded_file)
                content_parts.append(uploaded_file)

            # Configure model with structured output
            model = genai.GenerativeModel(self.model_name)

            # Determine if we expect single or multiple records
            expect_list = len(image_paths) > 1 or document_type == "batch"

            if expect_list:
                # Create a wrapper model for list response
                class PaymentRecordList(BaseModel):
                    payments: List[response_model]

                response_schema = PaymentRecordList
            else:
                response_schema = response_model

            # Generate content with structured output
            response = model.generate_content(
                contents=content_parts,
                generation_config={
                    "response_mime_type": "application/json",
                    "response_schema": response_schema,
                    "temperature": 0.1,  # Low temperature for accuracy
                    "max_output_tokens": 2048,
                },
            )

            # Parse the structured response
            if hasattr(response, "parsed") and response.parsed:
                result = response.parsed
                if expect_list and hasattr(result, "payments"):
                    return result.payments
                return result
            else:
                # Fallback to text parsing if structured parsing fails
                logger.warning("Structured parsing failed, falling back to text parsing")
                return self._parse_text_response(response.text, response_model, expect_list)

        except Exception as e:
            logger.error(f"Error in structured extraction: {str(e)}")
            raise GeminiAPIException(f"Failed to extract payment data: {str(e)}")
        finally:
            # Clean up uploaded files
            for uploaded_file in uploaded_files:
                try:
                    uploaded_file.delete()
                except Exception as e:
                    logger.warning(f"Failed to delete uploaded file: {e}")

    def _parse_text_response(
        self, text: str, response_model: Type[BaseModel], expect_list: bool
    ) -> Union[BaseModel, List[BaseModel]]:
        """Parse text response into structured format.

        Args:
            text: Response text from Gemini
            response_model: Pydantic model to parse into
            expect_list: Whether to expect a list of models

        Returns:
            Parsed model instance(s)
        """
        try:
            # Extract JSON from response
            json_text = self._extract_json_from_text(text)

            if expect_list:
                if isinstance(json_text, list):
                    return [response_model(**item) for item in json_text]
                else:
                    # Single item, wrap in list
                    return [response_model(**json_text)]
            else:
                if isinstance(json_text, list) and len(json_text) > 0:
                    # Multiple items but expecting single, take first
                    return response_model(**json_text[0])
                else:
                    return response_model(**json_text)

        except Exception as e:
            logger.error(f"Failed to parse text response: {e}")
            raise GeminiAPIException(f"Failed to parse response: {str(e)}")

    def _extract_json_from_text(self, text: str) -> Union[Dict, List]:
        """Extract JSON from text response."""
        import re

        # Try to find JSON in code blocks
        json_match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        if json_match:
            json_text = json_match.group(1)
        else:
            # Try to find JSON without code blocks
            json_text = text.strip()

        try:
            return json.loads(json_text)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            logger.error(f"Text that failed to parse: {json_text[:500]}...")
            raise

    def _get_default_structured_prompt(self, document_type: str) -> str:
        """Get default prompt for structured extraction."""
        base_prompt = """
Extract payment information from the provided documents and return structured data.

For checks:
- Identify if handwritten (amount/date handwritten) or printed
- Extract check number (usually upper right corner)
- Extract amount (both numeric and written should match)
- Extract date on check
- Extract memo information
- Extract payer name and address

For envelopes:
- Extract return address (this supersedes check addresses)
- Extract postmark date
- Look for additional contact info (phone, email)
- Note any additional memos

Payment Date Logic:
- Handwritten checks: Use postmark date if available, otherwise check date
- Printed checks: Use the date printed on the check
- Online payments: Use transaction date

Return structured JSON data following the provided schema.
"""

        if document_type == "check":
            return base_prompt + "\nFocus on check information primarily."
        elif document_type == "envelope":
            return base_prompt + "\nFocus on envelope and address information."
        else:
            return base_prompt

    # Backward compatibility methods
    def extract_donation_data(self, file_path: str) -> Optional[Union[Dict, List[Dict]]]:
        """Legacy method for extracting donation data.

        Internally uses structured extraction and converts to legacy format.
        """
        try:
            # Use structured extraction
            payment_records = self.extract_payment_structured(image_paths=[file_path], document_type="mixed")

            # Convert to legacy format
            if isinstance(payment_records, list):
                return [record.to_legacy_format() for record in payment_records]
            else:
                return payment_records.to_legacy_format()

        except Exception as e:
            logger.error(f"Error in legacy extraction: {e}")
            return None

    def verify_customer_match(self, extracted_data: Dict[str, Any], qbo_customer: Dict[str, Any]) -> Dict[str, Any]:
        """Legacy method for verifying customer matches.

        This method is maintained for backward compatibility.
        """
        # Convert legacy format to PaymentRecord if needed
        if "payment_info" not in extracted_data:
            # This is legacy format, convert it
            payment_record = PaymentRecord.from_legacy_format(extracted_data)
        else:
            # Already in new format
            payment_record = PaymentRecord(**extracted_data)

        # Use payer aliases for matching
        payer_names = []
        if payment_record.payer_info.organization_name:
            payer_names.append(payment_record.payer_info.organization_name)
        elif payment_record.payer_info.aliases:
            payer_names.extend(payment_record.payer_info.aliases)

        # Simple verification logic
        qbo_name = qbo_customer.get("DisplayName", "").lower()
        for payer_name in payer_names:
            if payer_name.lower() in qbo_name or qbo_name in payer_name.lower():
                return {
                    "validMatch": True,
                    "matchConfidence": "high",
                    "mismatchReason": None,
                }

        return {
            "validMatch": False,
            "matchConfidence": "none",
            "mismatchReason": "Names do not match sufficiently",
        }
