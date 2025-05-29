"""
Redis memory monitoring and cleanup utilities.
"""

import logging
import os
from urllib.parse import urlparse

import redis

logger = logging.getLogger(__name__)


class RedisMemoryMonitor:
    def __init__(self):
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

        # Parse Redis URL
        parsed = urlparse(redis_url)

        # Handle SSL
        ssl_required = redis_url.startswith("rediss://")

        self.redis_client = redis.Redis(
            host=parsed.hostname,
            port=parsed.port or 6379,
            password=parsed.password,
            db=0,
            ssl=ssl_required,
            ssl_cert_reqs=None if ssl_required else None,
            decode_responses=True,
            socket_keepalive=True,
            socket_keepalive_options={
                1: 3,  # TCP_KEEPIDLE
                2: 3,  # TCP_KEEPINTVL
                3: 3,  # TCP_KEEPCNT
            },
        )

    def get_memory_info(self):
        """Get Redis memory usage information."""
        try:
            info = self.redis_client.info("memory")
            return {
                "used_memory": info.get("used_memory", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "used_memory_peak": info.get("used_memory_peak", 0),
                "used_memory_peak_human": info.get("used_memory_peak_human", "0B"),
                "maxmemory": info.get("maxmemory", 0),
                "maxmemory_human": info.get("maxmemory_human", "0B"),
                "mem_fragmentation_ratio": info.get("mem_fragmentation_ratio", 0),
            }
        except Exception as e:
            logger.error(f"Error getting Redis memory info: {e}")
            return None

    def cleanup_expired_keys(self):
        """Force cleanup of expired keys."""
        try:
            # This command forces Redis to delete expired keys
            self.redis_client.execute_command("MEMORY PURGE")
            logger.info("Redis memory purge executed")
        except Exception as e:
            logger.warning(f"Could not purge Redis memory: {e}")

    def cleanup_old_results(self, pattern="celery-task-meta-*", max_age_seconds=300):
        """Clean up old Celery task results."""
        try:
            count = 0
            for key in self.redis_client.scan_iter(match=pattern):
                try:
                    # Get TTL
                    ttl = self.redis_client.ttl(key)
                    # If no TTL set or key is old, delete it
                    if ttl == -1 or ttl > max_age_seconds:
                        self.redis_client.delete(key)
                        count += 1
                except Exception as e:
                    logger.warning(f"Error deleting key {key}: {e}")

            logger.info(f"Cleaned up {count} old task results")
            return count
        except Exception as e:
            logger.error(f"Error cleaning up old results: {e}")
            return 0

    def check_memory_usage(self, threshold_mb=25):
        """Check if memory usage is above threshold."""
        info = self.get_memory_info()
        if info:
            used_mb = info["used_memory"] / (1024 * 1024)
            if used_mb > threshold_mb:
                logger.warning(f"Redis memory usage high: {used_mb:.2f}MB")
                # Try cleanup
                self.cleanup_expired_keys()
                self.cleanup_old_results()
                return True
        return False


# Global instance
redis_monitor = RedisMemoryMonitor()
