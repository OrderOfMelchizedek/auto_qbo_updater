import json
import re
import threading
import time
import uuid
from queue import Empty, Queue
from typing import List, Optional


class ProgressLogger:
    """Captures debug output and periodically summarizes it with AI for user-friendly progress updates."""

    def __init__(self, gemini_service=None, summary_interval=2.0):
        self.gemini_service = gemini_service
        self.summary_interval = summary_interval
        self.logs = []
        self.last_summary_time = time.time()
        self.session_id = None
        self.active = False
        self.lock = threading.Lock()
        self.subscribers = {}  # session_id -> queue
        self.recent_summaries = {}  # session_id -> list of recent summaries
        self.update_threads = {}  # session_id -> thread

    def start_session(self, session_id: str):
        """Start a new progress logging session."""
        with self.lock:
            self.session_id = session_id
            self.logs = []
            self.last_summary_time = time.time()
            self.active = True
            if session_id not in self.subscribers:
                self.subscribers[session_id] = Queue()

            # Initialize recent summaries buffer
            self.recent_summaries[session_id] = []

            # Add an initial status message
            initial_message = {
                "type": "progress",
                "summary": "Starting to process your files...\nPreparing to analyze your documents.",
                "timestamp": time.time(),
            }
            self.subscribers[session_id].put(initial_message)
            self.recent_summaries[session_id].append(initial_message)

            # Start periodic update thread
            self._start_periodic_updates(session_id)

    def end_session(self, session_id: str):
        """End a progress logging session."""
        with self.lock:
            if self.session_id == session_id:
                self.active = False
                self.session_id = None
                self.logs = []
            # Keep subscriber queue for final messages

    def log(self, message: str, force_summary: bool = False):
        """Log a progress message."""
        if not self.active:
            return

        print(f"[ProgressLogger] Logging: {message}")

        with self.lock:
            self.logs.append({"timestamp": time.time(), "message": message})

            # Check if we should summarize
            current_time = time.time()
            time_since_last = current_time - self.last_summary_time

            if (
                force_summary
                or time_since_last >= self.summary_interval
                or len(self.logs) >= 3
            ):
                print(
                    f"[ProgressLogger] Creating summary (force={force_summary}, time_since_last={time_since_last:.1f}s, log_count={len(self.logs)})"
                )
                self._create_summary()
                self.last_summary_time = current_time

    def _create_summary(self):
        """Create and send a summary of recent logs."""
        if not self.logs or not self.session_id:
            print(
                f"[ProgressLogger] Cannot create summary: logs={len(self.logs) if self.logs else 0}, session_id={self.session_id}"
            )
            return

        try:
            # Prepare logs for summarization
            log_messages = [
                log["message"] for log in self.logs[-10:]
            ]  # Last 10 messages
            print(f"[ProgressLogger] Summarizing {len(log_messages)} messages")

            # Use simple summary to avoid Gemini API overhead
            print("[ProgressLogger] Using simple summary for performance")
            summary = self._create_simple_summary(log_messages)

            print(f"[ProgressLogger] Summary created: {summary[:100]}...")

            # Create message
            message = {"type": "progress", "summary": summary, "timestamp": time.time()}

            # Store in recent summaries
            if self.session_id in self.recent_summaries:
                self.recent_summaries[self.session_id].append(message)
                # Keep only last 10 summaries
                self.recent_summaries[self.session_id] = self.recent_summaries[
                    self.session_id
                ][-10:]

            # Send to subscribers
            if self.session_id in self.subscribers:
                print(
                    f"[ProgressLogger] Sending summary to subscriber for session {self.session_id}"
                )
                self.subscribers[self.session_id].put(message)
            else:
                print(
                    f"[ProgressLogger] No subscriber found for session {self.session_id}"
                )

            # Clear processed logs
            self.logs = []

        except Exception as e:
            # Send error message
            error_summary = f"Processing your files...\nEncountered an issue: {str(e)}"
            if self.session_id in self.subscribers:
                self.subscribers[self.session_id].put(
                    {
                        "type": "progress",
                        "summary": error_summary,
                        "timestamp": time.time(),
                    }
                )

    def _summarize_with_gemini(self, log_messages: List[str]) -> str:
        """Use Gemini to create a user-friendly summary."""
        if not log_messages:
            return "Processing your files...\nPlease wait while we prepare your data."

        # Create prompt for Gemini
        logs_text = "\n".join(log_messages)

        # Extract specific details from logs
        file_names = []
        counts = []
        for msg in log_messages:
            # Extract file names
            if ".csv" in msg or ".pdf" in msg or ".jpg" in msg or ".png" in msg:
                files = re.findall(r"[\w\-]+\.\w+", msg)
                file_names.extend(files)
            # Extract numbers
            numbers = re.findall(r"\d+", msg)
            counts.extend(numbers)

        prompt = f"""Convert these technical log messages into a user-friendly progress update with EXACTLY 2 lines.
Line 1: Current action (5-10 words, active voice, present tense)
Line 2: Specific details with numbers/files/progress (15-25 words)

Guidelines:
- Use natural, conversational language
- Include specific file names when mentioned: {', '.join(list(set(file_names))[:3]) if file_names else 'files'}
- Include specific counts when available: {', '.join(list(set(counts))[:3]) if counts else 'items'}
- Vary the phrasing to avoid repetition
- Make line 2 informative and specific

Technical logs:
{logs_text}

IMPORTANT: Output exactly 2 lines of text, nothing else."""

        try:
            response = self.gemini_service.generate_text(prompt)
            if response and response.strip():
                lines = response.strip().split("\n")
                if len(lines) >= 2:
                    return f"{lines[0].strip()}\n{lines[1].strip()}"
                else:
                    return f"{response.strip()}\nProcessing continues..."
            else:
                return self._create_simple_summary(log_messages)
        except Exception as e:
            print(f"Gemini summarization failed: {e}")
            return f"Processing your files...\nError creating summary: {str(e)}"

    def _create_simple_summary(self, log_messages: List[str]) -> str:
        """Create a simple fallback summary."""
        if not log_messages:
            return "Processing your files...\nPlease wait while we prepare your data."

        # Simple analysis of recent messages
        recent_msg = log_messages[-1].lower()

        if "processing" in recent_msg and "file" in recent_msg:
            return "Reading and analyzing your uploaded files...\nExtracting donation information from documents."
        elif "customer" in recent_msg or "quickbooks" in recent_msg:
            return "Matching donations with customers in QuickBooks...\nVerifying donor information and addresses."
        elif "deduplication" in recent_msg or "duplicate" in recent_msg:
            return "Checking for duplicate donations...\nEnsuring each donation is counted only once."
        elif "extract" in recent_msg or "donation" in recent_msg:
            return "Found donations in your files...\nProcessing donor information and amounts."
        else:
            return "Processing your donation data...\nAlmost finished preparing everything for you."

    def _start_periodic_updates(self, session_id: str):
        """Start a thread that ensures updates are sent at least every 3 seconds."""

        def periodic_update():
            while self.active and self.session_id == session_id:
                time.sleep(3.0)
                with self.lock:
                    if self.active and self.session_id == session_id:
                        # Force a summary if we haven't sent one recently
                        current_time = time.time()
                        if current_time - self.last_summary_time >= 3.0:
                            if self.logs:
                                print(
                                    f"[ProgressLogger] Forcing periodic update for session {session_id}"
                                )
                                self._create_summary()
                                self.last_summary_time = current_time

        thread = threading.Thread(target=periodic_update, daemon=True)
        thread.start()
        self.update_threads[session_id] = thread

    def get_progress_stream(self, session_id: str):
        """Generator for SSE streaming of progress updates."""
        print(f"[ProgressLogger] Starting progress stream for session {session_id}")
        if session_id not in self.subscribers:
            self.subscribers[session_id] = Queue()

        # Send any recent summaries first (for late connections)
        if session_id in self.recent_summaries:
            for summary in self.recent_summaries[session_id]:
                print(f"[ProgressLogger] Replaying recent summary: {summary}")
                yield f"data: {json.dumps(summary)}\n\n"

        queue = self.subscribers[session_id]
        last_activity = time.time()

        try:
            while True:
                try:
                    # Wait for progress update with timeout
                    progress_data = queue.get(timeout=1.0)
                    last_activity = time.time()
                    print(f"[ProgressLogger] Streaming event: {progress_data}")
                    yield f"data: {json.dumps(progress_data)}\n\n"

                except Empty:
                    # Send heartbeat if no activity for 10 seconds
                    current_time = time.time()
                    if current_time - last_activity > 10:
                        yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': current_time})}\n\n"
                        last_activity = current_time

                    # Stop if session is inactive for too long
                    if current_time - last_activity > 30:
                        break

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        finally:
            # Clean up
            if session_id in self.subscribers:
                del self.subscribers[session_id]
            if session_id in self.recent_summaries:
                del self.recent_summaries[session_id]


# Global instance with 3-second update interval
progress_logger = ProgressLogger(summary_interval=3.0)


def init_progress_logger(gemini_service):
    """Initialize the global progress logger with Gemini service."""
    global progress_logger
    progress_logger.gemini_service = gemini_service
    progress_logger.summary_interval = 3.0


def log_progress(message: str, force_summary: bool = False):
    """Convenience function for logging progress."""
    global progress_logger
    progress_logger.log(message, force_summary)
