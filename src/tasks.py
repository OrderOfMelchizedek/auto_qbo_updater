"""Background tasks for donation processing."""
import logging
import os
from contextlib import suppress
from pathlib import Path
from typing import Optional

from .celery_app import celery_app
from .config import session_backend, storage_backend
from .donation_processor import process_donation_documents
from .job_tracker import JobStage, JobTracker
from .storage import S3Storage

logger = logging.getLogger(__name__)

# Initialize job tracker
job_tracker = JobTracker(os.getenv("REDIS_URL"))


@celery_app.task(bind=True, name="process_donations_task")
def process_donations_task(
    self, job_id: str, upload_id: str, session_id: Optional[str] = None
):
    """
    Process donation documents in the background.

    Args:
        job_id: Unique job identifier
        upload_id: Upload batch identifier
        session_id: Optional QuickBooks session ID
    """
    try:
        # Update job status to processing
        job_tracker.update_progress(
            job_id, JobStage.EXTRACTING, 10, "Starting document processing"
        )

        # Get upload metadata
        metadata = session_backend.get_upload_metadata(upload_id)
        if not metadata:
            raise ValueError(f"Upload {upload_id} not found")

        # Get file paths
        job_tracker.update_progress(
            job_id, JobStage.EXTRACTING, 20, "Loading uploaded files"
        )

        if isinstance(storage_backend, S3Storage):
            # For S3, download files to temp directory
            temp_paths = storage_backend.download_batch_to_temp(upload_id)
            file_paths = [str(p) for p in temp_paths]
        else:
            # For local storage, use paths directly
            file_paths = storage_backend.get_file_paths(upload_id)

        # Update progress
        job_tracker.update_progress(
            job_id, JobStage.EXTRACTING, 30, f"Processing {len(file_paths)} files"
        )

        # Check for CSV path in local dev mode
        csv_path = None
        if os.getenv("LOCAL_DEV_MODE") == "true":
            # Use absolute path to ensure it's found
            csv_path = (
                Path(__file__).parent.parent
                / "src/tests/test_files/customer_contact_list.csv"
            )
            logger.info(f"Local dev mode: Checking for CSV at {csv_path}")
            if csv_path.exists():
                logger.info(
                    f"Local dev mode: Using CSV for customer matching at {csv_path}"
                )
            else:
                logger.error(f"Local dev mode: CSV file not found at {csv_path}")

        # Process documents with progress updates
        job_tracker.update_progress(
            job_id, JobStage.EXTRACTING, 40, "Extracting donation data"
        )

        # Run the processing pipeline
        (
            processed_donations,
            extraction_metadata,
            display_donations,
        ) = process_donation_documents(
            file_paths, session_id=session_id, csv_path=csv_path  # type: ignore
        )

        # Update to validation stage
        job_tracker.update_progress(
            job_id, JobStage.VALIDATING, 60, "Validating donations"
        )

        # Update to matching stage
        job_tracker.update_progress(
            job_id, JobStage.MATCHING, 80, "Matching with QuickBooks"
        )

        # Calculate final metadata
        processing_metadata = {
            "files_processed": len(file_paths),
            "valid_count": extraction_metadata["valid_count"],
            "raw_count": extraction_metadata["raw_count"],
            "duplicate_count": extraction_metadata["duplicate_count"],
            "matched_count": extraction_metadata.get("matched_count", 0),
        }

        # Update to finalizing stage
        job_tracker.update_progress(
            job_id, JobStage.FINALIZING, 90, "Finalizing results"
        )

        # Update session with results
        session_backend.update_upload_metadata(
            upload_id,
            {
                "status": "processed",
                "donations": display_donations,
                "raw_donations": processed_donations,
                "processing_metadata": processing_metadata,
            },
        )

        # Clean up temp files if using S3
        if isinstance(storage_backend, S3Storage):
            for temp_path in temp_paths:
                with suppress(Exception):
                    temp_path.unlink()

        # Complete the job
        result = {
            "donations": display_donations,
            "raw_donations": processed_donations,
            "metadata": processing_metadata,
        }

        job_tracker.complete_job(job_id, result)
        job_tracker.update_progress(
            job_id, JobStage.FINALIZING, 100, "Processing complete"
        )

        logger.info(f"Job {job_id} completed successfully")
        return result

    except Exception as e:
        logger.error(f"Job {job_id} failed: {str(e)}")
        job_tracker.fail_job(job_id, str(e))

        # Update session status
        session_backend.update_upload_metadata(
            upload_id, {"status": "failed", "error": str(e)}
        )

        # Clean up temp files if they exist
        if isinstance(storage_backend, S3Storage) and "temp_paths" in locals():
            for temp_path in temp_paths:
                with suppress(Exception):
                    temp_path.unlink()

        raise
