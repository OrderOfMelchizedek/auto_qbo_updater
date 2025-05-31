"""
Enhanced Gemini adapter that returns PaymentRecord objects for the refactored workflow.
This replaces the legacy adapter that converted to legacy format.
"""

import logging
from typing import Any, Dict, List, Optional, Union

from ..models.payment import PaymentRecord
from .gemini_service import GeminiService
from .gemini_structured import GeminiStructuredService

logger = logging.getLogger(__name__)


class GeminiAdapterV2:
    """Enhanced adapter that returns PaymentRecord objects instead of legacy format."""

    def __init__(self, api_key: str, model_name: str = None):
        """Initialize the adapter with structured extraction service.

        Args:
            api_key: Gemini API key
            model_name: Optional model name (defaults to latest)
        """
        self.api_key = api_key
        self.structured_service = GeminiStructuredService(api_key, model_name)
        logger.info("Initialized Gemini adapter V2 (returns PaymentRecord objects)")

    def extract_payments(self, file_path: str, document_type: str = None) -> List[PaymentRecord]:
        """Extract payment records from a file.

        Args:
            file_path: Path to the image or PDF file
            document_type: Type of document (auto-detected if not provided)

        Returns:
            List of PaymentRecord objects
        """
        # Auto-detect document type if not provided
        if not document_type:
            file_ext = file_path.lower()
            if "envelope" in file_path:
                document_type = "envelope"
            elif file_ext.endswith(".csv"):
                document_type = "csv"
            else:
                # For check images, use batch mode to detect multiple checks
                document_type = "batch"

        # Use structured extraction
        payment_records = self.structured_service.extract_payment_structured(
            image_paths=[file_path], document_type=document_type
        )

        # Always return a list
        if isinstance(payment_records, list):
            return payment_records
        else:
            return [payment_records]

    def extract_payments_from_content(
        self,
        content: Dict[str, Any],
        file_type: str = "pdf_batch",
        batch_info: Optional[str] = None,
    ) -> List[PaymentRecord]:
        """Extract payment records from prepared content (for batch processing).

        Args:
            content: Prepared content with text and/or images
            file_type: Type of file being processed
            batch_info: Optional batch information

        Returns:
            List of PaymentRecord objects
        """
        # TODO: Implement structured extraction from content
        # For now, raise not implemented
        raise NotImplementedError("Structured extraction from content not yet implemented")

    def extract_text_data(self, prompt_text: str) -> Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]:
        """Extract data from text input using a custom prompt.

        Note: This returns legacy format for backward compatibility with specific use cases.

        Args:
            prompt_text: The complete prompt including the text to analyze

        Returns:
            Extracted data in legacy format
        """
        # This method is kept for backward compatibility with specific text extraction needs
        # It should not be used for payment extraction
        return self.structured_service.extract_text_data(prompt_text)
