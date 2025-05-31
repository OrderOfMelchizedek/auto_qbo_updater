# Frontend JavaScript Test Suite

This directory contains a comprehensive test suite for the FOM to QBO automation frontend JavaScript application.

## Overview

The test suite covers all major aspects of the frontend application:

### Test Categories

1. **Utility Functions** (`utility-functions.test.js`)
   - CSRF token handling
   - Fetch wrapper with timeout support
   - Currency formatting
   - String manipulation (toProperCase)
   - Toast notifications

2. **V3 Data Formatting & Compatibility** (`v3-data-formatting.test.js`)
   - V3 enriched format handling
   - Data structure compatibility
   - Field mapping validation
   - Legacy format prevention
   - Merge history display

3. **QBO Integration** (`qbo-integration.test.js`)
   - Customer management (fetch, create, update, match)
   - Item and account creation
   - Payment method handling
   - Sales receipt processing
   - Batch operations
   - QBO setup modals

4. **File Upload & Processing** (`file-upload-processing.test.js`)
   - File upload workflow
   - Async processing with progress tracking
   - Task status monitoring
   - Response processing
   - Progress display management
   - Auth validation

5. **UI Components** (`ui-components.test.js`)
   - Modal management (customer, manual match, batch)
   - Progress displays
   - Action button handling
   - Form interactions
   - Customer table population

6. **Error Handling & Edge Cases** (`error-handling.test.js`)
   - Network error scenarios
   - Data validation edge cases
   - DOM manipulation failures
   - File upload edge cases
   - Security considerations
   - Browser compatibility

7. **End-to-End Integration** (`e2e-integration.test.js`)
   - Complete workflow testing
   - Batch processing
   - Customer matching flows
   - Error recovery
   - Data persistence
   - Performance testing

## Test Infrastructure

### Setup (`setup.js`)
- Global mocks for DOM, Bootstrap, fetch
- AbortController polyfill
- Mock cleanup utilities
- Common test utilities

### Configuration (`jest.config.js`)
- jsdom environment for DOM testing
- Coverage collection settings
- Module mapping for static assets
- Global variable configuration

## Running Tests

### Prerequisites
```bash
cd tests/frontend
npm install
```

### Test Commands

```bash
# Run all tests
npm test

# Run tests in watch mode (for development)
npm run test:watch

# Run tests with coverage report
npm run test:coverage

# Run tests with verbose output
npm run test:verbose

# Debug tests
npm run test:debug
```

### Coverage Targets

The test suite maintains high coverage standards:
- **Branches**: 80%
- **Functions**: 80%
- **Lines**: 80%
- **Statements**: 80%

## Key Testing Patterns

### V3 Format Validation
```javascript
test('should handle V3 enriched format', () => {
  const v3Donation = {
    internal_id: 'test-123',
    payer_info: { customer_lookup: 'John Smith' },
    payment_info: { amount: 100.00 },
    match_status: 'New'
  };

  const result = formatDonationData(v3Donation);
  expect(result.customerLookup).toBe('John Smith');
});
```

### Fetch Mocking
```javascript
beforeEach(() => {
  global.fetch.mockClear();
  global.fetch.mockResolvedValue({
    ok: true,
    json: () => Promise.resolve({ success: true })
  });
});
```

### DOM Element Mocking
```javascript
const mockElement = {
  innerHTML: '',
  textContent: '',
  value: '',
  classList: { add: jest.fn(), remove: jest.fn() },
  addEventListener: jest.fn()
};
document.getElementById.mockReturnValue(mockElement);
```

## Test Data Generators

The test suite includes utilities for generating consistent test data:

```javascript
function generateV3Donation(id, overrides = {}) {
  return {
    internal_id: id,
    payer_info: { customer_lookup: 'Test Customer', ...overrides.payer_info },
    payment_info: { amount: 100.00, ...overrides.payment_info },
    match_status: 'New',
    ...overrides
  };
}
```

## Debugging Tests

### Common Issues

1. **DOM Element Not Found**
   - Ensure `document.getElementById` is properly mocked
   - Check element ID matches what the code expects

2. **Fetch Calls Not Mocked**
   - Verify `global.fetch.mockResolvedValue()` is called
   - Check fetch call parameters match expectations

3. **Bootstrap Modal Errors**
   - Ensure `global.bootstrap.Modal` is mocked in setup

### Debug Tools

```bash
# Run specific test file
npm test -- utility-functions.test.js

# Run specific test case
npm test -- --testNamePattern="should format currency"

# Run with verbose output
npm test -- --verbose

# Generate coverage report
npm run test:coverage
```

## Contributing

When adding new frontend functionality:

1. Add corresponding tests to the appropriate test file
2. Maintain high test coverage (>80%)
3. Test both success and error scenarios
4. Include edge cases and validation
5. Follow existing naming and structure patterns

## Architecture Notes

### V3 Format Compliance
All tests validate V3 enriched format compliance:
- `payer_info` object structure
- `payment_info` object structure
- `match_status` field
- `internal_id` for tracking

### Error Handling
Tests verify graceful error handling:
- Network failures
- Invalid data structures
- Missing DOM elements
- Browser compatibility issues

### Performance
Tests include performance validation:
- Large dataset handling
- Concurrent operation support
- Memory leak prevention
- Efficient DOM manipulation

## Integration with Backend Tests

This frontend test suite complements the backend Python test suite:
- Frontend tests focus on UI logic and data presentation
- Backend tests handle API endpoints and data processing
- Both validate V3 format compliance
- Shared test data patterns ensure consistency
