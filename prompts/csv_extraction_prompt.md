You are analyzing a CSV file containing donation information. This CSV data represents online donations.
Here is the raw CSV content:

{{csv_content}}

Please extract all donation records from this CSV file. 
VERY IMPORTANT: Return ONLY a valid JSON array containing objects with these fields, with NO additional text before or after:

[
  {
    "customerLookup": "string or null",
    "Salutation": "string or null",
    "Donor Name": "string (REQUIRED)",
    "Check No.": "N/A",
    "Gift Amount": "string (REQUIRED)",
    "Check Date": "string or null",
    "Gift Date": "string (REQUIRED)",
    "Deposit Date": "today's date",
    "Deposit Method": "Online Donation", 
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
]

For Online Donations:
- Check No. should always be "N/A"
- Deposit Method should always be "Online Donation"
- Deposit Date should be today's date

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

Return ONLY the JSON array with no additional text. Ensure it is valid JSON that can be parsed directly.