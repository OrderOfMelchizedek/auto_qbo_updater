# Product Requirements Document: QuickBooks Donation Manager

**Version:** 1.0
**Date:** June 3, 2025
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

## 3. Success Metrics

### Primary KPIs
- **Time Reduction:** 80% decrease in average processing time per donation
- **Accuracy Rate:** 95%+ accurate data extraction from clear documents
- **User Adoption:** 70% of users process >10 donations in first month
- **Customer Satisfaction:** Net Promoter Score (NPS) > 50

### Secondary Metrics
- **Processing Speed:** <30 seconds for 20-document batch
- **Match Rate:** 85%+ automatic donor matching in QuickBooks
- **Error Reduction:** 90% fewer data entry errors vs. manual process
- **Support Tickets:** <5% of processing sessions require support

### Measurement Methods
- In-app analytics for processing times and volumes
- Post-processing accuracy surveys
- Monthly user satisfaction surveys
- QuickBooks API response monitoring

---

## 4. Functional Requirements

### 4.1 Document Upload & Processing

**User Story:** As a treasurer, I want to upload multiple donation documents at once so I can process an entire week's donations in one session.

**Acceptance Criteria:**
- System accepts up to 20 files per batch
- Supported formats: JPEG, PNG, PDF, CSV
- File size limit: 20MB per file
- Drag-and-drop interface with progress indicators
- Clear error messages for unsupported formats

**User Story:** As a user, I want the system to automatically extract donation information so I don't have to type it manually.

**Acceptance Criteria:**
- AI extraction completes within 2 seconds per document
- Each image/PDF page processed independently and concurrently
- Extracted data follows defined JSON schema
- Confidence scores displayed for each field
- Document type auto-detection with manual override option

**User Story:** As a treasurer, I want duplicate donations automatically merged so I don't create duplicate entries in QuickBooks.

**Acceptance Criteria:**
- System identifies duplicates using check/payment number + amount as key
- When duplicates found, all data merged into single entry
- Merge preserves most complete information from all sources
- User notified of merged entries with source documents listed
- Deduplication occurs before QuickBooks matching

### 4.2 QuickBooks Integration

**User Story:** As a treasurer, I want donations automatically matched to existing donors so I maintain clean records.

**Acceptance Criteria:**
- OAuth 2.0 authentication with QuickBooks Online
- Fuzzy matching algorithm for donor names
- Match confidence displayed (High/Medium/Low)
- Manual match option for unmatched donors
- New customer creation when no match exists

**User Story:** As a bookkeeper, I want smart address updating so I don't overwrite good data with partial information.

**Acceptance Criteria:**
- Address updates only when >50% character difference
- Email/phone appended to existing lists
- Change preview before committing to QuickBooks
- Rollback capability for batch operations

### 4.3 Data Validation & Editing

**User Story:** As a user, I want to review and edit extracted data before sending to QuickBooks.

**Acceptance Criteria:**
- Editable table with all extracted fields
- Merged entries clearly marked with source count
- Inline editing with validation
- Bulk edit capabilities
- Validation rules (e.g., check number format)
- Visual indicators for required fields
- Ability to view/unmerge duplicate entries

### 4.4 Letter Generation

**User Story:** As a treasurer, I want to generate professional tax receipt letters for donors.

**Acceptance Criteria:**
- Customizable letter templates
- Merge fields for donor data
- IRS-compliant disclaimer included
- Batch PDF generation
- Print-ready formatting

---

## 5. Technical Architecture

### High-Level Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│   Web Browser   │────▶│  Load Balancer  │────▶│   Web Server    │
│   (React SPA)   │     │    (Heroku)     │     │   (Python/      │
│                 │     │                 │     │    FastAPI)     │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                          │
                                                          ▼
                                                ┌─────────────────┐
                                                │                 │
                                                │   Redis Cache   │
                                                │ (Sessions/Celery│
                                                │     Broker)     │
                                                └────────┬────────┘
                                                          │
                                                          ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  Google Gemini  │     │   QuickBooks    │     │    Amazon S3    │
│      API        │     │   Online API    │     │    Storage      │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Technology Stack

**Frontend:**
- React 18.x with TypeScript
- Material-UI component library
- React Query for API state management
- React Hook Form for form handling

**Backend:**
- Python 3.11+ with FastAPI
- Pydantic for data validation
- Celery with Redis broker for concurrent job processing
- authlib for OAuth authentication
- Deduplication service for merging extracted entries

**Key Python Libraries:**
- `python-quickbooks` - QuickBooks API integration
- `google-generativeai` - Official Gemini SDK
- `boto3` - AWS S3 integration
- `pdf2image` - PDF to image conversion
- `Pillow` - Image processing
- `aiohttp` - Async HTTP requests
- `pandas` - CSV processing and data manipulation
- `jinja2` - Letter template rendering
- `weasyprint` - PDF generation from HTML
- `redis` - Redis client for sessions/caching
- `python-multipart` - File upload handling

