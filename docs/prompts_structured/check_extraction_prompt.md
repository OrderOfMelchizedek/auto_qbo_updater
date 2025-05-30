Extract payment information specifically from CHECK images.

**Check Analysis Focus:**

1. **Check Number**: Located in the upper right corner of the check
2. **Amount**:
   - Numeric amount (in the box on the right)
   - Written amount (on the line)
   - These MUST match - flag any discrepancies
3. **Date**: Written date on the check (upper right area)
4. **Payment Method**:
   - If amount/date are handwritten = "handwritten_check"
   - If amount/date are printed = "printed_check"
5. **Payer Information**:
   - Name on the check (upper left)
   - Address below the name (if present)
6. **Memo**: Check the memo line (bottom left)
7. **Bank Information**: Note but don't extract routing/account numbers

**Critical Rules:**
- Be extremely accurate with amounts - double-check numeric vs written
- Check numbers are usually 3-6 digits
- If multiple checks are visible, extract each one separately
- Use null for unclear or missing information

**Name Aliases:**
For payer names, create variations:
- "John A. Smith" → ["John A. Smith", "John Smith", "Smith, John", "J. Smith", "Smith, John A."]

Return structured JSON following the provided schema.
