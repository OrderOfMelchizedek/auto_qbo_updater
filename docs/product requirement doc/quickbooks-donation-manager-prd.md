# Product Requirements Document: QuickBooks Donation Manager

**Version:** 1.1
**Date:** June 5, 2025
**Status:** Draft

---
## 1. Executive Summary

QuickBooks Donation Manager is a web application designed to revolutionize donation processing for nonprofits and small businesses by automating the extraction, validation, and recording of donation data. The application leverages AI technology to process various document types, integrates seamlessly with QuickBooks Online for financial record keeping, and generates professional tax receipt letters.

### Key Benefits:
- **80%+ reduction** in manual data entry time
- **Automated extraction** from checks, envelopes, and digital documents
- **Intelligent matching** with existing QuickBooks customer records
- **Streamlined generation** of tax-compliant receipt letters
- **Mobile-responsive** design for processing donations anywhere

### Target Market:
Primary users are nonprofit treasurers and bookkeepers who process 3-20 donations weekly and currently spend significant time on manual data entry and reconciliation.

---

## 2. Problem Statement & User Personas

### Problem Statement

Nonprofit organizations face significant operational challenges in processing donations:
- Manual data entry from paper checks and documents is time-consuming and error-prone
- Matching donors to existing records requires cross-referencing multiple systems
- Generating tax receipts involves repetitive document creation
- Current processes average 15-20 minutes per donation for complete processing

### Primary User Persona: Sarah, Nonprofit Treasurer

**Demographics:**
- Age: 45-65
- Role: Part-time treasurer at local nonprofit
- Tech comfort: Moderate (uses QuickBooks, email, basic web apps)

**Pain Points:**
- Spends 5-10 hours weekly on donation processing
- Makes frequent data entry errors requiring correction
- Struggles with illegible handwriting on checks
- Manually creates receipt letters in Word

**Goals:**
- Process donations quickly and accurately
- Maintain clean donor records in QuickBooks
- Provide timely tax receipts to donors
- Reduce administrative overhead

### Secondary User Persona: Michael, Bookkeeping Service Owner

**Demographics:**
- Age: 35-50
- Role: Provides bookkeeping services to 5-10 small nonprofits
- Tech comfort: High (uses multiple cloud accounting tools)

**Pain Points:**
- Clients send batches of donation documents weekly
- Each client has different receipt letter requirements
- Time spent on data entry reduces profitability

**Goals:**
- Process multiple clients' donations efficiently
- Maintain accuracy across all client accounts
- Scale services without adding staff

---

## 3. Process Flow

### QBO Authentication
1. When user clicks "Connect to QBO" or attempts to upload files and begin the process and they are not authenticated into quickbooks, a modal pops up in a separate window prompting them to log into quickbooks.
2. Once the user logs in, the separate window closes and they are redirected to the main page. The "Connect to QBO" button demonstrates that the user has logged into quickbooks and the main process can be executed.

### Page Load
3. Page loads. User sees the document upload screen with drag-and-drop interface (user may also click to add files from computer) and a button that says "Upload & Process".
  - "Upload & Process" is greyed out until user uploads at least one file.
  - Upper-right part of the page has a "Connect to QBO" button. When clicked, launches the Oauth2 flow to login to quickbooks online. When authenticated, this button is green; when not authenticated, this button is grey.
4. User adds files.
  - The filenames and filesizes for each file shows up in the UI.
  - The "Upload & Process" is no longer greyed out but is clickable.
5. User clicks on "Upload & Process".
  - If the user has already authenticated into quickbooks, the files are uploaded to S3, file references are added to Redis, and the main process begins.
  - If the user has NOT authenticated into quickbooks, this launches the QBO authentication flow.
### File Upload
6. Once the user is authenticated into quickbooks and has added files and clicks "Upload & Process", the files are then sent to Amazon S3 for temporary storage.
  - System accepts up to 20 files per batch
  - Supported formats: JPEG, PNG, PDF, CSV
  - File size limit: 20MB per file
  - Drag-and-drop interface with progress indicators
  - Clear error messages for unsupported formats
7. References to the files are stored in Redis so that the Heroku Web dyno and worker dyno can easily refer to the uploaded files.

### Data Extraction
8. Files are sent to the geminiservice.py module for data extraction. We get back a json object with the extracted data.

