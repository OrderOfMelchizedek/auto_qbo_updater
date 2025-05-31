"""
Enhanced Gemini adapter V3 that uses unified batching with smaller batch sizes.
"""

import logging
from typing import Any, Dict, List, Optional, Union

from src.models.payment import PaymentRecord

from .gemini_structured_v3 import GeminiStructuredServiceV3

logger = logging.getLogger(__name__)


class GeminiAdapterV3:
    """Adapter V3 that processes all files together in unified batches."""

    def __init__(self, api_key: str, model_name: str = None):
        """Initialize the adapter with structured extraction service V2.

        Args:
            api_key: Gemini API key
            model_name: Optional model name (defaults to latest)
        """
        self.api_key = api_key
        self.structured_service = GeminiStructuredServiceV3(api_key, model_name)
        logger.info("Initialized Gemini adapter V3 (structured outputs with size 3)")

    def extract_payments_batch(self, file_paths: List[str]) -> List[PaymentRecord]:
        """Extract payment records from multiple files in unified batches.

        Args:
            file_paths: List of paths to image or PDF files

        Returns:
            List of PaymentRecord objects
        """
        if not file_paths:
            return []

        # Always use batch mode for unified processing
        try:
            # Process all files together
            results = self.structured_service.extract_payment_structured(
                file_paths, document_type="batch", response_model=PaymentRecord
            )

            # Ensure we return a list
            if isinstance(results, list):
                return results
            else:
                return [results] if results else []

        except Exception as e:
            logger.error(f"Failed to extract payments: {str(e)}")
            raise RuntimeError(f"Failed to extract payment data: {str(e)}")

    def extract_payments(self, file_path: str, document_type: str = None) -> List[PaymentRecord]:
        """Extract payment records from a single file (for backward compatibility).

        Args:
            file_path: Path to the image or PDF file
            document_type: Type of document (ignored, always uses batch mode)

        Returns:
            List of PaymentRecord objects
        """
        return self.extract_payments_batch([file_path])
