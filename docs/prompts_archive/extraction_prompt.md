Please extract ONLY the donation check information from the document and return it in STRICT JSON format.
VERY IMPORTANT: 
- Extract ONLY actual donation checks with check numbers and amounts
- Do NOT extract summary totals, deposit slip headers, or memo lines that aren't part of a specific check
- Your response MUST include ONLY valid JSON with NO additional text

The JSON must include ALL of these fields, even if the value is null:
{
  "customerLookup": "string or null",
  "Salutation": "string or null",
  "Donor Name": "string (REQUIRED)",
  "Check No.": "string or null",
  "Gift Amount": "string (REQUIRED)",
  "Check Date": "string or null",
  "Gift Date": "string (REQUIRED)",
  "Deposit Date": "string or null",
  "Deposit Method": "string or null",
  "Memo": "string or null",
  "First Name": "string or null",
  "Last Name": "string or null",
  "Full Name": "string or null",
  "Organization Name": "string or null",
  "Address - Line 1": "string or null",
  "City": "string or null",
  "State": "string or null",
  "ZIP": "string or null"
}

These fields are REQUIRED and MUST have a value (not null):
- Donor Name
- Gift Amount
- Gift Date

These fields should be extracted if available, but use null if not found:
- First Name
- Last Name  
- Address - Line 1
- City
- State
- ZIP

IMPORTANT: Use null for missing information, NOT "N/A" or other placeholders

IMPORTANT NOTES FOR DATES:
- For "Gift Date", follow this priority:
  1. Use postmark date from envelope (if visible)
  2. Use "Check Date" from the check itself
  3. Use today's date ONLY if no other date is available
- NEVER use "Deposit Date" for "Gift Date"
- "Deposit Date" is when the bank processed the checks (usually shown on deposit slips)
- "Gift Date" is when the donation was made (check written or mailed)

Please examine the document thoroughly to find all required information.
IMPORTANT: Return ONLY the JSON object, with no additional text before or after.