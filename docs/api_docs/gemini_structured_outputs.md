I'll help you build an app to extract key information from scanned checks and documents using Gemini's structured outputs. Here's a comprehensive implementation:I've created a comprehensive implementation for extracting donation information from scanned documents using Gemini's structured outputs. Here are the key features:

## Key Components:

### 1. **Structured Data Models**
- Uses Pydantic models to define the exact JSON schema you specified
- Includes validation to ensure required fields are present (e.g., check numbers for checks, payment references for online donations)
- Handles the specific business logic for different payment types

### 2. **Document Processing**
The `DonationExtractor` class handles different document types:
- **Checks & Envelopes**: Uses Gemini's multimodal capabilities to analyze images
- **User Records**: Extracts handwritten lists with authoritative check numbers
- **CSV Files**: Processes online donation data

### 3. **Smart Field Extraction**
- Implements the payment date logic (postmark > check date for handwritten checks)
- Prioritizes envelope addresses over check addresses
- Uses user record check numbers as authoritative

### 4. **Batch Processing**
- Process multiple documents at once
- Merge data from different sources
- Handle errors gracefully

## Usage Example:

```python
# Initialize the extractor
extractor = DonationExtractor(model_name="gemini-2.5-flash-latest")

# Process a single check
record = extractor.extract_from_check(
    check_image_path="check.jpg",
    envelope_image_path="envelope.jpg"  # Optional
)

# Process a batch with all document types
records = extractor.process_batch(
    check_images=["check1.jpg", "check2.jpg"],
    envelope_images=["env1.jpg", "env2.jpg"],
    user_record_image="handwritten_list.jpg",
    csv_file="stripe_donations.csv"
)
```

## Additional Utilities You Might Want:## Key Implementation Tips:

### 1. **Handling Multiple Document Types**
Since you're processing different document types (checks, envelopes, user records, CSVs), consider creating separate prompts optimized for each:

```python
# Specialized prompts for each document type
CHECK_PROMPT = """
Focus on:
- Check number (upper right corner)
- Amount (numeric and written - they must match)
- Date on check
- Memo line
- Account holder name and address
Identify if handwritten vs printed by looking at the amount and date fields.
"""

ENVELOPE_PROMPT = """
Priority: Return address (this supersedes all other addresses)
Also extract:
- Postmark date
- Any handwritten notes
- Additional contact info (phone, email)
"""
```

### 2. **Error Handling and Validation**
Add robust validation for critical fields:

```python
def validate_amount_consistency(numeric_amount: str, written_amount: str) -> bool:
    """Ensure numeric and written amounts match on checks."""
    # Convert written amount to number and compare
    # This is crucial for check processing
```

### 3. **Batch Processing Optimization**
For better performance with multiple documents:

```python
# Use Gemini's batch API for multiple images
batch_config = {
    "response_mime_type": "application/json",
    "response_schema": DonationRecordList,
    "temperature": 0.1,
    "max_output_tokens": 2000,
}
```

### 4. **Address Reconciliation**
Since addresses can come from multiple sources with different priorities:

```python
def reconcile_addresses(check_address, envelope_address, database_address):
    # Priority: Envelope > Check > Database
    if envelope_address and is_valid_address(envelope_address):
        return envelope_address
    elif check_address and is_valid_address(check_address):
        return check_address
    else:
        return database_address
```

### 5. **Deployment Considerations**

- **API Rate Limits**: Implement retry logic and rate limiting
- **File Size**: Optimize images before sending to Gemini (compress, resize)
- **Caching**: Cache results to avoid reprocessing identical documents
- **Audit Trail**: Log all extractions for verification

### 6. **Testing Strategy**

Create test cases for:
- Different check types (personal, business, handwritten, printed)
- Edge cases (damaged documents, poor handwriting)
- Various CSV formats from different payment processors

The structured output feature of Gemini ensures you'll get consistent JSON responses that match your schema, making it much easier to integrate into your application workflow. The key is providing clear, detailed prompts and using appropriate temperature settings (low for accuracy).
