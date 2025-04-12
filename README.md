# Friends of Mwangaza Donation Processor

A web application to process donation information for Friends of Mwangaza, including LLM-based data extraction and QuickBooks Online integration.

## Features

- Upload and process donation documents (images, PDFs)
- Extract donation information using Google's Gemini 2.5 Pro LLM
- Parse online donation reports (CSV)
- Display and edit donation data
- QuickBooks Online integration for customer management and sales receipt creation
- Generate donation reports

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
   pip install -r requirements.txt
   ```
5. Set up the Intuit OAuth Library (included in the repo):
   ```
   python setup_oauth_lib.py
   ```
6. Copy `.env.example` to `.env` and add your API keys:
   ```
   cp .env.example .env
   ```
   Then edit `.env` with your QuickBooks Online and Gemini API credentials
7. Run the application:
   ```
   # Run with Sandbox environment (default)
   python src/app.py --env sandbox

   # Run with Production environment
   python src/app.py --env production
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