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

from models.payment import PaymentRecord

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
        self.model_name = model_name if model_name is not None else "gemini-2.0-flash-exp"
        genai.configure(api_key=api_key)

        # Initialize prompt managers for both old and new prompts
        self.prompt_manager = PromptManager(prompt_dir="lib/prompts_archive")
        self.structured_prompt_manager = PromptManager(prompt_dir="lib/current_prompts")

        logger.info(f"Initialized Gemini structured service with model: {self.model_name}")

        # Initialize rate limiter
        self._rate_limiter = RateLimiter(
            per_minute_limit=self.RATE_LIMIT_PER_MINUTE,
            per_hour_limit=self.RATE_LIMIT_PER_HOUR,
        )

    def _check_rate_limit(self):
        """Check and enforce rate limits for Gemini API calls."""
        try:
            self._rate_limiter.check_and_record()
        except RateLimitExceededException as e:
            logger.warning(f"Rate limit reached: {e}")
            raise

    def _prepare_image_part(self, image_path: str):
        """Prepare an image for Gemini API.

        Args:
            image_path: Path to the image file

        Returns:
            PIL Image object(s) for Gemini
        """
        file_ext = os.path.splitext(image_path)[1].lower()

        if file_ext == ".pdf":
            # For PDFs, we'll handle batch processing differently
            # Just return the path and a flag indicating it's a PDF
            return ("pdf", image_path)
        else:
            # Handle regular image files
            try:
                image = Image.open(image_path)
                logger.info(f"Successfully opened image file: {image_path}")
                return ("image", [image])  # Return as list for consistency
            except Exception as e:
                logger.error(f"Error loading image {image_path}: {e}")
                raise

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

        # Check if we have any PDFs that need batch processing
        pdf_paths = []
        regular_images = []

        try:
            for image_path in image_paths:
                file_type, content = self._prepare_image_part(image_path)
                if file_type == "pdf":
                    pdf_paths.append(content)
                else:
                    regular_images.extend(content)

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

            # Add JSON format instructions
            json_format_prompt = self._get_json_format_prompt(response_schema, expect_list)

            # If we have PDFs, process them with batch processing
            if pdf_paths:
                all_results = []

                for pdf_path in pdf_paths:
                    pdf_results = self._process_pdf_in_batches(
                        pdf_path, prompt, json_format_prompt, model, response_model, expect_list
                    )
                    all_results.extend(pdf_results)

                # Add any regular images
                if regular_images:
                    content_parts.extend(regular_images)
                    content_parts.insert(1, json_format_prompt)

                    response = model.generate_content(
                        contents=content_parts,
                        generation_config=genai.GenerationConfig(
                            temperature=0.1,
                            max_output_tokens=2048,
                        ),
                    )

                    image_results = self._parse_text_response(response.text, response_model, expect_list)
                    if isinstance(image_results, list):
                        all_results.extend(image_results)
                    else:
                        all_results.append(image_results)

                return all_results if expect_list else all_results[0] if all_results else None

            else:
                # No PDFs, just process regular images
                content_parts.extend(regular_images)
                content_parts.insert(1, json_format_prompt)

                response = model.generate_content(
                    contents=content_parts,
                    generation_config=genai.GenerationConfig(
                        temperature=0.1,
                        max_output_tokens=2048,
                    ),
                )

                return self._parse_text_response(response.text, response_model, expect_list)

        except Exception as e:
            logger.error(f"Error in structured extraction: {str(e)}")
            raise GeminiAPIException(
                message=f"Failed to extract payment data: {str(e)}", status_code=None, response_text=str(e)
            )
        finally:
            # No cleanup needed for PIL images
            pass

    def _get_json_format_prompt(self, response_schema: Type[BaseModel], expect_list: bool) -> str:
        """Generate JSON format instructions based on the Pydantic model."""
        if expect_list:
            return """
IMPORTANT: Return your response as a JSON object with a 'payments' array containing payment records.
Each payment record must have these fields:
- payment_info: Object with these REQUIRED fields:
  - payment_method: "handwritten_check", "printed_check", or "online_payment"
  - check_no: Check number (for checks) or null
  - payment_ref: Payment reference (for online) or null
  - amount: Numeric amount
  - payment_date: Date in YYYY-MM-DD format or null
  - check_date: Date on check in YYYY-MM-DD format or null
  - deposit_date: Deposit date in YYYY-MM-DD format or null
  - postmark_date: Postmark date in YYYY-MM-DD format or null
  - deposit_method: "ATM Deposit", "Mobile Deposit", etc. or null
  - memo: Memo text or null
- payer_info: Object with EITHER aliases (array of name variations) OR organization_name
  - For individuals: aliases must be a non-empty array like ["John Smith", "Smith, John"]
  - For organizations: organization_name must be provided, aliases can be null
- contact_info: Object with address_line_1, city, state, zip, email, phone (all can be null)

Example format:
{
  "payments": [
    {
      "payment_info": {
        "payment_method": "handwritten_check",
        "check_no": "1234",
        "amount": 100.00,
        "payment_date": "2025-05-30",
        "check_date": "2025-05-30",
        "deposit_date": "2025-05-30",
        "postmark_date": null,
        "deposit_method": "ATM Deposit",
        "memo": null
      },
      "payer_info": {
        "aliases": ["John Smith", "Smith, John"],
        "organization_name": null
      },
      "contact_info": {
        "address_line_1": "123 Main St",
        "city": "Springfield",
        "state": "IL",
        "zip": "62701"
      }
    }
  ]
}
"""
        else:
            return """
IMPORTANT: Return your response as a JSON object with payment information.
The response must have these fields:
- payment_info: Object with these REQUIRED fields:
  - payment_method: "handwritten_check", "printed_check", or "online_payment"
  - check_no: Check number (for checks) or null
  - payment_ref: Payment reference (for online) or null
  - amount: Numeric amount
  - payment_date: Date in YYYY-MM-DD format or null
  - check_date: Date on check in YYYY-MM-DD format or null
  - deposit_date: Deposit date in YYYY-MM-DD format or null
  - postmark_date: Postmark date in YYYY-MM-DD format or null
  - deposit_method: "ATM Deposit", "Mobile Deposit", etc. or null
  - memo: Memo text or null
- payer_info: Object with EITHER aliases (array of name variations) OR organization_name
  - For individuals: aliases must be a non-empty array like ["John Smith", "Smith, John"]
  - For organizations: organization_name must be provided, aliases can be null
- contact_info: Object with address_line_1, city, state, zip, email, phone (all can be null)

Example format:
{
  "payment_info": {
    "payment_method": "handwritten_check",
    "check_no": "1234",
    "payment_ref": null,
    "amount": 100.00,
    "payment_date": "2025-05-30",
    "check_date": "2025-05-30",
    "deposit_date": "2025-05-30",
    "postmark_date": null,
    "deposit_method": "ATM Deposit",
    "memo": null
  },
  "payer_info": {
    "aliases": ["John Smith", "Smith, John"],
    "organization_name": null
  },
  "contact_info": {
    "address_line_1": "123 Main St",
    "city": "Springfield",
    "state": "IL",
    "zip": "62701"
  }
}
"""

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

            # Log what we extracted for debugging
            logger.info(f"Parsing JSON with {len(json_text) if isinstance(json_text, list) else 1} items")
            if not isinstance(json_text, list):
                logger.debug(
                    f"First item: {json.dumps(json_text if not isinstance(json_text, dict) or 'payments' not in json_text else json_text.get('payments', [{}])[0], indent=2)[:500]}"
                )

            if expect_list:
                if isinstance(json_text, dict) and "payments" in json_text:
                    # Wrapped format with payments array
                    results = []
                    for item in json_text["payments"]:
                        try:
                            results.append(response_model(**item))
                        except Exception as e:
                            logger.error(f"Failed to parse payment item: {e}")
                            logger.error(f"Item data: {json.dumps(item, indent=2)}")
                            raise
                    return results
                elif isinstance(json_text, list):
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
            # Log the problematic JSON for debugging
            if "json_text" in locals():
                logger.error(f"Problematic JSON: {json.dumps(json_text, indent=2)[:1000]}")
            raise GeminiAPIException(
                message=f"Failed to parse response: {str(e)}",
                status_code=None,
                response_text=text if "text" in locals() else str(e),
            )

    def _process_pdf_in_batches(
        self,
        pdf_path: str,
        base_prompt: str,
        json_format_prompt: str,
        model,
        response_model: Type[BaseModel],
        expect_list: bool,
    ) -> List[BaseModel]:
        """Process PDF in batches like the legacy code does.

        Args:
            pdf_path: Path to PDF file
            base_prompt: Base extraction prompt
            json_format_prompt: JSON format instructions
            model: Gemini model instance
            response_model: Pydantic model for parsing
            expect_list: Whether to expect multiple records

        Returns:
            List of extracted payment records
        """
        import fitz  # PyMuPDF
        import PyPDF2

        all_results = []

        try:
            # Open PDF with PyMuPDF for images
            pdf_doc = fitz.open(pdf_path)

            # Try to open with PyPDF2 for text extraction
            pdf_reader = None
            try:
                pdf_reader = PyPDF2.PdfReader(pdf_path)
            except Exception as e:
                logger.warning(f"Could not open PDF for text extraction: {e}")

            # Process PDF in batches
            logger.info(f"PDF has {len(pdf_doc)} pages - processing in batches")

            # Maximum pages per batch (same as legacy)
            BATCH_SIZE = 15

            # Calculate number of batches
            num_batches = (len(pdf_doc) + BATCH_SIZE - 1) // BATCH_SIZE

            # Process each batch
            for batch_num in range(num_batches):
                batch_start = batch_num * BATCH_SIZE
                batch_end = min(batch_start + BATCH_SIZE, len(pdf_doc))

                logger.info(f"Processing batch {batch_num + 1} of {num_batches} (pages {batch_start + 1}-{batch_end})")

                # Extract text from this batch
                batch_text = ""
                if pdf_reader:
                    try:
                        for page_num in range(batch_start, batch_end):
                            if page_num < len(pdf_reader.pages):
                                page_text = pdf_reader.pages[page_num].extract_text()
                                if page_text:
                                    batch_text += f"\n--- Page {page_num + 1} ---\n{page_text}\n"
                    except Exception as e:
                        logger.warning(f"Error extracting text from batch: {e}")

                # Build prompt for this batch
                batch_prompt = base_prompt

                # Add text context if available
                if batch_text.strip():
                    logger.info(f"Batch {batch_num + 1} contains extractable text - adding as context")
                    # Add PDF text context
                    batch_prompt += f"\n\nPDF Text Content:\n{batch_text}"

                # Add batch info
                batch_info = f"\nProcessing pages {batch_start + 1} to {batch_end} of {len(pdf_doc)}."

                # Create content parts
                content_parts = [batch_prompt + batch_info, json_format_prompt]

                # Convert pages to images and add to content
                for page_num in range(batch_start, batch_end):
                    page = pdf_doc[page_num]

                    # Convert page to image with good resolution
                    pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))  # 1.5x zoom
                    img_data = pix.tobytes("png")

                    # Load as PIL image
                    image = Image.open(io.BytesIO(img_data))
                    content_parts.append(image)

                # Call Gemini API for this batch
                try:
                    self._check_rate_limit()

                    logger.info(f"Sending batch of {batch_end - batch_start} pages to Gemini")

                    batch_response = model.generate_content(
                        contents=content_parts,
                        generation_config=genai.GenerationConfig(
                            temperature=0.1,
                            max_output_tokens=2048,
                        ),
                    )

                    # Parse response for this batch
                    if batch_response.text:
                        logger.info(f"Received response for batch {batch_num + 1}")

                        try:
                            batch_results = self._parse_text_response(
                                batch_response.text, response_model, True  # Always expect list for batches
                            )

                            if isinstance(batch_results, list):
                                logger.info(f"Batch {batch_num + 1} extracted {len(batch_results)} payments")
                                all_results.extend(batch_results)
                            else:
                                all_results.append(batch_results)

                        except Exception as e:
                            logger.error(f"Error parsing batch {batch_num + 1} response: {e}")

                except Exception as e:
                    logger.error(f"Error processing batch {batch_num + 1}: {e}")

            pdf_doc.close()
            logger.info(f"Successfully extracted {len(all_results)} payments from PDF")

        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            raise

        return all_results

    def verify_customer_match(self, extracted_donor: Dict[str, Any], qbo_customer: Dict[str, Any]) -> Dict[str, Any]:
        """Verify if the QuickBooks customer is a match for the extracted donor data.

        Args:
            extracted_donor: Dictionary of extracted donor data
            qbo_customer: Dictionary of QuickBooks customer data

        Returns:
            Dictionary containing verification results
        """
        # TODO: Implement structured customer verification
        # For now, return a simple match
        return {"is_match": True, "confidence": 0.95, "enhanced_data": extracted_donor}

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
