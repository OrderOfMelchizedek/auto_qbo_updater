"""
Celery tasks for asynchronous file processing.
"""

import gc
import json
import logging
import os
import tempfile
import time
import traceback
from datetime import datetime

from celery import Task
from celery.exceptions import SoftTimeLimitExceeded
from werkzeug.utils import secure_filename

from .celery_app import celery_app
from .enhanced_file_processor_v3_second_pass import EnhancedFileProcessorV3
from .exceptions import FileProcessingException, FOMQBOException, ValidationException
from .gemini_adapter_v3 import GeminiAdapterV3

# from .gemini_service import GeminiService - moved to deprecated
from .memory_monitor import memory_monitor
from .progress_logger import log_progress, progress_logger
from .qbo_service import QBOService
from .redis_monitor import redis_monitor
from .result_store import result_store

logger = logging.getLogger(__name__)


class CallbackTask(Task):
    """Task base class with callbacks for progress tracking."""

    def on_success(self, retval, task_id, args, kwargs):
        """Called on successful task completion."""
        session_id = kwargs.get("session_id")
        if session_id:
            progress_logger.start_session(session_id)
            log_progress(f"Task {task_id} completed successfully")
            progress_logger.end_session(session_id)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called on task failure."""
        session_id = kwargs.get("session_id")
        if session_id:
            progress_logger.start_session(session_id)
            log_progress(f"Task {task_id} failed: {str(exc)}", force_summary=True)
            progress_logger.end_session(session_id)


@celery_app.task(
    base=CallbackTask,
    bind=True,
    name="src.utils.tasks.process_files_task",
    ignore_result=False,
    store_errors_even_if_ignored=True,
)
@memory_monitor.monitor_function
def process_files_task(
    self,
    s3_references=None,
    file_references=None,
    files_data=None,
    session_id=None,
    qbo_config=None,
    gemini_model=None,
):
    """
    Process uploaded files asynchronously.

    Args:
        s3_references: List of S3 file reference dicts (preferred method)
        file_references: List of file reference dicts (temp file method)
        files_data: List of dicts with file information (legacy method)
        session_id: Session ID for progress tracking
        qbo_config: QuickBooks configuration (access_token, realm_id, environment)
        gemini_model: Gemini model to use

    Returns:
        Processing results with donations data
    """
    try:
        # Initialize progress tracking
        if session_id:
            progress_logger.start_session(session_id)
            log_progress("Starting background file processing...")

        # Initialize services
        gemini_api_key = os.environ.get("GEMINI_API_KEY")
        if not gemini_api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")

        gemini_service = GeminiAdapterV3(
            api_key=gemini_api_key, model_name=gemini_model or "gemini-2.5-flash-preview-04-17"
        )
        # Get QBO credentials from environment
        qbo_client_id = os.environ.get("QBO_CLIENT_ID")
        qbo_client_secret = os.environ.get("QBO_CLIENT_SECRET")
        qbo_redirect_uri = os.environ.get("QBO_REDIRECT_URI", "http://localhost:5000/qbo/callback")

        if not qbo_client_id or not qbo_client_secret:
            raise ValueError("QBO_CLIENT_ID and QBO_CLIENT_SECRET environment variables must be set")

        qbo_service = QBOService(
            client_id=qbo_client_id,
            client_secret=qbo_client_secret,
            redirect_uri=qbo_redirect_uri,
            environment=qbo_config.get("environment", "sandbox") if qbo_config else "sandbox",
        )

        # Set QBO credentials if provided
        if qbo_config:
            qbo_service.access_token = qbo_config.get("access_token")
            qbo_service.realm_id = qbo_config.get("realm_id")
            qbo_service.refresh_token = qbo_config.get("refresh_token")
            # Set token expiry time if provided, otherwise default to 1 hour
            if qbo_config.get("token_expires_at"):
                qbo_service.token_expires_at = qbo_config.get("token_expires_at")
            elif qbo_config.get("access_token"):
                # Default to 1 hour if not provided but token exists
                qbo_service.token_expires_at = int(time.time()) + 3600

        # Initialize file processor with BOTH services
        file_processor = EnhancedFileProcessorV3(gemini_service, qbo_service)

        # Track processing results
        all_donations = []
        processing_errors = []
        warnings = []

        # Handle S3, temp file, and legacy methods
        saved_files = []
        temp_dir_context = None
        temp_dir = None

        if s3_references:
            # Preferred method: download files from S3
            try:
                from src.utils.s3_storage import S3Storage
            except ImportError:
                from utils.s3_storage import S3Storage

            s3_storage = S3Storage()

            # Create temp directory that will persist through processing
            temp_dir_context = tempfile.TemporaryDirectory()
            temp_dir = temp_dir_context.__enter__()

            for s3_ref in s3_references:
                try:
                    # Download from S3
                    file_content = s3_storage.download_file(s3_ref["s3_key"])

                    # Save to temp file for processing
                    filename = secure_filename(s3_ref["filename"])
                    filepath = os.path.join(temp_dir, filename)

                    with open(filepath, "wb") as f:
                        f.write(file_content)

                    saved_files.append(
                        {
                            "path": filepath,
                            "filename": s3_ref["filename"],
                            "content_type": s3_ref.get("content_type", "application/octet-stream"),
                            "s3_key": s3_ref["s3_key"],  # Keep reference for cleanup
                        }
                    )

                except Exception as e:
                    logger.error(f"Error downloading from S3: {s3_ref.get('filename', 'unknown')}: {str(e)}")
                    processing_errors.append(f"Failed to download {s3_ref.get('filename', 'unknown')}: {str(e)}")

        elif file_references:
            # Temp file method: files already saved to temp storage
            try:
                from src.utils.temp_file_manager import temp_file_manager
            except ImportError:
                from utils.temp_file_manager import temp_file_manager

            for file_ref in file_references:
                if os.path.exists(file_ref["temp_path"]):
                    saved_files.append(
                        {
                            "path": file_ref["temp_path"],
                            "filename": file_ref["original_filename"],
                            "content_type": file_ref["content_type"],
                        }
                    )
                else:
                    logger.error(f"Temp file not found: {file_ref['temp_path']}")
                    processing_errors.append(f"File not found: {file_ref['original_filename']}")

        elif files_data:
            # Legacy method: decode from base64 (for backward compatibility)
            temp_dir_context = tempfile.TemporaryDirectory()
            temp_dir = temp_dir_context.__enter__()

            for idx, file_data in enumerate(files_data):
                try:
                    filename = secure_filename(file_data["filename"])
                    if not filename:
                        filename = f"file_{idx}.dat"

                    filepath = os.path.join(temp_dir, filename)

                    # Write file content (base64 decoded)
                    import base64

                    with open(filepath, "wb") as f:
                        content = base64.b64decode(file_data["content"])
                        f.write(content)

                    saved_files.append(
                        {
                            "path": filepath,
                            "filename": filename,
                            "content_type": file_data.get("content_type", "application/octet-stream"),
                        }
                    )

                except Exception as e:
                    logger.error(f"Error saving file {file_data.get('filename', 'unknown')}: {str(e)}")
                    processing_errors.append(f"Failed to save {file_data.get('filename', 'unknown')}: {str(e)}")
        else:
            raise ValueError("No files provided to process")

        # Process all files together using V3 processor
        if saved_files:
            try:
                if session_id:
                    log_progress(f"Processing {len(saved_files)} files...")

                # Prepare file list for V3 processor
                files_to_process = []
                for file_info in saved_files:
                    _, ext = os.path.splitext(file_info["filename"])
                    files_to_process.append((file_info["path"], ext))

                # Process all files together - V3 returns enriched payments directly
                enriched_payments, file_errors = file_processor.process_files(files_to_process)

                if file_errors:
                    processing_errors.extend(file_errors)

                if enriched_payments:
                    if session_id:
                        log_progress(f"Found {len(enriched_payments)} donations total")

                    # V3 processor returns enriched payments in the correct format
                    all_donations.extend(enriched_payments)
                else:
                    warnings.append("No donations found in uploaded files")

            except SoftTimeLimitExceeded:
                error_msg = "Processing timeout for file batch"
                logger.error(error_msg)
                processing_errors.append(error_msg)
                if session_id:
                    log_progress(error_msg, force_summary=True)

            except Exception as e:
                error_msg = f"Error processing files: {str(e)}"
                logger.error(error_msg)
                processing_errors.append(error_msg)
                if session_id:
                    log_progress(error_msg)
            finally:
                # Force garbage collection after processing
                gc.collect()
                memory_monitor.log_memory_usage("After processing all files")

        # Clean up S3 files after processing
        if s3_references and "s3_storage" in locals():
            for file_info in saved_files:
                if "s3_key" in file_info:
                    try:
                        s3_storage.delete_file(file_info["s3_key"])
                        logger.info(f"Cleaned up S3 file: {file_info['s3_key']}")
                    except Exception as e:
                        logger.error(f"Failed to clean up S3 file {file_info['s3_key']}: {str(e)}")

        # V3 processor returns enriched donations (already deduplicated and matched)
        if all_donations:
            if session_id:
                log_progress(f"Processing complete with {len(all_donations)} donations")

            # V3 processor already handles deduplication, matching, and enrichment
            # Just validate final donations have required data
            filtered_donations = []
            for donation in all_donations:
                payment_info = donation.get("payment_info", {})
                payer_info = donation.get("payer_info", {})

                # Check for required data in enriched format
                payment_date = (payment_info.get("payment_date") or "").strip()
                deposit_date = (payment_info.get("deposit_date") or "").strip()
                amount = payment_info.get("amount", 0)
                customer_lookup = (payer_info.get("customer_lookup") or "").strip()

                # Only include donations that have amount, customer, AND either payment date or deposit date
                if amount and customer_lookup and (payment_date or deposit_date):
                    filtered_donations.append(donation)
                else:
                    logger.warning(
                        f"Filtering out donation without required data: Customer: {customer_lookup}, Amount: {amount}"
                    )

            if session_id and len(all_donations) != len(filtered_donations):
                log_progress(
                    f"Filtered to {len(filtered_donations)} valid donations (removed {len(all_donations) - len(filtered_donations)} without dates)"
                )

            # Log what we're about to return (enriched format)
            filtered_matched = sum(1 for d in filtered_donations if d.get("match_status") == "Matched")
            logger.warning(f"Returning {len(filtered_donations)} donations with {filtered_matched} matched")
            for idx, donation in enumerate(filtered_donations[:4]):
                payer_info = donation.get("payer_info", {})
                customer_lookup = payer_info.get("customer_lookup", "Unknown")
                match_status = donation.get("match_status", "New")
                qbo_customer_id = donation.get("qbo_customer_id")

                logger.warning(f"  Return {idx}: {customer_lookup} - Status: {match_status} - ID: {qbo_customer_id}")
                # Log full customer data if matched
                if match_status == "Matched":
                    logger.warning(
                        f"    Customer data: {json.dumps({'id': qbo_customer_id, 'name': customer_lookup, 'method': donation.get('match_method'), 'confidence': donation.get('match_confidence')})}"
                    )

            # Store full results in file system, return reference
            full_results = {
                "success": True,
                "donations": filtered_donations,
                "total_processed": len(filtered_donations),
                "warnings": warnings,
                "errors": processing_errors,
                "qboAuthenticated": qbo_service.is_token_valid(),
                "timestamp": datetime.now().isoformat(),
            }

            # Store large data in file and return reference
            if len(filtered_donations) > 50:  # Large result set
                result_ref = result_store.store_result(self.request.id, full_results)
                # Return lightweight reference for Redis
                results = {
                    "success": True,
                    "result_reference": result_ref,
                    "donations_count": len(filtered_donations),
                    "total_processed": len(all_donations),
                    "warnings_count": len(warnings),
                    "errors_count": len(processing_errors),
                    "qboAuthenticated": qbo_service.is_token_valid(),
                    "timestamp": datetime.now().isoformat(),
                }
            else:
                # Small result set - store normally
                results = full_results

            if session_id:
                log_progress(
                    f"Processing complete! Found {len(filtered_donations)} valid donations.",
                    force_summary=True,
                )

        else:
            results = {
                "success": False,
                "message": "No valid donations found in uploaded files",
                "warnings": warnings,
                "errors": processing_errors,
                "qboAuthenticated": qbo_service.is_token_valid(),
            }

            if session_id:
                log_progress("Processing complete. No valid donations found.", force_summary=True)

        return results

    except Exception as e:
        logger.error(f"Task failed: {str(e)}")
        if session_id:
            log_progress(f"Processing failed: {str(e)}", force_summary=True)

        return {"success": False, "message": f"Processing failed: {str(e)}", "errors": [str(e)]}
    finally:
        # Clean up temp directory
        if temp_dir_context:
            import contextlib

            with contextlib.suppress(Exception):
                temp_dir_context.__exit__(None, None, None)

        # Clean up temp files if using file references
        if file_references and session_id:
            try:
                from src.utils.temp_file_manager import temp_file_manager
            except ImportError:
                from utils.temp_file_manager import temp_file_manager
            temp_file_manager.cleanup_session(session_id)

        # Clean up S3 files if there was an error
        if s3_references and "s3_storage" in locals():
            for s3_ref in s3_references:
                try:
                    s3_storage.delete_file(s3_ref["s3_key"])
                    logger.info(f"Cleaned up S3 file on error: {s3_ref['s3_key']}")
                except Exception as e:
                    logger.error(f"Failed to clean up S3 file {s3_ref['s3_key']}: {str(e)}")

        # Final cleanup
        gc.collect()
        memory_monitor.log_memory_usage("Task completion")
        # Check Redis memory usage
        try:
            redis_monitor.check_memory_usage(threshold_mb=20)
        except Exception as e:
            logger.warning(f"Redis monitor error: {e}")


@celery_app.task(bind=True, name="src.utils.tasks.process_single_file_task")
def process_single_file_task(self, file_data, session_id=None):
    """Process a single file asynchronously (simplified version)."""
    try:
        # Similar to process_files_task but for single file
        # Implementation details omitted for brevity
        pass
    except Exception as e:
        logger.error(f"Single file task failed: {str(e)}")
        raise
