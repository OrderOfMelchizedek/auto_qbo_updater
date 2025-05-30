# May 30, 2025

## Customer Matching Refactor - Single Pass After Deduplication

### Overview
Refactor the customer matching process to only execute once after deduplication, instead of matching multiple times throughout the file processing pipeline. This will simplify the codebase and eliminate issues with match status preservation.

### Benefits
- Eliminates match status preservation bugs
- Reduces QBO API calls (better performance)
- Simplifies codebase by removing complex preservation logic
- Ensures consistent matching against the final deduplicated dataset

### Implementation Plan

#### Phase 1: Remove Matching from Individual File Processing
- [ ] In `batch_processor.py`:
  - [ ] Remove `match_donations_with_qbo_customers_batch()` call from `process_file_batch()`
  - [ ] Ensure `process_file_batch()` only returns extracted donation data

- [ ] In `file_processor.py`:
  - [ ] Remove matching logic from `extract_donation_data()` method
  - [ ] Remove matching logic from `_process_csv()` method
  - [ ] Ensure these methods only handle extraction and validation

#### Phase 2: Centralize Matching in Main Processing Flow
- [ ] In `file_processor.py` - `process_files_concurrently()`:
  - [ ] Keep extraction and deduplication as-is
  - [ ] Ensure matching only happens AFTER deduplication
  - [ ] Remove the "already_matched" counting logic
  - [ ] Remove the conditional matching based on unmatched_count

#### Phase 3: Clean Up Redundant Code
- [ ] Remove `match_donations_with_qbo_customers()` (non-batch version) if no longer needed
- [ ] Remove all "Skip if already matched" checks from:
  - [ ] `match_donations_with_qbo_customers_batch()`
  - [ ] Any other matching-related methods
- [ ] Remove match preservation logic from `deduplication.py`:
  - [ ] Simplify `_merge_customer_fields()` to just merge data, not preserve status

#### Phase 4: Update Progress Logging
- [ ] Adjust progress messages to reflect single-pass matching
- [ ] Update log messages to be clearer about when matching occurs
- [ ] Ensure user feedback accurately reflects the new flow

#### Phase 5: Testing & Validation
- [ ] Test with multiple file uploads containing duplicates
- [ ] Verify matching accuracy is maintained
- [ ] Confirm performance improvements
- [ ] Ensure no regressions in functionality
- [ ] Test edge cases:
  - [ ] Files with no valid donations
  - [ ] Files with all duplicates
  - [ ] Large batch processing

### Code Structure After Refactor

```python
def process_files_concurrently(self, files, task_id=None):
    # Step 1: Extract all donations (NO matching)
    all_donations = []
    for batch in batches:
        batch_donations = batch_processor.process_file_batch(batch)
        all_donations.extend(batch_donations)

    # Step 2: Validate donations
    validated_donations = self._validate_donations(all_donations)

    # Step 3: Deduplicate
    deduplicated = self._deduplicate_donations(validated_donations)

    # Step 4: Single matching pass
    if self.qbo_service and deduplicated:
        matched = self.match_donations_with_qbo_customers_batch(deduplicated)
        return matched

    return deduplicated
```

### Risks & Mitigation
- **Risk**: Higher memory usage holding all donations before matching
  - **Mitigation**: Current batch processing already handles this well

- **Risk**: Delayed user feedback about matches
  - **Mitigation**: Improve progress messages to set expectations

- **Risk**: Potential for timeout on very large batches
  - **Mitigation**: Implement chunked matching if needed

### Rollback Plan
- Git commit before changes for easy revert
- Feature flag to toggle between old/new behavior if needed
- Comprehensive testing before deployment
