#!/bin/bash

echo "Starting QuickBooks Donation Manager..."

# Kill any existing processes on ports 5000 and 3000
echo "Cleaning up existing processes..."
lsof -ti:5000 | xargs kill -9 2>/dev/null
lsof -ti:3000 | xargs kill -9 2>/dev/null

# Start Flask backend
echo "Starting Flask backend on port 5000..."
cd /Users/svaug/dev/svl_apps/fom_to_qbo_automation
python -m src.app &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Start React frontend
echo "Starting React frontend on port 3000..."
cd /Users/svaug/dev/svl_apps/fom_to_qbo_automation/frontend
npm start &
FRONTEND_PID=$!

echo ""
echo "================================"
echo "Application is starting up..."
echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo ""
echo "Backend API: http://localhost:5000"
echo "Frontend UI: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop both servers"
echo "================================"

# Keep script running
wait
