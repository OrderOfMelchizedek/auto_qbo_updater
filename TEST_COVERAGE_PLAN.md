# Test Coverage Analysis & Plan

## Current Status (29% Coverage)

### ✅ Working Tests (16 tests passing)
- `test_prompt_manager.py` - 100% coverage on PromptManager
- `test_csv_parser.py` - 81% coverage on CSVParser  
- `test_gemini_service.py` - 64% coverage on GeminiService

### ❌ Broken Tests (60 tests failing)
Most failures due to:
1. Wrong import paths (importing from `app` instead of `src.app`)
2. Wrong function signatures expectations
3. Wrong return type expectations
4. Missing mock setups

## Coverage Goals: Reach 70%

### Priority 1: Fix Existing Invalid Tests
1. **test_data_validation.py** - Fix import paths and expectations
2. **test_file_upload_security.py** - Fix function signature mismatches
3. **test_oauth_flow.py** - Fix QBO service mocking
4. **test_qbo_integration.py** - Fix service initialization

### Priority 2: Add High-Impact Tests

#### src/app.py (1405 lines, 29% coverage)
**Critical untested functions:**
- Flask route handlers (upload, donations, qbo endpoints)
- Helper functions (validate_*, normalize_*, security functions)
- Error handling and edge cases

**Target functions for 70% coverage:**
- `validate_donation_date()` - Date validation logic
- `normalize_*()` functions - Data normalization  
- `generate_secure_filename()` - Security function
- `validate_file_content()` - File validation
- Route handlers: `/upload`, `/donations`, `/qbo/*`

#### src/utils/qbo_service.py (1125 lines, 0% coverage)
**Critical functions:**
- OAuth flow (`get_tokens`, `refresh_access_token`)
- Customer operations (`find_customer`, `get_all_customers`) 
- CRUD operations (`create_customer`, `create_sales_receipt`)
- Caching functions (`_is_cache_valid`, `_update_customer_cache`)

#### src/utils/file_processor.py (420 lines, 0% coverage)
**Critical functions:**
- `process()` - Main file processing entry point
- `_process_image()`, `_process_pdf()`, `_process_csv()` - File type handlers
- `_process_with_validation()` - Validation wrapper

### Priority 3: Add Missing Test Coverage

#### High-Impact Areas:
1. **Error handling and exception paths**
2. **Security validation functions** 
3. **Data transformation and normalization**
4. **Flask route integration tests**
5. **Performance optimization features (caching, pagination)**

## Implementation Plan

### Phase 1: Fix Broken Tests (Target: 50% coverage)
1. Fix import issues in all test files
2. Correct function signature expectations  
3. Fix mock configurations
4. Update return type expectations

### Phase 2: Add Core Functionality Tests (Target: 65% coverage)
1. Add comprehensive app.py route tests
2. Add QBO service core functionality tests
3. Add file processor tests with proper mocks

### Phase 3: Add Edge Cases & Security Tests (Target: 70%+)
1. Error handling paths
2. Security validation edge cases  
3. Performance optimization features
4. Integration scenarios

## Files Requiring Attention

### Immediate Fixes Needed:
- `tests/test_data_validation.py` - Import and expectation fixes
- `tests/test_file_upload_security.py` - Function signature fixes
- `tests/test_oauth_flow.py` - Mock setup fixes
- `tests/test_qbo_integration.py` - Service initialization fixes

### New Tests Needed:
- `tests/test_app_routes.py` - Flask route testing
- `tests/test_app_helpers.py` - Helper function testing  
- `tests/test_qbo_service_comprehensive.py` - Full QBO service testing
- `tests/test_file_processor_comprehensive.py` - File processing testing
- `tests/test_security_comprehensive.py` - Security feature testing