"""Gemini service module for text generation using Google's Gemini API."""
import base64
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import google.generativeai as genai
from dotenv import load_dotenv
from PIL import Image

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Get the base path for prompts
PROMPTS_DIR = Path(__file__).parent / "lib" / "prompts"


def load_prompt(prompt_name: str) -> str:
    """Load a prompt from the prompts directory.

    Args:
        prompt_name: Name of the prompt file (without extension)

    Returns:
        str: The prompt content

    Raises:
        FileNotFoundError: If the prompt file doesn't exist
    """
    # Try .md first, then .txt
    for extension in [".md", ".txt"]:
        prompt_path = PROMPTS_DIR / f"{prompt_name}{extension}"
        if prompt_path.exists():
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read().strip()

    # If neither exists, raise error
    raise FileNotFoundError(
        f"Prompt file not found: {prompt_name}.md or {prompt_name}.txt in {PROMPTS_DIR}"
    )


def call_gemini_api(prompt_name: str = "api_design"):
    """Make a call to the Gemini API with a prompt loaded from file.

    Args:
        prompt_name: Name of the prompt file to load (default: "api_design")

    Returns:
        str: The text response from the Gemini API
    """
    logger.info(f"Generating text with prompt: {prompt_name}")

    # Get API key from environment
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables")

    # Get model name from environment, or use default
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-preview-05-20")

    # Configure the API key
    genai.configure(api_key=api_key)

    # Initialize the model
    model = genai.GenerativeModel(model_name)

    # Load prompt from file
    prompt = load_prompt(prompt_name)

    try:
        # Make the API call
        response = model.generate_content(prompt)

        if response.text is None:
            raise Exception("Received empty response from Gemini API")

        logger.info("Text generation completed successfully")
        return response.text
    except Exception as e:
        logger.error(f"Error calling Gemini API: {str(e)}")
        raise Exception(f"Error calling Gemini API: {str(e)}")


def call_gemini_api_with_image(prompt_name: str, image_path: Union[str, Path]) -> str:
    """Make a call to the Gemini API with a prompt and an image.

    Args:
        prompt_name: Name of the prompt file to load
        image_path: Path to the image file

    Returns:
        str: The text response from the Gemini API

    Raises:
        ValueError: If the API key is not found
        FileNotFoundError: If the prompt or image file doesn't exist
        Exception: For other API errors
    """
    # Get API key from environment
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables")

    # Get model name from environment, or use default
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-preview-05-20")

    # Configure the API key
    genai.configure(api_key=api_key)

    # Initialize the model
    model = genai.GenerativeModel(model_name)

    # Load prompt from file
    prompt = load_prompt(prompt_name)

    # Load image
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    logger.info(f"Generating text with image: {image_path} and prompt: {prompt_name}")

    try:
        # Open the image with PIL
        img = Image.open(image_path)

        # Make the API call with both prompt and image
        response = model.generate_content([prompt, img])

        if response.text is None:
            raise Exception("Received empty response from Gemini API")

        logger.info("Image-based text generation completed successfully")
        return response.text
    except Exception as e:
        logger.error(f"Error calling Gemini API with image: {str(e)}")
        raise Exception(f"Error calling Gemini API with image: {str(e)}")


def call_gemini_api_with_pdf(prompt_name: str, pdf_path: Union[str, Path]) -> str:
    """Make a call to the Gemini API with a prompt and a PDF document.

    Args:
        prompt_name: Name of the prompt file to load
        pdf_path: Path to the PDF file

    Returns:
        str: The text response from the Gemini API

    Raises:
        ValueError: If the API key is not found
        FileNotFoundError: If the prompt or PDF file doesn't exist
        Exception: For other API errors
    """
    # Get API key from environment
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables")

    # Get model name from environment, or use default
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-preview-05-20")

    # Configure the API key
    genai.configure(api_key=api_key)

    # Initialize the model
    model = genai.GenerativeModel(model_name)

    # Load prompt from file
    prompt = load_prompt(prompt_name)

    # Load PDF
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    logger.info(f"Generating text with PDF: {pdf_path} and prompt: {prompt_name}")

    try:
        # Read PDF file bytes
        with open(pdf_path, "rb") as f:
            pdf_data = f.read()

        # Create a blob from the PDF data
        # The Gemini API expects the PDF as part of the content
        # We'll pass it as a dict with inline_data
        # The data needs to be base64 encoded
        pdf_part = {
            "inline_data": {
                "mime_type": "application/pdf",
                "data": base64.b64encode(pdf_data).decode("utf-8"),
            }
        }

        # Make the API call with both prompt and PDF
        response = model.generate_content([pdf_part, prompt])

        if response.text is None:
            raise Exception("Received empty response from Gemini API")

        logger.info("PDF-based text generation completed successfully")
        return response.text
    except Exception as e:
        logger.error(f"Error calling Gemini API with PDF: {str(e)}")
        raise Exception(f"Error calling Gemini API with PDF: {str(e)}")