### Validation & Deduplication
9. The JSON object is sent through the validation and deduplication module.
  - Validation
    - Anything in all caps rewritten to proper case
    - Leading zeros removed from Check Nos. greater than 4 digits
  - Deduplication
    - Every item must have a unique key, which shall be the Payment Ref + Amount. That is, no two items shall have the same Payment Ref and Amount.
    - The data for any two items with the same Payment Ref and Amount shall be merged into one item.
    - Merge preserves most complete information from all sources
  - After validation and deduplication, if any item is missing Payment Ref or Amount, discard it. The result is a deduplicated json object with full, merged data from all pages of the upload.

### Quickbooks Matching
10. For each entry, attempt to match it to its corresponding CustomerRef in quickbooks.
11. Once matched, pull all of that entry's quickbooks data into the following json structure:
  ```json
  {
    "CustomerRef": {
      "FirstName": "",
      "LastName": "",
      "FullName": "",
      "QBOrganizationName": "",
      "QBAddress": {
        "Line1": "",
        "City": "",
        "State": "",
        "ZIP": ""
      },
      "QBEmail": "",
      "QBPhone": ""
    }
  }
  ```
  - If not matched, it needs to show up in the UI as a new customer and give the user the opportunity to add them to quickbooks.
12. Compare the Quickbooks data to the extracted payer data to determine if QuickBooks (QB) requires any updates.
  - Address:
    - Compare the extracted address with the existing QB address.
      - Fields to compare: Address - Line 1, City, State, and ZIP.
      - If most of the characters in Address - Line 1 match: Keep the existing QB address.
      - If more than half of the characters in Address - Line 1 differ: Update QB address with the extracted address data.
      - Provide a visual indicator in the UI to show that the address was updated.
    - Note regarding ZIP codes:
      - ZIPs are 5 digits long and may contain leading zeros — these must be preserved.
      - If the ZIP includes a 4-digit extension (e.g., 12345-6789), ignore the extension and use only the 5-digit ZIP.
  - Email and Phone:
    - If QB does not have an email or phone number, but the extracted data does:
      - Add the corresponding data to the QB json object.
    - If QB already has email or phone:
      - Due to possible inaccuracies in handwritten data, do not overwrite existing QB data.
      - If the extracted email/phone is completely different from the QB email/phone:
        - Add the new email/phone to QB alongside the existing one.
        - This implies that the Email and Phone fields in QB may need to support multiple entries (i.e., they should be lists in the json schema).

### Final Display
13. The final display of information will have information from the extracted json from initial gemini processing as well as the json from the matched quickbooks entry. When the user chooses to send an entry to quickbooks, the data sent will come from this object.
  ```json
  {
    "PayerInfo": {
      "CustomerRef": {
        "Salutation": "",
        "FirstName": "",
        "LastName": "",
        "FullName": ""
      },
      "QBOrganizationName": "",
      "QBAddress": {
        "Line1": "",
        "City": "",
        "State": "",
        "ZIP": ""
      },
      "QBEmail": "",
      "QBPhone": ""
    },
    "PaymentInfo": {
      "PaymentRef": "",
      "Amount": "",
      "PaymentDate": "",
      "DepositDate": "",
      "DepositMethod": "",
      "Memo": ""
    }
  }
  ```
  - This should be displayed as a table in the UI. The following columns should be displayed by default:
    - CustomerRef
    - FullName (or Organization Name if an Organization)
    - PaymentRef
    - Amount
    - PaymentDate
    - QBAddress shown in 4 columns (Line1, City, State, ZIP their own columns)
    - Memo
  - Every field in this table should be editable by the user to correct any inaccuracies in the extracted information. Whenever an edit is made, update the corresponding value in the json object.
14. There should be a column on the right side called Actions which should have the following buttons for each entry:
  - Send to QB. This sends the line item to Quickbooks as a Sales Receipt.
  - Manual Match. If the automatic matching is inaccurate or there was no match, this allows the user to manually match the payer to quickbooks.
  - New Customer. If the item was not matched, pressing this will add a new customer to quickbooks and create a sales receipt with the corresponding data and send it to quickbooks
  - Delete. In case the user wants to delete an entry.
15. There should be a column to the left of the Actions columns called Status. It should display badges corresponding to the results of the processing (more than one can be displayed)
  - Matched (for an entry that was matched)
  - New Customer (for an entry that was not matched)
  - Sent to Quickbooks (if the user sent that entry to quickbooks)
  - Address Updated (if the address from the extracted data updated what was in quickbooks)
  - Edited (if the user edited any of the fields in the table)
