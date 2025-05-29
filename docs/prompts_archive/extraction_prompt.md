Please extract ONLY the donation check information from the document and return it in STRICT JSON format.

🚨 CRITICAL DATE EXTRACTION RULES - READ THIS FIRST 🚨
==================================================
YOU MUST FOLLOW THIS EXACT PROCESS FOR EVERY SINGLE DONATION:

STEP 1 - IDENTIFY THE DEPOSIT SLIP (DO NOT USE ITS DATE FOR CHECKS!)
- Look for a handwritten list with a date at the top
- This date is when checks were DEPOSITED AT THE BANK
- ⛔ NEVER USE THIS AS THE CHECK DATE ⛔
- This date should ONLY be used for the "Deposit Date" field

STEP 2 - EXTRACT EACH CHECK'S DATE INDIVIDUALLY:

For EACH check:
- Look at the upper right area of the check (below check number)
- Find the date line (handwritten like "5/14/24" or printed)
- This is the "Check Date" for that specific check
- If you cannot read the date on a specific check, use null

⚠️ VALIDATION BEFORE PROCEEDING ⚠️
- ✅ Each check has its OWN Check Date from the check itself
- ❌ NOT all checks have the same date
- ❌ NOT using the deposit slip date for Check Date

Please extract ONLY the donation check information from the document and return it in STRICT JSON format.
VERY IMPORTANT:
- Extract ONLY actual donation checks with check numbers and amounts
- Do NOT extract summary totals, deposit slip headers, or memo lines that aren't part of a specific check
- Each check should have its OWN date - do not apply one date to all checks
- If you cannot clearly read the date on a specific check, use null for that check's dates
- Your response MUST include ONLY valid JSON with NO additional text

The JSON must include ALL of these fields, even if the value is null:
{
  "customerLookup": "string or null",
  "Salutation": "string or null",
  "Donor Name": "string (REQUIRED)",
  "Check No.": "string or null",
  "Gift Amount": "string (REQUIRED)",
  "Check Date": "string (REQUIRED)",
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
- Check Date

These fields should be extracted if available, but use null if not found:
- First Name
- Last Name
- Address - Line 1
- City
- State
- ZIP

IMPORTANT: Use null for missing information, NOT "N/A" or other placeholders

CRITICAL DATE EXTRACTION RULES:

For "Check Date" - This is the date written on the check itself:
  - Look in the upper right area of each check (usually near or below the check number)
  - This is typically handwritten like "5/14/24" or printed
  - EACH CHECK HAS ITS OWN DATE - read it from that specific check
  - If you cannot read the date on a specific check, use today's date (2025-05-24)

For "Deposit Date" - This is when the batch was deposited at the bank:
  - Usually found on the handwritten deposit slip or summary
  - This is the SAME for all checks in a batch
  - If not specified, use today's date (2025-05-24)

EXTREMELY IMPORTANT:
- Each check MUST have its OWN Check Date read from that individual check
- Do NOT apply the same Check Date to all checks in a batch
- The Deposit Date can be the same for all checks (that's expected)
- Common error: Using the deposit slip date as the Check Date - this is WRONG

Please examine the document thoroughly to find all required information.
IMPORTANT: Return ONLY the JSON object, with no additional text before or after.
