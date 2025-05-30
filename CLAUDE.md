# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build/Lint/Test Commands
- Install dependencies: `pip install -r requirements.txt`
- Run all tests: `pytest`
- Run single test: `pytest tests/test_file.py::TestClass::test_method`
- Test with coverage: `pytest --cov=intuitlib`

## Code Style Guidelines
- Follow PEP 8 conventions
- Use docstrings for all functions, classes, and modules
- Import order: standard library, third-party packages, local modules
- Error handling: Use explicit exceptions with descriptive messages
- Naming: Use snake_case for variables/functions, CamelCase for classes
- Type hints encouraged but not required
- Include unit tests for all new functionality
- Keep line length to 100 characters or less

## Logging Guidelines
- All log files MUST be created in the `logs/` directory
- Use the logging configuration from `src/config/logging_config.py`
- Never create log files in the root directory or other locations
- Log file naming convention: `{component}_{date}.log` or `{component}.log` with rotation
- Use appropriate log levels:
  - DEBUG: Detailed information for diagnosing problems
  - INFO: General informational messages
  - WARNING: Warning messages for potentially harmful situations
  - ERROR: Error events that might still allow the application to continue
  - CRITICAL: Critical problems that have caused the application to fail

## Project Structure
This project implements an OAuth2 client for QuickBooks Online API integration, with a focus on processing FOM donation data and creating QBO Sales Receipts.

### File Organization Guidelines
**IMPORTANT:** Always place new files in their appropriate directories:

#### Source Code (`src/`)
- **Models** → `src/models/` - Pydantic models, data structures
- **Routes** → `src/routes/` - Flask route handlers
- **Services** → `src/services/` - Business logic services
- **Utils** → `src/utils/` - Utility functions and helpers
- **Config** → `src/config/` - Configuration files
- **Templates** → `src/templates/` - HTML templates
- **Static** → `src/static/` - CSS, JS, images

#### Tests (`tests/`)
- **Unit Tests** → `tests/unit/` - Test individual functions/classes
- **Integration Tests** → `tests/integration/` - Test component interactions
- **E2E Tests** → `tests/e2e/` - End-to-end workflow tests

#### Scripts (`scripts/`)
- All shell scripts (.sh files) → `scripts/`
- Python utility scripts → `scripts/utils/`
- Monitoring scripts → `scripts/monitoring/`

#### Prompts (`lib/`)
- **Current Prompts** → `lib/current_prompts/` - Prompts used by refactored code
- **Legacy Prompts** → `lib/legacy_prompts/` - Prompts used by legacy code
- **Archive Prompts** → `lib/prompts_archive/` - Historical/unused prompts

#### Logs (`logs/`)
- **All log files** → `logs/` - Application logs, error logs, debug logs
- Log files should follow naming convention: `{component}_{date}.log`
- Example: `celery_2025-05-30.log`, `app_error_2025-05-30.log`

#### Documentation (`docs/`)
- **API Documentation** → `docs/api_docs/`
- **Project Specs** → `docs/project_specs/`
- **Reports** → `docs/reports/` - ALL summaries, reports, and analysis documents
  - Implementation summaries
  - Test reports
  - Performance analysis
  - Refactoring summaries
  - Any document ending in _SUMMARY.md or _REPORT.md

#### Root Directory
The root directory should only contain:
- Configuration files (`.env`, `requirements.txt`, `pyproject.toml`, etc.)
- Docker files (`Dockerfile`, `docker-compose.yml`)
- Deployment files (`Procfile`, `Makefile`)
- Key documentation (`README.md`, `TASKS.md`, `CLAUDE.md`)
- **NO loose test files or scripts in root!**

## Task Management
The TASKS.md file serves two main purposes:
- **Planning & Progress:** Document all actions you intend to take and monitor their advancement.
- **Comprehensive Logging:** Maintain a record of every task you attempt, regardless of whether it was successful or not.

Keep your TASKS.md file up-to-date with clear indicators of task status. Each task entry requires a checkbox ☐.
- **Successfully Completed Tasks:** Mark with a white checkmark ✅.
- **Failed Tasks:** Mark with a red 'x' ❌.

Maintain human readability by judicious use of headings and subheadings.

## Heroku Deployment
- The app name is `auto-qbo-updater`
