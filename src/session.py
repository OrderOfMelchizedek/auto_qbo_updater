"""
Session abstraction layer for upload metadata storage.

Supports local JSON files (development) and Redis (production).
"""
import json
import logging
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

    # OAuth2 token storage methods
    @abstractmethod
    def store_auth_state(self, session_id: str, state_data: Dict[str, Any]) -> bool:
        """Store OAuth2 state for CSRF protection."""
        pass

    @abstractmethod
    def get_auth_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve OAuth2 state."""
        pass

    @abstractmethod
    def delete_auth_state(self, session_id: str) -> bool:
        """Delete OAuth2 state."""
        pass

    @abstractmethod
    def store_tokens(self, session_id: str, encrypted_tokens: bytes) -> bool:
        """Store encrypted OAuth2 tokens."""
        pass

    @abstractmethod
    def get_tokens(self, session_id: str) -> Optional[bytes]:
        """Retrieve encrypted OAuth2 tokens."""
        pass

    @abstractmethod
    def delete_tokens(self, session_id: str) -> bool:
        """Delete OAuth2 tokens."""
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

    # OAuth2 token storage implementation
    def store_auth_state(self, session_id: str, state_data: Dict[str, Any]) -> bool:
        """Store OAuth2 state for CSRF protection."""
        try:
            state_path = self.base_path / "auth_states" / f"{session_id}.json"
            state_path.parent.mkdir(exist_ok=True)

            with open(state_path, "w") as f:
                json.dump(state_data, f)
            return True
        except Exception as e:
            logger.error(f"Failed to store auth state: {e}")
            return False

    def get_auth_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve OAuth2 state."""
        try:
            state_path = self.base_path / "auth_states" / f"{session_id}.json"
            if state_path.exists():
                with open(state_path, "r") as f:
                    return json.load(f)
            return None
        except Exception as e:
            logger.error(f"Failed to get auth state: {e}")
            return None

    def delete_auth_state(self, session_id: str) -> bool:
        """Delete OAuth2 state."""
        try:
            state_path = self.base_path / "auth_states" / f"{session_id}.json"
            if state_path.exists():
                state_path.unlink()
            return True
        except Exception:
            return False

    def store_tokens(self, session_id: str, encrypted_tokens: bytes) -> bool:
        """Store encrypted OAuth2 tokens."""
        try:
            token_path = self.base_path / "tokens" / f"{session_id}.bin"
            token_path.parent.mkdir(exist_ok=True)

            with open(token_path, "wb") as f:
                f.write(encrypted_tokens)
            return True
        except Exception as e:
            logger.error(f"Failed to store tokens: {e}")
            return False

    def get_tokens(self, session_id: str) -> Optional[bytes]:
        """Retrieve encrypted OAuth2 tokens."""
        try:
            token_path = self.base_path / "tokens" / f"{session_id}.bin"
            if token_path.exists():
                with open(token_path, "rb") as f:
                    return f.read()
            return None
        except Exception as e:
            logger.error(f"Failed to get tokens: {e}")
            return None

    def delete_tokens(self, session_id: str) -> bool:
        """Delete OAuth2 tokens."""
        try:
            token_path = self.base_path / "tokens" / f"{session_id}.bin"
            if token_path.exists():
                token_path.unlink()
            return True
        except Exception:
            return False


class RedisSession(SessionBackend):
    """Redis-based session storage for production."""

    def __init__(self):
        """Initialize Redis session storage."""
        from .redis_connection import create_redis_client

        self.redis_client = create_redis_client(
            decode_responses=True, max_connections=5
        )
        self.key_prefix = "donation_upload:"
        self.ttl_seconds = 86400 * 7  # 7 days
        self.enabled = self.redis_client is not None

    def _get_redis_key(self, upload_id: str) -> str:
        """Generate Redis key for upload."""
        return f"{self.key_prefix}{upload_id}"

    def store_upload_metadata(self, upload_id: str, metadata: Dict[str, Any]) -> bool:
        """Store metadata in Redis with TTL."""
        if not self.enabled:
            return False

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
        if not self.enabled:
            return None

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
        if not self.enabled:
            return False

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
        if not self.enabled:
            return []

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
        if not self.enabled:
            return 0

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

    # OAuth2 token storage implementation
    def store_auth_state(self, session_id: str, state_data: Dict[str, Any]) -> bool:
        """Store OAuth2 state for CSRF protection."""
        if not self.enabled:
            return False

        try:
            key = f"auth_state:{session_id}"
            # Short TTL for auth state (10 minutes)
            self.redis_client.setex(key, 600, json.dumps(state_data))
            return True
        except Exception as e:
            logger.error(f"Failed to store auth state in Redis: {e}")
            return False

    def get_auth_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve OAuth2 state."""
        if not self.enabled:
            return None

        try:
            key = f"auth_state:{session_id}"
            data = self.redis_client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Failed to get auth state from Redis: {e}")
            return None

    def delete_auth_state(self, session_id: str) -> bool:
        """Delete OAuth2 state."""
        if not self.enabled:
            return False

        try:
            key = f"auth_state:{session_id}"
            self.redis_client.delete(key)
            return True
        except Exception:
            return False

    def store_tokens(self, session_id: str, encrypted_tokens: bytes) -> bool:
        """Store encrypted OAuth2 tokens."""
        if not self.enabled:
            return False

        try:
            key = f"oauth_tokens:{session_id}"
            # Store with 100 day TTL (matching refresh token expiry)
            self.redis_client.setex(key, 86400 * 100, encrypted_tokens)
            return True
        except Exception as e:
            logger.error(f"Failed to store tokens in Redis: {e}")
            return False

    def get_tokens(self, session_id: str) -> Optional[bytes]:
        """Retrieve encrypted OAuth2 tokens."""
        if not self.enabled:
            return None

        try:
            key = f"oauth_tokens:{session_id}"
            data = self.redis_client.get(key)
            if data:
                return data.encode() if isinstance(data, str) else data
            return None
        except Exception as e:
            logger.error(f"Failed to get tokens from Redis: {e}")
            return None

    def delete_tokens(self, session_id: str) -> bool:
        """Delete OAuth2 tokens."""
        if not self.enabled:
            return False

        try:
            key = f"oauth_tokens:{session_id}"
            self.redis_client.delete(key)
            return True
        except Exception:
            return False
