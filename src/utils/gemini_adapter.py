"""
Adapter to seamlessly integrate structured Gemini service with existing codebase.
Provides backward compatibility while using new structured extraction internally.
"""

import logging
from typing import Any, Dict, List, Optional, Union

from models.payment import PaymentRecord

from .gemini_service import GeminiService
from .gemini_structured import GeminiStructuredService

logger = logging.getLogger(__name__)


class GeminiAdapter(GeminiService):
    """
    Adapter class that maintains the GeminiService interface while using
    structured extraction internally. This allows gradual migration.
    """

    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash-preview-04-17"):
        """Initialize adapter with both old and new services.

        Args:
            api_key: Gemini API key
            model_name: Model name (will be upgraded to 2.0 for structured service)
        """
        # Initialize parent class
        super().__init__(api_key, model_name)

        # Initialize structured service with newer model
        structured_model = "gemini-2.0-flash-exp"
        self.structured_service = GeminiStructuredService(api_key, structured_model)

        # Feature flag to control which service to use
        self.use_structured = True

        logger.info(f"Initialized Gemini adapter (structured={self.use_structured})")

    def extract_donation_data(
        self, file_path: str, custom_prompt: str = None
    ) -> Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]:
        """Extract donation data from a file - now uses payment extraction internally.

        Args:
            file_path: Path to the image or PDF file
            custom_prompt: Optional custom prompt (ignored in structured mode)

        Returns:
            Dictionary or list of dictionaries with donation data in legacy format
        """
        try:
            # Determine document type from file extension
            file_ext = file_path.lower()
            if "envelope" in file_path:
                doc_type = "envelope"
            elif file_ext.endswith(".csv"):
                doc_type = "csv"
            else:
                # For check images, use batch mode to detect multiple checks
                doc_type = "batch"

            # Use structured extraction
            payment_records = self.structured_service.extract_payment_structured(
                image_paths=[file_path], document_type=doc_type
            )

            # Convert to legacy format
            if isinstance(payment_records, list):
                legacy_data = [record.to_legacy_format() for record in payment_records]
            else:
                legacy_data = payment_records.to_legacy_format()

            # Log successful extraction
            count = len(legacy_data) if isinstance(legacy_data, list) else 1
            logger.info(f"Extracted {count} payment(s) using structured service")

            return legacy_data

        except Exception as e:
            logger.error(f"Structured extraction failed: {e}")
            # Re-raise the exception instead of falling back
            raise

    def extract_donation_data_from_content(
        self,
        content: Dict[str, Any],
        file_type: str = "pdf_batch",
        batch_info: Optional[str] = None,
    ) -> Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]:
        """Extract donation data from prepared content (for batch processing).

        This method is used for PDF batch processing where content is pre-processed.
        """
        # TODO: Implement structured batch processing for content
        raise NotImplementedError("Structured extraction from content not yet implemented")

    def verify_customer_match(self, extracted_donor: Dict[str, Any], qbo_customer: Dict[str, Any]) -> Dict[str, Any]:
        """Verify if the QuickBooks customer is a match for the extracted donor data.

        Args:
            extracted_donor: Dictionary of extracted donor/payer data
            qbo_customer: Dictionary of QuickBooks customer data

        Returns:
            Dictionary containing verification results
        """
        try:
            # Use structured service for verification
            return self.structured_service.verify_customer_match(extracted_donor, qbo_customer)
        except Exception as e:
            logger.error(f"Structured verification failed: {e}")
            raise

    def set_use_structured(self, use_structured: bool):
        """Toggle between structured and legacy extraction.

        Args:
            use_structured: Whether to use structured extraction
        """
        self.use_structured = use_structured
        logger.info(f"Gemini adapter set to use_structured={use_structured}")


def create_gemini_service(api_key: str, model_name: str = None) -> GeminiService:
    """Factory function to create appropriate Gemini service.

    This function can be used as a drop-in replacement for GeminiService instantiation.

    Args:
        api_key: Gemini API key
        model_name: Optional model name

    Returns:
        GeminiAdapter instance that provides backward compatibility
    """
    if model_name is None:
        model_name = "gemini-2.5-flash-preview-04-17"

    return GeminiAdapter(api_key, model_name)
