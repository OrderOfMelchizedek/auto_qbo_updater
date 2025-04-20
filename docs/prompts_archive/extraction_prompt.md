Please extract the donation information from the document and return it in STRICT JSON format.
VERY IMPORTANT: Your response MUST include ONLY valid JSON with NO additional text.

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
  "First Name": "string (REQUIRED)",
  "Last Name": "string (REQUIRED)",
  "Full Name": "string or null",
  "Organization Name": "string or null",
  "Address - Line 1": "string (REQUIRED)",
  "City": "string (REQUIRED)",
  "State": "string (REQUIRED)",
  "ZIP": "string (REQUIRED)"
}

These fields are REQUIRED and MUST have a value (not null):
- Donor Name
- Gift Amount
- Gift Date
- First Name
- Last Name
- Address - Line 1
- City
- State
- ZIP

Please examine the document thoroughly to find all required information.
IMPORTANT: Return ONLY the JSON object, with no additional text before or after.