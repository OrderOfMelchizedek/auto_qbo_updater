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
        include=['src.utils.tasks', 'src.utils.cleanup_tasks']  # Include tasks modules
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
        result_expires=300,  # Results expire after 5 minutes (reduced from 1 hour)
        result_backend_transport_options={
            'master_name': 'mymaster',
            'visibility_timeout': 300,
            'fanout_prefix': True,
            'fanout_patterns': True
        },
        
        # Worker configuration
        worker_prefetch_multiplier=1,  # Only fetch one task at a time
        worker_max_tasks_per_child=25,  # Restart worker after 25 tasks
        worker_max_memory_per_child=100000,  # 100MB max memory per worker (lower for multiple workers)
        
        # Task execution configuration
        task_soft_time_limit=300,  # 5 minutes soft limit (reduced from 10)
        task_time_limit=600,  # 10 minutes hard limit (reduced from 15)
        task_acks_late=True,  # Acknowledge tasks after completion
        task_reject_on_worker_lost=True,
        
        # Task routing
        task_routes={
            'src.utils.tasks.process_files_task': {'queue': 'file_processing'},
            'src.utils.tasks.process_single_file_task': {'queue': 'file_processing'},
        },
        
        # Broker configuration to prevent memory issues
        broker_transport_options={
            'fanout_prefix': True,
            'fanout_patterns': True,
            'visibility_timeout': 300,  # 5 minutes
            'priority_steps': list(range(10)),
            'max_retries': 3,
        },
        
        # Broker connection retry configuration
        broker_connection_retry_on_startup=True,
        broker_connection_retry=True,
        broker_connection_max_retries=10,
        
        # Redis memory optimization
        redis_max_connections=10,  # Limit connection pool
        redis_socket_keepalive=True,
        redis_socket_keepalive_options={
            1: 3,  # TCP_KEEPIDLE
            2: 3,  # TCP_KEEPINTVL
            3: 3,  # TCP_KEEPCNT
        },
    )
    
    return celery

# Create the Celery app
celery_app = make_celery('fom_qbo_automation')