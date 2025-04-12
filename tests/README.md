# Testing Guide for FOM to QBO Automation

This guide provides an overview of the testing setup for the FOM to QBO Automation project.

## Overview

This project uses pytest for testing. The tests are organized in the `tests` directory, with each test file focusing on a specific component of the system.

## Running Tests

To run all tests:
```bash
python -m pytest
```

To run specific test files:
```bash
python -m pytest tests/test_prompt_manager.py
```

To run with verbose output:
```bash
python -m pytest -v
```

## Test Coverage

You can get a report of test coverage using the `--cov` option:
```bash
python -m pytest --cov=utils
```

For a more detailed report showing which lines are not covered:
```bash
python -m pytest --cov=utils --cov-report=term-missing
```

## Existing Tests

The project has tests for the following components:

1. **PromptManager** (`test_prompt_manager.py`) - Tests for loading, caching, and combining prompts.
2. **CSVParser** (`test_csv_parser.py`) - Tests for parsing CSV files with different delimiters and headers.
3. **GeminiService** (`test_gemini_service.py`) - Tests for extracting donation data from images and PDFs.
4. **FileProcessor** (`test_file_processor.py`) - Tests for processing different file types and validating donation data.

## Test Structure

Each test file follows a similar structure:

1. Import the necessary modules and the component to test
2. Define a test class that inherits from `unittest.TestCase`
3. Implement a `setUp` method to prepare the test environment
4. Implement a `tearDown` method to clean up after tests
5. Implement test methods for different aspects of the component

Example:
```python
import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import tempfile

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from utils.prompt_manager import PromptManager

class TestPromptManager(unittest.TestCase):
    def setUp(self):
        # Set up code here
        pass
        
    def tearDown(self):
        # Clean up code here
        pass
        
    def test_something(self):
        # Test code here
        pass
```

## Mocking

Many of the tests use mocking to avoid dependencies on external services. For example, the `test_gemini_service.py` file mocks the Google Gemini API to avoid making actual API calls during testing.

Example of mocking:
```python
@patch('utils.gemini_service.Image.open')
def test_extract_donation_data_success(self, mock_image_open):
    # Mock setup
    mock_image = MagicMock()
    mock_image_open.return_value = mock_image
    
    # Test code
    # ...
```

## Next Steps

Areas for improvement in testing:

1. Add tests for QBOService
2. Add tests for QBOOAuthService
3. Add integration tests for the Flask app (test_app.py exists but has issues with pandas)
4. Increase overall test coverage (currently at 54%)

## Best Practices

1. Keep tests independent - one test should not depend on another
2. Use descriptive test names that convey what is being tested
3. Mock external dependencies to ensure tests run quickly and consistently
4. Use appropriate assertions for the type of test
5. Include both success and failure cases in tests
6. Regularly check test coverage to identify areas needing more tests