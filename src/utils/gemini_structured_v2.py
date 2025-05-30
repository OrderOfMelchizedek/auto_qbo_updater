"""
Enhanced Gemini service with structured output support using Pydantic models.
V2: Uses smaller batches (5 pages) and combines all files into unified batches.
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


class GeminiStructuredServiceV2:
    """Enhanced Gemini service with structured output support and smaller batches."""

    # Rate limiting configuration
    RATE_LIMIT_PER_MINUTE = int(os.environ.get("GEMINI_RATE_LIMIT_PER_MINUTE", "60"))
    RATE_LIMIT_PER_HOUR = int(os.environ.get("GEMINI_RATE_LIMIT_PER_HOUR", "1500"))

    # Smaller batch size for better accuracy
    BATCH_SIZE = 5

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

        logger.info(f"Initialized Gemini structured service V2 with model: {self.model_name}")

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
            Tuple of (type, content) where type is 'pdf' or 'image'
        """
        file_ext = os.path.splitext(image_path)[1].lower()

        if file_ext == ".pdf":
            # For PDFs, return path and type
            return ("pdf", image_path)
        else:
            # Handle regular image files
            try:
                image = Image.open(image_path)
                logger.info(f"Successfully opened image file: {image_path}")
                return ("image", image)
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
        """Extract payment information using structured output with unified batching.

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

        # Configure model
        model = genai.GenerativeModel(self.model_name)

        # Always expect list for batch processing
        expect_list = True
        response_schema = PaymentRecord  # Will wrap in list during parsing
        json_format_prompt = self._get_json_format_prompt(response_schema, expect_list)

        # Process all files together in unified batches
        try:
            return self._process_files_in_unified_batches(
                image_paths, prompt, json_format_prompt, model, response_model
            )
        except Exception as e:
            logger.error(f"Error in structured extraction: {str(e)}")
            raise GeminiAPIException(
                message=f"Failed to extract payment data: {str(e)}", status_code=None, response_text=str(e)
            )

    def _process_files_in_unified_batches(
        self, file_paths: List[str], base_prompt: str, json_format_prompt: str, model, response_model: Type[BaseModel]
    ) -> List[PaymentRecord]:
        """Process all files (PDFs and images) in unified batches.

        Args:
            file_paths: List of file paths to process
            base_prompt: Base extraction prompt
            json_format_prompt: JSON format instructions
            model: Gemini model instance
            response_model: Pydantic model for response

        Returns:
            List of extracted payment records
        """
        import fitz  # PyMuPDF
        import PyPDF2

        # Prepare all content items (pages + images)
        all_content_items = []

        # Process each file
        for file_path in file_paths:
            file_type, content = self._prepare_image_part(file_path)

            if file_type == "pdf":
                # Extract pages from PDF
                logger.info(f"Processing PDF: {file_path}")
                pdf_doc = fitz.open(content)

                # Try to get text reader
                pdf_reader = None
                try:
                    pdf_reader = PyPDF2.PdfReader(content)
                except Exception as e:
                    logger.warning(f"Could not open PDF for text extraction: {e}")

                # Add each page as a content item
                for page_num in range(len(pdf_doc)):
                    # Extract text for this page
                    page_text = ""
                    if pdf_reader and page_num < len(pdf_reader.pages):
                        try:
                            page_text = pdf_reader.pages[page_num].extract_text()
                        except Exception as e:
                            logger.warning(f"Error extracting text from page {page_num + 1}: {e}")

                    # Convert page to image
                    page = pdf_doc[page_num]
                    pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))  # 1.5x zoom
                    img_data = pix.tobytes("png")
                    image = Image.open(io.BytesIO(img_data))

                    # Add to content items
                    all_content_items.append(
                        {
                            "type": "pdf_page",
                            "source": file_path,
                            "page_num": page_num + 1,
                            "image": image,
                            "text": page_text,
                        }
                    )

                pdf_doc.close()

            else:  # Regular image
                logger.info(f"Processing image: {file_path}")
                all_content_items.append(
                    {"type": "image", "source": file_path, "page_num": None, "image": content, "text": None}
                )

        logger.info(f"Total content items to process: {len(all_content_items)}")

        # Process in batches of BATCH_SIZE
        all_results = []
        num_batches = (len(all_content_items) + self.BATCH_SIZE - 1) // self.BATCH_SIZE

        for batch_num in range(num_batches):
            batch_start = batch_num * self.BATCH_SIZE
            batch_end = min(batch_start + self.BATCH_SIZE, len(all_content_items))
            batch_items = all_content_items[batch_start:batch_end]

            logger.info(f"Processing batch {batch_num + 1} of {num_batches} ({len(batch_items)} items)")

            # Build batch prompt
            batch_prompt = base_prompt

            # Add text context if available
            batch_text = ""
            for item in batch_items:
                if item["text"]:
                    source = os.path.basename(item["source"])
                    if item["page_num"]:
                        batch_text += f"\n--- {source} Page {item['page_num']} ---\n"
                    else:
                        batch_text += f"\n--- {source} ---\n"
                    batch_text += item["text"] + "\n"

            if batch_text.strip():
                logger.info(f"Batch {batch_num + 1} contains extractable text - adding as context")
                batch_prompt += f"\n\nText Content:\n{batch_text}"

            # Add batch info
            batch_info = f"\nProcessing batch {batch_num + 1} of {num_batches} ({len(batch_items)} items)"

            # Create content parts
            content_parts = [batch_prompt + batch_info, json_format_prompt]

            # Add images
            for item in batch_items:
                content_parts.append(item["image"])

            # Call Gemini API
            try:
                self._check_rate_limit()
                logger.info(f"Sending batch of {len(batch_items)} items to Gemini")

                batch_response = model.generate_content(
                    contents=content_parts,
                    generation_config=genai.GenerationConfig(
                        temperature=0.1,
                        max_output_tokens=2048,
                    ),
                )

                # Parse response
                if batch_response.text:
                    logger.info(f"Received response for batch {batch_num + 1}")

                    try:
                        batch_results = self._parse_text_response(batch_response.text, response_model, True)

                        if isinstance(batch_results, list):
                            logger.info(f"Batch {batch_num + 1} extracted {len(batch_results)} payments")
                            all_results.extend(batch_results)
                        else:
                            all_results.append(batch_results)

                    except Exception as e:
                        logger.error(f"Error parsing batch {batch_num + 1} response: {e}")

            except Exception as e:
                logger.error(f"Error processing batch {batch_num + 1}: {e}")

        logger.info(f"Successfully extracted {len(all_results)} payments total")
        return all_results

    def _parse_text_response(
        self, response_text: str, response_model: Type[BaseModel], expect_list: bool
    ) -> Union[BaseModel, List[BaseModel]]:
        """Parse text response into Pydantic models.

        Args:
            response_text: Raw text response from Gemini
            response_model: Pydantic model class
            expect_list: Whether to expect a list response

        Returns:
            Parsed model instance(s)
        """
        try:
            # Clean response text
            response_text = response_text.strip()

            # Remove markdown code blocks if present
            if response_text.startswith("```") and response_text.endswith("```"):
                lines = response_text.split("\n")
                response_text = "\n".join(lines[1:-1])
            elif response_text.startswith("```json") and response_text.endswith("```"):
                response_text = response_text[7:-3].strip()

            # Parse JSON
            parsed_json = json.loads(response_text)
            logger.info(f"Parsing JSON with {len(parsed_json) if isinstance(parsed_json, list) else 1} items")

            # Handle list response
            if expect_list:
                if isinstance(parsed_json, dict) and "payments" in parsed_json:
                    # Response wrapped in payments array
                    payments_data = parsed_json["payments"]
                    return [response_model(**payment) for payment in payments_data]
                elif isinstance(parsed_json, list):
                    # Direct list response
                    return [response_model(**payment) for payment in parsed_json]
                else:
                    # Single payment, wrap in list
                    return [response_model(**parsed_json)]
            else:
                # Single response expected
                if isinstance(parsed_json, list) and len(parsed_json) > 0:
                    return response_model(**parsed_json[0])
                else:
                    return response_model(**parsed_json)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response text: {response_text[:500]}...")
            raise
        except Exception as e:
            logger.error(f"Error creating Pydantic model: {e}")
            raise

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
        ...
      },
      "payer_info": {
        "aliases": ["John Smith", "Smith, John"],
        "organization_name": null
      },
      "contact_info": {
        ...
      }
    }
  ]
}
"""
        else:
            return self._get_single_payment_prompt()

    def _get_single_payment_prompt(self) -> str:
        """Get JSON format prompt for single payment."""
        return """
Return a single payment record with these fields:
- payment_info: Object with payment details
- payer_info: Object with payer information
- contact_info: Object with contact details
"""

    def _get_default_structured_prompt(self, document_type: str) -> str:
        """Get default prompt based on document type."""
        if document_type == "batch":
            return self.structured_prompt_manager.get_prompt(
                "batch_extraction_prompt", default_prompt="Extract all payment information from these documents."
            )
        else:
            return "Extract payment information from this document."

    # Copy other methods from original GeminiStructuredService that aren't changed
    def extract_from_text(self, text_content: str, prompt: str) -> str:
        """Extract information from text content."""
        self._check_rate_limit()

        try:
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(
                contents=[prompt, text_content],
                generation_config=genai.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=2048,
                ),
            )

            return response.text

        except Exception as e:
            logger.error(f"Error in text extraction: {str(e)}")
            raise GeminiAPIException(
                message=f"Failed to extract from text: {str(e)}", status_code=None, response_text=str(e)
            )
