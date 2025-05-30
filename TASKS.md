# May 30, 2025

## Phase 1: Payment Extraction Refactor - Generalization and Structured Outputs

### Overview
Transform the donation-specific extraction system into a general-purpose payment extraction system using Gemini's structured outputs. This maintains backward compatibility while making the app usable by any business processing payments.

### Goals
1. Replace donor/donation terminology with payer/payment
2. Implement Gemini structured outputs with Pydantic models
3. Extract new fields per the chat log specification
4. Maintain all existing infrastructure (Redis, S3, API keys)
5. Set foundation for future document type expansion

### Implementation Steps

#### 1.1 Create Pydantic Models for Structured Output
- [:white_check_mark:] Create `src/models/__init__.py`
- [:white_check_mark:] Create `src/models/payment.py` with:
  ```python
  class PaymentMethod(str, Enum):
      HANDWRITTEN_CHECK = "handwritten_check"
      PRINTED_CHECK = "printed_check"
      ONLINE_PAYMENT = "online_payment"

  class PaymentInfo(BaseModel):
      payment_method: PaymentMethod  # REQUIRED
      check_no: Optional[str]  # REQUIRED for checks
      payment_ref: Optional[str]  # REQUIRED for online
      amount: float  # REQUIRED
      payment_date: str  # REQUIRED
      check_date: Optional[str]
      postmark_date: Optional[str]
      deposit_date: Optional[str]
      deposit_method: Optional[str]
      memo: Optional[str]

  class PayerInfo(BaseModel):
      aliases: Optional[List[str]]  # REQUIRED for individuals
      salutation: Optional[str]
      organization_name: Optional[str]  # REQUIRED for orgs

  class ContactInfo(BaseModel):
      address_line_1: Optional[str]
      city: Optional[str]
      state: Optional[str]
      zip: Optional[str]
      email: Optional[str]
      phone: Optional[str]

  class PaymentRecord(BaseModel):
      payment_info: PaymentInfo
      payer_info: PayerInfo
      contact_info: ContactInfo
      source_document_type: Optional[str]  # Track document type
  ```

#### 1.2 Update Gemini Service for Structured Output
- [:white_check_mark:] Create `gemini_structured.py` with structured output support:
  - [:white_check_mark:] Updated to Gemini 2.0 Flash model
  - [:white_check_mark:] Implemented structured response handling
  - [:white_check_mark:] Added `response_mime_type: "application/json"`
  - [:white_check_mark:] Added `response_schema` with Pydantic models
- [:white_check_mark:] Create `gemini_adapter.py` for backward compatibility:
  - [:white_check_mark:] Maintains existing method signatures
  - [:white_check_mark:] Feature flag for structured vs legacy extraction

#### 1.3 Create New Extraction Prompts
- [:white_check_mark:] Create `docs/prompts_structured/` directory
- [:white_check_mark:] Create structured prompts following new schema:
  - [:white_check_mark:] `payment_extraction_prompt.md` (general)
  - [:white_check_mark:] `check_extraction_prompt.md` (specific rules for checks)
  - [:white_check_mark:] `envelope_extraction_prompt.md` (address priority)
  - [:white_check_mark:] `csv_extraction_prompt.md` (online payments)
- [:white_check_mark:] Updated PromptManager in gemini_structured.py to load new prompts

#### 1.4 Update Field Mappings
- [:white_check_mark:] Created mapping in PaymentRecord model with conversion methods:
  - [:white_check_mark:] `PaymentRecord.from_legacy_format()` method
  - [:white_check_mark:] `PaymentRecord.to_legacy_format()` method
  - [:white_check_mark:] Handles all field conversions automatically
- [:white_check_mark:] Built adapter (`GeminiAdapter`) to convert between formats seamlessly

#### 1.5 Update Deduplication Logic
- [:white_check_mark:] Modified deduplication.py to handle payment_ref for online payments:
  - [:white_check_mark:] Added payment_ref handling in `_generate_unique_key()`
  - [:white_check_mark:] Online payments use `ONLINE_{payment_ref}_{amount}` key
  - [:white_check_mark:] Check payments use `CHECK_{check_no}_{amount}` key
- [:white_check_mark:] Kept core deduplication logic unchanged

#### 1.6 Terminology Updates Throughout Codebase
- [ ] Global find/replace (careful with QBO-specific terms):
  - [ ] "donation" → "payment" (except in QBO sales receipt context)
  - [ ] "donor" → "payer"
  - [ ] "Gift Amount" → "amount"
- [ ] Update log messages and error messages
- [ ] Update variable names in core logic

