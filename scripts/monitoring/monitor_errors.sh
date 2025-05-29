#!/bin/bash

# Configuration
APP_NAME="auto-qbo-updater"

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Print start message
echo "Starting error/warning monitoring for $APP_NAME"
echo "Displaying only ERROR and WARNING messages"
echo "Press Ctrl+C to stop monitoring"
echo "----------------------------------------"

# Stream logs and filter for errors/warnings
# Using grep with -E for extended regex to match multiple patterns
# --line-buffered ensures real-time output
heroku logs --app=$APP_NAME --tail | grep --line-buffered -E "ERROR|WARNING|Error|Warning|error|warning|failed|Failed|FAILED|Exception|exception" | while IFS= read -r line; do
    if [[ $line =~ (ERROR|Error|error|FAILED|Failed|failed|Exception|exception) ]]; then
        echo -e "${RED}$line${NC}"
    elif [[ $line =~ (WARNING|Warning|warning) ]]; then
        echo -e "${YELLOW}$line${NC}"
    else
        echo "$line"
    fi
done
