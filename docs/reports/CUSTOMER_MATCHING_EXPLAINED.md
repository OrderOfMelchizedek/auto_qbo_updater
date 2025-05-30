# Customer Matching Process - Detailed Explanation

## Overview
After Phase 2 refactoring, customer matching happens in a single pass after deduplication. This document explains the JSON data structure from file extraction and how it's used to look up customers in QuickBooks Online (QBO).

## JSON Data Structure from File Extraction

### Sample Extracted Payment Data
```json
{
  "Donor Name": "John Smith",
  "Gift Amount": "500.00",
  "Check No.": "1234",
  "Check Date": "2025-05-28",
  "Deposit Date": "2025-05-30",
  "Memo": "Annual contribution",
  "Address - Line 1": "123 Main St",
  "City": "Springfield",
  "State": "IL",
  "ZIP": "62701",
  "Email": "john.smith@example.com",
  "Phone": "(555) 123-4567",
  "First Name": "John",
  "Last Name": "Smith",
  "customerLookup": "Smith Family Foundation"
}
```

### Key Fields for Customer Matching

1. **Primary Lookup Fields** (in order of priority):
   - `customerLookup`: Explicit QBO customer name if known
   - `Donor Name`: Full name of the payer/donor
   - `Email`: Email address for matching
   - `Phone`: Phone number for matching

2. **Address Fields** (used for verification):
   - `Address - Line 1`
   - `City`
   - `State`
   - `ZIP`

3. **Name Components** (for advanced matching):
   - `First Name`
   - `Last Name`

## How Customer Lookup Works

### Step 1: Collect Lookup Values
From `file_processor.py` (lines 336-358):

```python
# Collect all unique lookup values
all_lookups = set()
donation_to_lookups = {}

for i, donation in enumerate(donations_list):
    lookups = []
    lookup_strategies = ["customerLookup", "Donor Name", "Email", "Phone"]

    for field in lookup_strategies:
        value = donation.get(field)
        if value and str(value).strip():
            clean_value = str(value).strip()
            lookups.append(clean_value)
            all_lookups.add(clean_value)

    donation_to_lookups[i] = lookups
```

### Step 2: Batch API Lookup
The system collects all unique lookup values and queries QBO in one batch:

```python
# Batch lookup all unique customer names
customer_results = self.qbo_service.find_customers_batch(list(all_lookups))
```

### Step 3: Progressive Matching Strategies

From `qbo_service/customers.py` (lines 127-243), the system tries multiple strategies:

#### Strategy 1: Exact Match
```sql
SELECT * FROM Customer WHERE DisplayName = 'John Smith'
```

#### Strategy 2: Partial Match
```sql
SELECT * FROM Customer WHERE DisplayName LIKE '%John Smith%'
```

#### Strategy 3: Name Reversal
- Handles "John Smith" vs "Smith, John"
- Converts between comma-separated and space-separated formats

#### Strategy 4: Significant Parts
- Extracts meaningful tokens (ignoring "and", "the", etc.)
- Searches for longest/most specific parts

#### Strategy 5: Email Domain
- For emails like "john@smithfoundation.org"
- Extracts "smithfoundation" and searches for it

#### Strategy 6: Phone Number
- Searches by last 7 digits of phone number

### Step 4: AI Verification

Once a potential match is found, Gemini AI verifies it:

```python
verification_result = self.gemini_service.verify_customer_match(donation, customer)
```

The AI checks:
- Name similarity
- Address matching
- Context clues
- Returns confidence level and whether addresses differ materially

### Step 5: Set Match Status

Based on verification results:

```python
if verification_result.get("validMatch", False):
    if verification_result.get("addressMateriallyDifferent", False):
        donation["qbCustomerStatus"] = "Matched-AddressNeedsReview"
    else:
        donation["qbCustomerStatus"] = "Matched"
else:
    donation["qbCustomerStatus"] = "New"
```

## Match Status Values

- **"Matched"**: Valid match with consistent address
- **"Matched-AddressNeedsReview"**: Valid match but address differs
- **"Matched-AddressMismatch"**: Match found but needs verification
- **"New"**: No match found, new customer needed

## Data Flow Example

### Input JSON (from extraction):
```json
{
  "Donor Name": "ABC Foundation",
  "Email": "contact@abcfoundation.org",
  "Gift Amount": "1000.00",
  "Check No.": "5678"
}
```

### Lookup Process:
1. Try "ABC Foundation" → No exact match
2. Try partial match → Finds "ABC Foundation Inc."
3. AI verifies: Same organization, just different suffix
4. Result: Matched

### Output JSON (after matching):
```json
{
  "Donor Name": "ABC Foundation",
  "Email": "contact@abcfoundation.org",
  "Gift Amount": "1000.00",
  "Check No.": "5678",
  "customerLookup": "ABC Foundation Inc.",
  "qboCustomerId": "123",
  "qbCustomerStatus": "Matched",
  "matchMethod": "donor name",
  "matchConfidence": "high"
}
```

## Special Cases

### 1. Organization Name Variations
- "XYZ Foundation" matches "XYZ Foundation, Inc."
- "ABC Corp" matches "ABC Corporation"

### 2. Individual Name Formats
- "John Smith" matches "Smith, John"
- "Dr. Jane Doe" matches "Jane Doe"

### 3. Email-Based Matching
- "john@smithfamily.org" might match "Smith Family Foundation"

### 4. Phone-Based Matching
- Useful for businesses that might be listed by phone

## Performance Optimization

### Caching
- Customer data is cached for 5 minutes
- Reduces redundant API calls
- Cache key is lowercase display name

### Batch Processing
- All lookups collected before API calls
- Single batch request instead of N individual requests
- Parallel processing with ThreadPoolExecutor

## Error Handling

If matching fails at any point:
- Status defaults to "New"
- Original donation data preserved
- Error logged but processing continues
- User can manually match later

## Future Enhancements

1. **Fuzzy Matching Score**: Add numeric confidence scores
2. **Machine Learning**: Train on successful matches
3. **Address Standardization**: Use USPS API for addresses
4. **Duplicate Detection**: Flag potential duplicate customers
