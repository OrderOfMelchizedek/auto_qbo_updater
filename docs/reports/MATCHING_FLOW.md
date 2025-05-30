# Customer Matching Flow (After Phase 2 Refactor)

## Overview
Customer matching now happens in a single pass after deduplication, providing consistent and efficient matching across all donations.

## Current Flow

### 1. File Processing (No Matching)
```python
# In file_processor.py - _process_with_validation()
- Extract donation data from images/PDFs
- Validate required fields
- Reprocess if critical fields missing
- Return raw donation data (NO customer matching)

# In file_processor.py - _process_csv()
- Extract donation data from CSV
- Parse and structure data
- Return raw donation data (NO customer matching)
```

### 2. Batch Processing (No Matching)
```python
# In batch_processor.py
- Process multiple files concurrently
- Extract data in batches
- Return all extracted donations
- NO customer matching at this stage
```

### 3. Deduplication (No Customer Field Handling)
```python
# In deduplication.py - deduplicate_donations()
- Generate unique keys (check_no + amount or payment_ref + amount)
- Merge duplicate records
- Preserve non-customer fields only
- NO customer field merging or preservation
```

### 4. Single-Pass Customer Matching
```python
# In file_processor.py - process_files_concurrently()
# This is the ONLY place where customer matching happens

1. Extract all donations from all files
2. Validate donations
3. Deduplicate donations
4. IF QBO service is available:
   - Match ALL deduplicated donations in one pass
   - Use batch API calls for efficiency
   - Log results
```

## Matching Process Details

### Batch Matching Method
```python
# In file_processor.py - match_donations_with_qbo_customers_batch()

1. Pre-load QBO customer cache
2. Collect all unique lookup values from donations
3. Batch lookup all customers at once
4. For each donation:
   - Try multiple lookup strategies:
     * customerLookup field (if exists)
     * Donor Name
     * Email
     * Phone
   - Verify match with Gemini AI
   - Set match status:
     * "Matched" - Valid match confirmed
     * "Matched-AddressMismatch" - Match but address differs
     * "Matched-AddressNeedsReview" - Match needs review
     * "New" - No match found
```

## Benefits of Single-Pass Matching

1. **Performance**: One batch API call instead of N individual calls
2. **Consistency**: All donations matched against same customer data
3. **Simplicity**: No complex state management or preservation logic
4. **Accuracy**: No risk of stale matches from earlier processing

## Key Differences from Previous Implementation

### Before:
- Matching happened during individual file processing
- Matching happened again after deduplication (for unmatched only)
- Complex logic to preserve match status through pipeline
- Multiple API calls to QBO

### After:
- NO matching during file processing
- NO matching during CSV processing
- NO customer field handling in deduplication
- ONE matching pass after all processing complete

## Code Locations

- **Single matching call**: `src/utils/file_processor.py` line 714
- **Batch matching logic**: `src/utils/file_processor.py` lines 312-499
- **QBO API calls**: `src/utils/qbo_service/customers.py`
- **AI verification**: `src/utils/gemini_service.py` - `verify_customer_match()`

## Testing

See `test_phase2_refactor.py` for comprehensive tests verifying:
- No matching during extraction
- Matching happens after deduplication
- Proper flow execution
