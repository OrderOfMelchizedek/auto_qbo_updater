#!/bin/bash

# Create logs directory if it doesn't exist
mkdir -p logs

# Function to get current log filename
get_log_filename() {
    echo "logs/heroku_$(date +%Y-%m-%d_%H-%M).log"
}

# Function to get the 10-minute mark for the current time
get_10min_mark() {
    current_minute=$(date +%M)
    # Calculate which 10-minute block we're in (00, 10, 20, 30, 40, 50)
    echo $((current_minute / 10 * 10))
}

echo "Starting Heroku log capture in 10-minute chunks"
echo "Logs will be saved to: logs/heroku_YYYY-MM-DD_HH-MM.log"
echo "Press Ctrl+C to stop"

# Initialize variables
current_10min_mark=$(get_10min_mark)
current_log_file=$(get_log_filename)

echo "=== Log capture started at $(date) ===" >> "$current_log_file"
echo "Writing to: $current_log_file"

# Start capturing logs
heroku logs --tail --app auto-qbo-updater | while IFS= read -r line; do
    # Check if we've moved to a new 10-minute block
    new_10min_mark=$(get_10min_mark)
    
    if [ "$new_10min_mark" != "$current_10min_mark" ]; then
        # We've entered a new 10-minute block
        echo "=== Log capture ended at $(date) ===" >> "$current_log_file"
        
        # Update to new file
        current_10min_mark=$new_10min_mark
        current_log_file=$(get_log_filename)
        
        echo "=== Log capture started at $(date) ===" >> "$current_log_file"
        echo "Switching to new log file: $current_log_file"
    fi
    
    # Write the log line to current file
    echo "$line" >> "$current_log_file"
done