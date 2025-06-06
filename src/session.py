"""
Session abstraction layer for upload metadata storage.

Supports local JSON files (development) and Redis (production).
"""
import json
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SessionBackend(ABC):
    """Abstract base class for session/metadata storage backends."""

    @abstractmethod
    def store_upload_metadata(self, upload_id: str, metadata: Dict[str, Any]) -> bool:
        """
        Store metadata for an upload batch.

        Args:
            upload_id: Unique identifier for the upload batch
            metadata: Dictionary containing upload information

        Returns:
            bool: True if successful, False otherwise
        """
        pass

    @abstractmethod
    def get_upload_metadata(self, upload_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve metadata for an upload batch.

        Args:
            upload_id: Unique identifier for the upload batch

        Returns:
            Dict or None: Metadata if found, None otherwise
        """
        pass

    @abstractmethod
    def update_upload_metadata(self, upload_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update existing metadata for an upload batch.

        Args:
            upload_id: Unique identifier for the upload batch
            updates: Dictionary of fields to update

        Returns:
            bool: True if successful, False otherwise
        """
        pass

    @abstractmethod
    def delete_upload_metadata(self, upload_id: str) -> bool:
        """
        Delete metadata for an upload batch.

        Args:
            upload_id: Unique identifier for the upload batch

        Returns:
            bool: True if successful, False otherwise
        """
        pass

    @abstractmethod
    def list_uploads(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        List recent upload batches.

        Args:
            limit: Maximum number of uploads to return

        Returns:
            List of upload metadata dictionaries
        """
        pass


class LocalSession(SessionBackend):
    """JSON file-based session storage for development."""

    def __init__(self, base_path: str = "session_data"):
        """
        Initialize local session storage.

        Args:
            base_path: Base directory for storing session files
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)

    def _get_metadata_path(self, upload_id: str) -> Path:
        """Get path to metadata file for upload."""
        return self.base_path / f"{upload_id}.json"

    def store_upload_metadata(self, upload_id: str, metadata: Dict[str, Any]) -> bool:
        """Store metadata as JSON file."""
        try:
            # Add timestamp if not present
            if "created_at" not in metadata:
                metadata["created_at"] = datetime.utcnow().isoformat()

            metadata["upload_id"] = upload_id

            metadata_path = self._get_metadata_path(upload_id)
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

            logger.info(f"Stored metadata for upload {upload_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to store metadata: {e}")
            return False

    def get_upload_metadata(self, upload_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve metadata from JSON file."""
        metadata_path = self._get_metadata_path(upload_id)

        if not metadata_path.exists():
            return None

        try:
            with open(metadata_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read metadata: {e}")
            return None

    def update_upload_metadata(self, upload_id: str, updates: Dict[str, Any]) -> bool:
        """Update existing metadata."""
        metadata = self.get_upload_metadata(upload_id)

        if not metadata:
            return False

        # Update fields
        metadata.update(updates)
        metadata["updated_at"] = datetime.utcnow().isoformat()

        return self.store_upload_metadata(upload_id, metadata)

    def delete_upload_metadata(self, upload_id: str) -> bool:
        """Delete metadata file."""
        metadata_path = self._get_metadata_path(upload_id)

        if metadata_path.exists():
            metadata_path.unlink()
            logger.info(f"Deleted metadata for upload {upload_id}")
            return True

        return False

    def list_uploads(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List recent uploads from JSON files."""
        uploads = []

        # Get all JSON files
        for metadata_file in self.base_path.glob("*.json"):
            try:
                with open(metadata_file, "r") as f:
                    metadata = json.load(f)
                    uploads.append(metadata)
            except Exception:
                continue

        # Sort by created_at descending
        uploads.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        return uploads[:limit]


class RedisSession(SessionBackend):
    """Redis-based session storage for production."""

    def __init__(self):
        """Initialize Redis session storage."""
        import redis

        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            raise ValueError("REDIS_URL environment variable not set")

        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        self.key_prefix = "donation_upload:"
        self.ttl_seconds = 86400 * 7  # 7 days

    def _get_redis_key(self, upload_id: str) -> str:
        """Generate Redis key for upload."""
        return f"{self.key_prefix}{upload_id}"

    def store_upload_metadata(self, upload_id: str, metadata: Dict[str, Any]) -> bool:
        """Store metadata in Redis with TTL."""
        try:
            # Add timestamp if not present
            if "created_at" not in metadata:
                metadata["created_at"] = datetime.utcnow().isoformat()

            metadata["upload_id"] = upload_id

            key = self._get_redis_key(upload_id)

            # Store as JSON string
            self.redis_client.setex(key, self.ttl_seconds, json.dumps(metadata))

            # Also add to sorted set for listing
            self.redis_client.zadd(
                f"{self.key_prefix}uploads", {upload_id: datetime.utcnow().timestamp()}
            )

            logger.info(f"Stored metadata for upload {upload_id} in Redis")
            return True

        except Exception as e:
            logger.error(f"Failed to store metadata in Redis: {e}")
            return False

    def get_upload_metadata(self, upload_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve metadata from Redis."""
        try:
            key = self._get_redis_key(upload_id)
            data = self.redis_client.get(key)

            if data:
                return json.loads(data)

            return None

        except Exception as e:
            logger.error(f"Failed to get metadata from Redis: {e}")
            return None

    def update_upload_metadata(self, upload_id: str, updates: Dict[str, Any]) -> bool:
        """Update existing metadata in Redis."""
        metadata = self.get_upload_metadata(upload_id)

        if not metadata:
            return False

        # Update fields
        metadata.update(updates)
        metadata["updated_at"] = datetime.utcnow().isoformat()

        return self.store_upload_metadata(upload_id, metadata)

    def delete_upload_metadata(self, upload_id: str) -> bool:
        """Delete metadata from Redis."""
        try:
            key = self._get_redis_key(upload_id)

            # Delete the metadata
            self.redis_client.delete(key)

            # Remove from sorted set
            self.redis_client.zrem(f"{self.key_prefix}uploads", upload_id)

            logger.info(f"Deleted metadata for upload {upload_id} from Redis")
            return True

        except Exception as e:
            logger.error(f"Failed to delete metadata from Redis: {e}")
            return False

    def list_uploads(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List recent uploads from Redis sorted set."""
        try:
            # Get recent upload IDs from sorted set
            upload_ids = self.redis_client.zrevrange(
                f"{self.key_prefix}uploads", 0, limit - 1
            )

            uploads = []
            for upload_id in upload_ids:
                metadata = self.get_upload_metadata(upload_id)
                if metadata:
                    uploads.append(metadata)

            return uploads

        except Exception as e:
            logger.error(f"Failed to list uploads from Redis: {e}")
            return []

    def cleanup_old_uploads(self, days: int = 7) -> int:
        """
        Clean up uploads older than specified days.

        Args:
            days: Number of days to keep uploads

        Returns:
            int: Number of uploads cleaned up
        """
        try:
            cutoff_timestamp = (datetime.utcnow() - timedelta(days=days)).timestamp()

            # Get old upload IDs
            old_uploads = self.redis_client.zrangebyscore(
                f"{self.key_prefix}uploads", 0, cutoff_timestamp
            )

            # Delete them
            for upload_id in old_uploads:
                self.delete_upload_metadata(upload_id)

            logger.info(f"Cleaned up {len(old_uploads)} old uploads")
            return len(old_uploads)

        except Exception as e:
            logger.error(f"Failed to cleanup old uploads: {e}")
            return 0
