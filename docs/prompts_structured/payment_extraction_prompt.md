Extract payment information from the provided documents and return structured JSON data.

**Document Analysis Instructions:**

1. **Identify Payment Method:**
   - Handwritten check: Amount and date are handwritten
   - Printed check: Amount and date are printed (usually from organizations)
   - Online payment: Electronic payment records or CSV data

2. **Required Information:**
   - Payment method (as identified above)
   - Check number (for checks) OR payment reference (for online)
   - Amount (must be accurate - verify numeric matches written amount on checks)
   - Payment date (follow rules below)

3. **Payment Date Rules:**
   - Handwritten check: Use postmark date from envelope if available, otherwise use check date
   - Printed check: Use the date printed on the check
   - Online payment: Use transaction date from the record

4. **Payer Identification:**
   - For individuals: Extract all name variations you can find
     - From check: Account holder name
     - From envelope: Return address name
     - Create aliases like ["John Smith", "Smith, John", "J. Smith"]
   - For organizations: Use the organization name exactly as written

5. **Address Priority:**
   - Envelope return address takes priority over all other addresses
   - Check address is secondary
   - No address is better than wrong address

6. **Additional Fields:**
   - Memo: Any memo from check or notes with payment
   - Check/Postmark dates: Extract if clearly visible
   - Contact info: Email or phone if provided

Return structured data following the exact schema provided. Use null for any missing optional fields.
