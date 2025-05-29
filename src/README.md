# Source Code Directory Structure

This directory contains the main application source code for the FOM to QBO Automation project.

## Directory Structure

```
src/
├── app.py              # Main Flask application and routes
├── run.py              # Application entry point
├── config/             # Configuration modules
│   ├── celery.py      # Celery configuration
│   ├── flask.py       # Flask configuration (future)
│   └── logging.py     # Logging configuration (future)
├── routes/             # Flask route blueprints (future modularization)
├── services/           # Business logic services (future modularization)
├── utils/              # Utility modules
│   ├── batch_processor.py      # Batch file processing
│   ├── celery_app.py          # Celery app initialization
│   ├── cleanup_tasks.py       # Cleanup and maintenance tasks
│   ├── csv_parser.py          # CSV file parsing
│   ├── exceptions.py          # Custom exceptions
│   ├── file_processor.py      # Main file processing logic
│   ├── gemini_service.py      # Google Gemini AI integration
│   ├── memory_monitor.py      # Memory monitoring utilities
│   ├── progress_logger.py     # Progress tracking for async tasks
│   ├── prompt_manager.py      # AI prompt management
│   ├── qbo_service.py         # QuickBooks Online integration
│   ├── redis_monitor.py       # Redis monitoring utilities
│   ├── result_store.py        # Result storage management
│   ├── retry.py               # Retry logic utilities
│   ├── s3_storage.py          # AWS S3 integration
│   ├── tasks.py               # Celery task definitions
│   └── temp_file_manager.py   # Temporary file management
├── static/             # Frontend static assets
│   ├── css/           # Stylesheets
│   └── js/            # JavaScript files
└── templates/          # HTML templates
    └── index.html     # Main application interface
```

## Key Components

### app.py
The main Flask application containing all route definitions. This file is scheduled for modularization to improve maintainability.

### utils/
Contains all utility modules for various functionalities:
- **file_processor.py**: Core file processing logic for images, PDFs, and CSVs
- **gemini_service.py**: Integration with Google's Gemini AI for data extraction
- **qbo_service.py**: QuickBooks Online API integration for customer and sales receipt management
- **tasks.py**: Asynchronous task definitions for Celery

### static/ and templates/
Frontend assets including the main single-page application interface.

## Import Conventions

When importing from within the `src` directory:
```python
# From within src/ files
from utils.qbo_service import QBOService
from utils.file_processor import FileProcessor

# From outside src/ (e.g., tests)
from src.utils.qbo_service import QBOService
```

## Configuration

Configuration is managed through environment variables and the `config/` directory:
- Environment variables are loaded from `.env` file
- Celery configuration is in `config/celery.py`
- Flask configuration will be modularized to `config/flask.py`

## Running the Application

From the project root:
```bash
# Development
python src/run.py

# Production
gunicorn src.app:app

# Celery worker
celery -A src.utils.celery_app worker
```