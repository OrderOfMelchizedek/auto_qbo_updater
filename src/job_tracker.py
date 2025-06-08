"""Job tracking system for background tasks."""
import json
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

import redis


class JobStatus(Enum):
    """Job status enumeration."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobStage(Enum):
    """Processing stages for donation jobs."""

    UPLOADING = "uploading"
    EXTRACTING = "extracting"
    VALIDATING = "validating"
    MATCHING = "matching"
    FINALIZING = "finalizing"


class JobTracker:
    """Track background job status and progress in Redis."""

    def __init__(self, redis_url: Optional[str] = None):
        """Initialize job tracker with Redis connection."""
        self.redis_url = redis_url or "redis://localhost:6379/0"

        # Handle SSL for Heroku Redis
        if self.redis_url.startswith("rediss://"):
            # Use SSL but disable cert verification for Heroku
            self.redis_client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                max_connections=3,
                socket_keepalive=True,
                ssl_cert_reqs=None,
                ssl_ca_certs=None,
                ssl_certfile=None,
                ssl_keyfile=None,
                ssl_check_hostname=False,
            )
        else:
            self.redis_client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                max_connections=3,
                socket_keepalive=True,
            )

        self.ttl = 3600  # Job data expires after 1 hour

    def create_job(self, job_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new job entry."""
        job_data = {
            "id": job_id,
            "status": JobStatus.PENDING.value,
            "stage": JobStage.UPLOADING.value,
            "progress": 0,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "data": data,
            "result": None,
            "error": None,
            "events": [],
        }

        # Store in Redis with expiration
        self.redis_client.setex(f"job:{job_id}", self.ttl, json.dumps(job_data))

        return job_data

    def update_job(
        self, job_id: str, updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update job status and data."""
        job_key = f"job:{job_id}"
        job_data = self.get_job(job_id)

        if not job_data:
            return None

        # Update fields
        job_data.update(updates)
        job_data["updated_at"] = datetime.utcnow().isoformat()

        # Store updated data
        self.redis_client.setex(job_key, self.ttl, json.dumps(job_data))

        # Publish update event for SSE
        event_data = {
            "job_id": job_id,
            "type": "job_update",
            "timestamp": job_data["updated_at"],
            **updates,
        }
        self.publish_event(job_id, event_data)

        return job_data

    def update_progress(
        self, job_id: str, stage: JobStage, progress: int, message: Optional[str] = None
    ):
        """Update job progress and stage."""
        updates = {
            "stage": stage.value,
            "progress": min(100, max(0, progress)),
            "status": JobStatus.PROCESSING.value,
        }

        if message:
            self.add_event(
                job_id,
                {
                    "type": "progress",
                    "stage": stage.value,
                    "progress": updates["progress"],
                    "message": message,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

        return self.update_job(job_id, updates)

    def complete_job(self, job_id: str, result: Dict[str, Any]):
        """Mark job as completed with results."""
        return self.update_job(
            job_id,
            {"status": JobStatus.COMPLETED.value, "progress": 100, "result": result},
        )

    def fail_job(self, job_id: str, error: str):
        """Mark job as failed with error."""
        return self.update_job(
            job_id, {"status": JobStatus.FAILED.value, "error": error}
        )

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job data by ID."""
        job_data = self.redis_client.get(f"job:{job_id}")
        if job_data:
            return json.loads(job_data)
        return None

    def add_event(self, job_id: str, event: Dict[str, Any]):
        """Add event to job history."""
        job_data = self.get_job(job_id)
        if job_data:
            job_data["events"].append(event)
            self.redis_client.setex(f"job:{job_id}", self.ttl, json.dumps(job_data))

    def publish_event(self, job_id: str, event_data: Dict[str, Any]):
        """Publish event for SSE subscribers."""
        channel = f"job_events:{job_id}"
        self.redis_client.publish(channel, json.dumps(event_data))

    def subscribe_to_job(self, job_id: str):
        """Subscribe to job events for SSE."""
        pubsub = self.redis_client.pubsub()
        channel = f"job_events:{job_id}"
        pubsub.subscribe(channel)
        return pubsub

    def cleanup_expired_jobs(self):
        """Clean up expired job data (called periodically)."""
        # Redis handles expiration automatically with TTL
        pass