def process_multiple_files(prompt_name: str, file_paths: List[Union[str, Path]]) -> str:
    """Process multiple files (PDFs and/or images) with a single API call.

    Args:
        prompt_name: Name of the prompt file to load
        file_paths: List of paths to files to process

    Returns:
        str: The text response from the Gemini API

    Raises:
        ValueError: If no files provided, API key not found, or unsupported file format
        FileNotFoundError: If prompt or any file doesn't exist
        Exception: For other API errors
    """
    # Validate inputs
    if not file_paths:
        raise ValueError("No files provided")

    if len(file_paths) > 100:  # Reasonable limit
        raise ValueError(
            f"Too many files provided ({len(file_paths)}). Maximum is 100."
        )

    # Get API key from environment
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables")

    # Get model name from environment, or use default
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-preview-05-20")

    # Configure the API key
    genai.configure(api_key=api_key)

    # Initialize the model
    model = genai.GenerativeModel(model_name)

    # Load prompt from file
    prompt = load_prompt(prompt_name)

    # Prepare content parts list
    content_parts: List[Union[str, dict, Image.Image]] = []

    # Process each file
    for file_path in file_paths:
        file_path = Path(file_path)

        # Get file extension
        extension = file_path.suffix.lower()

        # Check if file format is supported before checking existence
        if extension not in [".pdf", ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"]:
            raise ValueError(
                f"Unsupported file format: {extension} for file {file_path}"
            )

        # Check if file exists
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Process based on file type
        if extension == ".pdf":
            logger.debug(f"Processing PDF: {file_path}")
            # Read PDF file
            with open(file_path, "rb") as f:
                pdf_data = f.read()

            # Create PDF part
            pdf_part = {
                "inline_data": {
                    "mime_type": "application/pdf",
                    "data": base64.b64encode(pdf_data).decode("utf-8"),
                }
            }
            content_parts.append(pdf_part)

        elif extension in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"]:
            logger.debug(f"Processing image: {file_path}")
            # Open image with PIL
            img = Image.open(file_path)

            # Add image to content parts
            content_parts.append(img)

    # Add the prompt at the end (could experiment with putting it first)
    content_parts.append(prompt)

    logger.info(f"Processing {len(file_paths)} files with prompt: {prompt_name}")

    # Implement retry mechanism with exponential backoff
    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        try:
            # Make the API call with all content parts
            response = model.generate_content(content_parts)

            if response.text is None:
                raise Exception("Received empty response from Gemini API")

            logger.info(f"Successfully processed {len(file_paths)} files")
            return response.text
        except Exception as e:
            # Check if this is a retriable error (API errors typically are)
            # Non-retriable errors like ValueError should not be retried
            if isinstance(e, ValueError):
                raise Exception(
                    f"Error calling Gemini API with multiple files: {str(e)}"
                )

            # Check if error message contains server error codes
            error_str = str(e).lower()
            is_retriable = any(
                code in error_str
                for code in [
                    "500",
                    "502",
                    "503",
                    "504",
                    "timeout",
                    "deadline",
                    "unavailable",
                ]
            )

            if not is_retriable:
                # Non-retriable error
                logger.error(f"Non-retriable error: {str(e)}")
                raise Exception(
                    f"Error calling Gemini API with multiple files: {str(e)}"
                )

            retry_count += 1

            if retry_count >= max_retries:
                # Max retries exceeded, raise the error
                logger.error(f"Max retries ({max_retries}) exceeded")
                raise Exception(
                    f"Error calling Gemini API with multiple files: {str(e)}"
                )

            # Calculate exponential backoff: 2^(retry_count-1) seconds
            wait_time = 2 ** (retry_count - 1)
            logger.warning(
                f"API error: {e}. Retrying in {wait_time}s... "
                f"(attempt {retry_count}/{max_retries})"
            )
            time.sleep(wait_time)

            # Continue to next retry

    # This should never be reached
    raise Exception("Unexpected error: retry loop exited without result")


def create_donation_extraction_schema() -> Dict[str, Any]:
    """Create the JSON schema for donation extraction.

    Returns:
        Dict[str, Any]: The JSON schema for structured output
    """
    return {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "PaymentInfo": {
                    "type": "object",
                    "properties": {
                        "Payment_Ref": {"type": "string"},
                        "Payment_Method": {
                            "type": "string",
                            "enum": [
                                "handwritten check",
                                "printed check",
                                "online payment",
                            ],
                        },
                        "Amount": {"type": "number"},
                        "Payment_Date": {"type": "string"},
                        "Check_Date": {"type": "string", "nullable": True},
                        "Postmark_Date": {"type": "string", "nullable": True},
                        "Deposit_Date": {"type": "string", "nullable": True},
                        "Deposit_Method": {"type": "string", "nullable": True},
                        "Memo": {"type": "string", "nullable": True},
                    },
                    "required": [
                        "Payment_Ref",
                        "Payment_Method",
                        "Amount",
                        "Payment_Date",
                    ],
                },
                "PayerInfo": {
                    "type": "object",
                    "properties": {
                        "Aliases": {"type": "array", "items": {"type": "string"}},
                        "Salutation": {"type": "string", "nullable": True},
                        "Organization_Name": {"type": "string", "nullable": True},
                    },
                },
                "ContactInfo": {
                    "type": "object",
                    "properties": {
                        "Address_Line_1": {"type": "string", "nullable": True},
                        "City": {"type": "string", "nullable": True},
                        "State": {"type": "string", "nullable": True},
                        "ZIP": {"type": "string", "nullable": True},
                        "Email": {"type": "string", "nullable": True},
                        "Phone": {"type": "string", "nullable": True},
                    },
                },
            },
            "required": ["PaymentInfo", "PayerInfo", "ContactInfo"],
        },
    }


