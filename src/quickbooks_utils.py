"""QuickBooks utility classes and functions."""


class QuickBooksError(Exception):
    """QuickBooks API error with additional detail information."""

    def __init__(self, message, status_code=500, detail=None):
        """Initialize QuickBooks error with message, status code, and details."""
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail or {}
