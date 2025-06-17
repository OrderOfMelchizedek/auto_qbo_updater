"""Simple Redis-based job queue to replace Celery.

This module provides a lightweight alternative to Celery that:
- Eliminates SSL broker connection issues
- Uses existing Redis connections
- Provides atomic job processing with BRPOPLPUSH
- Includes dead letter queue for failed jobs
"""
import json
import logging
import time
from typing import Any, Dict, Optional

import redis

from .redis_retry import redis_retry

logger = logging.getLogger(__name__)

# Queue names
JOB_QUEUE = "donation_jobs:pending"
PROCESSING_QUEUE = "donation_jobs:processing"
DEAD_LETTER_QUEUE = "donation_jobs:failed"
COMPLETED_QUEUE = "donation_jobs:completed"

# Timeouts
BLOCKING_TIMEOUT = 30  # seconds to wait for new job
JOB_TIMEOUT = 900  # 15 minutes max per job
CLEANUP_INTERVAL = 300  # 5 minutes


class JobQueue:
    """Simple Redis-based job queue."""

    def __init__(self, redis_client: redis.Redis):
        """Initialize job queue with Redis client.

        Args:
            redis_client: Redis client instance (reuses existing connection)
        """
        self.redis = redis_client
        self.enabled = redis_client is not None

    @redis_retry(exceptions=(redis.ConnectionError, redis.TimeoutError, Exception))
    def push_job(self, job_data: Dict[str, Any]) -> bool:
        """Push a job to the queue.

        Args:
            job_data: Dictionary containing job information
                Expected keys: job_id, upload_id, session_id

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            logger.error("Job queue disabled - Redis not available")
            return False

        try:
            # Add timestamp
            job_data["queued_at"] = time.time()

            # Push to queue (LPUSH for FIFO behavior with BRPOP)
            self.redis.lpush(JOB_QUEUE, json.dumps(job_data))

            logger.info(f"Job {job_data.get('job_id')} queued successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to queue job: {e}")
            return False

    def pop_job(self, timeout: int = BLOCKING_TIMEOUT) -> Optional[Dict[str, Any]]:
        """Pop a job from the queue (blocking).

        Uses BRPOPLPUSH for atomic move to processing queue.
        This ensures jobs aren't lost if worker crashes.

        Args:
            timeout: Seconds to wait for a job (0 = wait forever)

        Returns:
            Job data dict or None if timeout
        """
        if not self.enabled:
            return None

        try:
            # Atomic move from pending to processing queue
            result = self.redis.brpoplpush(JOB_QUEUE, PROCESSING_QUEUE, timeout=timeout)

            if result:
                job_data = json.loads(result)
                job_data["processing_started_at"] = time.time()
                logger.info(f"Job {job_data.get('job_id')} dequeued for processing")
                return job_data

            return None

        except json.JSONDecodeError as e:
            logger.error(f"Invalid job data in queue: {e}")
            # Move to dead letter queue
            if result:
                self.redis.lrem(PROCESSING_QUEUE, 1, result)
                self.redis.lpush(DEAD_LETTER_QUEUE, result)
            return None

        except redis.ConnectionError as e:
            logger.error(f"Redis connection error in pop_job: {e}")
            return None

        except Exception as e:
            logger.error(f"Unexpected error in pop_job: {e}")
            return None

    @redis_retry(exceptions=(redis.ConnectionError, redis.TimeoutError, Exception))
    def complete_job(self, job_data: Dict[str, Any]) -> bool:
        """Mark a job as completed.

        Removes from processing queue and adds to completed queue.

        Args:
            job_data: The job that was completed

        Returns:
            True if successful
        """
        if not self.enabled:
            return False

        try:
            # Get all jobs in processing queue to find exact match
            processing_jobs = self.redis.lrange(PROCESSING_QUEUE, 0, -1)
            removed = 0

            # Find and remove the job by job_id
            for job_json in processing_jobs:
                try:
                    existing_job = json.loads(job_json)
                    if existing_job.get("job_id") == job_data.get("job_id"):
                        removed = self.redis.lrem(PROCESSING_QUEUE, 1, job_json)
                        break
                except json.JSONDecodeError:
                    continue

            # Add completed timestamp and push to completed queue
            job_data["completed_at"] = time.time()
            completed_json = json.dumps(job_data)
            self.redis.lpush(COMPLETED_QUEUE, completed_json)
            self.redis.expire(COMPLETED_QUEUE, 86400)  # 24 hour TTL

            logger.info(f"Job {job_data.get('job_id')} completed")
            return removed > 0

        except Exception as e:
            logger.error(f"Failed to complete job: {e}")
            return False

    @redis_retry(exceptions=(redis.ConnectionError, redis.TimeoutError, Exception))
    def fail_job(self, job_data: Dict[str, Any], error: str) -> bool:
        """Mark a job as failed.

        Moves from processing to dead letter queue.

        Args:
            job_data: The job that failed
            error: Error message

        Returns:
            True if successful
        """
        if not self.enabled:
            return False

        try:
            # Get all jobs in processing queue to find exact match
            processing_jobs = self.redis.lrange(PROCESSING_QUEUE, 0, -1)
            removed = 0

            # Find and remove the job by job_id
            for job_json in processing_jobs:
                try:
                    existing_job = json.loads(job_json)
                    if existing_job.get("job_id") == job_data.get("job_id"):
                        removed = self.redis.lrem(PROCESSING_QUEUE, 1, job_json)
                        break
                except json.JSONDecodeError:
                    continue

            # Add failure info and push to dead letter queue
            job_data["failed_at"] = time.time()
            job_data["error"] = error
            failed_json = json.dumps(job_data)
            self.redis.lpush(DEAD_LETTER_QUEUE, failed_json)

            logger.error(f"Job {job_data.get('job_id')} failed: {error}")
            return removed > 0

        except Exception as e:
            logger.error(f"Failed to mark job as failed: {e}")
            return False

    def cleanup_stale_jobs(self, max_age_seconds: int = JOB_TIMEOUT) -> int:
        """Clean up jobs stuck in processing queue.

        Jobs that have been processing for too long are moved to dead letter queue.

        Args:
            max_age_seconds: Maximum time a job should be processing

        Returns:
            Number of stale jobs cleaned up
        """
        if not self.enabled:
            return 0

        try:
            stale_count = 0
            current_time = time.time()

            # Get all jobs in processing queue
            processing_jobs = self.redis.lrange(PROCESSING_QUEUE, 0, -1)

            for job_json in processing_jobs:
                try:
                    job_data = json.loads(job_json)
                    processing_started = job_data.get("processing_started_at", 0)

                    if current_time - processing_started > max_age_seconds:
                        # Move to dead letter queue
                        self.redis.lrem(PROCESSING_QUEUE, 1, job_json)
                        job_data["error"] = f"Job timed out after {max_age_seconds}s"
                        job_data["failed_at"] = current_time
                        self.redis.lpush(DEAD_LETTER_QUEUE, json.dumps(job_data))
                        stale_count += 1
                        logger.warning(f"Cleaned up stale job {job_data.get('job_id')}")

                except Exception as e:
                    logger.error(f"Error processing stale job: {e}")

            if stale_count > 0:
                logger.info(f"Cleaned up {stale_count} stale jobs")

            return stale_count

        except Exception as e:
            logger.error(f"Failed to cleanup stale jobs: {e}")
            return 0

    def get_queue_stats(self) -> Dict[str, Any]:
        """Get current queue statistics.

        Returns:
            Dict with queue lengths
        """
        if not self.enabled:
            return {"error": "Queue disabled"}

        try:
            return {
                "pending": self.redis.llen(JOB_QUEUE),
                "processing": self.redis.llen(PROCESSING_QUEUE),
                "failed": self.redis.llen(DEAD_LETTER_QUEUE),
                "completed": self.redis.llen(COMPLETED_QUEUE),
            }
        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")
            return {"error": str(e)}

    def is_job_completed(self, job_id: str) -> bool:
        """Check if a job is in the completed queue.

        Args:
            job_id: The job ID to check

        Returns:
            True if job is in completed queue, False otherwise
        """
        if not self.enabled:
            return False

        try:
            # Get all jobs in completed queue
            completed_jobs = self.redis.lrange(COMPLETED_QUEUE, 0, -1)
            for job_data in completed_jobs:
                job = json.loads(job_data)
                if job.get("job_id") == job_id:
                    return True
            return False
        except Exception as e:
            logger.error(f"Failed to check completed status for job {job_id}: {e}")
            return False

    def is_job_failed(self, job_id: str) -> bool:
        """Check if a job is in the failed queue.

        Args:
            job_id: The job ID to check

        Returns:
            True if job is in failed queue, False otherwise
        """
        if not self.enabled:
            return False

        try:
            # Get all jobs in failed queue
            failed_jobs = self.redis.lrange(DEAD_LETTER_QUEUE, 0, -1)
            for job_data in failed_jobs:
                job = json.loads(job_data)
                if job.get("job_id") == job_id:
                    return True
            return False
        except Exception as e:
            logger.error(f"Failed to check failed status for job {job_id}: {e}")
            return False

    def get_job_data(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job data from any queue.

        Args:
            job_id: The job ID to find

        Returns:
            Job data dict if found, None otherwise
        """
        if not self.enabled:
            return None

        try:
            # Check all queues
            all_queues = [
                JOB_QUEUE,
                PROCESSING_QUEUE,
                COMPLETED_QUEUE,
                DEAD_LETTER_QUEUE,
            ]

            for queue in all_queues:
                jobs = self.redis.lrange(queue, 0, -1)
                for job_data in jobs:
                    job = json.loads(job_data)
                    if job.get("job_id") == job_id:
                        return job

            return None
        except Exception as e:
            logger.error(f"Failed to get job data for {job_id}: {e}")
            return None
