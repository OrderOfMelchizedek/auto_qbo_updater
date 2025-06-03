# Product Requirements
The product requirement document is found in '/Users/svaug/dev/svl_apps/fom_to_qbo_automation/docs/product requirement doc/quickbooks-donation-manager-prd.md'. Refer to this to understand the full specification of the project. Update this as required or requested by the user.

# Development Methodology
Follow the 12-Factor App principles where applicable (reference: 'docs/12factor-reference') and Test-Driven Development:
- Write failing tests first
- Implement code to pass tests
- Refactor while keeping tests green

# Project Structure
```
fom_to_qbo_automation/
├── src/
│   ├── api/               # FastAPI routes and endpoints
│   ├── services/          # Business logic (extraction, deduplication, QB sync)
│   ├── models/            # Pydantic models and data structures
│   ├── workers/           # Celery tasks
│   ├── utils/             # Shared utilities
│   ├── config/            # Configuration and settings
│   └── tests/
│       ├── unit/          # Mock external services, 80% coverage minimum
│       ├── integration/   # Test API endpoints and Celery tasks
│       └── e2e/           # Full workflow tests
├── lib/
│   └── prompts/
│       ├── current/       # Active Gemini prompts (never hardcode)
│       └── old/           # Archived prompts
├── static/                # React build output
├── templates/             # Letter templates (Jinja2)
└── docs/
```

# Python Standards
- Follow PEP 8, use Black (88 char limit), type hints, and Google-style docstrings
- Use python-dotenv for env vars (document in .env.example, never commit .env)
- Use Pydantic Settings for type-safe configuration

# Core Business Logic

## Deduplication
- **Key**: (check_number, amount) - both must match
- **Implementation**: Use pandas DataFrame for efficiency
- **Merge Strategy**: Keep most complete data, combine aliases, use earliest date
- **Audit**: Store all source document references, log merge decisions

## Data Validation
- **Check numbers**: Strip leading zeros if length > 4
- **Amounts**: Positive numbers, max 2 decimal places
- **Dates**: Valid format, not future dated
- **Emails**: Validate format before QuickBooks sync
- **ZIP codes**: Preserve leading zeros, validate 5 or 9 digits

# External APIs

## Gemini API ('docs/gemini api docs')
- Include structured output schema in all requests
- Process images at max 4096x4096 resolution
- Implement retry with exponential backoff
- Return confidence scores with extractions

## QuickBooks API ('docs/quickbooks')
- Check customer existence before creation
- Cache OAuth tokens with refresh logic
- Implement exponential backoff for rate limits
- Handle maintenance windows gracefully

# Error Handling & Logging

## Exception Hierarchy
```python
class DonationProcessingError(Exception): pass
class GeminiExtractionError(DonationProcessingError): pass
class QuickBooksIntegrationError(DonationProcessingError): pass
```

## Logging Standards
- **ERROR**: API failures, processing errors
- **WARNING**: Retryable errors, data quality issues
- **INFO**: Successful operations, milestones
- **DEBUG**: Detailed payloads (never log sensitive data)
- Include correlation IDs for request tracking

# Security & Performance
- Validate file uploads (type, size, content), sanitize filenames
- Implement rate limiting, JWT tokens expire in 24 hours
- Cache QuickBooks lookups and extraction results in Redis
- Limit concurrent Gemini calls to 5
- Implement progress tracking for long operations

# Development Workflow

## Git Conventions
- Branches: `feature/description`, `bugfix/description`
- Commits: Follow conventional commits format
- PRs require: passing tests, code review, updated docs

## CI/CD Pipeline
1. **Pre-commit hooks**: flake8, Black, isort, run all tests
2. **Deployment**:
   - Update version in pyproject.toml
   - Deploy to staging → smoke test → production
   - Monitor logs for 30 minutes post-deploy

## Monitoring
- Health endpoint at `/health`
- Use Sentry for error tracking
- Alert thresholds: >5% error rate, >30s processing, failed QB syncs

# Development Principles
- Don't disable aspects of CI/CD or testing workflows just to commit unless I specifically ask you to.
