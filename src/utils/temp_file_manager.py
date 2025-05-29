"""
Temporary file management for async uploads.
Stores uploaded files temporarily and provides references for Celery tasks.
"""
import os
import tempfile
import uuid
import json
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class TempFileManager:
    """Manages temporary file storage for async processing."""
    
    def __init__(self):
        # Create a dedicated temp directory for uploads
        self.temp_dir = os.path.join(tempfile.gettempdir(), 'fom_qbo_uploads')
        os.makedirs(self.temp_dir, exist_ok=True)
        
    def save_upload(self, file, session_id):
        """
        Save an uploaded file to temporary storage.
        
        Args:
            file: Flask FileStorage object
            session_id: Session ID for grouping files
            
        Returns:
            dict: File reference with path and metadata
        """
        try:
            # Create session directory
            session_dir = os.path.join(self.temp_dir, session_id)
            os.makedirs(session_dir, exist_ok=True)
            
            # Generate unique filename to avoid collisions
            file_id = str(uuid.uuid4())
            ext = os.path.splitext(file.filename)[1]
            temp_filename = f"{file_id}{ext}"
            temp_path = os.path.join(session_dir, temp_filename)
            
            # Save file
            file.save(temp_path)
            
            # Create metadata file
            metadata = {
                'original_filename': file.filename,
                'content_type': file.content_type or 'application/octet-stream',
                'file_id': file_id,
                'temp_path': temp_path,
                'uploaded_at': datetime.now().isoformat(),
                'size_bytes': os.path.getsize(temp_path)
            }
            
            metadata_path = temp_path + '.meta'
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f)
            
            logger.info(f"Saved file {file.filename} to {temp_path} ({metadata['size_bytes']} bytes)")
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error saving uploaded file: {e}")
            raise
    
    def get_file_info(self, temp_path):
        """Retrieve file info from metadata."""
        try:
            metadata_path = temp_path + '.meta'
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    return json.load(f)
            return None
        except Exception as e:
            logger.error(f"Error reading file metadata: {e}")
            return None
    
    def cleanup_session(self, session_id):
        """Clean up all files for a session."""
        try:
            session_dir = os.path.join(self.temp_dir, session_id)
            if os.path.exists(session_dir):
                import shutil
                shutil.rmtree(session_dir)
                logger.info(f"Cleaned up session directory: {session_dir}")
        except Exception as e:
            logger.error(f"Error cleaning up session {session_id}: {e}")
    
    def cleanup_old_files(self, max_age_hours=2):
        """Clean up old temporary files."""
        try:
            count = 0
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            
            for session_id in os.listdir(self.temp_dir):
                session_dir = os.path.join(self.temp_dir, session_id)
                if not os.path.isdir(session_dir):
                    continue
                    
                # Check directory age
                dir_mtime = datetime.fromtimestamp(os.path.getmtime(session_dir))
                if dir_mtime < cutoff_time:
                    import shutil
                    shutil.rmtree(session_dir)
                    count += 1
                    logger.info(f"Cleaned up old session: {session_id}")
            
            return count
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return 0

# Global instance
temp_file_manager = TempFileManager()