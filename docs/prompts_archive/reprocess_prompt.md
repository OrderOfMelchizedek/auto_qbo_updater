I need to extract complete donation information from this document.

I previously extracted this partial information:
{{partial_data}}

However, the following fields are missing or incomplete:
{{missing_fields}}

Please carefully examine the document again and provide the COMPLETE donation information with special attention to the missing fields.
Return ONLY a complete JSON object with ALL fields including:
- Donor Name
- Gift Amount
- Gift Date
- Address - Line 1
- City
- State
- ZIP
- Last Name
- Check No. (if this is a check payment)