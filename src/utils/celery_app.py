"""
Celery configuration and initialization.
"""
import os
from celery import Celery
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def make_celery(app_name=__name__):
    """Create and configure Celery instance."""
    
    # Get Redis URL from environment
    redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    
    # Handle Heroku Redis SSL URLs
    if redis_url.startswith('rediss://'):
        # For SSL Redis connections, add SSL parameters
        redis_url = f"{redis_url}?ssl_cert_reqs=none"
    
    # Create Celery instance
    celery = Celery(
        app_name,
        broker=redis_url,
        backend=redis_url,
        include=['src.utils.tasks']  # Include tasks module
    )
    
    # Update configuration
    celery.conf.update(
        # Task configuration
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        
        # Result backend configuration
        result_expires=3600,  # Results expire after 1 hour
        
        # Worker configuration
        worker_prefetch_multiplier=1,  # Only fetch one task at a time
        worker_max_tasks_per_child=100,  # Restart worker after 100 tasks
        
        # Task execution configuration
        task_soft_time_limit=600,  # 10 minutes soft limit
        task_time_limit=900,  # 15 minutes hard limit
        
        # Task routing
        task_routes={
            'src.utils.tasks.process_files_task': {'queue': 'file_processing'},
            'src.utils.tasks.process_single_file_task': {'queue': 'file_processing'},
        },
        
        # Broker connection retry configuration
        broker_connection_retry_on_startup=True,
        broker_connection_retry=True,
        broker_connection_max_retries=10,
    )
    
    return celery

# Create the Celery app
celery_app = make_celery('fom_qbo_automation')