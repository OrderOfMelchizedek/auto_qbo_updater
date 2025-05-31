Extract payment information from CSV data for ONLINE PAYMENTS.

**CSV Processing Instructions:**

1. **Payment Method**: Always set to "online_payment"

2. **Required Field Mappings**:
   - Payment Reference: Look for fields like "Payment_Ref", "Transaction ID", "Reference", "ID"
   - Amount: Look for "Amount", "Total", "Payment Amount", "Value"
   - Payment Date: Look for "Date", "Transaction Date", "Payment Date", "Created"

3. **Payer Identification**:
   - Individual names: "Name", "Donor Name", "Payer Name", "Customer"
   - Organizations: "Company", "Organization", "Business Name"
   - Create comprehensive aliases for individuals:
     * "John A. Smith" → ["John Smith", "J. Smith", "Smith, John", "Smith, J.", "John A. Smith", "Smith, John A."]
     * Include variations with/without middle initials
     * Create initial versions (John → J.)
     * DO NOT expand initials

4. **Contact Information**:
   - Email: "Email", "Email Address", "Payer Email"
   - Phone: "Phone", "Phone Number", "Contact"
   - Address fields: May be split across multiple columns

5. **Payment Platform Detection**:
   - If source is identifiable (Stripe, PayPal, etc.), set deposit_method accordingly:
     - "Online - Stripe"
     - "Online - PayPal"
     - "Online" (if platform unknown)

6. **Special Handling**:
   - Convert date formats to YYYY-MM-DD
   - Handle currency symbols in amounts
   - Merge address components into proper fields
   - Skip header rows and summary rows

**Important Notes:**
- Each row should become a separate payment record
- payment_ref is REQUIRED for online payments
- Skip rows with zero or negative amounts
- Handle both individual and organization payers appropriately

Return an array of payment records in the structured format.
