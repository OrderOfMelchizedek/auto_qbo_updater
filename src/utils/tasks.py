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
from .redis_monitor import redis_monitor
from .result_store import result_store
from .exceptions import FOMQBOException, ValidationException, FileProcessingException

logger = logging.getLogger(__name__)

class CallbackTask(Task):
    """Task base class with callbacks for progress tracking."""
    
    def on_success(self, retval, task_id, args, kwargs):
        """Called on successful task completion."""
        session_id = kwargs.get('session_id')
        if session_id:
            progress_logger.start_session(session_id)
            log_progress(f"Task {task_id} completed successfully")
            progress_logger.end_session(session_id)
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called on task failure."""
        session_id = kwargs.get('session_id')
        if session_id:
            progress_logger.start_session(session_id)
            log_progress(f"Task {task_id} failed: {str(exc)}", force_summary=True)
            progress_logger.end_session(session_id)


@celery_app.task(base=CallbackTask, bind=True, name='src.utils.tasks.process_files_task', 
                ignore_result=False, store_errors_even_if_ignored=True)
@memory_monitor.monitor_function
def process_files_task(self, file_references=None, files_data=None, session_id=None, qbo_config=None, gemini_model=None):
    """
    Process uploaded files asynchronously.
    
    Args:
        file_references: List of file reference dicts (new method)
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
        gemini_api_key = os.environ.get('GEMINI_API_KEY')
        if not gemini_api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        
        gemini_service = GeminiService(
            api_key=gemini_api_key,
            model_name=gemini_model or 'gemini-2.5-flash-preview-04-17'
        )
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
        
        # Handle both new (file_references) and legacy (files_data) methods
        saved_files = []
        
        if file_references:
            # New method: files already saved to temp storage
            try:
                from src.utils.temp_file_manager import temp_file_manager
            except ImportError:
                from utils.temp_file_manager import temp_file_manager
                
            for file_ref in file_references:
                if os.path.exists(file_ref['temp_path']):
                    saved_files.append({
                        'path': file_ref['temp_path'],
                        'filename': file_ref['original_filename'],
                        'content_type': file_ref['content_type']
                    })
                else:
                    logger.error(f"Temp file not found: {file_ref['temp_path']}")
                    processing_errors.append(f"File not found: {file_ref['original_filename']}")
        
        elif files_data:
            # Legacy method: decode from base64 (for backward compatibility)
            with tempfile.TemporaryDirectory() as temp_dir:
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
        else:
            raise ValueError("No files provided to process")
            
            # Process each file
            for file_info in saved_files:
                try:
                    if session_id:
                        log_progress(f"Processing {file_info['filename']}...")
                    
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
                        log_progress(error_msg, force_summary=True)
                    
                except Exception as e:
                    error_msg = f"Error processing {file_info['filename']}: {str(e)}"
                    logger.error(error_msg)
                    processing_errors.append(error_msg)
                    if session_id:
                        log_progress(error_msg)
                finally:
                    # Force garbage collection after each file
                    gc.collect()
                    memory_monitor.log_memory_usage(f"After processing {file_info.get('filename', 'file')}")
        
        # Validate and enhance donations
        if all_donations:
            if session_id:
                log_progress(f"Validating {len(all_donations)} donations...")
            
            try:
                from src.app import validate_and_enhance_donations
            except ImportError:
                from ..app import validate_and_enhance_donations
            validated_donations = validate_and_enhance_donations(all_donations)
            
            # Deduplicate donations
            if session_id:
                log_progress("Removing duplicate donations...")
            
            try:
                from src.app import deduplicate_donations
            except ImportError:
                from ..app import deduplicate_donations
            unique_donations = deduplicate_donations(validated_donations, [])
            
            # Match with QBO customers if authenticated
            if qbo_service.is_token_valid() and unique_donations:
                if session_id:
                    log_progress("Matching donations with QuickBooks customers...")
                
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
            
            # Store full results in file system, return reference
            full_results = {
                'success': True,
                'donations': unique_donations,
                'total_processed': len(unique_donations),
                'warnings': warnings,
                'errors': processing_errors,
                'qboAuthenticated': qbo_service.is_token_valid(),
                'timestamp': datetime.now().isoformat()
            }
            
            # Store large data in file and return reference
            if len(unique_donations) > 50:  # Large result set
                result_ref = result_store.store_result(self.request.id, full_results)
                # Return lightweight reference for Redis
                results = {
                    'success': True,
                    'result_reference': result_ref,
                    'donations_count': len(unique_donations),
                    'total_processed': len(unique_donations),
                    'warnings_count': len(warnings),
                    'errors_count': len(processing_errors),
                    'qboAuthenticated': qbo_service.is_token_valid(),
                    'timestamp': datetime.now().isoformat()
                }
            else:
                # Small result set - store normally
                results = full_results
            
            if session_id:
                log_progress(
                    f"Processing complete! Found {len(unique_donations)} unique donations.", 
                    force_summary=True
                )
            
        else:
            results = {
                'success': False,
                'message': 'No valid donations found in uploaded files',
                'warnings': warnings,
                'errors': processing_errors,
                'qboAuthenticated': qbo_service.is_token_valid()
            }
            
            if session_id:
                log_progress(
                    "Processing complete. No valid donations found.", 
                    force_summary=True
                )
        
        return results
        
    except Exception as e:
        logger.error(f"Task failed: {str(e)}")
        if session_id:
            log_progress(f"Processing failed: {str(e)}", force_summary=True)
        
        return {
            'success': False,
            'message': f'Processing failed: {str(e)}',
            'errors': [str(e)]
        }
    finally:
        # Clean up temp files if using file references
        if file_references and session_id:
            try:
                from src.utils.temp_file_manager import temp_file_manager
            except ImportError:
                from utils.temp_file_manager import temp_file_manager
            temp_file_manager.cleanup_session(session_id)
            
        # Final cleanup
        gc.collect()
        memory_monitor.log_memory_usage("Task completion")
        # Check Redis memory usage
        try:
            redis_monitor.check_memory_usage(threshold_mb=20)
        except Exception as e:
            logger.warning(f"Redis monitor error: {e}")


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