#### 1.7 Create Backward Compatibility Layer
- [:white_check_mark:] Created GeminiAdapter class with full compatibility:
  - [:white_check_mark:] Adapter functions convert between formats automatically
  - [:white_check_mark:] Existing API endpoints continue to work unchanged
  - [:white_check_mark:] Legacy field names preserved in responses

#### 1.8 Testing the Extraction Refactor
- [:white_check_mark:] Created test_structured_extraction.py test script
- [:white_check_mark:] Verified Pydantic models work correctly
- [:white_check_mark:] Tested conversion between legacy and new formats
- [ ] Test structured output with actual image files
- [ ] Verify backward compatibility with full workflow
- [ ] Ensure deduplication works with payment_ref field

---

## Phase 2: Customer Matching Refactor - Single Pass After Deduplication

### Overview
After extraction is updated, refactor the customer matching to only execute once after deduplication. This depends on Phase 1 being complete.

### Prerequisites
- Phase 1 (Payment Extraction Refactor) must be complete
- All payments use new PaymentRecord structure

### Implementation Plan

#### 2.1 Remove Matching from Individual File Processing
- [:white_check_mark:] In `batch_processor.py`:
  - [:white_check_mark:] No customer matching found - already clean
  - [:white_check_mark:] Returns only extracted payment data

- [:white_check_mark:] In `file_processor.py`:
  - [:white_check_mark:] Remove matching from `_process_with_validation()` (lines 186-189)
  - [:white_check_mark:] Remove matching from `_process_csv()` (lines 300-302)
  - [:white_check_mark:] Ensure only extraction and validation occur

#### 2.2 Centralize Matching After Deduplication
- [:white_check_mark:] In `file_processor.py` - `process_files_concurrently()`:
  - [:white_check_mark:] Extract all payments without matching
  - [:white_check_mark:] Deduplicate all payments
  - [:white_check_mark:] Single matching pass on deduplicated set
  - [:white_check_mark:] Added logging for match results
  - [ ] Update to use "payer" terminology (Phase 3)

#### 2.3 Update Customer Service for Payers
- [ ] Update `qbo_service/customers.py`:
  - [ ] Update matching to look for payer aliases
  - [ ] Handle organization names properly
  - [ ] Keep core matching strategies

#### 2.4 Clean Up Redundant Code
- [:white_check_mark:] Remove duplicate "skip if already matched" logic
- [:white_check_mark:] Remove match preservation logic from deduplication:
  - [:white_check_mark:] Removed `_merge_customer_fields()` calls
  - [:white_check_mark:] Removed customer status logging during merge
  - [:white_check_mark:] Deprecated `_merge_customer_fields()` method
- [:white_check_mark:] Simplified the overall flow

#### 2.5 Testing the Matching Refactor
- [ ] Test full pipeline with new single-pass matching
- [ ] Verify performance improvements
- [ ] Ensure no regressions in match quality

---

## Phase 3: Frontend and API Updates

### Overview
Update user-facing components to reflect the generalized payment system.

### Implementation Steps

#### 3.1 API Endpoint Updates
- [ ] Create v2 endpoints with payment terminology:
  - [ ] `/api/v2/payments/extract`
  - [ ] `/api/v2/payers/search`
- [ ] Maintain v1 endpoints with adapters for compatibility

#### 3.2 Frontend Terminology
- [ ] Update UI labels:
  - [ ] "Donations" → "Payments"
  - [ ] "Donor" → "Payer"
  - [ ] "Gift Amount" → "Amount"
- [ ] Update column headers in tables
- [ ] Update button labels and messages

#### 3.3 Configuration Options
- [ ] Add config for business type (nonprofit, retail, service)
- [ ] Make field labels configurable
- [ ] Allow customization of payment methods shown

---

## Implementation Timeline

### Week 1: Extraction Refactor (Phase 1)
- Days 1-2: Create Pydantic models and update Gemini service
- Days 3-4: Update prompts and implement structured extraction
- Day 5: Test and verify backward compatibility

### Week 2: Matching Refactor (Phase 2)
- Days 1-2: Remove matching from individual processing
- Day 3: Implement single-pass matching
- Days 4-5: Testing and optimization

### Week 3: Frontend Updates (Phase 3)
- Days 1-2: API updates with compatibility layer
- Days 3-4: Frontend terminology updates
- Day 5: End-to-end testing

### Week 4: Deployment
- Staged rollout with feature flags
- Monitor for issues
- Document changes

---

## Customer Matching Refactor - Single Pass After Deduplication

*[Previous implementation plan content remains below but will be executed as Phase 2]*

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
