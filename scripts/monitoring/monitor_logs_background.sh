#!/bin/bash

# Configuration
APP_NAME="auto-qbo-updater"
LOG_FILE="logs/heroku_continuous.log"

# Create logs directory if it doesn't exist
mkdir -p logs

# Print start message
echo "Starting background log monitoring for $APP_NAME"
echo "Logs will be appended to: $LOG_FILE"
echo "Run 'tail -f $LOG_FILE' in another terminal to watch logs"
echo "Process will run in background. Find PID in logs/monitor.pid"
echo "To stop: kill \$(cat logs/monitor.pid)"
echo "----------------------------------------"

# Start logging in background
nohup heroku logs --app=$APP_NAME --tail >> "$LOG_FILE" 2>&1 &
echo $! > logs/monitor.pid

echo "Log monitoring started with PID: $(cat logs/monitor.pid)"
