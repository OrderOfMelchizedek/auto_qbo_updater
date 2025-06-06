# QuickBooks Donation Manager

An automated system for processing donation documents and integrating with QuickBooks Online. This application uses Google's Gemini AI to extract donation information from various document formats and provides a user-friendly interface for managing donations.

## Features

- **Document Processing**: Upload and process multiple donation documents (JPEG, PNG, PDF, CSV)
- **AI-Powered Extraction**: Uses Google Gemini AI to intelligently extract donation information
- **Data Validation**: Automatic validation and deduplication of donation records
- **React Frontend**: Modern, responsive UI with drag-and-drop file upload
- **RESTful API**: Flask-based backend with comprehensive API endpoints
- **Production Ready**: Deployed on Heroku with proper static file serving

## Tech Stack

- **Backend**: Python Flask with Flask-CORS
- **Frontend**: React with TypeScript
- **AI/ML**: Google Gemini API for document processing
- **Storage**: Configurable storage backends (Local/S3)
- **Session Management**: Configurable session backends (Local/Redis)
- **Deployment**: Heroku with dual buildpacks (Python & Node.js)

## Project Structure

```
fom_to_qbo_automation/
├── frontend/               # React TypeScript frontend
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── services/      # API service layer
│   │   └── types/         # TypeScript type definitions
│   └── public/            # Static assets
├── src/                   # Python backend
│   ├── app.py            # Flask application
│   ├── config.py         # Configuration management
│   ├── donation_processor.py  # Core processing logic
│   ├── geminiservice.py  # Gemini AI integration
│   ├── storage.py        # Storage abstraction
│   ├── session.py        # Session management
│   └── lib/
│       └── prompts/      # AI prompt templates
├── scripts/              # Utility scripts
│   ├── run_local.sh      # Run backend locally
│   └── start_local.sh    # Run both frontend and backend
├── docs/                 # Documentation
└── requirements.txt      # Python dependencies
```

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Google Gemini API key

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd fom_to_qbo_automation
   ```

2. **Set up environment variables**
   ```bash
   # Create .env file
   cp .env.example .env
   # Add your Gemini API key
   echo "GEMINI_API_KEY=your-api-key-here" >> .env
   ```

3. **Install dependencies**
   ```bash
   # Backend dependencies
   pip install -r requirements.txt

   # Frontend dependencies
   cd frontend
   npm install
   cd ..
   ```

4. **Run locally**
   ```bash
   # Run both frontend and backend
   ./scripts/start_local.sh

   # Or run separately:
   # Backend only
   ./scripts/run_local.sh

   # Frontend only
   cd frontend && npm start
   ```

   - Frontend: http://localhost:3000
   - Backend API: http://localhost:5000/api/

## API Endpoints

- `GET /api/` - API information
- `GET /api/health` - Health check
- `POST /api/upload` - Upload donation documents
- `POST /api/process` - Process uploaded documents

## Deployment

The application is configured for Heroku deployment:

```bash
# Add Heroku remote
heroku git:remote -a your-app-name

# Deploy
git push heroku main
```

## Configuration

The application supports multiple configuration options:

- **Storage Backends**: Local filesystem or AWS S3
- **Session Backends**: Local files or Redis
- **Environment Variables**:
  - `GEMINI_API_KEY` - Required for AI document processing
  - `NODE_ENV` - Set to "production" for production deployments
  - `STORAGE_BACKEND` - "local" or "s3"
  - `SESSION_BACKEND` - "local" or "redis"

## Testing

```bash
# Run Python tests
python -m pytest src/tests/

# Run frontend tests
cd frontend && npm test
```

## Future Enhancements

- QuickBooks OAuth2 authentication integration
- Direct QuickBooks API integration for creating Sales Receipts
- Customer matching with QuickBooks Online
- Receipt letter generation
- User authentication system

## License

This project is proprietary software.