def process_multiple_files_structured(
    prompt_name: str,
    file_paths: List[Union[str, Path]],
    response_schema: Optional[Dict[str, Any]] = None,
    response_mime_type: Optional[str] = None,
) -> str:
    """Process multiple files with optional structured output.

    Args:
        prompt_name: Name of the prompt file to load
        file_paths: List of paths to files to process
        response_schema: Optional JSON schema for structured output
        response_mime_type: Optional MIME type for response (e.g., "application/json")

    Returns:
        str: The text response from the Gemini API

    Raises:
        ValueError: If no files provided, API key not found, or unsupported file format
        FileNotFoundError: If prompt or any file doesn't exist
        Exception: For other API errors
    """
    # Validate inputs
    if not file_paths:
        raise ValueError("No files provided")

    if len(file_paths) > 100:  # Reasonable limit
        raise ValueError(
            f"Too many files provided ({len(file_paths)}). Maximum is 100."
        )

    # Get API key from environment
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables")

    # Get model name from environment, or use default
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-preview-05-20")

    # Configure the API key
    genai.configure(api_key=api_key)

    # Initialize the model with generation config if schema provided
    if response_schema and response_mime_type:
        generation_config = {
            "response_mime_type": response_mime_type,
            "response_schema": response_schema,
        }
        model = genai.GenerativeModel(model_name, generation_config=generation_config)
    else:
        model = genai.GenerativeModel(model_name)

    # Load prompt from file
    prompt = load_prompt(prompt_name)

    # Prepare content parts list
    content_parts: List[Union[str, dict, Image.Image]] = []

    # Process each file
    for file_path in file_paths:
        file_path = Path(file_path)

        # Get file extension
        extension = file_path.suffix.lower()

        # Check if file format is supported before checking existence
        if extension not in [".pdf", ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"]:
            raise ValueError(
                f"Unsupported file format: {extension} for file {file_path}"
            )

        # Check if file exists
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Process based on file type
        if extension == ".pdf":
            logger.debug(f"Processing PDF: {file_path}")
            # Read PDF file
            with open(file_path, "rb") as f:
                pdf_data = f.read()

            # Create PDF part
            pdf_part = {
                "inline_data": {
                    "mime_type": "application/pdf",
                    "data": base64.b64encode(pdf_data).decode("utf-8"),
                }
            }
            content_parts.append(pdf_part)

        elif extension in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"]:
            logger.debug(f"Processing image: {file_path}")
            # Open image with PIL
            img = Image.open(file_path)

            # Add image to content parts
            content_parts.append(img)

    # Add the prompt at the end
    content_parts.append(prompt)

    logger.info(f"Processing {len(file_paths)} files with prompt: {prompt_name}")

    # Implement retry mechanism with exponential backoff
    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        try:
            # Make the API call with all content parts
            response = model.generate_content(content_parts)

            if response.text is None:
                raise Exception("Received empty response from Gemini API")

            logger.info(f"Successfully processed {len(file_paths)} files")
            return response.text
        except Exception as e:
            # Check if this is a retriable error
            if isinstance(e, ValueError):
                raise Exception(
                    f"Error calling Gemini API with multiple files: {str(e)}"
                )

            # Check if error message contains server error codes
            error_str = str(e).lower()
            is_retriable = any(
                code in error_str
                for code in [
                    "500",
                    "502",
                    "503",
                    "504",
                    "timeout",
                    "deadline",
                    "unavailable",
                ]
            )

            if not is_retriable:
                # Non-retriable error
                logger.error(f"Non-retriable error: {str(e)}")
                raise Exception(
                    f"Error calling Gemini API with multiple files: {str(e)}"
                )

            retry_count += 1

            if retry_count >= max_retries:
                # Max retries exceeded, raise the error
                logger.error(f"Max retries ({max_retries}) exceeded")
                raise Exception(
                    f"Error calling Gemini API with multiple files: {str(e)}"
                )

            # Calculate exponential backoff: 2^(retry_count-1) seconds
            wait_time = 2 ** (retry_count - 1)
            logger.warning(
                f"API error: {e}. Retrying in {wait_time}s... "
                f"(attempt {retry_count}/{max_retries})"
            )
            time.sleep(wait_time)

            # Continue to next retry

    # This should never be reached
    raise Exception("Unexpected error: retry loop exited without result")


def extract_donations_from_documents(
    file_paths: List[Union[str, Path]], validate_output: bool = False
) -> List[Dict[str, Any]]:
    """Extract donation information from document files using structured output.

    Args:
        file_paths: List of paths to files to process
        validate_output: Whether to validate the output against the schema

    Returns:
        List[Dict[str, Any]]: List of extracted donation records

    Raises:
        ValueError: If validation fails or response is invalid
        Exception: For API or processing errors
    """
    # Create the schema for structured output
    schema = create_donation_extraction_schema()

    # Process files with structured output
    response_text = process_multiple_files_structured(
        "document_extraction_prompt",
        file_paths,
        response_schema=schema,
        response_mime_type="application/json",
    )

    # Parse the JSON response
    try:
        # Handle potential markdown code fences
        if response_text.startswith("```json") and response_text.endswith("```"):
            response_text = response_text[7:-3].strip()
        elif response_text.startswith("```") and response_text.endswith("```"):
            response_text = response_text[3:-3].strip()

        donations = json.loads(response_text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON. Response text: {response_text[:200]}...")
        raise ValueError(f"Invalid JSON response: {str(e)}")

    # Validate if requested
    if validate_output:
        for i, donation in enumerate(donations):
            # Check required payment fields
            payment_info = donation.get("PaymentInfo", {})
            required_payment_fields = [
                "Payment_Ref",
                "Payment_Method",
                "Amount",
                "Payment_Date",
            ]
            missing_fields = [
                f for f in required_payment_fields if f not in payment_info
            ]

            if missing_fields:
                raise ValueError(
                    f"Missing required payment fields in donation {i}: "
                    f"{', '.join(missing_fields)}"
                )

            # Check that either organization or aliases is present
            payer_info = donation.get("PayerInfo", {})
            has_org = bool(payer_info.get("Organization_Name"))
            has_aliases = bool(payer_info.get("Aliases"))

            if not has_org and not has_aliases:
                raise ValueError(
                    f"Either Organization_Name or Aliases must be provided "
                    f"in donation {i}"
                )

    return donations


if __name__ == "__main__":
    # Test the function
    try:
        result = call_gemini_api()
        print("Gemini API Response:")
        print(result)
    except Exception as e:
        print(f"Error: {e}")
