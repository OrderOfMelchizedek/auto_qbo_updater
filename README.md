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
│   ├── app.py             # Main Flask application
│   ├── config/            # Configuration modules
│   ├── utils/             # Utility modules
│   ├── static/            # Frontend assets
│   └── templates/         # HTML templates
├── tests/                  # Test suites
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── e2e/               # End-to-end tests
├── scripts/                # Utility scripts
│   ├── monitoring/        # Log monitoring scripts
│   └── utils/             # Other utilities
├── docs/                   # Documentation
│   ├── architecture/      # Architecture docs
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

- Run tests:
  ```
  pytest
  ```
- Format code:
  ```
  black src tests
  ```

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