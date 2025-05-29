"""
Celery configuration for production/Heroku deployment.
"""

import os

# Get Redis URL and handle SSL
redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
if redis_url.startswith("rediss://"):
    redis_url = f"{redis_url}?ssl_cert_reqs=none"

broker_url = redis_url
result_backend = redis_url

# Optimization for low memory environments (Heroku)
worker_max_memory_per_child = 100000  # 100MB per worker (allows 2 workers)
worker_concurrency = 2  # Two worker threads
worker_prefetch_multiplier = 1
task_acks_late = True
task_reject_on_worker_lost = True

# Result expiration
result_expires = 300  # 5 minutes

# Task time limits
task_soft_time_limit = 300  # 5 minutes
task_time_limit = 600  # 10 minutes

# Connection pool limits
broker_pool_limit = 1
redis_max_connections = 5

# Serialization
task_serializer = "json"
result_serializer = "json"
accept_content = ["json"]

# Don't store task results for some operations
task_ignore_result = False
task_store_eager_result = False

# Memory optimization
result_compression = "gzip"
result_backend_transport_options = {
    "master_name": "mymaster",
    "visibility_timeout": 300,
}
