#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting development servers...${NC}"
echo "================================"

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Stopping servers...${NC}"
    if [ ! -z "$BACKEND_PID" ]; then
        kill -TERM $BACKEND_PID 2>/dev/null
        echo "Backend stopped"
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill -TERM $FRONTEND_PID 2>/dev/null
        echo "Frontend stopped"
    fi

    # Check for any lingering Celery workers (in case someone used wrong script)
    if pgrep -f "celery.*worker" > /dev/null; then
        echo -e "${YELLOW}Note: Celery workers are still running.${NC}"
        echo "To stop them, run: pkill -f 'celery.*worker'"
    fi

    exit 0
}

# Set trap for cleanup
trap cleanup INT TERM EXIT

# Start backend
echo -e "${YELLOW}Starting Flask backend on http://localhost:5000...${NC}"
python -m src.app > backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# Wait for backend to start
sleep 3

# Check if backend is running
if ! ps -p $BACKEND_PID > /dev/null; then
    echo -e "${RED}Backend failed to start! Check backend.log for errors.${NC}"
    exit 1
fi

# Start frontend
echo -e "${YELLOW}Starting React frontend on http://localhost:3000...${NC}"
cd frontend && npm start > ../frontend.log 2>&1 &
FRONTEND_PID=$!
echo "Frontend PID: $FRONTEND_PID"

echo "================================"
echo -e "${GREEN}Both servers are starting...${NC}"
echo "Logs are being written to:"
echo "  - backend.log"
echo "  - frontend.log"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop both servers${NC}"
echo "================================"

# Keep script running
while true; do
    sleep 1
done
