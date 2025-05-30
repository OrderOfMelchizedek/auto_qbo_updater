# Customer Matching Locations in FOM to QBO Automation

This document identifies all locations where customer matching occurs in the codebase, in the order they execute in the file processing pipeline.

## 1. Initial File Processing - `file_processor.py`

### Single File Processing (`_process_with_validation`)
- **Location**: Lines 186-189
- **Method**: `match_donations_with_qbo_customers_batch`
- **When**: After validation and reprocessing of missing fields
- **Purpose**: Matches all donations from a single file with QBO customers

### Concurrent/Batch File Processing (`process_files_concurrently`)
- **Location**: Lines 726-739
- **Method**: `match_donations_with_qbo_customers_batch`
- **When**: After deduplication of all donations from multiple files
- **Purpose**: Only matches unmatched donations (checks for existing match status)

## 2. Customer Matching Methods in `file_processor.py`

### Batch Matching Method (`match_donations_with_qbo_customers_batch`)
- **Location**: Lines 312-499
- **Process**:
  1. Pre-loads QBO customer cache (line 332)
  2. Collects unique lookup values from all donations (lines 339-363)
  3. Batch lookup using `qbo_service.find_customers_batch` (line 367)
  4. For each matched customer, calls `gemini_service.verify_customer_match` (line 412)
  5. Updates donation with match results

### Individual Matching Method (`match_donations_with_qbo_customers`)
- **Location**: Lines 501-668
- **Process**:
  1. Tries multiple lookup strategies in order:
     - customerLookup field
     - Donor Name
     - Email
     - Phone
  2. For each match found, calls `gemini_service.verify_customer_match` (line 568)
  3. Updates donation with match results

## 3. Background Task Processing - `tasks.py`

### Async File Processing (`process_files_task`)
- **Location**: Lines 296-320
- **Method**: `file_processor.match_donations_with_qbo_customers`
- **When**: After deduplication, only if QBO is authenticated
- **Purpose**: Matches unique donations with QBO customers in background jobs

## 4. QBO Customer Service - `qbo_service/customers.py`

### Find Customers Batch (`find_customers_batch`)
- **Location**: Lines 38-95
- **Purpose**: Batch processing for multiple customer lookups
- **Features**:
  - Uses cache to avoid redundant API calls
  - Parallel processing with ThreadPoolExecutor
  - Calls individual `find_customer` for each uncached lookup

### Find Customer (`find_customer`)
- **Location**: Lines 97-250
- **Strategies** (in order):
  1. Exact match on DisplayName
  2. Partial match (contains) on DisplayName
  3. Name reversal (handles "John Smith" vs "Smith, John")
  4. Significant parts matching (removes common tokens)
  5. Email domain matching (for organizations)
  6. Phone number matching

## 5. Customer Verification - `gemini_service.py`

### Verify Customer Match (`verify_customer_match`)
- **Location**: Lines 155-238
- **Purpose**: Uses AI to verify if a QBO customer matches the extracted donor
- **Returns**:
  - `validMatch`: boolean
  - `matchConfidence`: high/medium/low
  - `addressMateriallyDifferent`: boolean
  - `enhancedData`: merged donor information

## 6. Deduplication Service - `deduplication.py`

### Merge Customer Fields (`_merge_customer_fields`)
- **Location**: Lines 278-338
- **Purpose**: Intelligently merges customer match data when deduplicating
- **Priority**:
  1. Matched records over unmatched
  2. Higher confidence matches over lower
  3. Preserves existing match data when confidence is equal

## 7. Frontend Routes - `routes/files.py`

### Synchronous Upload (`upload_files`)
- **Location**: Lines 336-349
- **Method**: Direct `qbo_service.find_customer` calls
- **When**: After deduplication in synchronous upload flow
- **Note**: This is a simplified matching without AI verification

## Summary of Matching Flow

1. **File Processing**: Each file's donations are matched individually
2. **Batch Processing**: When processing multiple files concurrently, matching happens after deduplication
3. **Duplicate Handling**: The deduplication service preserves the best match when merging duplicates
4. **Background Tasks**: Async processing includes customer matching after deduplication
5. **Verification**: All matches (except frontend sync) go through AI verification to ensure accuracy

## Potential Issues

1. **Double Matching**: In concurrent processing, donations might be matched twice:
   - Once during individual file processing
   - Again after deduplication (though it checks for existing matches)

2. **Inconsistent Methods**:
   - Batch processing uses `match_donations_with_qbo_customers_batch`
   - Background tasks use `match_donations_with_qbo_customers`
   - Frontend sync uses direct `find_customer` without verification

3. **Cache Management**: Customer cache is loaded multiple times in batch processing, which could lead to stale data if customers are updated during processing.
