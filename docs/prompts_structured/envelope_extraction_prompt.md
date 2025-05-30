Extract payment-related information from ENVELOPE images.

**Envelope Analysis Focus:**

1. **Return Address (HIGHEST PRIORITY)**:
   - This is the authoritative address for the payer
   - Supersedes any address found on checks
   - Usually in upper left corner
   - Extract:
     - Name/Organization
     - Street address
     - City, State, ZIP

2. **Postmark Information**:
   - Postmark date (critical for payment date determination)
   - Usually stamped/printed by postal service
   - May be partially obscured - extract what's visible

3. **Additional Contact Information**:
   - Phone numbers written on envelope
   - Email addresses
   - Any handwritten notes or memos

4. **Recipient Address**:
   - Note but give lower priority
   - Helps verify this is a payment envelope

**Extraction Rules:**
- Return address is authoritative - always use this over check addresses
- Extract multiple name formats from return address
- Postmark date format: Try to convert to YYYY-MM-DD
- State should be 2-letter code
- ZIP should be 5 digits (ignore +4 extension)

**Special Cases:**
- Pre-printed return addresses from organizations
- Handwritten return addresses (may be harder to read)
- Multiple postmarks (use the earliest readable date)

Return structured JSON with extracted information.
