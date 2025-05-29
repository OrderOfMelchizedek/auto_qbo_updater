#!/bin/bash

# Create logs directory if it doesn't exist
mkdir -p logs

# Function to get current log filename with timestamp
get_log_filename() {
    echo "logs/heroku_$(date +%Y-%m-%d_%H-%M-%S).log"
}

echo "Starting Heroku log capture - new file every 500 lines"
echo "Logs will be saved to: logs/heroku_YYYY-MM-DD_HH-MM-SS.log"
echo "Press Ctrl+C to stop"

# Initialize variables
line_count=0
max_lines=500
current_log_file=$(get_log_filename)

echo "=== Log capture started at $(date) ===" >> "$current_log_file"
echo "Writing to: $current_log_file"

# Start capturing logs
heroku logs --tail --app auto-qbo-updater | while IFS= read -r line; do
    # Write the log line to current file
    echo "$line" >> "$current_log_file"

    # Increment line counter
    ((line_count++))

    # Check if we've reached 500 lines
    if [ $line_count -ge $max_lines ]; then
        # Add closing marker
        echo "=== Log capture ended at $(date) - $line_count lines ===" >> "$current_log_file"
        echo "Completed file: $current_log_file ($line_count lines)"

        # Reset counter and create new file
        line_count=0
        current_log_file=$(get_log_filename)

        echo "=== Log capture started at $(date) ===" >> "$current_log_file"
        echo "Switching to new log file: $current_log_file"
    fi
done

# Handle script termination
trap 'echo "=== Log capture interrupted at $(date) - $line_count lines ===" >> "$current_log_file"; echo "Final file: $current_log_file ($line_count lines)"' EXIT</content>
</invoke>
