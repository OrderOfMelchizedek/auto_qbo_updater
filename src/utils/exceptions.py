"""
Custom exception classes for the FOM to QBO automation application.

These exceptions provide better error handling and user-friendly messages
while logging detailed information for debugging.
"""


class FOMQBOException(Exception):
    """Base exception class for all FOM to QBO application errors."""

    def __init__(self, message, user_message=None, details=None):
        """Initialize base FOM to QBO exception.

        Args:
            message: Detailed error message for logging
            user_message: User-friendly message to display
            details: Additional error details as dictionary
        """
        super().__init__(message)
        self.message = message
        self.user_message = user_message or "An error occurred. Please try again."
        self.details = details or {}


class ExternalAPIException(FOMQBOException):
    """Base exception for external API errors."""

    def __init__(self, service, message, status_code=None, response_text=None, user_message=None):
        """Initialize external API exception.

        Args:
            service: Name of the external service
            message: Detailed error message
            status_code: HTTP status code from API
            response_text: Raw response text from API
            user_message: User-friendly message
        """
        details = {
            "service": service,
            "status_code": status_code,
            "response_text": response_text,
        }
        super().__init__(message, user_message, details)
        self.service = service
        self.status_code = status_code
        self.response_text = response_text


class QBOAPIException(ExternalAPIException):
    """Exception for QuickBooks Online API errors."""

    def __init__(self, message, status_code=None, response_text=None, user_message=None):
        """Initialize QuickBooks API exception.

        Args:
            message: Detailed error message
            status_code: HTTP status code from QBO API
            response_text: Raw response text from QBO API
            user_message: User-friendly message
        """
        if not user_message:
            if status_code == 401:
                user_message = "QuickBooks authentication expired. Please reconnect to QuickBooks."
            elif status_code == 429:
                user_message = "Too many requests to QuickBooks. Please wait a moment and try again."
            elif status_code and status_code >= 500:
                user_message = "QuickBooks service is temporarily unavailable. Please try again later."
            else:
                user_message = "Error communicating with QuickBooks. Please try again."

        super().__init__("QuickBooks", message, status_code, response_text, user_message)


class GeminiAPIException(ExternalAPIException):
    """Exception for Google Gemini API errors."""

    def __init__(self, message, status_code=None, response_text=None, user_message=None):
        """Initialize QuickBooks API exception.

        Args:
            message: Detailed error message
            status_code: HTTP status code from QBO API
            response_text: Raw response text from QBO API
            user_message: User-friendly message
        """
        if not user_message:
            if status_code == 429:
                user_message = "AI processing limit reached. Please wait a moment and try again."
            elif status_code and status_code >= 500:
                user_message = "AI service is temporarily unavailable. Please try again later."
            else:
                user_message = "Error processing with AI. Please try again."

        super().__init__("Gemini", message, status_code, response_text, user_message)


class FileProcessingException(FOMQBOException):
    """Exception for file processing errors."""

    def __init__(self, filename, message, user_message=None):
        """Initialize file processing exception.

        Args:
            filename: Name of the file being processed
            message: Detailed error message
            user_message: User-friendly message
        """
        details = {"filename": filename}
        if not user_message:
            user_message = f"Error processing file {filename}. Please check the file and try again."
        super().__init__(message, user_message, details)
        self.filename = filename


class ValidationException(FOMQBOException):
    """Exception for data validation errors."""

    def __init__(self, field, value, message, user_message=None):
        """Initialize validation exception.

        Args:
            field: Field name that failed validation
            value: Invalid value that was provided
            message: Detailed validation error message
            user_message: User-friendly message
        """
        details = {"field": field, "value": value}
        if not user_message:
            user_message = f"Invalid {field}: {message}"
        super().__init__(message, user_message, details)
        self.field = field
        self.value = value


class RetryableException(FOMQBOException):
    """Exception for errors that can be retried."""

    def __init__(self, message, max_retries=3, user_message=None):
        """Initialize retryable exception.

        Args:
            message: Detailed error message
            max_retries: Maximum number of retry attempts
            user_message: User-friendly message
        """
        details = {"max_retries": max_retries}
        super().__init__(message, user_message, details)
        self.max_retries = max_retries
