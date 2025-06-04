"""Celery tasks for document processing."""
import logging
from typing import Any, Dict, List, Optional

from celery import Task, group

from src.models.document import DocumentPage, FileType
from src.models.donation import ContactInfo, PayerInfo, PaymentInfo
from src.services.extraction.gemini_extractor import GeminiExtractor
from src.services.processing.document_processor import DocumentProcessor
from src.services.storage.s3_service import S3Service
from src.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


class DocumentProcessingTask(Task):
    """Base task class with shared resources."""

    _s3_service = None
    _document_processor = None
    _gemini_extractor = None

    @property
    def s3_service(self):
        """Get or create S3 service instance."""
        if self._s3_service is None:
            self._s3_service = S3Service()
        return self._s3_service

    @property
    def document_processor(self):
        """Get or create document processor instance."""
        if self._document_processor is None:
            self._document_processor = DocumentProcessor(s3_service=self.s3_service)
        return self._document_processor

    @property
    def gemini_extractor(self):
        """Get or create Gemini extractor instance."""
        if self._gemini_extractor is None:
            self._gemini_extractor = GeminiExtractor()
        return self._gemini_extractor


@celery_app.task(
    base=DocumentProcessingTask,
    bind=True,
    name="process_document_batch",
    max_retries=3,
)
def process_document_batch(
    self, batch_id: str, file_ids: List[str], user_id: str
) -> Dict[str, Any]:
    """
    Process a batch of documents concurrently.

    Args:
        batch_id: Batch identifier
        file_ids: List of file IDs to process
        user_id: User who uploaded the files

    Returns:
        Dictionary with batch processing results
    """
    try:
        logger.info(
            f"Starting batch processing for {batch_id} with {len(file_ids)} files"
        )

        # Create a group of tasks for concurrent processing
        job = group(
            process_single_document.s(file_id, batch_id, user_id)
            for file_id in file_ids
        )

        # Execute all tasks concurrently
        result = job.apply_async()

        # Wait for all tasks to complete and get results
        results = result.get(timeout=300)  # 5 minute timeout

        # Aggregate results
        successful = sum(1 for r in results if r["status"] == "success")
        failed = sum(1 for r in results if r["status"] == "failed")

        return {
            "batch_id": batch_id,
            "total_files": len(file_ids),
            "successful": successful,
            "failed": failed,
            "results": results,
        }

    except Exception as e:
        logger.error(f"Batch processing failed for {batch_id}: {str(e)}")
        raise self.retry(exc=e, countdown=60)  # Retry after 1 minute


@celery_app.task(
    base=DocumentProcessingTask,
    bind=True,
    name="process_single_document",
    max_retries=3,
)
def process_single_document(
    self, file_id: str, batch_id: str, user_id: str
) -> Dict[str, Any]:
    """
    Process a single document through the extraction pipeline.

    Args:
        file_id: File identifier
        batch_id: Batch identifier
        user_id: User who uploaded the file

    Returns:
        Dictionary with processing results
    """
    try:
        logger.info(f"Processing document {file_id}")

        # Get file metadata (in production, this would query the database)
        # For now, we'll construct the S3 key
        # TODO: Get actual file metadata from database
        file_info = {
            "file_id": file_id,
            "file_type": FileType.PNG,  # This should come from DB
            "s3_key": f"uploads/{user_id}/{batch_id}/{file_id}/document.png",
        }

        # Download file from S3
        file_content = self.s3_service.download_file(file_info["s3_key"])

        # Process document into pages
        pages = self.document_processor.process_document(
            file_content, file_info["file_type"], file_id
        )

        # Process each page through Gemini
        extraction_results = []
        for page in pages:
            result = process_document_page.apply_async(
                args=[page.model_dump(), file_info["file_type"]]
            ).get(timeout=60)
            extraction_results.append(result)

        # Aggregate results from all pages
        aggregated = aggregate_page_results(extraction_results)

        return {
            "status": "success",
            "file_id": file_id,
            "page_count": len(pages),
            "extraction_results": aggregated,
        }

    except Exception as e:
        logger.error(f"Document processing failed for {file_id}: {str(e)}")
        return {
            "status": "failed",
            "file_id": file_id,
            "error": str(e),
        }


