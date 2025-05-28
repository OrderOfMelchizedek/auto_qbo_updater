# Memory Optimizations for FOM to QBO Automation

This document outlines the memory optimizations implemented to fix the 503 Service Unavailable errors caused by memory exhaustion on Heroku.

## Problem Summary
- The application was exceeding Heroku's 512MB memory limit for Basic dynos
- Memory usage accumulated over time, especially when processing PDFs
- R14 memory errors were causing service unavailability

## Implemented Solutions

### 1. Memory Monitoring System
- Created `memory_monitor.py` utility to track and log memory usage
- Added memory thresholds (400MB warning, 450MB critical)
- Automatic garbage collection when thresholds are exceeded
- Memory usage logging at key points in the application

### 2. File Processing Optimizations
- Added `@memory_monitor.monitor_function` decorator to PDF processing
- Explicit garbage collection after processing each file
- Proper cleanup of PDF documents and image objects
- Memory logging before/after major operations

### 3. Batch Processing Improvements
- Enhanced cleanup in `_prepare_pdf_batches` with proper resource disposal
- Added memory monitoring to `_process_pdf_batch`
- Immediate cleanup of pixmaps and image data
- Forced garbage collection after each batch

### 4. Worker Configuration
- Reduced Gunicorn workers from 2 to 1
- Lowered max requests from 500 to 200 for more frequent worker recycling
- Added `--preload` flag to share memory between master and worker
- Reduced Celery concurrency from 2 to 1
- Added `--max-memory-per-child=200000` to auto-restart workers at 200MB

### 5. Application-Level Cleanup
- Enhanced `cleanup_uploaded_file` to trigger garbage collection
- Added memory monitoring to the main upload endpoint
- Cleanup in finally blocks to ensure execution
- Memory logging in health check endpoint

### 6. Celery Task Optimizations
- Added memory monitoring to async tasks
- Garbage collection after processing each file in tasks
- Memory cleanup in finally blocks
- Progress tracking includes memory status

## Testing
Run the memory test script to verify improvements:
```bash
python test_memory.py
```

## Monitoring in Production
1. Check memory usage via health endpoint:
   ```bash
   curl https://your-app.herokuapp.com/health | jq .system.memory_monitor
   ```

2. Monitor Heroku logs for memory warnings:
   ```bash
   heroku logs --tail --app your-app | grep "Memory Monitor"
   ```

3. View Heroku metrics:
   ```bash
   heroku ps --app your-app
   ```

## Future Improvements
1. **Streaming PDF Processing**: Implement page-by-page streaming instead of loading entire PDFs
2. **Worker Pool Management**: Implement dynamic worker scaling based on memory usage
3. **Redis-Based Task Queue**: Move heavy processing entirely to background workers
4. **Memory Profiling**: Add detailed memory profiling in development mode
5. **Upgrade Dyno Type**: Consider Standard-1X dynos for guaranteed 512MB without throttling

## Configuration Changes

### Procfile
```
web: gunicorn src.app:app --timeout 300 --workers 1 --worker-class sync --max-requests 200 --max-requests-jitter 50 --graceful-timeout 30 --preload
worker: celery -A src.utils.celery_app:celery_app worker --loglevel=info --concurrency=1 -Q file_processing,celery --max-memory-per-child=200000
```

### Environment Variables
No new environment variables required. Memory thresholds are configured in `memory_monitor.py`.

## Deployment
1. Commit all changes
2. Deploy to Heroku: `git push heroku master`
3. Monitor logs during first file processing
4. Verify memory stays below 450MB threshold

## Emergency Actions
If memory issues persist:
1. Immediate: `heroku restart --app your-app`
2. Short-term: Scale down to 0 then back up
3. Long-term: Upgrade to larger dyno type