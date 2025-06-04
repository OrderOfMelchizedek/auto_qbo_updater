"""Unit tests for logging configuration."""
import logging
from unittest.mock import patch

from src.config.logging_config import setup_logging


def test_setup_logging_configures_root_logger():
    """Test that setup_logging configures the root logger."""
    with patch("logging.basicConfig") as mock_basic_config:
        # Explicitly pass debug=False to override environment variable
        setup_logging(debug=False)

        mock_basic_config.assert_called_once()
        call_kwargs = mock_basic_config.call_args.kwargs

        assert call_kwargs["level"] == logging.INFO
        assert "format" in call_kwargs
        assert "%(asctime)s" in call_kwargs["format"]
        assert "%(levelname)s" in call_kwargs["format"]


def test_setup_logging_debug_mode():
    """Test that setup_logging sets DEBUG level when debug=True."""
    with patch("logging.basicConfig") as mock_basic_config:
        setup_logging(debug=True)

        call_kwargs = mock_basic_config.call_args.kwargs
        assert call_kwargs["level"] == logging.DEBUG


def test_setup_logging_silences_noisy_libraries():
    """Test that setup_logging reduces log level for noisy libraries."""
    with patch("logging.getLogger") as mock_get_logger:
        setup_logging()

        # Check that we silence noisy libraries
        expected_calls = [
            "urllib3.connectionpool",
            "boto3",
            "botocore",
            "google.auth",
        ]

        for lib in expected_calls:
            mock_get_logger.assert_any_call(lib)
