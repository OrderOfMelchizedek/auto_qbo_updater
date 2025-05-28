"""
Celery tasks for asynchronous file processing.
"""
import os
import json
import tempfile
import logging
import gc
from celery import Task
from celery.exceptions import SoftTimeLimitExceeded
from werkzeug.utils import secure_filename
from datetime import datetime

from .celery_app import celery_app
from .file_processor import FileProcessor
from .gemini_service import GeminiService
from .qbo_service import QBOService
from .progress_logger import log_progress, progress_logger
from .memory_monitor import memory_monitor
from .exceptions import FOMQBOException, ValidationException, FileProcessingException

logger = logging.getLogger(__name__)

class CallbackTask(Task):
    """Task base class with callbacks for progress tracking."""
    
    def on_success(self, retval, task_id, args, kwargs):
        """Called on successful task completion."""
        session_id = kwargs.get('session_id')
        if session_id:
            log_progress(f"Task {task_id} completed successfully", session_id=session_id)
            progress_logger.end_session(session_id)
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called on task failure."""
        session_id = kwargs.get('session_id')
        if session_id:
            log_progress(f"Task {task_id} failed: {str(exc)}", session_id=session_id, force_summary=True)
            progress_logger.end_session(session_id)


@celery_app.task(base=CallbackTask, bind=True, name='src.utils.tasks.process_files_task')
@memory_monitor.monitor_function
def process_files_task(self, files_data, session_id=None, qbo_config=None, gemini_model=None):
    """
    Process uploaded files asynchronously.
    
    Args:
        files_data: List of dicts with file information (filename, content, content_type)
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
            log_progress("Starting background file processing...", session_id=session_id)
        
        # Initialize services
        gemini_service = GeminiService(model_name=gemini_model)
        qbo_service = QBOService(
            environment=qbo_config.get('environment', 'sandbox') if qbo_config else 'sandbox'
        )
        
        # Set QBO credentials if provided
        if qbo_config:
            qbo_service.access_token = qbo_config.get('access_token')
            qbo_service.realm_id = qbo_config.get('realm_id')
            qbo_service.refresh_token = qbo_config.get('refresh_token')
        
        file_processor = FileProcessor(gemini_service)
        
        # Track processing results
        all_donations = []
        processing_errors = []
        warnings = []
        
        # Create temporary directory for file processing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save uploaded files to temp directory
            saved_files = []
            for idx, file_data in enumerate(files_data):
                try:
                    filename = secure_filename(file_data['filename'])
                    if not filename:
                        filename = f"file_{idx}.dat"
                    
                    filepath = os.path.join(temp_dir, filename)
                    
                    # Write file content (base64 decoded)
                    import base64
                    with open(filepath, 'wb') as f:
                        content = base64.b64decode(file_data['content'])
                        f.write(content)
                    
                    saved_files.append({
                        'path': filepath,
                        'filename': filename,
                        'content_type': file_data.get('content_type', 'application/octet-stream')
                    })
                    
                except Exception as e:
                    logger.error(f"Error saving file {file_data.get('filename', 'unknown')}: {str(e)}")
                    processing_errors.append(f"Failed to save {file_data.get('filename', 'unknown')}: {str(e)}")
            
            # Process each file
            for file_info in saved_files:
                try:
                    if session_id:
                        log_progress(f"Processing {file_info['filename']}...", session_id=session_id)
                    
                    # Process file based on type
                    donations = file_processor.process_file(
                        file_info['path'],
                        file_info['filename'],
                        file_info['content_type']
                    )
                    
                    if donations:
                        all_donations.extend(donations)
                        if session_id:
                            log_progress(
                                f"Found {len(donations)} donations in {file_info['filename']}", 
                                session_id=session_id
                            )
                    else:
                        warnings.append(f"No donations found in {file_info['filename']}")
                        
                except SoftTimeLimitExceeded:
                    error_msg = f"Processing timeout for {file_info['filename']}"
                    logger.error(error_msg)
                    processing_errors.append(error_msg)
                    if session_id:
                        log_progress(error_msg, session_id=session_id, force_summary=True)
                    
                except Exception as e:
                    error_msg = f"Error processing {file_info['filename']}: {str(e)}"
                    logger.error(error_msg)
                    processing_errors.append(error_msg)
                    if session_id:
                        log_progress(error_msg, session_id=session_id)
                finally:
                    # Force garbage collection after each file
                    gc.collect()
                    memory_monitor.log_memory_usage(f"After processing {file_info.get('filename', 'file')}")
        
        # Validate and enhance donations
        if all_donations:
            if session_id:
                log_progress(f"Validating {len(all_donations)} donations...", session_id=session_id)
            
            try:
                from src.app import validate_and_enhance_donations
            except ImportError:
                from ..app import validate_and_enhance_donations
            validated_donations = validate_and_enhance_donations(all_donations)
            
            # Deduplicate donations
            if session_id:
                log_progress("Removing duplicate donations...", session_id=session_id)
            
            try:
                from src.app import deduplicate_donations
            except ImportError:
                from ..app import deduplicate_donations
            unique_donations = deduplicate_donations(validated_donations, [])
            
            # Match with QBO customers if authenticated
            if qbo_service.is_authenticated() and unique_donations:
                if session_id:
                    log_progress("Matching donations with QuickBooks customers...", session_id=session_id)
                
                try:
                    try:
                        from src.app import match_donations_with_qbo_customers
                    except ImportError:
                        from ..app import match_donations_with_qbo_customers
                    unique_donations = match_donations_with_qbo_customers(
                        unique_donations, 
                        qbo_service,
                        gemini_service
                    )
                except Exception as e:
                    logger.error(f"Error matching QBO customers: {str(e)}")
                    warnings.append(f"Could not match QuickBooks customers: {str(e)}")
            
            # Prepare results
            results = {
                'success': True,
                'donations': unique_donations,
                'total_processed': len(unique_donations),
                'warnings': warnings,
                'errors': processing_errors,
                'qboAuthenticated': qbo_service.is_authenticated(),
                'timestamp': datetime.now().isoformat()
            }
            
            if session_id:
                log_progress(
                    f"Processing complete! Found {len(unique_donations)} unique donations.", 
                    session_id=session_id,
                    force_summary=True
                )
            
        else:
            results = {
                'success': False,
                'message': 'No valid donations found in uploaded files',
                'warnings': warnings,
                'errors': processing_errors,
                'qboAuthenticated': qbo_service.is_authenticated()
            }
            
            if session_id:
                log_progress(
                    "Processing complete. No valid donations found.", 
                    session_id=session_id,
                    force_summary=True
                )
        
        return results
        
    except Exception as e:
        logger.error(f"Task failed: {str(e)}")
        if session_id:
            log_progress(f"Processing failed: {str(e)}", session_id=session_id, force_summary=True)
        
        return {
            'success': False,
            'message': f'Processing failed: {str(e)}',
            'errors': [str(e)]
        }
    finally:
        # Final cleanup
        gc.collect()
        memory_monitor.log_memory_usage("Task completion")


@celery_app.task(bind=True, name='src.utils.tasks.process_single_file_task')
def process_single_file_task(self, file_data, session_id=None):
    """Process a single file asynchronously (simplified version)."""
    try:
        # Similar to process_files_task but for single file
        # Implementation details omitted for brevity
        pass
    except Exception as e:
        logger.error(f"Single file task failed: {str(e)}")
        raise