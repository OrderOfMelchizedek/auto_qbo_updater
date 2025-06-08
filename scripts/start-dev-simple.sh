#!/bin/bash

# Simple development server without Redis/Celery
# For testing when Redis is not available

echo "Starting simple development environment (no background processing)..."
echo "================================"
echo "⚠️  WARNING: Background processing disabled!"
echo "⚠️  Processing will happen synchronously"
echo "================================"

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
echo "Services running:"
echo "- Flask Backend: http://localhost:5000"
echo "- React Frontend: http://localhost:3000"
echo ""
echo "To stop all services, press Ctrl+C"
echo "================================"

# Wait for Ctrl+C
trap "echo 'Stopping all services...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT
wait