**Infrastructure:**
- Heroku (12-factor app principles)
- Python buildpack with uvicorn ASGI server
- Redis for session management and Celery broker
- Amazon S3 for document storage

**Third-Party Services:**
- Google Gemini API for AI extraction
- QuickBooks Online API

### Python-Specific Architecture Benefits

**Async Processing:**
- FastAPI's native async support for handling concurrent requests
- Celery workers for parallel document processing
- asyncio for efficient API calls to external services

**Data Processing:**
- pandas for efficient deduplication operations
- Native JSON handling for Gemini API responses
- Strong typing with Pydantic models

**Deployment:**
- Simple Heroku deployment with `requirements.txt` and `Procfile`
- Automatic API documentation at `/docs` endpoint
- Built-in request validation and serialization

---

## 6. API Specifications

### 6.1 Google Gemini API Integration

**Endpoint:** `https://generativelanguage.googleapis.com/v1beta/models/gemini-pro-vision:generateContent`

**Request Structure:**
```json
{
  "contents": [{
    "parts": [
      {
        "text": "Extract donation information from this document following the schema..."
      },
      {
        "inline_data": {
          "mime_type": "image/jpeg",
          "data": "base64_encoded_image"
        }
      }
    ]
  }],
  "generationConfig": {
    "response_mime_type": "application/json",
    "response_schema": {
      "type": "object",
      "properties": {
        "payment_info": {...},
        "payer_info": {...},
        "contact_info": {...}
      }
    }
  }
}
```

### 6.2 QuickBooks Online API

**Authentication:** OAuth 2.0 flow
**Base URL:** `https://api.intuit.com/v3/company/{companyId}`

**Key Endpoints:**
- `GET /query?query=select * from Customer` - Search customers
- `POST /customer` - Create new customer
- `POST /salesreceipt` - Create donation receipt
- `PUT /customer/{id}` - Update customer info

### 6.3 Internal REST API

**Framework:** FastAPI with automatic OpenAPI/Swagger documentation
**Authentication:** JWT tokens with Redis session store

**FastAPI Endpoints:**
```python
POST   /api/auth/quickbooks         # Initiate QB OAuth
GET    /api/auth/callback          # OAuth callback handler
POST   /api/documents/upload       # Upload documents
POST   /api/documents/extract      # Process with Gemini (async)
POST   /api/documents/deduplicate  # Merge duplicate entries
GET    /api/donations              # Get processed donations
PUT    /api/donations/{id}         # Update donation data
POST   /api/donations/match        # Match to QB customer
POST   /api/donations/sync         # Send to QuickBooks
POST   /api/letters/generate       # Generate receipt letters
GET    /api/ws/processing-status   # WebSocket for real-time updates
```

**Example FastAPI Implementation:**
```python
from fastapi import FastAPI, UploadFile, File
from typing import List

app = FastAPI()

@app.post("/api/documents/upload")
async def upload_documents(files: List[UploadFile] = File(...)):
    # Process uploaded files
    # Queue Celery tasks for extraction
    return {"status": "processing", "file_count": len(files)}
```

---

## 7. Data Flow Diagrams

### Document Processing Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Upload    │────▶│   Convert   │────▶│  Extract    │────▶│ Deduplicate │
│  Documents  │     │  to Images  │     │ with AI     │     │   Entries   │
└─────────────┘     └─────────────┘     │ (Concurrent)│     └─────────────┘
                                        └─────────────┘            │
                                                                   ▼
                    ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
                    │   Generate  │◀────│    Match    │◀────│  Validate   │
                    │   Letters   │     │   Donors    │     │    Data     │
                    └─────────────┘     └─────────────┘     └─────────────┘
                                               │                   ▲
                                               ▼                   │
                                        ┌─────────────┐     ┌─────────────┐
                                        │   Send to   │     │    Edit     │
                                        │ QuickBooks  │────▶│    Data     │
                                        └─────────────┘     └─────────────┘
