**Project Specification: Friends of Mwangaza Donation Processor**

**1. Project Goal:**

Develop a web application that allows users from Friends of Mwangaza (FoM) to upload donation documents (images, PDFs) and online donation reports (CSV), extract relevant information using the Gemini 2.5 Pro Preview LLM, display this information in an editable table, integrate with QuickBooks Online (QBO) to create Sales Receipts and manage Customer data, and generate summary reports. The initial development target is localhost, with eventual deployment to Heroku.

**2. Core Features:**

*   **File Upload:** Allow users to upload multiple files at once:
    *   Image files (e.g., JPG, PNG) containing scans or photos of checks/donation slips.
    *   PDF files containing scans of checks/donation slips.
    *   A single CSV file containing data for online donations (exported from a system like Stripe, etc.).
*   **Data Extraction (LLM):**
    *   Use Google's Gemini 2.5 Pro Preview LLM API.
    *   Process uploaded image and PDF files to extract structured donation information.
    *   Utilize function calling and/or structured output capabilities of the LLM for reliable data extraction based on the fields defined in `FOM_deposit_report_header_descriptions_2025-04-12.md`.
    *   Leverage and potentially revise the provided prompt template `FOM Deposit Assistant Prompt 2025-04-12.md` for optimal extraction results.
    *   Parse the uploaded CSV file using standard CSV parsing logic (no LLM needed for CSV).
*   **Data Display & Editing:**
    *   Present all extracted and parsed donation data (from images, PDFs, and CSV) in a single consolidated table within the web browser.
    *   Table columns should correspond to the headers defined in `FOM_deposit_report_header_descriptions_2025-04-12.md`.
    *   All cells in the table (except perhaps an internal identifier or source indicator) should be editable by the user to correct any extraction/parsing errors.
*   **Data Persistence (Local):**
    *   Implement a "Save Changes" button that persists the user's edits to the displayed table data within the current session or local browser storage (for localhost version). A simple in-memory store or browser local storage is acceptable initially.
*   **QuickBooks Online Integration:**
    *   Connect securely to the FoM QuickBooks Online account (implement OAuth 2.0 authentication flow).
    *   **Donor/Customer Management:**
        *   For *each* donation row (from *any* source: image, PDF, CSV):
            *   Query QBO `Customer` API to check if the donor exists (match based on the `customerLookup` field extracted/parsed).
            *   **If Donor Exists:** Retrieve the QBO customer record. Compare the address details (Street, City, State, Zip) from the extracted/parsed data with the QBO record. If they differ:
                *   Visually flag the difference to the user in the table row.
                *   Provide an option (e.g., a small button/icon within the row) for the user to update the address *in QBO* with the data from the app. This option *should not* be available for rows originating from the CSV file.
            *   **If Donor Does Not Exist:**
                *   Visually flag the donor as "New" in the table row.
                *   Provide an option (e.g., a small button/icon within the row) for the user to create a *new* `Customer` record *in QBO* using the extracted/parsed data (Name, Address, etc.). This option *should not* be available for rows originating from the CSV file.
    *   **Sales Receipt Creation:**
        *   **Individual Send:** Add a "Send to QB" button to each row in the table. When clicked, create a QBO `Sales Receipt` using the data from that row. This button *must be disabled or hidden* for rows originating from the CSV file.
        *   **Batch Send:** Add a "Send All to QB" button near the top/bottom of the table. When clicked, iterate through *all* rows in the table. For each row *not* originating from the CSV file, create a QBO `Sales Receipt`. Rows originating from the CSV file must be skipped.
        *   Implement visual feedback (e.g., changing button state, adding a status indicator) to show which rows have been successfully sent to QBO.
*   **Report Generation:**
    *   Add a "Generate Report" button near the "Send All to QB" button.
    *   When clicked, generate a report that includes *all* donation records currently displayed in the table (from images, PDFs, and CSV).
    *   The specific format and layout should be based on the provided example reports (details on accessing/interpreting these examples needed - assume they define columns, grouping, and potentially totals). The output could be an HTML view on the page, a downloadable CSV, or PDF. Start with a simple HTML or CSV output.

**3. User Interface (UI) / User Experience (UX):**

*   **Layout:** Simple, clean interface.
    *   Section for file uploads (drag-and-drop or browse).
    *   Main area displaying the editable data table.
    *   Clear buttons for primary actions: "Save Changes", "Send All to QB", "Generate Report".
*   **Table:**
    *   Clearly display headers from `FOM_deposit_report_header_descriptions_2025-04-12.md`.
    *   Inline editing capability for cells.
    *   Visual indicators for:
        *   Data source (e.g., an icon for Image/PDF vs. CSV).
        *   QBO sync status (e.g., Not Sent, Sent, Error).
        *   QBO customer status (e.g., Matched, New, Address Mismatch).
    *   Action buttons/icons within each row for:
        *   "Send to QB" (disabled/hidden for CSV rows).
        *   "Update QBO Address" (only if mismatch detected, disabled/hidden for CSV rows).
        *   "Create QBO Customer" (only if flagged as "New", disabled/hidden for CSV rows).
*   **Feedback:** Provide clear feedback to the user on actions (e.g., "Upload successful", "X rows sent to QB", "Report generated", "Error connecting to QB").

**4. Backend Logic & Processing:**