@celery_app.task(
    base=DocumentProcessingTask,
    bind=True,
    name="process_document_page",
    max_retries=3,
)
def process_document_page(
    self, page_data: Dict, file_type: str, document_type_hint: Optional[str] = None
) -> Dict[str, Any]:
    """
    Process a single page through Gemini extraction.

    Args:
        page_data: Page information dictionary
        file_type: Type of the original file
        document_type_hint: Optional hint about document type

    Returns:
        Extraction results
    """
    try:
        page = DocumentPage(**page_data)

        # Handle CSV differently
        if file_type == FileType.CSV:
            # CSV extraction would be handled differently
            # For now, return the stored CSV content
            return {
                "page_id": page.page_id,
                "status": "success",
                "extraction": page.extraction_result,
            }

        # Get image data
        if page.s3_key:
            image_data = self.s3_service.download_file(page.s3_key)
        elif page.image_data:
            # Convert from hex string to bytes
            image_data = bytes.fromhex(page.image_data)
        else:
            raise ValueError("No image data available for page")

        # Extract with Gemini
        extraction_response = self.gemini_extractor.extract_from_image(
            image_data, document_type=document_type_hint, include_confidence=True
        )

        return {
            "page_id": page.page_id,
            "page_number": page.page_number,
            "status": "success",
            "extraction": extraction_response.model_dump(),
        }

    except Exception as e:
        logger.error(f"Page extraction failed for {page_data.get('page_id')}: {str(e)}")
        raise self.retry(exc=e, countdown=30)  # Retry after 30 seconds


def aggregate_page_results(page_results: List[Dict]) -> Dict[str, Any]:
    """
    Aggregate extraction results from multiple pages.

    Args:
        page_results: List of extraction results from pages

    Returns:
        Aggregated donation information
    """
    # For multi-page documents, we need to intelligently combine results
    # For now, we'll take the first successful extraction
    # In production, this would be more sophisticated

    for result in page_results:
        if result.get("status") == "success" and result.get("extraction"):
            extraction = result["extraction"]

            # Convert to our donation models
            payment_info = None
            payer_info = None
            contact_info = None

            if extraction.get("payment_info"):
                payment_info = PaymentInfo(**extraction["payment_info"])

            if extraction.get("payer_info"):
                payer_data = extraction["payer_info"]
                # Ensure name field exists
                if "name" not in payer_data and "aliases" in payer_data:
                    aliases = payer_data["aliases"]
                    if isinstance(aliases, list) and len(aliases) > 0:
                        payer_data["name"] = aliases[0]
                    else:
                        payer_data["name"] = "Unknown"
                payer_info = PayerInfo(**payer_data)

            if extraction.get("contact_info"):
                contact_info = ContactInfo(**extraction["contact_info"])

            return {
                "payment_info": payment_info.model_dump() if payment_info else None,
                "payer_info": payer_info.model_dump() if payer_info else None,
                "contact_info": contact_info.model_dump() if contact_info else None,
                "confidence_scores": extraction.get("confidence_scores"),
                "document_type": extraction.get("document_type"),
            }

    # No successful extractions
    return {
        "payment_info": None,
        "payer_info": None,
        "contact_info": None,
        "error": "No successful extractions from any page",
    }


@celery_app.task(name="check_extraction_status")
def check_extraction_status(task_id: str) -> Dict[str, Any]:
    """
    Check the status of an extraction task.

    Args:
        task_id: Celery task ID

    Returns:
        Task status and result
    """
    from celery.result import AsyncResult

    result = AsyncResult(task_id, app=celery_app)

    return {
        "task_id": task_id,
        "status": result.status,
        "ready": result.ready(),
        "successful": result.successful() if result.ready() else None,
        "result": result.result if result.ready() else None,
    }
