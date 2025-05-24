Extract donation information from the provided document and return ONLY valid JSON.

Look for checks and extract the following for EACH check:

Required fields (MUST have values):
- Donor Name: Name on the check
- Gift Amount: Dollar amount (numbers on check)

Optional fields (use null if not clearly visible):
- Check No.: Number in upper right of check
- Check Date: Date written on the check itself (NOT the deposit slip date)
- customerLookup: null
- Salutation: null
- Deposit Date: Date from deposit slip (if visible)
- Deposit Method: "ATM Deposit"
- Memo: Text from memo line
- First Name: First name if identifiable
- Last Name: Last name if identifiable
- Full Name: null
- Organization Name: null
- Address - Line 1: From envelope or check
- City: From address
- State: Two-letter code from address
- ZIP: Five-digit code from address

Return JSON array format:
[
  {
    "customerLookup": null,
    "Salutation": null,
    "Donor Name": "John Smith",
    "Check No.": "1234",
    "Gift Amount": "100.00",
    "Check Date": "5/14/24",
    "Deposit Date": "5/15/24",
    "Deposit Method": "ATM Deposit",
    "Memo": null,
    "First Name": "John",
    "Last Name": "Smith",
    "Full Name": null,
    "Organization Name": null,
    "Address - Line 1": null,
    "City": null,
    "State": null,
    "ZIP": null
  }
]

IMPORTANT:
- Extract ONLY actual checks (not summaries or totals)
- Read the date from EACH individual check
- Use null for any unclear/missing information
- Return ONLY the JSON array, no other text