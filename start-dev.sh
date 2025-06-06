#!/bin/bash

# Start both frontend and backend in development mode

echo "Starting development servers..."
echo "================================"

# Start backend in background
echo "Starting Flask backend on http://localhost:5000..."
python -m src.app &
BACKEND_PID=$!

# Give backend a moment to start
sleep 2

# Start frontend
echo "Starting React frontend on http://localhost:3000..."
cd frontend && npm start &
FRONTEND_PID=$!

echo "================================"
echo "Both servers are starting..."
echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo ""
echo "To stop both servers, press Ctrl+C"
echo "================================"

# Wait for Ctrl+C
trap "echo 'Stopping servers...'; kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
