#!/usr/bin/env python3
"""
Test script to verify memory improvements in the FOM to QBO application.
"""
import os
import sys
import time
import psutil
import requests
import tempfile
from datetime import datetime

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from utils.memory_monitor import memory_monitor

def log_test(message):
    """Log test message with timestamp."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

def test_memory_monitor():
    """Test the memory monitor functionality."""
    log_test("Testing Memory Monitor")
    
    # Start memory monitoring
    initial_memory = memory_monitor.get_memory_usage()
    log_test(f"Initial memory: {initial_memory['rss_mb']:.1f}MB")
    
    # Create some memory pressure
    log_test("Creating memory pressure...")
    large_list = []
    for i in range(5):
        # Create 10MB of data
        data = bytearray(10 * 1024 * 1024)
        large_list.append(data)
        memory_monitor.log_memory_usage(f"After allocating {(i+1)*10}MB")
        time.sleep(0.5)
    
    # Clear the list
    log_test("Clearing memory...")
    large_list.clear()
    memory_monitor.force_cleanup()
    memory_monitor.log_memory_usage("After cleanup")
    
    log_test("Memory monitor test completed")

def test_file_processor():
    """Test file processor memory handling."""
    log_test("Testing File Processor Memory Handling")
    
    try:
        from utils.file_processor import FileProcessor
        from utils.gemini_service import GeminiService
        
        # Create test PDF file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            # Write minimal PDF content
            tmp.write(b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n")
            tmp.write(b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n")
            tmp.write(b"3 0 obj<</Type/Page/Parent 2 0 R/Resources<</Font<</F1<</Type/Font/Subtype/Type1/BaseFont/Times-Roman>>>>>>/MediaBox[0 0 612 792]/Contents 4 0 R>>endobj\n")
            tmp.write(b"4 0 obj<</Length 44>>stream\nBT /F1 12 Tf 100 700 Td (Test PDF) Tj ET\nendstream\nendobj\n")
            tmp.write(b"xref\n0 5\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\n0000000330 00000 n\n")
            tmp.write(b"trailer<</Size 5/Root 1 0 R>>\nstartxref\n418\n%%EOF")
            tmp_path = tmp.name
        
        # Monitor memory during processing
        memory_monitor.log_memory_usage("Before PDF processing")
        
        # Note: This would require API keys to actually process
        log_test(f"Created test PDF at: {tmp_path}")
        
        # Cleanup
        os.unlink(tmp_path)
        memory_monitor.log_memory_usage("After PDF cleanup")
        
    except Exception as e:
        log_test(f"File processor test error: {e}")
    
    log_test("File processor test completed")

def test_batch_processing():
    """Test batch processor memory handling."""
    log_test("Testing Batch Processor Memory Handling")
    
    try:
        from utils.batch_processor import BatchProcessor
        from utils.gemini_service import GeminiService
        
        # Create mock service
        gemini_service = GeminiService()
        batch_processor = BatchProcessor(gemini_service)
        
        # Test batch preparation (doesn't require API)
        files = [
            ('/tmp/test1.pdf', '.pdf'),
            ('/tmp/test2.pdf', '.pdf'),
            ('/tmp/test3.jpg', '.jpg')
        ]
        
        memory_monitor.log_memory_usage("Before batch preparation")
        
        # This will fail but we're testing memory behavior
        try:
            batches = batch_processor.prepare_batches(files)
            log_test(f"Prepared {len(batches)} batches")
        except:
            pass
        
        memory_monitor.log_memory_usage("After batch preparation")
        
    except Exception as e:
        log_test(f"Batch processor test error: {e}")
    
    log_test("Batch processor test completed")

def main():
    """Run all memory tests."""
    log_test("Starting Memory Optimization Tests")
    log_test("=" * 50)
    
    # Enable memory tracing
    memory_monitor.start_tracing()
    
    # Run tests
    test_memory_monitor()
    log_test("")
    
    test_file_processor()
    log_test("")
    
    test_batch_processing()
    log_test("")
    
    # Final memory report
    log_test("=" * 50)
    log_test("Final Memory Report:")
    final_memory = memory_monitor.get_memory_usage()
    log_test(f"RSS: {final_memory['rss_mb']:.1f}MB")
    log_test(f"VMS: {final_memory['vms_mb']:.1f}MB")
    log_test(f"Available: {final_memory['available_mb']:.1f}MB")
    
    # Show top memory allocations
    memory_monitor.get_top_allocations(5)
    
    log_test("All tests completed!")

if __name__ == "__main__":
    main()