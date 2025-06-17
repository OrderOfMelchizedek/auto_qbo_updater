"""Worker process for handling donation processing jobs.

This replaces the Celery worker with a simple Redis-based job processor.
"""
import contextlib
import logging
import os
import signal
import sys
import time

from .config import session_backend, storage_backend
from .donation_processor import process_donation_documents
from .job_queue import JobQueue
from .redis_connection import create_redis_client
from .storage import S3Storage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class Worker:
    """Simple worker that processes jobs from Redis queue."""

    def __init__(self):
        """Initialize worker with Redis connection."""
        # Create Redis client for job queue
        self.redis_client = create_redis_client(
            decode_responses=True, max_connections=3
        )

        if not self.redis_client:
            logger.error("Failed to connect to Redis - worker cannot start")
            sys.exit(1)

        self.job_queue = JobQueue(self.redis_client)
        self.running = True
        self.current_job = None

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

        logger.info("✓ Worker initialized successfully")

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False

        # If processing a job, let it complete
        if self.current_job:
            logger.info(
                f"Waiting for current job {self.current_job.get('job_id')} "
                "to complete..."
            )

    def process_job(self, job_data: dict) -> bool:
        """Process a single job.

        Args:
            job_data: Job information from queue

        Returns:
            True if successful, False otherwise
        """
        job_id = job_data.get("job_id")
        upload_id = job_data.get("upload_id")
        session_id = job_data.get("session_id")

        if not upload_id:
            raise ValueError("Missing upload_id in job data")

        logger.info(f"Processing job {job_id} for upload {upload_id}")

        try:
            # Get upload metadata
            metadata = session_backend.get_upload_metadata(upload_id)
            if not metadata:
                raise ValueError(f"Upload {upload_id} not found")

            # Get file paths
            from pathlib import Path as PathType
            from typing import List, Union

            if isinstance(storage_backend, S3Storage):
                # For S3, download files to temp directory
                temp_paths = storage_backend.download_batch_to_temp(upload_id)
                file_paths: List[Union[str, PathType]] = [str(p) for p in temp_paths]
            else:
                # For local storage, use paths directly
                raw_file_paths = storage_backend.get_file_paths(upload_id)
                file_paths = [
                    PathType(p) if isinstance(p, str) else p for p in raw_file_paths
                ]

            logger.info(f"Processing {len(file_paths)} files for job {job_id}")

            # Check for CSV path in local dev mode
            csv_path = None
            if os.getenv("LOCAL_DEV_MODE") == "true":
                from pathlib import Path

                csv_path = (
                    Path(__file__).parent.parent
                    / "src/tests/test_files/customer_contact_list.csv"
                )
                if csv_path.exists():
                    logger.info(f"Local dev mode: Using CSV at {csv_path}")

            # Process documents
            (
                processed_donations,
                extraction_metadata,
                display_donations,
            ) = process_donation_documents(
                file_paths, session_id=session_id, csv_path=csv_path
            )

            # Calculate final metadata
            processing_metadata = {
                "files_processed": len(file_paths),
                "valid_count": extraction_metadata["valid_count"],
                "raw_count": extraction_metadata["raw_count"],
                "duplicate_count": extraction_metadata["duplicate_count"],
                "matched_count": extraction_metadata.get("matched_count", 0),
            }

            # Update session with results
            session_backend.update_upload_metadata(
                upload_id,
                {
                    "status": "completed",
                    "donations": display_donations,
                    "raw_donations": processed_donations,
                    "processing_metadata": processing_metadata,
                    "summary": processing_metadata,  # Add summary for frontend
                },
            )

            # Clean up temp files if using S3
            if isinstance(storage_backend, S3Storage) and "temp_paths" in locals():
                for temp_path in temp_paths:
                    with contextlib.suppress(Exception):
                        temp_path.unlink()

            logger.info(
                f"Job {job_id} completed successfully. "
                f"Processed {len(display_donations)} donations"
            )
            return True

        except Exception as e:
            logger.error(f"Job {job_id} failed: {str(e)}", exc_info=True)

            # Update session status
            with contextlib.suppress(Exception):
                session_backend.update_upload_metadata(
                    upload_id, {"status": "failed", "error": str(e)}
                )

            return False

    def run(self):
        """Run the main worker loop."""
        logger.info("Worker starting main loop...")
        cleanup_counter = 0

        while self.running:
            try:
                # Periodically cleanup stale jobs
                cleanup_counter += 1
                if cleanup_counter >= 10:  # Every 10 iterations (~5 minutes)
                    self.job_queue.cleanup_stale_jobs()
                    cleanup_counter = 0

                    # Log queue stats
                    stats = self.job_queue.get_queue_stats()
                    logger.info(f"Queue stats: {stats}")

                # Wait for next job (blocking with timeout)
                logger.debug("Waiting for next job...")
                job_data = self.job_queue.pop_job(timeout=30)

                if not job_data:
                    # No job available, continue waiting
                    continue

                # Process the job
                self.current_job = job_data
                success = False

                try:
                    success = self.process_job(job_data)
                finally:
                    self.current_job = None

                # Mark job as completed or failed
                if success:
                    self.job_queue.complete_job(job_data)
                else:
                    error_msg = (
                        job_data.get("error", "Job processing failed")
                        if "error" in job_data
                        else "Unknown error"
                    )
                    self.job_queue.fail_job(job_data, error_msg)

            except Exception as e:
                logger.error(f"Worker error: {e}", exc_info=True)
                # Continue running unless shutdown signal received
                if self.running:
                    time.sleep(5)  # Brief pause before retrying

        logger.info("Worker shutting down")


def main():
    """Run the main entry point for worker process."""
    logger.info("Starting donation processing worker...")

    # Print configuration
    logger.info(f"Redis URL: {os.getenv('REDIS_URL', 'Not set')}")
    logger.info(f"Storage backend: {type(storage_backend).__name__}")
    logger.info(f"Session backend: {type(session_backend).__name__}")

    # Create and run worker
    worker = Worker()
    worker.run()


if __name__ == "__main__":
    main()
