import os
import sys
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

# Import from the correct location
from src.services.validation import (
    normalize_amount,
    normalize_check_number,
    normalize_date,
    normalize_donor_name,
    validate_donation_date,
)


class TestDataValidation(unittest.TestCase):
    """Test data validation functions."""

    def setUp(self):
        """Set up test environment."""
        # Mock environment variables for date validation
        self.env_patcher = patch.dict(os.environ, {"DATE_WARNING_DAYS": "365", "FUTURE_DATE_LIMIT_DAYS": "7"})
        self.env_patcher.start()

    def tearDown(self):
        """Clean up after tests."""
        self.env_patcher.stop()

    def test_validate_donation_date_valid_recent(self):
        """Test validation of recent valid date."""
        recent_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        is_valid, warning_msg, parsed_date = validate_donation_date(recent_date)

        self.assertTrue(is_valid)
        self.assertIsNone(warning_msg)
        self.assertIsNotNone(parsed_date)

    def test_validate_donation_date_valid_old_with_warning(self):
        """Test validation of old date that should have warning."""
        # 400 days old - should trigger warning (> 365 days)
        old_date = (datetime.now() - timedelta(days=400)).strftime("%Y-%m-%d")

        is_valid, warning_msg, parsed_date = validate_donation_date(old_date)

        self.assertTrue(is_valid)  # Still valid
        self.assertIsNotNone(warning_msg)  # Should have warning
        self.assertIn("years old", warning_msg)
        self.assertIsNotNone(parsed_date)

    def test_validate_donation_date_future_invalid(self):
        """Test validation of future date beyond limit."""
        # 10 days in future - beyond the 7 day limit
        future_date = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")

        is_valid, warning_msg, parsed_date = validate_donation_date(future_date)

        self.assertFalse(is_valid)  # Should be invalid
        self.assertIsNotNone(warning_msg)
        self.assertIn("future", warning_msg)
        self.assertIsNone(parsed_date)  # None when invalid

    def test_validate_donation_date_future_valid_with_warning(self):
        """Test validation of future date within limit."""
        # 3 days in future - within the 7 day limit
        future_date = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")

        is_valid, warning_msg, parsed_date = validate_donation_date(future_date)

        self.assertTrue(is_valid)  # Should be valid
        self.assertIsNotNone(warning_msg)  # But with warning
        self.assertIn("future", warning_msg)
        self.assertIsNotNone(parsed_date)

    def test_validate_donation_date_empty(self):
        """Test validation of empty date."""
        is_valid, warning_msg, parsed_date = validate_donation_date("")

        self.assertTrue(is_valid)
        self.assertIsNone(warning_msg)
        self.assertIsNone(parsed_date)

    def test_validate_donation_date_invalid_format(self):
        """Test validation of invalid date format."""
        is_valid, warning_msg, parsed_date = validate_donation_date("not-a-date")

        self.assertFalse(is_valid)
        self.assertIsNotNone(warning_msg)
        self.assertIn("Invalid", warning_msg)
        self.assertIsNone(parsed_date)

    def test_normalize_donor_name(self):
        """Test donor name normalization."""
        self.assertEqual(normalize_donor_name("John Smith"), "John Smith")
        self.assertEqual(normalize_donor_name("  Jane  Doe  "), "Jane Doe")
        self.assertEqual(normalize_donor_name("JOHN SMITH"), "John Smith")
        self.assertEqual(normalize_donor_name("o'brien"), "O'Brien")
        self.assertEqual(normalize_donor_name("mary-jane watson"), "Mary-Jane Watson")

    def test_normalize_amount(self):
        """Test amount normalization."""
        self.assertEqual(normalize_amount("$100.00"), "100.00")
        self.assertEqual(normalize_amount("1,234.56"), "1234.56")
        self.assertEqual(normalize_amount("  $50  "), "50.00")
        self.assertEqual(normalize_amount("100"), "100.00")
        self.assertEqual(normalize_amount("abc"), None)
        self.assertEqual(normalize_amount(""), None)

    def test_normalize_check_number(self):
        """Test check number normalization."""
        self.assertEqual(normalize_check_number("1234"), "1234")
        self.assertEqual(normalize_check_number("  001234  "), "1234")
        self.assertEqual(normalize_check_number("#1234"), "1234")
        self.assertEqual(normalize_check_number("Check 1234"), "1234")
        self.assertEqual(normalize_check_number(""), None)

    def test_normalize_date(self):
        """Test date normalization."""
        # Test various formats
        self.assertEqual(normalize_date("2024-01-15"), "2024-01-15")
        self.assertEqual(normalize_date("01/15/2024"), "2024-01-15")
        self.assertEqual(normalize_date("15-Jan-2024"), "2024-01-15")
        self.assertEqual(normalize_date("January 15, 2024"), "2024-01-15")
        self.assertEqual(normalize_date("invalid-date"), None)
        self.assertEqual(normalize_date(""), None)


if __name__ == "__main__":
    unittest.main()
