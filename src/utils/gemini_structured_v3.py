"""
Enhanced Gemini service V3 using true structured outputs with guaranteed JSON schema compliance.
This replaces the manual JSON parsing approach with Gemini's native structured output feature.
"""

import logging
import os
import time
from typing import Any, Dict, List, Optional, Type, Union

import google.generativeai as genai
from PIL import Image
from pydantic import BaseModel

from src.models.payment import ContactInfo, PayerInfo, PaymentInfo, PaymentRecord

from .exceptions import GeminiAPIException, RetryableException
from .prompt_manager import PromptManager
from .rate_limiter import RateLimiter, RateLimitExceededException
from .retry import retry_on_failure

# Configure logger
logger = logging.getLogger(__name__)


class PaymentRecordList(BaseModel):
    """Wrapper for multiple payment records."""

    payments: List[PaymentRecord]


class GeminiStructuredServiceV3:
    """Enhanced Gemini service using native structured outputs for guaranteed JSON compliance."""

    # Rate limiting configuration
    RATE_LIMIT_PER_MINUTE = int(os.environ.get("GEMINI_RATE_LIMIT_PER_MINUTE", "60"))
    RATE_LIMIT_PER_HOUR = int(os.environ.get("GEMINI_RATE_LIMIT_PER_HOUR", "1500"))

    # Optimal batch size for structured outputs
    BATCH_SIZE = 3

    def __init__(self, api_key: str, model_name: str = None):
        """Initialize the Gemini service with API key and model name.

        Args:
            api_key: Gemini API key
            model_name: Gemini model name (uses environment variable GEMINI_MODEL or defaults)
        """
        self.api_key = api_key
        default_model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-preview-05-20")
        self.model_name = model_name if model_name is not None else default_model

        # Configure Gemini API
        genai.configure(api_key=api_key)

        # Initialize prompt manager
        self.prompt_manager = PromptManager(prompt_dir="lib/current_prompts")

        logger.info(f"Initialized Gemini structured service V3 with model: {self.model_name}")

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

    def _prepare_content_parts(self, file_paths: List[str], text_content: str = None) -> List[Any]:
        """Prepare content parts for Gemini API including images and text.

        Args:
            file_paths: List of file paths (images or PDFs)
            text_content: Optional text content to include

        Returns:
            List of content parts for Gemini API
        """
        import io

        import fitz  # PyMuPDF
        import PyPDF2

        content_parts = []

        # Add text content first if provided
        if text_content:
            content_parts.append(text_content)

        # Process each file
        for file_path in file_paths:
            file_ext = os.path.splitext(file_path)[1].lower()

            if file_ext == ".pdf":
                # Process PDF - convert pages to images
                logger.info(f"Processing PDF: {file_path}")
                pdf_doc = fitz.open(file_path)

                # Try to get text reader
                pdf_reader = None
                try:
                    pdf_reader = PyPDF2.PdfReader(file_path)
                except Exception as e:
                    logger.warning(f"Could not open PDF for text extraction: {e}")

                # Add each page as an image
                for page_num in range(len(pdf_doc)):
                    # Extract text for this page
                    page_text = ""
                    if pdf_reader and page_num < len(pdf_reader.pages):
                        try:
                            page_text = pdf_reader.pages[page_num].extract_text()
                            if page_text.strip():
                                content_parts.append(f"\\n--- PDF Page {page_num + 1} Text ---\\n{page_text}")
                        except Exception as e:
                            logger.warning(f"Error extracting text from page {page_num + 1}: {e}")

                    # Convert page to image
                    page = pdf_doc[page_num]
                    pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))  # 1.5x zoom
                    img_data = pix.tobytes("png")
                    image = Image.open(io.BytesIO(img_data))
                    content_parts.append(image)

                pdf_doc.close()

            else:
                # Handle regular image files
                try:
                    image = Image.open(file_path)
                    logger.info(f"Successfully opened image file: {file_path}")
                    content_parts.append(image)
                except Exception as e:
                    logger.error(f"Error loading image {file_path}: {e}")
                    raise

        return content_parts

    @retry_on_failure(max_attempts=3)
    def extract_payment_structured(
        self,
        image_paths: List[str],
        document_type: str = "batch",
        response_model: Type[BaseModel] = PaymentRecord,
    ) -> List[PaymentRecord]:
        """Extract payment information using structured output with guaranteed JSON compliance.

        Args:
            image_paths: List of paths to images (checks, envelopes, etc.)
            document_type: Type of documents ("check", "envelope", "batch", "mixed")
            response_model: Pydantic model for response structure

        Returns:
            List of structured payment data as PaymentRecord objects
        """
        self._check_rate_limit()

        if not image_paths:
            return []

        # Get prompt based on document type
        prompt_key = f"{document_type}_extraction_prompt"
        base_prompt = self.prompt_manager.get_prompt(
            prompt_key, default_prompt=self._get_default_extraction_prompt(document_type)
        )

        # Add schema guidance to prompt
        schema_prompt = self._get_schema_guidance_prompt()
        full_prompt = f"{base_prompt}\\n\\n{schema_prompt}"

        # Process files in batches
        try:
            return self._process_files_in_batches(image_paths, full_prompt, response_model)
        except Exception as e:
            logger.error(f"Error in structured extraction: {str(e)}")
            raise GeminiAPIException(
                message=f"Failed to extract payment data: {str(e)}", status_code=None, response_text=str(e)
            )

    def _process_files_in_batches(
        self, file_paths: List[str], base_prompt: str, response_model: Type[BaseModel]
    ) -> List[PaymentRecord]:
        """Process files in smaller batches using structured outputs.

        Args:
            file_paths: List of file paths to process
            base_prompt: Base extraction prompt
            response_model: Pydantic model for response

        Returns:
            List of extracted payment records
        """
        all_results = []
        num_batches = (len(file_paths) + self.BATCH_SIZE - 1) // self.BATCH_SIZE

        for batch_num in range(num_batches):
            batch_start = batch_num * self.BATCH_SIZE
            batch_end = min(batch_start + self.BATCH_SIZE, len(file_paths))
            batch_files = file_paths[batch_start:batch_end]

            logger.info(f"Processing batch {batch_num + 1} of {num_batches} ({len(batch_files)} files)")

            try:
                # Prepare content parts for this batch
                content_parts = self._prepare_content_parts(batch_files, base_prompt)

                # Always use list schema for batches
                response_schema = PaymentRecordList

                # Generate structured response
                self._check_rate_limit()
                logger.info(f"Sending batch of {len(batch_files)} files to Gemini with structured output")

                # Use Gemini with structured outputs
                model = genai.GenerativeModel(self.model_name)
                response = model.generate_content(
                    contents=content_parts,
                    generation_config=genai.GenerationConfig(
                        response_mime_type="application/json",
                        response_schema=response_schema,
                        temperature=0.1,
                        max_output_tokens=4096,
                    ),
                )

                # Parse structured response
                if response and hasattr(response, "parsed") and response.parsed:
                    logger.info(f"Received structured response for batch {batch_num + 1}")

                    # Extract payments from parsed response
                    if hasattr(response.parsed, "payments"):
                        batch_results = response.parsed.payments
                        logger.info(f"Batch {batch_num + 1} extracted {len(batch_results)} payments")
                        all_results.extend(batch_results)
                    else:
                        logger.warning(f"Batch {batch_num + 1} returned no payments in structured response")
                else:
                    logger.warning(f"Batch {batch_num + 1} returned no valid response")

            except Exception as e:
                logger.error(f"Error processing batch {batch_num + 1}: {e}")
                # Continue with other batches rather than failing completely

        logger.info(f"Successfully extracted {len(all_results)} payments total from {len(file_paths)} files")
        return all_results

    def _get_schema_guidance_prompt(self) -> str:
        """Get schema guidance for structured output."""
        return """
CRITICAL: You must extract payment information and return it as a JSON object with this exact structure:

{
  "payments": [
    {
      "payment_info": {
        "payment_method": "handwritten_check" | "printed_check" | "online_payment",
        "check_no": "string (REQUIRED for checks)",
        "payment_ref": "string (REQUIRED for online payments)",
        "amount": number (REQUIRED),
        "payment_date": "YYYY-MM-DD format (REQUIRED)",
        "check_date": "YYYY-MM-DD format or null",
        "postmark_date": "YYYY-MM-DD format or null",
        "deposit_date": "YYYY-MM-DD format or null",
        "deposit_method": "string or null",
        "memo": "string or null"
      },
      "payer_info": {
        "aliases": ["array of name variations"] or null,
        "salutation": "string or null",
        "organization_name": "string or null"
      },
      "contact_info": {
        "address_line_1": "string or null",
        "city": "string or null",
        "state": "2-letter code or null",
        "zip": "5-digit string or null",
        "email": "string or null",
        "phone": "string or null"
      }
    }
  ]
}

IMPORTANT RULES:
- For individuals: provide "aliases" array with name variations, "organization_name" should be null
- For organizations: provide "organization_name", "aliases" can be null
- For handwritten checks: payment_date = postmark_date (if available) or check_date
- For printed checks: payment_date = check_date
- For online payments: payment_date = transaction_date
- ZIP codes must be 5-digit strings (preserve leading zeros)
- All dates in YYYY-MM-DD format
"""

    def _get_default_extraction_prompt(self, document_type: str) -> str:
        """Get default prompt based on document type."""
        prompts = {
            "batch": lambda: self.prompt_manager.get_prompt(
                "batch_extraction_prompt", default_prompt=self._get_comprehensive_batch_prompt()
            ),
            "check": lambda: """
Analyze the check image to extract payment information.

Focus on:
- Check number (usually upper right corner)
- Amount (both numeric and written - ensure they match)
- Date on check
- Memo line
- Payer name and address
- Determine if handwritten (amount/date handwritten) or printed check
""",
            "envelope": lambda: """
Analyze the envelope image to extract contact information.

Focus on:
- Return address (this is the primary address to use)
- Postmark date
- Any additional contact information
- Any handwritten notes or memos
""",
        }

        return prompts.get(
            document_type, lambda: "Extract all payment and contact information from the provided documents."
        )()

    def _get_comprehensive_batch_prompt(self) -> str:
        """Get comprehensive prompt for batch processing."""
        return """
Analyze all provided documents to extract complete payment information. You may see:

1. CHECK IMAGES:
   - Extract check number, amount (numeric and written), date, memo
   - Determine if handwritten or printed based on amount/date fields
   - Extract payer name and address from check

2. ENVELOPE IMAGES:
   - Extract return address (THIS SUPERSEDES check address)
   - Extract postmark date
   - Look for additional contact info (phone, email)
   - Note any handwritten memos

3. PDF DOCUMENTS:
   - May contain multiple pages with checks, deposit slips, or records
   - Extract all payment information from each page

PAYMENT DATE LOGIC:
- Handwritten checks: Use postmark date if available, otherwise check date
- Printed checks: Use check date
- Online payments: Use transaction date

ADDRESS PRIORITY:
1. Envelope return address (highest priority)
2. Check address
3. Any other address found

For each payment found, extract complete information including payment details, payer information, and contact details.
"""

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

            return response.text if response else ""

        except Exception as e:
            logger.error(f"Error in text extraction: {str(e)}")
            raise GeminiAPIException(
                message=f"Failed to extract from text: {str(e)}", status_code=None, response_text=str(e)
            )