```

### Extraction Rules by Document Type

**Checks:**
- Payment Date = Check Date (if visible) or Deposit Date
- Amount from numeric box
- Check number stripped of leading zeros if >4 digits

**Envelopes:**
- Return address as authoritative donor address
- Postmark date for payment date

**Online Donations:**
- Payment reference required
- Email/transaction ID as matching key

**CSV Files:**
- Flexible column mapping
- Header row detection
- Date format auto-detection

### Deduplication Logic

**Concurrent Processing:**
- Each image/PDF page processed independently by Gemini API
- Celery workers handle parallel processing for faster batch completion
- Results aggregated in Redis before deduplication

**Deduplication Rules:**
- **Primary Key:** Check/Payment Number + Amount (both must match)
- **Merge Strategy:** When duplicates detected:
  - Preserve most complete donor name
  - Keep longest address information
  - Combine all aliases into single list
  - Use earliest payment date found
  - List all source documents for audit trail
- **User Notification:** Display merged entries with indicator showing source count
- **Manual Override:** Allow users to unmerge if needed

---

## 8. UI Wireframes & User Flows

### Main Dashboard

```
┌─────────────────────────────────────────────────────────────────┐
│  QuickBooks Donation Manager            [User Name] │ Sign Out  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────┐     │
│  │                                                       │     │
│  │         Drag & Drop Documents Here                    │     │
│  │              or Click to Browse                       │     │
│  │                                                       │     │
│  │         ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐            │     │
│  │         │ PDF │ │ JPG │ │ PNG │ │ CSV │            │     │
│  │         └─────┘ └─────┘ └─────┘ └─────┘            │     │
│  │                                                       │     │
│  └───────────────────────────────────────────────────────┘     │
│                                                                 │
│  Processing Status: [████████░░░░░░░░] 8/20 documents          │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Donor Name │ Amount │ Date │ Check # │ Status │ Actions │   │
│  ├───────────┼────────┼──────┼─────────┼────────┼─────────┤   │
│  │ J. Smith  │ $100   │ 5/1  │ 1234    │ Matched│ [···]   │   │
│  │ ABC Corp  │ $500   │ 5/2  │ -       │ New    │ [···]   │   │
│  │ M. Jones  │ $50    │ 5/3  │ 5678    │ No Match│ [···]  │   │
│  │ T. Wilson │ $250   │ 5/4  │ 9012    │Merged(2)│ [···]  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  [Send All to QuickBooks] [Generate All Letters]               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Manual Match Modal

```
┌─────────────────────────────────────────────────────────┐
│                 Match Donor                             │
│                                                         │
│  Extracted: "M. Jones"                                  │
│                                                         │
│  Possible Matches:                                      │
│  ○ Mary Jones (mary@email.com)                        │
│  ○ Michael Jones (123 Main St)                        │
│  ○ M&J Jones Family Trust                             │
│  ○ Create New Customer                                │
│                                                         │
│  [Cancel]                              [Match Selected] │
└─────────────────────────────────────────────────────────┘
```

---

## 9. Security & Compliance Considerations

### Data Security
- **Encryption:** TLS 1.3 for all API communications
- **Storage:** AES-256 encryption for documents at rest in S3
- **Authentication:** OAuth 2.0 for QuickBooks, JWT for sessions
- **Authorization:** Role-based access via QuickBooks permissions

### Compliance Requirements
- **PCI DSS:** Not applicable (no credit card processing)
- **IRS Requirements:** Include required disclaimer on tax receipts
- **Data Retention:** Documents purged after 30 days
- **Privacy:** GDPR-compliant data handling and deletion

### Security Best Practices
- Input validation on all user data
- XSS protection through React's built-in escaping
- Rate limiting on API endpoints
- Security headers (HSTS, CSP, X-Frame-Options)

---

## 10. Implementation Schedule

### MVP (Phase 1) - 3 months

**Core Features:**
- Document upload and AI extraction with concurrent processing
- Deduplication of extracted entries
- QuickBooks customer matching and creation
- Basic letter generation
- Single organization support

**Technical Implementation:**
- **Infrastructure Setup**
  - Development environment configuration with Python 3.11+
  - Heroku deployment pipeline with Python buildpack
  - Redis configuration for session management and Celery broker
  - S3 bucket setup for document storage
  - OAuth 2.0 authentication framework with authlib

- **Document Processing Engine**
  - Multi-file upload interface (up to 20 files, 20MB each)
  - PDF to image conversion with pdf2image
  - Google Gemini API integration with structured outputs
  - Concurrent extraction processing using Celery workers
  - Deduplication service implementation with pandas

- **QuickBooks Integration**
  - OAuth flow implementation using authlib
  - Customer search and fuzzy matching algorithms
  - Smart data synchronization logic with python-quickbooks
  - Error handling and retry mechanisms

- **User Interface**
  - React SPA with Material-UI components
  - FastAPI REST endpoints with automatic OpenAPI documentation
  - WebSocket support for real-time processing updates
  - Batch operations interface

- **Letter Generation**
  - Jinja2 template engine integration
  - PDF generation with weasyprint
  - Batch processing capabilities
  - Print-optimized formatting

**Deliverables:**
- Fully functional web application
- API documentation
- User guide and video tutorials
- 2-week post-launch stabilization

### Phase 2 - Enhanced Features (Months 4-6)
- Multi-organization support
- Custom letter templates with template library
- Batch scheduling and automation
- Advanced matching rules and confidence scoring
- Audit trail and comprehensive reporting
- Performance optimizations for larger batches

