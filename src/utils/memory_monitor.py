import gc
import os
import psutil
import tracemalloc
from functools import wraps
from typing import Callable, Any

class MemoryMonitor:
    """Monitor and manage memory usage in the application."""
    
    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.high_memory_threshold_mb = 400  # Threshold for high memory warning
        self.critical_memory_threshold_mb = 450  # Threshold for critical memory
        
    def get_memory_usage(self) -> dict:
        """Get current memory usage statistics."""
        memory_info = self.process.memory_info()
        memory_percent = self.process.memory_percent()
        
        return {
            'rss_mb': memory_info.rss / 1024 / 1024,
            'vms_mb': memory_info.vms / 1024 / 1024,
            'percent': memory_percent,
            'available_mb': psutil.virtual_memory().available / 1024 / 1024
        }
    
    def log_memory_usage(self, context: str = ""):
        """Log current memory usage."""
        stats = self.get_memory_usage()
        print(f"[Memory Monitor] {context} - RSS: {stats['rss_mb']:.1f}MB ({stats['percent']:.1f}%), Available: {stats['available_mb']:.1f}MB")
        
        if stats['rss_mb'] > self.critical_memory_threshold_mb:
            print(f"[Memory Monitor] CRITICAL: Memory usage exceeds {self.critical_memory_threshold_mb}MB!")
            # Force garbage collection
            self.force_cleanup()
        elif stats['rss_mb'] > self.high_memory_threshold_mb:
            print(f"[Memory Monitor] WARNING: Memory usage exceeds {self.high_memory_threshold_mb}MB")
    
    def force_cleanup(self):
        """Force garbage collection and memory cleanup."""
        print("[Memory Monitor] Forcing garbage collection...")
        collected = gc.collect()
        print(f"[Memory Monitor] Garbage collector freed {collected} objects")
    
    def monitor_function(self, func: Callable) -> Callable:
        """Decorator to monitor memory usage of a function."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Log memory before
            self.log_memory_usage(f"Before {func.__name__}")
            
            try:
                # Execute function
                result = func(*args, **kwargs)
                
                # Log memory after
                self.log_memory_usage(f"After {func.__name__}")
                
                # Check if we should run garbage collection
                stats = self.get_memory_usage()
                if stats['rss_mb'] > self.high_memory_threshold_mb:
                    self.force_cleanup()
                    self.log_memory_usage(f"After cleanup in {func.__name__}")
                
                return result
                
            except Exception as e:
                self.log_memory_usage(f"Error in {func.__name__}")
                raise
                
        return wrapper
    
    def start_tracing(self):
        """Start memory allocation tracing."""
        tracemalloc.start()
    
    def get_top_allocations(self, limit: int = 10):
        """Get top memory allocations."""
        if not tracemalloc.is_tracing():
            return []
            
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics('lineno')
        
        print(f"[Memory Monitor] Top {limit} memory allocations:")
        for stat in top_stats[:limit]:
            print(f"  {stat}")

# Global instance
memory_monitor = MemoryMonitor()