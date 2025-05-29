# Modular Architecture - FOM to QBO Automation

## Overview

This document describes the modular architecture of the FOM to QBO automation application after the Phase 1 refactoring completed on May 28, 2025.

## Project Structure

```
src/
├── app.py                    # Main Flask application (541 lines, reduced from 3,625)
├── config/                   # Configuration modules
│   ├── __init__.py
│   ├── logging_config.py     # Logging configuration
│   └── session_config.py     # Session management configuration
├── routes/                   # Flask blueprints for organized routing
│   ├── __init__.py
│   ├── auth.py              # QBO OAuth authentication routes
│   ├── donations.py         # Donation CRUD operations
│   ├── files.py             # File upload and processing
│   ├── health.py            # Health checks and monitoring
│   └── qbo.py               # QuickBooks integration routes
├── services/                 # Business logic services
│   ├── __init__.py
│   ├── deduplication.py     # Donation deduplication logic
│   └── validation.py        # Data validation and normalization
└── utils/                    # Utility modules
    ├── batch_processor.py
    ├── celery_app.py
    ├── cleanup_tasks.py
    ├── csv_parser.py
    ├── exceptions.py
    ├── file_processor.py
    ├── gemini_service.py
    ├── memory_monitor.py
    ├── progress_logger.py
    ├── prompt_manager.py
    ├── qbo_service.py
    ├── redis_monitor.py
    ├── result_store.py
    ├── retry.py
    ├── s3_storage.py
    ├── tasks.py
    └── temp_file_manager.py
```

## Key Changes

### 1. Route Organization

Routes have been organized into logical blueprints:

- **`auth.py`** - Authentication endpoints:
  - `/qbo/auth-status` - Check authentication status
  - `/qbo/disconnect` - Disconnect from QuickBooks
  - `/qbo/authorize` - Initiate OAuth flow
  - `/qbo/callback` - OAuth callback handler

- **`health.py`** - Monitoring endpoints:
  - `/health` - System health check
  - `/ready` - Kubernetes-style readiness probe
  - `/session-info` - Debug session information
  - `/test-progress` - Test progress streaming

- **`files.py`** - File handling endpoints:
  - `/upload-start` - Initialize upload session
  - `/upload-async` - Async file upload via Celery
  - `/upload` - Synchronous file upload
  - `/task-status/<id>` - Check async task status

- **`donations.py`** - Donation management:
  - `/donations` - Get all donations
  - `/donations/<id>` - Update specific donation
  - `/donations/remove-invalid` - Remove invalid donations
  - `/donations/update-session` - Bulk update donations
  - `/progress-stream/<id>` - SSE progress updates

- **`qbo.py`** - QuickBooks operations:
  - `/qbo/customer/<id>` - Search for customer
  - `/qbo/customers/all` - Get all customers
  - `/qbo/customer/manual-match/<id>` - Manual customer matching
  - `/qbo/customer/create/<id>` - Create new customer
  - `/qbo/customer/update/<id>` - Update customer
  - `/qbo/sales-receipt/<id>` - Create sales receipt

### 2. Service Extraction

Business logic has been extracted into reusable services:

- **`validation.py`** - Data validation utilities:
  - `sanitize_for_logging()` - Remove sensitive data from logs
  - `validate_donation_date()` - Validate date ranges
  - `validate_environment()` - Check required env vars
  - `normalize_*()` - Data normalization functions
  - `log_audit_event()` - Audit logging

- **`deduplication.py`** - Donation deduplication:
  - `DeduplicationService.deduplicate_donations()` - Main deduplication logic
  - `DeduplicationService.merge_donation_data()` - Merge duplicate records
  - Preserves customer matching data during deduplication

### 3. Application Context

Services are made available to blueprints via Flask application context:

```python
# In app.py
app.qbo_service = qbo_service
app.file_processor = file_processor
app.memory_monitor = memory_monitor
app.process_single_file = process_single_file
app.cleanup_uploaded_file = cleanup_uploaded_file

# In blueprints
qbo_service = current_app.qbo_service
```

## Benefits Achieved

1. **Improved Maintainability**
   - 85% reduction in app.py size (3,625 → 541 lines)
   - Clear separation of concerns
   - Easier to locate and modify specific functionality

2. **Better Testing**
   - Comprehensive test coverage for all blueprints
   - Isolated unit tests for services
   - Mock-friendly architecture

3. **Enhanced Scalability**
   - Routes can be modified independently
   - Services can be reused across different routes
   - Clear boundaries for future expansion

4. **Improved Developer Experience**
   - Intuitive file organization
   - Reduced cognitive load
   - Faster onboarding for new developers

## Testing

Comprehensive test suites have been created for all components:

- `test_health_routes.py` - Health check endpoint tests
- `test_auth_routes.py` - Authentication flow tests
- `test_files_routes.py` - File upload and processing tests
- `test_donations_routes.py` - Donation management tests
- `test_qbo_routes.py` - QuickBooks integration tests
- `test_validation.py` - Validation service tests
- `test_deduplication.py` - Deduplication service tests

## Migration Notes

### For Developers

1. All route handlers are now in the `routes/` directory
2. Import blueprints from `routes` module
3. Access shared services via `current_app` context
4. Use service modules for business logic

### For Deployment

1. No changes to deployment configuration required
2. All environment variables remain the same
3. URL endpoints are unchanged
4. Backward compatibility maintained

## Next Steps

### Phase 2: QBO Service Modularization
- Break down `qbo_service.py` into focused modules
- Extract OAuth, customers, and sales receipt logic
- Create facade for backward compatibility

### Phase 3: Minor Extractions
- Extract rate limiting from `gemini_service.py`
- Modularize file processing by type
- Extract S3 operations into dedicated service

## Code Examples

### Using a Blueprint

```python
from flask import Blueprint, jsonify, request
from services.validation import log_audit_event

donations_bp = Blueprint('donations', __name__)

@donations_bp.route('/donations', methods=['GET'])
def get_donations():
    donations = session.get('donations', [])
    return jsonify({
        'success': True,
        'donations': donations,
        'count': len(donations)
    })
```

### Using a Service

```python
from services.deduplication import DeduplicationService

# In route handler
existing = session.get('donations', [])
new_donations = process_files(files)
unique_donations = DeduplicationService.deduplicate_donations(
    existing, new_donations
)
session['donations'] = unique_donations
```

## Conclusion

The Phase 1 modularization has successfully transformed a monolithic application into a well-organized, maintainable codebase while preserving all functionality and maintaining backward compatibility.