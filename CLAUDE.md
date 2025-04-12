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

## Project Structure
This project implements an OAuth2 client for QuickBooks Online API integration, with a focus on processing FOM donation data and creating QBO Sales Receipts.