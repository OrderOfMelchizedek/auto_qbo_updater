# Local Redis Setup for Development

## Quick Start

1. **Install Redis** (if not already installed):
   ```bash
   # macOS
   brew install redis

   # Ubuntu/Debian
   sudo apt-get install redis-server

   # Windows (using WSL)
   sudo apt-get install redis-server
   ```

2. **Start the development environment**:
   ```bash
   ./scripts/start-dev.sh
   ```

   This script will:
   - Check if Redis is running and start it if needed
   - Start the Celery worker for background processing
   - Start the Flask backend on http://localhost:5000
   - Start the React frontend on http://localhost:3000

3. **Stop all services**:
   Press `Ctrl+C` in the terminal where the script is running.

## Manual Setup (Alternative)

If you prefer to run services separately:

1. **Start Redis**:
   ```bash
   redis-server
   ```

2. **Start Celery Worker** (in a new terminal):
   ```bash
   celery -A src.celery_app worker --loglevel=info
   ```

3. **Start Flask Backend** (in a new terminal):
   ```bash
   python -m src.app
   ```

4. **Start React Frontend** (in a new terminal):
   ```bash
   cd frontend
   npm start
   ```

## Verification

To verify everything is working:

1. Check Redis is running:
   ```bash
   redis-cli ping
   # Should return: PONG
   ```

2. Check the API health endpoint:
   ```bash
   curl http://localhost:5000/api/health
   ```

3. Access the app at http://localhost:3000

## Troubleshooting

- **Redis won't start**: Check if another process is using port 6379
- **Celery errors**: Ensure Redis is running before starting Celery
- **Frontend can't connect**: Verify backend is running on port 5000

## Architecture

The app uses the same async processing architecture in both local and production:
- Redis queues background jobs
- Celery workers process the jobs
- Server-Sent Events (SSE) provide real-time updates
- No code differences between local and production environments
