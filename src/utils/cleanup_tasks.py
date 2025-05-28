"""
Periodic cleanup tasks to manage memory and storage.
"""
import logging
from celery import Task
from .celery_app import celery_app
from .redis_monitor import redis_monitor
from .result_store import result_store
from .temp_file_manager import temp_file_manager

logger = logging.getLogger(__name__)

@celery_app.task(name='src.utils.cleanup_tasks.cleanup_redis_memory')
def cleanup_redis_memory():
    """Periodic task to clean up Redis memory."""
    try:
        logger.info("Running Redis memory cleanup")
        
        # Check and cleanup Redis
        redis_monitor.check_memory_usage(threshold_mb=25)
        
        # Cleanup old Celery results
        cleaned = redis_monitor.cleanup_old_results(max_age_seconds=300)
        
        logger.info(f"Redis cleanup completed. Cleaned {cleaned} old results")
        return {'success': True, 'cleaned_count': cleaned}
        
    except Exception as e:
        logger.error(f"Redis cleanup failed: {e}")
        return {'success': False, 'error': str(e)}

@celery_app.task(name='src.utils.cleanup_tasks.cleanup_result_files')
def cleanup_result_files():
    """Periodic task to clean up old result files."""
    try:
        logger.info("Running result file cleanup")
        
        # Cleanup files older than 1 hour
        cleaned = result_store.cleanup_old_results(max_age_hours=1)
        
        logger.info(f"File cleanup completed. Removed {cleaned} old files")
        return {'success': True, 'cleaned_count': cleaned}
        
    except Exception as e:
        logger.error(f"File cleanup failed: {e}")
        return {'success': False, 'error': str(e)}

@celery_app.task(name='src.utils.cleanup_tasks.cleanup_temp_files')
def cleanup_temp_files():
    """Periodic task to clean up old temporary upload files."""
    try:
        logger.info("Running temp file cleanup")
        
        # Cleanup files older than 2 hours
        cleaned = temp_file_manager.cleanup_old_files(max_age_hours=2)
        
        logger.info(f"Temp file cleanup completed. Removed {cleaned} old sessions")
        return {'success': True, 'cleaned_count': cleaned}
        
    except Exception as e:
        logger.error(f"Temp file cleanup failed: {e}")
        return {'success': False, 'error': str(e)}

# Configure periodic tasks
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    'cleanup-redis-memory': {
        'task': 'src.utils.cleanup_tasks.cleanup_redis_memory',
        'schedule': crontab(minute='*/10'),  # Every 10 minutes
    },
    'cleanup-result-files': {
        'task': 'src.utils.cleanup_tasks.cleanup_result_files',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
    },
    'cleanup-temp-files': {
        'task': 'src.utils.cleanup_tasks.cleanup_temp_files',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
    },
}