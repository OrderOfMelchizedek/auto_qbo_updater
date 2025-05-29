"""Alternative result storage to avoid Redis memory issues.

Store large results in temporary files and only keep references in Redis.
"""

import json
import logging
import os
import tempfile
import uuid
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ResultStore:
    """Store large task results in temp files instead of Redis."""

    def __init__(self, temp_dir=None):
        """Initialize the result store.

        Args:
            temp_dir: Optional custom temporary directory path. If not provided,
                     uses the system's default temp directory.
        """
        self.temp_dir = temp_dir or tempfile.gettempdir()
        self.results_dir = os.path.join(self.temp_dir, "fom_qbo_results")
        os.makedirs(self.results_dir, exist_ok=True)

    def store_result(self, task_id, result_data):
        """Store result data in a temp file and return reference."""
        try:
            # Generate unique filename
            filename = f"result_{task_id}_{uuid.uuid4().hex}.json"
            filepath = os.path.join(self.results_dir, filename)

            # Write result to file
            with open(filepath, "w") as f:
                json.dump(result_data, f)

            # Return reference
            return {
                "type": "file_reference",
                "filepath": filepath,
                "task_id": task_id,
                "timestamp": datetime.now().isoformat(),
                "size_bytes": os.path.getsize(filepath),
            }

        except Exception as e:
            logger.error(f"Failed to store result for task {task_id}: {e}")
            # Fallback to returning truncated data
            return {
                "type": "inline",
                "data": str(result_data)[:1000],  # Truncate to 1KB
                "truncated": True,
                "error": str(e),
            }

    def retrieve_result(self, reference):
        """Retrieve result data from reference."""
        try:
            if reference.get("type") == "file_reference":
                filepath = reference.get("filepath")
                if filepath and os.path.exists(filepath):
                    with open(filepath, "r") as f:
                        return json.load(f)
            elif reference.get("type") == "inline":
                return reference.get("data")

        except Exception as e:
            logger.error(f"Failed to retrieve result: {e}")

        return None

    def cleanup_old_results(self, max_age_hours=1):
        """Clean up old result files."""
        try:
            count = 0
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

            for filename in os.listdir(self.results_dir):
                filepath = os.path.join(self.results_dir, filename)
                try:
                    # Check file age
                    mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                    if mtime < cutoff_time:
                        os.remove(filepath)
                        count += 1
                except Exception as e:
                    logger.warning(f"Error cleaning up {filename}: {e}")

            logger.info(f"Cleaned up {count} old result files")
            return count

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return 0

    def get_task_metadata(self, task_id):
        """Get metadata for a task.

        Args:
            task_id: The task ID to get metadata for

        Returns:
            Dictionary with task metadata or None if not found
        """
        try:
            # Look for result files matching this task ID
            for filename in os.listdir(self.results_dir):
                if f"result_{task_id}_" in filename:
                    filepath = os.path.join(self.results_dir, filename)

                    # Get file stats
                    stats = os.stat(filepath)
                    mtime = datetime.fromtimestamp(stats.st_mtime)

                    return {
                        "task_id": task_id,
                        "filename": filename,
                        "filepath": filepath,
                        "size_bytes": stats.st_size,
                        "created_at": mtime.isoformat(),
                        "age_seconds": (datetime.now() - mtime).total_seconds(),
                    }
        except Exception as e:
            logger.error(f"Error getting task metadata for {task_id}: {e}")

        return None

    def store_task_metadata(self, task_id, metadata):
        """Store metadata for a task.

        Args:
            task_id: The task ID
            metadata: Dictionary of metadata to store

        Returns:
            True if successful, False otherwise
        """
        try:
            # Store metadata in a separate file
            metadata_filename = f"metadata_{task_id}.json"
            metadata_filepath = os.path.join(self.results_dir, metadata_filename)

            # Add timestamp
            metadata["stored_at"] = datetime.now().isoformat()

            with open(metadata_filepath, "w") as f:
                json.dump(metadata, f)

            return True

        except Exception as e:
            logger.error(f"Error storing task metadata for {task_id}: {e}")
            return False


# Global instance
result_store = ResultStore()
