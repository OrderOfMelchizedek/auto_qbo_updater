# Friends of Mwangaza Donation Processor

A web application to process donation information for Friends of Mwangaza, including LLM-based data extraction and QuickBooks Online integration.

## Features

- Upload and process donation documents (images, PDFs)
- Extract donation information using Google's Gemini 2.5 Pro LLM
- Parse online donation reports (CSV)
- Display and edit donation data
- QuickBooks Online integration for customer management and sales receipt creation
- Generate donation reports

## Project Structure

```
fom_to_qbo_automation/
├── src/                    # Application source code
│   ├── app.py             # Main Flask application (541 lines)
│   ├── config/            # Configuration modules
│   │   ├── logging_config.py
│   │   └── session_config.py
│   ├── routes/            # Flask blueprints (modular routing)
│   │   ├── auth.py        # QBO authentication routes
│   │   ├── donations.py   # Donation CRUD operations
│   │   ├── files.py       # File upload and processing
│   │   ├── health.py      # Health checks and monitoring
│   │   └── qbo.py         # QuickBooks integration routes
│   ├── services/          # Business logic services
│   │   ├── deduplication.py  # Donation deduplication
│   │   └── validation.py     # Data validation
│   ├── utils/             # Utility modules
│   │   ├── file_processor.py    # File processing
│   │   ├── gemini_service.py    # Gemini AI integration
│   │   ├── qbo_service.py       # QuickBooks API
│   │   └── ...                  # Other utilities
│   ├── static/            # Frontend assets
│   └── templates/         # HTML templates
├── tests/                  # Test suites
│   ├── unit/              # Unit tests
│   │   ├── test_*_routes.py    # Blueprint tests
│   │   ├── test_validation.py  # Service tests
│   │   └── test_deduplication.py
│   ├── integration/       # Integration tests
│   └── e2e/               # End-to-end tests
├── scripts/                # Utility scripts
│   ├── monitoring/        # Log monitoring scripts
│   └── utils/             # Other utilities
├── docs/                   # Documentation
│   ├── architecture/      # Architecture docs
│   │   ├── MODULARIZATION_PLAN.md
│   │   └── MODULAR_STRUCTURE.md
│   ├── deployment/        # Deployment guides
│   ├── development/       # Development guides
│   └── api/               # API documentation
├── requirements/           # Dependency files
│   ├── base.txt          # Core dependencies
│   ├── dev.txt           # Development dependencies
│   ├── prod.txt          # Production dependencies
│   └── test.txt          # Testing dependencies
└── Makefile               # Common commands

## Setup

1. Clone this repository
2. Create a virtual environment:
   ```
   python -m venv venv
   ```
3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`
4. Install dependencies:
   ```
   # Production dependencies
   make install

   # Development dependencies (includes testing tools)
   make install-dev
   ```
5. Copy `.env.example` to `.env` and add your API keys:
   ```
   make setup
   ```
   Then edit `.env` with your credentials:
   - Generate a Flask secret key: `python -c 'import secrets; print(secrets.token_hex(32))'`
   - Add your QuickBooks Online credentials from [Intuit Developer Portal](https://developer.intuit.com/)
   - Add your Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
6. Run the application:
   ```
   # Run with default settings (Sandbox QBO, Gemini Flash model)
   make run

   # Or use the Python script directly:
   python src/run.py

   # Run with Gemini Pro model (better quality but slower)
   python src/run.py --model gemini-pro

   # Run with Production environment
   python src/run.py --env production

   # Full model names can also be used
   python src/run.py --model gemini-2.5-flash-preview-05-20
   python src/run.py --model gemini-2.5-pro-preview-05-06
   ```

## QuickBooks Online Integration

This application can connect to either QuickBooks Sandbox or Production environments. Use the `--env` flag when starting the application to choose your environment.

**Note**: When switching between environments, you need to re-authenticate, as each environment has different authentication tokens and company data.

This application uses OAuth 2.0 to authenticate with QuickBooks Online. You'll need to:

1. Create a developer account at [Intuit Developer](https://developer.intuit.com/)
2. Create an app and get your Client ID and Client Secret
3. Set the redirect URI to `http://localhost:5000/qbo/callback` for local development
4. Add your Client ID and Client Secret to the `.env` file

## Google Gemini API Integration

To use the Gemini API for donation document processing:

1. Create a Google Cloud project
2. Enable the Generative Language API
3. Create an API key
4. Add your API key to the `.env` file

## Project Structure

- `/src` - Application source code
- `/docs` - Documentation and reference materials
  - `/docs/project_specs` - Project specifications and requirements
  - `/docs/prompts_archive` - AI prompt templates for data extraction
- `/vendor` - Third-party libraries and dependencies
- `/tests` - Test suite
- `/uploads` - Temporary storage for uploaded files (auto-created)

## Development

### Backend Development

- Run tests:
  ```
  pytest
  ```
- Format code:
  ```
  black src tests
  ```

### Frontend Development & Testing

This project includes a comprehensive JavaScript test suite for frontend functionality.

#### Setup Frontend Testing

1. Install Node.js 16+ and npm 8+
2. Run the setup script:
   ```bash
   ./scripts/setup-frontend-tests.sh
   ```

#### Available Commands

```bash
# Lint JavaScript files
npm run lint:js
npm run lint:js:fix          # Auto-fix issues

# Run frontend tests
npm run test:frontend        # Run all frontend tests
npm run test:frontend:coverage # Run with coverage report
npm run test:frontend:watch  # Watch mode for development

# Run tests directly in the frontend directory
cd tests/frontend
npm test                     # Run all tests
npm test -- --watch         # Watch mode
npm test -- --coverage      # Coverage report
```

#### Frontend Test Coverage

The frontend test suite includes:

- **Utility Functions**: CSRF handling, fetch wrappers, formatting
- **V3 Data Compatibility**: Enriched format validation, field mapping
- **QBO Integration**: Customer management, sales receipt processing
- **File Upload**: Complete upload workflow with progress tracking
- **UI Components**: Modals, forms, progress displays
- **Error Handling**: Network failures, edge cases, security
- **End-to-End**: Complete user workflows and integration scenarios

#### Pre-commit Integration

Frontend tests are automatically run by pre-commit hooks:

- **On commit**: Quick tests for changed JavaScript files
- **On push**: Full test suite with coverage validation

### Code Quality

The project uses pre-commit hooks to ensure code quality:

```bash
# Install pre-commit hooks
pre-commit install

# Run all checks manually
pre-commit run --all-files
```

Quality checks include:
- **Python**: Black formatting, isort, flake8 linting, bandit security
- **JavaScript**: ESLint linting with auto-fix
- **Tests**: Backend pytest + Frontend Jest
- **General**: Trailing whitespace, file endings, YAML/JSON validation

## Deployment to Heroku

1. Create a Heroku account and install the Heroku CLI
2. Create a new Heroku app:
   ```
   heroku create fom-donation-processor
   ```
3. Set up environment variables:
   ```
   heroku config:set QBO_CLIENT_ID=your_client_id
   heroku config:set QBO_CLIENT_SECRET=your_client_secret
   heroku config:set QBO_REDIRECT_URI=https://your-app-name.herokuapp.com/qbo/callback
   heroku config:set QBO_ENVIRONMENT=sandbox
   heroku config:set GEMINI_API_KEY=your_gemini_api_key
   ```
   Note: For Heroku deployment, you'll need to modify the app to accept the environment from config vars instead of command-line arguments.
4. Push to Heroku:
   ```
   git push heroku master
   ```