*   **File Handling:** Receive and temporarily store uploaded files for processing. Handle potential upload errors.
*   **LLM Interaction:**
    *   Construct API calls to Gemini 2.5 Pro Preview, including the (revised) prompt and image/PDF data.
    *   Handle API responses, parse the structured output (JSON expected).
    *   Implement error handling for LLM API calls (e.g., timeouts, errors, malformed responses).
*   **CSV Parsing:** Use a standard library to parse the uploaded CSV file, mapping columns to the expected data structure.
*   **Data Aggregation:** Combine results from LLM extraction and CSV parsing into a unified list of donation records. Add a field to each record indicating its source (`source: 'llm'` or `source: 'csv'`).
*   **QBO API Interaction:**
    *   Implement QBO API client using an appropriate library/SDK.
    *   Handle OAuth 2.0 authentication flow and secure storage/refresh of tokens.
    *   Implement functions for: `findCustomer`, `createCustomer`, `updateCustomer`, `createSalesReceipt`.
    *   Map application data fields to the corresponding QBO object fields accurately.
    *   Robust error handling for all QBO API calls.
*   **State Management:** Manage the state of the donation data table, including user edits and QBO sync status.

**5. LLM Integration Details:**

*   **Model:** Gemini 2.5 Pro Preview.
*   **Input:** Image data (bytes), PDF data (potentially requires preprocessing or direct API support), text prompt.
*   **Prompt Engineering:** Review `FOM Deposit Assistant Prompt 2025-04-12.md`. Refine it to:
    *   Clearly define the desired output structure (JSON schema).
    *   Specify all required fields based on `FOM_deposit_report_header_descriptions_2025-04-12.md`.
    *   Include instructions for handling common edge cases (e.g., missing information, handwritten notes).
    *   Optimize for accuracy in extracting names, addresses, amounts, check numbers, dates, and donation designations/memos.
*   **Output:** Expect structured JSON output matching the defined schema. Implement validation for the received JSON.

**6. Data Model / Structure:**

*   Define a consistent data structure (e.g., a list of Python dictionaries or JavaScript objects) for donation records.
*   Each record should contain fields corresponding to the headers in `FOM_deposit_report_header_descriptions_2025-04-12.md`.
*   Include internal fields:
    *   `internalId`: A unique ID for the record within the app session.
    *   `dataSource`: ('LLM', 'CSV').
    *   `qbSyncStatus`: ('Pending', 'Sent', 'Error').
    *   `qbCustomerStatus`: ('Unknown', 'Matched', 'Matched-AddressMismatch', 'New').
    *   `qboCustomerId`: (Store the QBO Customer ID once matched/created).
    *   `qboSalesReceiptId`: (Store the QBO Sales Receipt ID once created).

**7. Technical Stack Suggestions:**

*   **Backend:** Python (Flask/Django) or Node.js (Express). Python is often preferred for ML/LLM integrations.
*   **Frontend:** Plain HTML/CSS/JavaScript, or a simple framework like React, Vue, or HTMX.
*   **LLM API:** Google AI SDK/Client Library for Gemini.
*   **QBO API:** QuickBooks Online Python SDK or Node.js SDK (or direct REST API calls with an OAuth2 library).
*   **Libraries:**
    *   CSV parsing (e.g., Python `csv`, Node `csv-parser`).
    *   HTTP requests (e.g., Python `requests`, Node `axios`).
    *   (Potentially) PDF/Image processing if needed before LLM (e.g., `Pillow`, `PyMuPDF` in Python; `pdfjs`, `sharp` in Node). Check if Gemini API handles file types directly first.
*   **Database (for Heroku):** Start with in-memory/local storage. For Heroku, consider Heroku Postgres (free tier available) or another suitable database if persistence beyond a single session is needed long-term (though not strictly required by the initial spec).

**8. Deployment Plan:**

*   **Phase 1: Localhost Development:**
    *   Build and test all features on the local machine.
    *   Use dummy data or safe sandbox credentials for QBO testing initially.
    *   Store API keys and secrets securely (e.g., environment variables, `.env` file).
*   **Phase 2: Heroku Deployment:**
    *   Prepare the application for Heroku (Procfile, requirements.txt/package.json).
    *   Configure Heroku environment variables for API keys (Gemini, QBO), QBO OAuth credentials, and any other necessary configurations.
    *   Set up QBO OAuth Redirect URI for the Heroku app domain.
    *   Deploy and test thoroughly on Heroku.

**9. Non-Functional Requirements:**

*   **Error Handling:** Implement user-friendly error messages for file upload issues, LLM processing errors, QBO API errors, data validation failures.
*   **Security:** Securely handle API keys and QBO OAuth tokens. Do not expose sensitive credentials in client-side code. Sanitize user inputs if applicable (though most inputs come from extraction/parsing).
*   **Usability:** Ensure the interface is intuitive for non-technical users at FoM.

**10. Provided Assets:**

*   `FOM Deposit Assistant Prompt 2025-04-12.md`: Base prompt for LLM extraction (review and revise as needed).
*   `FOM_deposit_report_header_descriptions_2025-04-12.md`: Defines the required data fields and table structure.
*   Example Reports: (Assume these are accessible) Use these to define the structure and content of the "Generate Report" feature output.

**11. Future Considerations (Optional):**

*   User authentication/accounts for different FoM users.
*   Persistent storage of processed batches in a database.
*   More sophisticated reporting options (filtering, date ranges).
*   Direct integration with online donation platforms if CSV import becomes cumbersome.
*   Batch editing capabilities in the table.