16. There should be a button that allows for bulk actions
  - Send all to QB. This sends every item in the table to quickbooks as a sales receipt.
  - Clear all. This clears everything from the table.
  - Generate Report. This generates a text-based report summarizing every entry in the table.
  - Export to .csv. This exports all the data as a .csv file (all fields, not just the ones displayed in the UI table)

I'll create a plain-text diagram of this QBO (QuickBooks Online) integration process flow:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         QBO INTEGRATION PROCESS FLOW                         │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────┐
│   PAGE LOAD      │
│                  │
│ • Upload Screen  │
│ • Connect to QBO │
│   Button (Grey)  │
└────────┬─────────┘
         │
         ▼
┌──────────────────────────────────────┐        ┌─────────────────────────┐
│  USER CLICKS "CONNECT TO QBO"        │        │   QBO AUTH MODAL        │
│  (or Upload & Process w/o auth)      │───────►│                         │
└──────────────────────────────────────┘        │  • User logs into QB    │
                                                 │  • Window closes        │
                                                 │  • Button turns green   │
                                                 └───────────┬─────────────┘
                                                             │
         ┌───────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────┐
│        USER UPLOADS FILES            │
│                                      │
│  • Drag & drop interface             │
│  • Up to 20 files                    │
│  • JPEG, PNG, PDF, CSV               │
│  • 20MB limit per file               │
│  • "Upload & Process" activates      │
└────────┬─────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────┐
│   CLICK "UPLOAD & PROCESS"           │
│                                      │
│  If authenticated:                   │
│    → Continue to upload              │
│  If not authenticated:               │
│    → Launch QBO auth flow            │
└────────┬─────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────┐        ┌─────────────────────────┐
│        FILE STORAGE                  │───────►│    AMAZON S3            │
│                                      │        │  (Temporary Storage)    │
│  • Files sent to S3                  │        └─────────────────────────┘
│  • References stored in Redis        │        ┌─────────────────────────┐
│                                      │───────►│      REDIS              │
└────────┬─────────────────────────────┘        │  (File References)      │
         │                                      └─────────────────────────┘
         ▼
┌──────────────────────────────────────┐
│      DATA EXTRACTION                 │
│                                      │
│  • Files → geminiservice.py          │
│  • Returns JSON with extracted data  │
└────────┬─────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────┐
│   VALIDATION & DEDUPLICATION         │
│                                      │
│  Validation:                         │
│  • ALL CAPS → Proper case            │
│  • Remove leading zeros (Check No.)  │
│                                      │
│  Deduplication:                      │
│  • Unique key: Payment Ref + Amount  │
│  • Merge duplicate entries           │
│  • Discard if missing key fields     │
└────────┬─────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────┐        ┌─────────────────────────┐
│     QUICKBOOKS MATCHING              │◄──────►│   QUICKBOOKS API        │
│                                      │        │                         │
│  For each entry:                     │        │  • Search customers     │
│  • Match to CustomerRef              │        │  • Pull customer data   │
│  • Pull QB customer data             │        │  • Compare & update     │
│  • Compare addresses                 │        └─────────────────────────┘
│  • Update if needed                  │
│  • Flag new customers                │
└────────┬─────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                            FINAL DISPLAY (UI TABLE)                       │
│                                                                           │
│  ┌─────────┬────────────┬─────────┬────────┬──────┬─────────┬─────────┐ │
│  │Customer │ Full Name  │Payment  │ Amount │ Date │ Address │  Memo   │ │
│  │  Ref    │            │  Ref    │        │      │         │         │ │
│  └─────────┴────────────┴─────────┴────────┴──────┴─────────┴─────────┘ │
│                                                                           │
│  Status Badges:                    Actions per row:                      │
│  • Matched                         • Send to QB                          │
│  • New Customer                    • Manual Match                        │
│  • Sent to QuickBooks              • New Customer                        │
│  • Address Updated                 • Delete                              │
│  • Edited                                                                 │
│                                                                           │
│  Bulk Actions:                                                            │
│  • Send all to QB                                                        │
│  • Clear all                                                              │
│  • Generate Report                                                        │
│  • Export to CSV                                                          │
└───────────────────────────────────────────────────────────────────────────┘

LEGEND:
─────────
→  Direct flow
◄─► Two-way communication
▼  Sequential step
```

This diagram shows the complete flow from initial page load through authentication, file upload, data extraction, validation, QuickBooks matching, and final display with user actions. The process includes both the happy path (authenticated user) and the authentication flow for new/unauthenticated users.
