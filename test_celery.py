#!/usr/bin/env python3
"""
Test script to verify Celery setup is working.
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from utils.celery_app import celery_app
from utils.tasks import process_files_task

def test_celery_connection():
    """Test if Celery can connect to Redis."""
    print("Testing Celery connection...")
    
    try:
        # Test connection
        i = celery_app.control.inspect()
        stats = i.stats()
        
        if stats:
            print("✅ Celery is connected and workers are running!")
            print(f"Active workers: {list(stats.keys())}")
        else:
            print("⚠️  No Celery workers are currently running.")
            print("Start a worker with: celery -A src.utils.celery_app:celery_app worker --loglevel=info")
    except Exception as e:
        print(f"❌ Error connecting to Celery: {e}")
        print("Make sure Redis is running and REDIS_URL is set correctly.")

def test_simple_task():
    """Test submitting a simple task."""
    print("\nTesting task submission...")
    
    try:
        # Create a simple test task
        test_data = [{
            'filename': 'test.txt',
            'content': 'VGVzdCBjb250ZW50',  # Base64 encoded "Test content"
            'content_type': 'text/plain'
        }]
        
        # Submit task
        result = process_files_task.apply_async(
            args=[test_data],
            kwargs={'session_id': 'test-session'}
        )
        
        print(f"✅ Task submitted successfully!")
        print(f"Task ID: {result.id}")
        print(f"Task state: {result.state}")
        
        # Wait for result (with timeout)
        print("\nWaiting for result (5 seconds timeout)...")
        try:
            task_result = result.get(timeout=5)
            print(f"✅ Task completed: {task_result}")
        except Exception as e:
            print(f"⚠️  Task not completed within timeout: {e}")
            print("This is normal if no worker is running.")
            
    except Exception as e:
        print(f"❌ Error submitting task: {e}")

if __name__ == "__main__":
    print("Celery Test Script")
    print("==================")
    print(f"Redis URL: {os.getenv('REDIS_URL', 'Not set')}")
    print()
    
    test_celery_connection()
    test_simple_task()
    
    print("\nTo start a Celery worker locally, run:")
    print("celery -A src.utils.celery_app:celery_app worker --loglevel=info")