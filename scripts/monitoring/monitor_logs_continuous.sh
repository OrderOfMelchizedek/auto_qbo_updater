#!/bin/bash

# Configuration
APP_NAME="auto-qbo-updater"
LOG_FILE="logs/heroku_continuous.log"

# Create logs directory if it doesn't exist
mkdir -p logs

# Print start message
echo "Starting continuous log monitoring for $APP_NAME"
echo "Logs will be appended to: $LOG_FILE"
echo "Press Ctrl+C to stop monitoring"
echo "----------------------------------------"

# Start tailing logs and append to file
# The --tail flag starts with recent logs, then streams new ones
# Using tee to both display on screen and write to file
heroku logs --app=$APP_NAME --tail | tee -a "$LOG_FILE"