### Phase 3 - Advanced Capabilities (Months 7-9)
- Mobile native apps (iOS/Android)
- Recurring donation detection and tracking
- Pledge management system
- Campaign attribution and tagging
- Advanced analytics dashboard
- Bulk operations and data export

### Future Considerations
- Integration with other accounting systems (Xero, Wave)
- Direct bank deposit reconciliation
- Donor portal for self-service updates
- AI-powered donor insights and giving predictions
- Automated thank you communications
- Grant management capabilities

---

## 11. Risks & Mitigation Strategies

### Technical Risks

**Risk:** Google Gemini API changes or deprecation
- **Mitigation:** Abstract extraction logic; implement provider-agnostic interface for potential AI service switching

**Risk:** QuickBooks API rate limits
- **Mitigation:** Implement request queuing and caching

**Risk:** Large file processing delays
- **Mitigation:** Async processing with progress indicators

**Risk:** Incorrect deduplication merging valid separate donations
- **Mitigation:** Conservative matching (exact check # + amount), manual unmerge option

### Business Risks

**Risk:** Low user adoption due to complexity
- **Mitigation:** Onboarding wizard and video tutorials

**Risk:** Inaccurate AI extraction
- **Mitigation:** Confidence scoring and manual review workflow

**Risk:** Security breach of donor data
- **Mitigation:** Regular security audits and minimal data retention

### Operational Risks

**Risk:** Support burden exceeds capacity
- **Mitigation:** Comprehensive documentation and self-service resources

**Risk:** Scaling issues with growing user base
- **Mitigation:** Horizontal scaling architecture from day one

---

## Appendices

### A. Detailed JSON Schema for Extraction

```json
{
  "payment_info": {
    "payment_method": {
      "type": "string",
      "enum": ["check", "cash", "online", "other"],
      "required": true
    },
    "check_no": {
      "type": "string",
      "required_if": "payment_method == check"
    },
    "payment_ref": {
      "type": "string",
      "required_if": "payment_method == online"
    },
    "amount": {
      "type": "number",
      "required": true
    },
    "payment_date": {
      "type": "string",
      "format": "date",
      "required": true
    },
    "check_date": {
      "type": "string",
      "format": "date"
    },
    "postmark_date": {
      "type": "string",
      "format": "date"
    },
    "deposit_date": {
      "type": "string",
      "format": "date"
    },
    "deposit_method": {
      "type": "string"
    },
    "memo": {
      "type": "string"
    }
  },
  "payer_info": {
    "aliases": {
      "type": "array",
      "items": { "type": "string" },
      "required_if": "!organization_name"
    },
    "salutation": {
      "type": "string"
    },
    "organization_name": {
      "type": "string",
      "required_if": "is_organization"
    }
  },
  "contact_info": {
    "address_line_1": {
      "type": "string"
    },
    "city": {
      "type": "string"
    },
    "state": {
      "type": "string",
      "pattern": "^[A-Z]{2}$"
    },
    "zip": {
      "type": "string",
      "pattern": "^\\d{5}(-\\d{4})?$"
    },
    "email": {
      "type": "string",
      "format": "email"
    },
    "phone": {
      "type": "string"
    }
  }
}
```

### B. Sample Letter Template

```
[Organization Letterhead]

[Date]

[Donor Name]
[Address Line 1]
[City, State ZIP]

Dear [Salutation] [Last Name],

Thank you for your generous donation of $[Amount] to [Organization Name], received on [Payment Date].

[If check: Your check #[Check No] has been processed and deposited.]

Your support helps us [mission statement/impact].

For tax purposes, please retain this letter as your official receipt. No goods or services were provided in exchange for this contribution.

[Organization Name] is a 501(c)(3) tax-exempt organization. Our Federal Tax ID is [EIN].

With gratitude,

[Signature]
[Treasurer Name]
[Title]
```

### C. Performance Benchmarks

- Document upload: <2 seconds per file
- AI extraction: <2 seconds per document (concurrent processing)
- Deduplication: <1 second for 20 documents
- QuickBooks API calls: <500ms average
- Letter generation: <1 second per letter
- Full batch processing: <30 seconds for 20 documents (including deduplication)

### D. Heroku Deployment Configuration

**Procfile:**
```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
worker: celery -A app.celery worker --loglevel=info
beat: celery -A app.celery beat --loglevel=info
```

**requirements.txt (key dependencies):**
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
celery[redis]==5.3.4
python-quickbooks==0.9.1
google-generativeai==0.3.0
boto3==1.29.7
pdf2image==1.16.3
Pillow==10.1.0
aiohttp==3.9.1
pandas==2.1.3
jinja2==3.1.2
weasyprint==60.1
redis==5.0.1
python-multipart==0.0.6
authlib==1.2.1
python-jose[cryptography]==3.3.0
pydantic==2.5.0
```

---

**Document End**
