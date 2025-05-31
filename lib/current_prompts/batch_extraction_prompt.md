Extract payment information from the provided batch of documents.

**Batch Processing Instructions:**

1. **Multiple Items Expected**: This batch may contain multiple checks, payments, or donation records
2. **Extract Each Separately**: Create a separate payment record for each check or payment found
3. **Look Carefully**: Some images may show multiple checks on one page (e.g., deposit slips)
4. **Cross-Reference**: If you see both a deposit slip and individual checks, extract from the more detailed source

**For Each Payment, Extract:**

1. **Payment Information**:
   - Payment method (handwritten_check, printed_check, online_payment)
   - Check number or payment reference
   - Amount (verify numeric matches written amount for checks)
   - All relevant dates (check date, postmark date, deposit date)
   - Memo information

2. **Payer Information**:
   - For individuals: Create comprehensive name aliases:
     * "John A. Smith" → ["John Smith", "J. Smith", "Smith, John", "Smith, J.", "John A. Smith", "Smith, John A."]
     * Include versions with/without middle initials
     * Create initial versions (John → J.)
     * DO NOT expand initials (J. does not become John)
   - For organizations: Use the organization name exactly
   - Include any titles or salutations

3. **Contact Information**:
   - Complete mailing address
   - Email and phone if available
   - Ensure ZIP codes are 5 digits

**Important Rules:**
- If a deposit slip shows multiple checks, extract each check as a separate record
- Use the most complete information available (individual checks usually have more detail than deposit slips)
- Preserve exact check numbers (including leading zeros)
- Be extremely accurate with amounts
- Return NULL for missing or unclear information

Return a JSON array of payment records following the structured format.
