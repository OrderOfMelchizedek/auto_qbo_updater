"""Routes for file upload and processing operations."""

import logging
import os
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request, session
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

files_bp = Blueprint("files", __name__)


def get_qbo_service():
    """Get QBO service instance from app context."""
    return current_app.qbo_service


def get_file_processor():
    """Get file processor instance from app context."""
    return current_app.file_processor


def get_memory_monitor():
    """Get memory monitor instance from app context."""
    return current_app.memory_monitor


@files_bp.route("/upload-start", methods=["POST"])
def upload_start():
    """Initialize a new upload session."""
    try:
        # Generate new session ID
        new_session_id = str(uuid.uuid4())
        session["session_id"] = new_session_id
        session["donations"] = []
        session["upload_in_progress"] = True
        session["upload_start_time"] = datetime.now().isoformat()

        logger.info(f"Started new upload session: {new_session_id}")

        return jsonify({"success": True, "session_id": new_session_id})
    except Exception as e:
        logger.error(f"Error starting upload session: {str(e)}")
        return jsonify({"error": str(e)}), 500


@files_bp.route("/upload-async", methods=["POST"])
def upload_files_async():
    """Handle file upload with async processing via Celery."""
    try:
        from services.validation import log_audit_event
        from utils.result_store import ResultStore
        from utils.tasks import process_files_task

        result_store = ResultStore()

        # Check for files
        if "files" not in request.files:
            return jsonify({"error": "No files provided"}), 400

        files = request.files.getlist("files")
        if not files or all(f.filename == "" for f in files):
            return jsonify({"error": "No files selected"}), 400

        # Validate file count
        max_files = int(os.getenv("MAX_FILES_PER_UPLOAD", 20))
        if len(files) > max_files:
            return jsonify({"error": f"Too many files. Maximum {max_files} files allowed."}), 400

        # Generate session ID
        session_id = session.get("session_id") or str(uuid.uuid4())
        session["session_id"] = session_id

        # Check authentication
        qbo_authenticated = session.get("qbo_authenticated", False)

        # Log upload attempt
        log_audit_event(
            "file_upload_async",
            user_id=session_id,
            details={"file_count": len(files), "qbo_authenticated": qbo_authenticated},
            request_ip=request.remote_addr,
        )

        # Process each file
        file_paths = []
        for file in files:
            if file and file.filename:
                # Generate secure filename
                original_filename = secure_filename(file.filename)
                unique_filename = f"{uuid.uuid4()}_{original_filename}"
                file_path = os.path.join(current_app.config["UPLOAD_FOLDER"], unique_filename)

                # Save file
                file.save(file_path)
                file_paths.append({"path": file_path, "original_name": original_filename})

                logger.info(f"Saved file for async processing: {original_filename}")

        # Submit to Celery
        task = process_files_task.delay(
            file_paths=file_paths, session_id=session_id, qbo_authenticated=qbo_authenticated
        )

        # Store task metadata
        result_store.store_task_metadata(
            task.id,
            {
                "session_id": session_id,
                "file_count": len(file_paths),
                "status": "pending",
                "created_at": datetime.utcnow().isoformat(),
            },
        )

        logger.info(f"Submitted async task {task.id} for session {session_id}")

        return jsonify(
            {
                "success": True,
                "task_id": task.id,
                "session_id": session_id,
                "message": f"Processing {len(file_paths)} files...",
            }
        )

    except Exception as e:
        logger.error(f"Error in async upload: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@files_bp.route("/upload", methods=["POST"])
def upload_files():
    """Synchronous file upload handler with memory monitoring."""
    try:
        from services.deduplication import DeduplicationService
        from services.validation import log_audit_event
        from utils.progress_logger import log_progress

        memory_monitor = get_memory_monitor()
        memory_monitor.log_memory("upload_start")

        # Check for files
        if "files" not in request.files:
            return jsonify({"error": "No files provided"}), 400

        files = request.files.getlist("files")
        if not files or all(f.filename == "" for f in files):
            return jsonify({"error": "No files selected"}), 400

        # Validate file count
        max_files = int(os.getenv("MAX_FILES_PER_UPLOAD", 20))
        if len(files) > max_files:
            return jsonify({"error": f"Too many files. Maximum {max_files} files allowed."}), 400

        # Generate or get session ID
        session_id = session.get("session_id")
        if not session_id:
            session_id = str(uuid.uuid4())
            session["session_id"] = session_id
            session["donations"] = []
            logger.info(f"Created new session: {session_id}")

        # Check QBO authentication
        qbo_authenticated = session.get("qbo_authenticated", False)
        qbo_service = get_qbo_service() if qbo_authenticated else None

        # Initialize progress
        log_progress("Starting file upload...", 0)

        # Log upload attempt
        log_audit_event(
            "file_upload",
            user_id=session_id,
            details={
                "file_count": len(files),
                "filenames": [f.filename for f in files if f.filename],
                "qbo_authenticated": qbo_authenticated,
            },
            request_ip=request.remote_addr,
        )

        # Store file data for parallel processing
        file_data_list = []
        for idx, file in enumerate(files):
            if file and file.filename:
                file_data_list.append(
                    {"file_storage": file, "filename": file.filename, "index": idx}
                )

        if not file_data_list:
            return jsonify({"error": "No valid files to process"}), 400

        # Process files in parallel
        all_donations = []
        errors = []
        processed_files = []

        log_progress(f"Processing {len(file_data_list)} files...", 10)

        # Import process_single_file from app context
        process_single_file = current_app.process_single_file

        # Use ThreadPoolExecutor for parallel processing
        max_workers = min(4, len(file_data_list))  # Limit concurrent processing

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all files for processing
            future_to_file = {
                executor.submit(process_single_file, file_data, qbo_authenticated): file_data
                for file_data in file_data_list
            }

            # Process completed tasks
            for idx, future in enumerate(as_completed(future_to_file)):
                file_data = future_to_file[future]
                progress = 10 + int((idx + 1) / len(file_data_list) * 60)  # 10-70%

                try:
                    result = future.result()

                    if result["success"]:
                        processed_files.append(
                            {
                                "filename": result["filename"],
                                "donation_count": len(result["donations"]),
                                "processing_time": result["processing_time"],
                            }
                        )
                        all_donations.extend(result["donations"])
                        log_progress(
                            f"Processed {result['filename']}: {len(result['donations'])} donations",
                            progress,
                        )
                    else:
                        errors.append({"filename": result["filename"], "error": result["error"]})
                        log_progress(
                            f"Error processing {result['filename']}: {result['error']}", progress
                        )

                    # Clean up uploaded file
                    if result.get("file_path"):
                        cleanup_uploaded_file = current_app.cleanup_uploaded_file
                        cleanup_uploaded_file(result["file_path"])

                except Exception as e:
                    logger.error(
                        f"Error processing {file_data['filename']}: {str(e)}", exc_info=True
                    )
                    errors.append({"filename": file_data["filename"], "error": str(e)})

                # Memory cleanup after each file
                memory_monitor.cleanup()

        # Log memory after file processing
        memory_monitor.log_memory("after_file_processing")

        # Deduplicate donations
        if all_donations:
            log_progress("Deduplicating donations...", 75)

            # Get existing donations from session
            existing_donations = session.get("donations", [])

            # Use deduplication service
            unique_donations = DeduplicationService.deduplicate_donations(
                existing_donations, all_donations
            )

            # Store in session
            session["donations"] = unique_donations
            session.modified = True

            log_progress(f"Found {len(unique_donations)} unique donations", 85)

            # Apply customer matching if QBO is authenticated
            if qbo_authenticated and qbo_service:
                log_progress("Matching customers in QuickBooks...", 90)
                matched_count = 0

                for donation in unique_donations:
                    if donation.get("Donor Name"):
                        try:
                            customer = qbo_service.find_customer(donation["Donor Name"])
                            if customer:
                                donation["qboCustomerId"] = customer.get("Id")
                                donation["qbCustomerStatus"] = "Found"
                                donation["matchMethod"] = "Automatic"
                                donation["matchConfidence"] = "High"
                                matched_count += 1
                        except Exception as e:
                            logger.error(f"Error matching customer: {e}")

                log_progress(f"Matched {matched_count} customers", 95)

        # Log final memory usage
        memory_monitor.log_memory("upload_complete")

        # Prepare response
        response_data = {
            "success": True,
            "session_id": session_id,
            "processed_files": processed_files,
            "total_donations": len(session.get("donations", [])),
            "errors": errors,
            "qbo_authenticated": qbo_authenticated,
        }

        if all_donations:
            response_data["donations_found"] = len(all_donations)
            response_data["unique_donations"] = len(session.get("donations", []))

        log_progress("Upload complete!", 100)

        # Log successful processing
        log_audit_event(
            "file_processing_complete",
            user_id=session_id,
            details={
                "files_processed": len(processed_files),
                "total_donations": len(session.get("donations", [])),
                "errors": len(errors),
            },
            request_ip=request.remote_addr,
        )

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Upload error: {str(e)}", exc_info=True)
        memory_monitor.log_memory("upload_error")

        log_audit_event(
            "file_upload_error",
            user_id=session.get("session_id"),
            details={"error": str(e)},
            request_ip=request.remote_addr,
        )

        return jsonify({"error": str(e)}), 500
    finally:
        # Always clean up memory
        memory_monitor.cleanup()


@files_bp.route("/task-status/<task_id>", methods=["GET"])
def get_task_status(task_id):
    """Get status of async processing task."""
    try:
        from utils.celery_app import celery_app
        from utils.result_store import ResultStore

        result_store = ResultStore()

        # Get task result
        result = celery_app.AsyncResult(task_id)

        # Get metadata
        metadata = result_store.get_task_metadata(task_id)

        response = {"task_id": task_id, "state": result.state, "metadata": metadata}

        if result.state == "PENDING":
            response["status"] = "Task is waiting to be processed"
        elif result.state == "PROGRESS":
            response["current"] = result.info.get("current", 0)
            response["total"] = result.info.get("total", 1)
            response["status"] = result.info.get("status", "")
        elif result.state == "SUCCESS":
            response["result"] = result.result
            response["status"] = "Task completed successfully"

            # Store results in session if available
            if result.result and "donations" in result.result:
                session_id = metadata.get("session_id")
                if session_id and session.get("session_id") == session_id:
                    session["donations"] = result.result["donations"]
                    session.modified = True
        elif result.state == "FAILURE":
            response["error"] = str(result.info)
            response["status"] = "Task failed"

        return jsonify(response)

    except Exception as e:
        logger.error(f"Error getting task status: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500
