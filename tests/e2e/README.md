# End-to-End Test Suite

This directory contains comprehensive end-to-end tests for the FOM to QBO automation pipeline.

## Overview

The E2E test script (`test_full_pipeline.py`) provides a complete test of the donation processing pipeline with mocked external dependencies.

## Features

1. **File Discovery**: Automatically finds dummy files in the `dummy files` directory
2. **Mock External Dependencies**: Mocks Redis, Celery, S3, and QBO API
3. **Full Pipeline Processing**: Tests both individual and batch file processing
4. **Customer Matching**: Simulates QBO customer search and matching
5. **Address Verification**: Tests address comparison and mismatch detection
6. **Comprehensive Logging**: Captures all logs to timestamped files
7. **Result Export**: Exports final results to JSON for analysis

## Running the Tests

```bash
cd /path/to/project
python tests/e2e/test_full_pipeline.py
```

## Output

The test generates:
- **Log File**: `logs/e2e_test_YYYYMMDD_HHMMSS.log`
- **Results File**: `tests/e2e/output/e2e_results_YYYYMMDD_HHMMSS.json`

## Test Scenarios

### 1. Successful Customer Match
- Donor: John Smith
- Status: Matched
- Match Method: Multiple strategies (name, email)
- Confidence: High

### 2. New Customer
- Donor: Jane Doe
- Status: New
- Reason: No matching customer found in QBO

### 3. Address Mismatch (when enabled)
- Donor: Acme Corporation
- Status: Matched-AddressNeedsReview
- Reason: Different city between extracted and QBO data

## Mock Data

### Mock QBO Customers
1. **John Smith** - Individual donor with email
2. **Acme Corp** - Corporate donor
3. **Bob Wilson** - Individual donor with email

### Mock Extractions
- **PDF**: Returns Acme Corporation and Bob Wilson
- **Image**: Returns John Smith and Jane Doe (or Acme for address mismatch test)

## Directory Structure

```
tests/e2e/
├── README.md                 # This file
├── test_full_pipeline.py     # Main E2E test script
├── dummy files/              # Test input files
│   ├── 2025-05-17-12-48-17.pdf
│   └── 2025-05-17 12.50.27-1.jpg
└── output/                   # Test results (created on run)
```

## Extending the Tests

To add new test scenarios:

1. Add new mock customers to `MockQBOService.mock_customers`
2. Modify `MockGeminiService.extract_donation_data()` to return different data
3. Update `MockGeminiService.verify_customer_match()` for new verification logic

## Notes

- The test uses mocked services to avoid external dependencies
- Memory monitoring is included to track resource usage
- Batch processing errors are expected due to simplified mocks
- Focus is on testing the integration flow rather than exact implementation
