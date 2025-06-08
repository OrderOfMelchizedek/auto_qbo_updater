#!/bin/bash

# Start all services in development mode

echo "Starting development environment..."
echo "================================"

# Check if Redis is installed
if ! command -v redis-server &> /dev/null; then
    echo "❌ Redis is not installed!"
    echo ""
    echo "Please install Redis first:"
    echo "  macOS:    brew install redis"
    echo "  Ubuntu:   sudo apt-get install redis-server"
    echo ""
    echo "After installing, run this script again."
    exit 1
fi

# Check if Redis is running
echo "Checking Redis..."
if ! redis-cli ping > /dev/null 2>&1; then
    echo "Starting Redis server..."
    redis-server --daemonize yes
    sleep 2

    # Check again
    if ! redis-cli ping > /dev/null 2>&1; then
        echo "❌ Failed to start Redis"
        echo "Try starting it manually: redis-server"
        exit 1
    fi
fi
echo "✓ Redis is running"

# Load environment variables from .env file
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Start Celery worker in background
echo "Starting Celery worker..."
celery -A src.celery_app worker --loglevel=info > celery-worker.log 2>&1 &
CELERY_PID=$!
echo "✓ Celery worker started (PID: $CELERY_PID)"

# Start backend in background
echo "Starting Flask backend on http://localhost:5000..."
python -m src.app &
BACKEND_PID=$!
echo "✓ Backend started (PID: $BACKEND_PID)"

# Give backend a moment to start
sleep 2

# Start frontend
echo "Starting React frontend on http://localhost:3000..."
cd frontend && npm start &
FRONTEND_PID=$!
echo "✓ Frontend started (PID: $FRONTEND_PID)"

echo "================================"
echo "All services are running:"
echo "- Redis: localhost:6379"
echo "- Celery Worker"
echo "- Flask Backend: http://localhost:5000"
echo "- React Frontend: http://localhost:3000"
echo ""
echo "To stop all services, press Ctrl+C"
echo "================================"

# Function to cleanup all processes
cleanup() {
    echo ""
    echo "Stopping all services..."

    # Kill the main processes
    if [ ! -z "$CELERY_PID" ]; then
        echo "Stopping Celery worker (PID: $CELERY_PID)..."
        kill -TERM $CELERY_PID 2>/dev/null
        # Also kill any child processes
        pkill -P $CELERY_PID 2>/dev/null
    fi

    if [ ! -z "$BACKEND_PID" ]; then
        echo "Stopping Flask backend (PID: $BACKEND_PID)..."
        kill -TERM $BACKEND_PID 2>/dev/null
    fi

    if [ ! -z "$FRONTEND_PID" ]; then
        echo "Stopping React frontend (PID: $FRONTEND_PID)..."
        kill -TERM $FRONTEND_PID 2>/dev/null
    fi

    # Give processes time to shut down gracefully
    sleep 2

    # Force kill any remaining Celery workers
    if pgrep -f "celery.*worker" > /dev/null; then
        echo "Force stopping remaining Celery workers..."
        pkill -9 -f "celery.*worker"
    fi

    echo "All services stopped."
    exit 0
}

# Set trap for multiple signals
trap cleanup INT TERM EXIT

# Wait for processes
wait
