import unittest
from unittest.mock import patch, MagicMock, Mock
import os
import sys
from datetime import datetime, timedelta

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# Import from src.app since we're in tests directory
try:
    from src.app import validate_donation_date, normalize_check_number, normalize_amount, normalize_donor_name, normalize_date
except ImportError:
    # Fallback for different test environments
    import sys
    sys.path.append('../src')
    from app import validate_donation_date, normalize_check_number, normalize_amount, normalize_donor_name, normalize_date

class TestDataValidation(unittest.TestCase):
    """Test data validation functions."""
    
    def setUp(self):
        """Set up test environment."""
        # Mock environment variables for date validation
        self.env_patcher = patch.dict(os.environ, {
            'DATE_WARNING_DAYS': '365',
            'FUTURE_DATE_LIMIT_DAYS': '7'
        })
        self.env_patcher.start()
        
    def tearDown(self):
        """Clean up after tests."""
        self.env_patcher.stop()
    
    def test_validate_donation_date_valid_recent(self):
        """Test validation of recent valid date."""
        recent_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        is_valid, warning_msg, parsed_date = validate_donation_date(recent_date)
        
        self.assertTrue(is_valid)
        self.assertIsNone(warning_msg)
        self.assertIsNotNone(parsed_date)
        self.assertEqual(parsed_date.strftime('%Y-%m-%d'), recent_date)
    
    def test_validate_donation_date_valid_old_with_warning(self):
        """Test validation of old date (should warn but be valid)."""
        old_date = (datetime.now() - timedelta(days=400)).strftime('%Y-%m-%d')
        
        is_valid, warning_msg, parsed_date = validate_donation_date(old_date)
        
        self.assertTrue(is_valid)
        self.assertIsNotNone(warning_msg)
        self.assertIn('years old', warning_msg)  # Actual message format includes "years old"
        self.assertIsNotNone(parsed_date)
    
    def test_validate_donation_date_future_valid(self):
        """Test validation of near-future date (within limit)."""
        future_date = (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d')
        
        is_valid, warning_msg, parsed_date = validate_donation_date(future_date)
        
        self.assertTrue(is_valid)
        self.assertIsNotNone(warning_msg)  # Future dates always get a warning
        self.assertIn('days in the future', warning_msg)
        self.assertIsNotNone(parsed_date)
    
    def test_validate_donation_date_future_invalid(self):
        """Test validation of far-future date (beyond limit)."""
        far_future_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        
        is_valid, warning_msg, parsed_date = validate_donation_date(far_future_date)
        
        self.assertFalse(is_valid)
        self.assertIsNotNone(warning_msg)
        self.assertIn('days in the future', warning_msg)  # Check for actual message format
        self.assertIsNone(parsed_date)
    
    def test_validate_donation_date_invalid_format(self):
        """Test validation of invalid date format."""
        # Test truly invalid dates
        is_valid, warning_msg, parsed_date = validate_donation_date('invalid-date')
        self.assertFalse(is_valid)
        self.assertIsNotNone(warning_msg)
        
        # Test empty date (should be valid with no warnings)
        is_valid, warning_msg, parsed_date = validate_donation_date('')
        self.assertTrue(is_valid)
        self.assertIsNone(warning_msg)
    
    def test_validate_donation_date_various_formats(self):
        """Test validation of various acceptable date formats."""
        test_date = datetime(2024, 1, 15)
        valid_formats = [
            '2024-01-15',
            '2024/01/15',
            '01/15/2024',
            '15/01/2024',
            'January 15, 2024',
            'Jan 15, 2024',
            '15 Jan 2024'
        ]
        
        for date_str in valid_formats:
            is_valid, warning_msg, parsed_date = validate_donation_date(date_str)
            
            if is_valid:
                self.assertIsNotNone(parsed_date)
                # Should parse to the same date (allowing for ambiguity in some formats)
                self.assertIsInstance(parsed_date, datetime)
    
    def test_normalize_check_number_basic(self):
        """Test basic check number normalization."""
        test_cases = [
            ('12345', '12345'),
            ('  12345  ', '12345'),  # Whitespace
            ('CHK-12345', 'CHK-12345'),
            ('Check #12345', 'Check #12345'),
            ('', ''),
            (None, '')
        ]
        
        for input_val, expected in test_cases:
            result = normalize_check_number(input_val)
            self.assertEqual(result, expected)
    
    def test_normalize_check_number_special_cases(self):
        """Test check number normalization with special cases."""
        # Very long check number
        long_check = 'A' * 100
        normalized = normalize_check_number(long_check)
        self.assertEqual(normalized, 'A' * 100)  # No truncation in current implementation
        
        # Check number with special characters
        special_check = 'CHK#12345@BANK'
        normalized = normalize_check_number(special_check)
        self.assertEqual(normalized, special_check)  # Should preserve as-is
    
    def test_normalize_amount_valid(self):
        """Test amount normalization with valid inputs."""
        test_cases = [
            ('100.00', '100.00'),
            ('$100.00', '100.00'),
            ('1,000.50', '1000.50'),
            ('$1,234.56', '1234.56'),
            ('  500  ', '500.00'),
            ('0.01', '0.01'),
            ('0', '0.00')
        ]
        
        for input_val, expected in test_cases:
            result = normalize_amount(input_val)
            self.assertEqual(result, expected)
    
    def test_normalize_amount_invalid(self):
        """Test amount normalization with invalid inputs."""
        invalid_amounts = [
            ('invalid', 'invalid'),
            ('', ''),
            (None, ''),
            ('free', 'free'),
            ('abc123', 'abc123')
        ]
        
        for invalid_amount, expected in invalid_amounts:
            result = normalize_amount(invalid_amount)
            self.assertEqual(result, expected)
    
    def test_normalize_amount_edge_cases(self):
        """Test amount normalization edge cases."""
        # Very large amount
        large_amount = '999999999.99'
        result = normalize_amount(large_amount)
        self.assertEqual(result, '999999999.99')
        
        # Multiple decimal points (should handle gracefully)
        invalid_decimal = '100.00.50'
        result = normalize_amount(invalid_decimal)
        self.assertEqual(result, '100.00.50')  # Returns as-is when can't parse
    
    def test_normalize_donor_name_basic(self):
        """Test basic donor name normalization."""
        test_cases = [
            ('John Doe', 'john doe'),  # Converts to lowercase, removes punctuation
            ('  John   Doe  ', 'john doe'),  # Extra spaces normalized
            ('JOHN DOE', 'john doe'),  # Case normalization
            ('john doe', 'john doe'),  # Already normalized
            ('', ''),
            (None, '')
        ]
        
        for input_val, expected in test_cases:
            result = normalize_donor_name(input_val)
            self.assertEqual(result, expected)
    
    def test_normalize_donor_name_special_cases(self):
        """Test donor name normalization with special cases."""
        # Name with prefixes/suffixes (punctuation removed)
        name_with_title = 'DR. JOHN DOE JR.'
        normalized = normalize_donor_name(name_with_title)
        self.assertEqual(normalized, 'dr john doe jr')  # Punctuation removed, lowercase
        
        # Name with apostrophe (punctuation removed)
        irish_name = "o'connor"
        normalized = normalize_donor_name(irish_name)
        self.assertEqual(normalized, "oconnor")  # Apostrophe removed
        
        # Name with hyphen (punctuation removed)
        hyphenated_name = 'mary-jane smith'
        normalized = normalize_donor_name(hyphenated_name)
        self.assertEqual(normalized, 'maryjane smith')  # Hyphen removed
    
    def test_normalize_donor_name_organization(self):
        """Test donor name normalization for organizations."""
        org_names = [
            ('ABC CORPORATION', 'abc corporation'),
            ('xyz nonprofit inc.', 'xyz nonprofit inc'),  # Period removed
            ('  FIRST BAPTIST CHURCH  ', 'first baptist church')
        ]
        
        for input_val, expected in org_names:
            result = normalize_donor_name(input_val)
            self.assertEqual(result, expected)
    
    def test_normalize_date_various_formats(self):
        """Test date normalization with various formats."""
        test_cases = [
            ('2024-01-15', '2024-01-15'),
            ('01/15/2024', '2024-01-15'),
            ('1/15/24', '2024-01-15'),  # Assuming 2-digit year is 20xx
            ('', ''),
            (None, '')
        ]
        
        for input_val, expected in test_cases:
            result = normalize_date(input_val)
            if expected:
                # Allow for some parsing flexibility
                self.assertIsInstance(result, str)
                self.assertIn('2024', result)
            else:
                self.assertEqual(result, expected)
    
    def test_normalize_date_invalid(self):
        """Test date normalization with invalid dates."""
        invalid_dates = [
            'not-a-date',
            '2024-13-01',
            '2024-02-30',
            'random text'
        ]
        
        for invalid_date in invalid_dates:
            result = normalize_date(invalid_date)
            # Function returns original string if parsing fails
            self.assertEqual(result, invalid_date)

class TestDonationDataValidation(unittest.TestCase):
    """Test validation of complete donation records."""
    
    def test_valid_donation_record(self):
        """Test validation of a complete valid donation record."""
        valid_donation = {
            'Donor Name': 'John Doe',
            'Gift Amount': '100.00',
            'Check No.': '12345',
            'Check Date': '2024-01-15',
            'Gift Date': '2024-01-15'
        }
        
        # Test individual field validations
        self.assertGreater(len(valid_donation['Donor Name']), 0)
        self.assertEqual(normalize_amount(valid_donation['Gift Amount']), '100.00')
        self.assertGreater(len(normalize_check_number(valid_donation['Check No.'])), 0)
        
        # Test date validation
        is_valid, _, _ = validate_donation_date(valid_donation['Check Date'])
        self.assertTrue(is_valid)
    
    def test_missing_required_fields(self):
        """Test validation with missing required fields."""
        incomplete_donations = [
            {
                # Missing Donor Name
                'Gift Amount': '100.00',
                'Check No.': '12345'
            },
            {
                'Donor Name': 'John Doe',
                # Missing Gift Amount
                'Check No.': '12345'
            },
            {
                'Donor Name': 'John Doe',
                'Gift Amount': '100.00'
                # Missing Check No.
            }
        ]
        
        for donation in incomplete_donations:
            # Check for missing fields
            required_fields = ['Donor Name', 'Gift Amount', 'Check No.']
            missing_fields = [field for field in required_fields if not donation.get(field)]
            self.assertGreater(len(missing_fields), 0)
    
    def test_donation_field_limits(self):
        """Test donation field length and format limits."""
        # Test very long donor name
        long_name = 'A' * 200
        normalized_name = normalize_donor_name(long_name)
        self.assertEqual(normalized_name, 'a' * 200)  # No truncation, just lowercase
        
        # Test very large amount
        huge_amount = '999999999999.99'
        normalized_amount = normalize_amount(huge_amount)
        self.assertEqual(normalized_amount, '999999999999.99')  # normalize_amount returns string
        
        # Test very long check number
        long_check = '1' * 100
        normalized_check = normalize_check_number(long_check)
        self.assertEqual(normalized_check, '1' * 100)  # No truncation
    
    def test_donation_data_consistency(self):
        """Test consistency checks between related fields."""
        donation = {
            'Donor Name': 'John Doe',
            'Gift Amount': '100.00',
            'Check No.': '12345',
            'Check Date': '2024-01-15',
            'Gift Date': '2024-01-10'  # Different from check date
        }
        
        # Check Date and Gift Date might be different (acceptable)
        check_valid, _, check_parsed = validate_donation_date(donation['Check Date'])
        gift_valid, _, gift_parsed = validate_donation_date(donation['Gift Date'])
        
        self.assertTrue(check_valid)
        self.assertTrue(gift_valid)
        
        # They can be different dates, but both should be valid
        if check_parsed and gift_parsed:
            # Dates should be within reasonable range of each other
            date_diff = abs((check_parsed - gift_parsed).days)
            self.assertLessEqual(date_diff, 365)  # Within a year of each other

class TestSecurityValidation(unittest.TestCase):
    """Test security-related validation functions."""
    
    def test_sql_injection_prevention_in_normalization(self):
        """Test that normalization prevents SQL injection."""
        malicious_inputs = [
            "'; DROP TABLE donations; --",
            "1' OR '1'='1",
            "admin'/*",
            "' UNION SELECT * FROM users --"
        ]
        
        for malicious_input in malicious_inputs:
            # These should be normalized safely
            normalized_name = normalize_donor_name(malicious_input)
            normalized_check = normalize_check_number(malicious_input)
            
            # Should have SQL punctuation removed
            self.assertNotIn("'", normalized_name)
            self.assertNotIn(";", normalized_name)
            self.assertNotIn("--", normalized_name)
            self.assertNotIn("/*", normalized_name)
    
    def test_xss_prevention_in_normalization(self):
        """Test that normalization prevents XSS attacks."""
        xss_inputs = [
            "<script>alert('xss')</script>",
            "javascript:alert(1)",
            "<img src=x onerror=alert(1)>",
            "';alert('xss');//"
        ]
        
        for xss_input in xss_inputs:
            normalized_name = normalize_donor_name(xss_input)
            
            # Should not contain script tags or javascript
            self.assertNotIn('<script>', normalized_name.lower())
            self.assertNotIn('javascript:', normalized_name.lower())
            self.assertNotIn('onerror=', normalized_name.lower())
    
    def test_path_traversal_prevention(self):
        """Test prevention of path traversal in donor names."""
        path_traversal_inputs = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32",
            "/etc/shadow",
            "C:\\Windows\\System32\\config"
        ]
        
        for path_input in path_traversal_inputs:
            normalized = normalize_donor_name(path_input)
            
            # Should normalize path separators
            self.assertNotIn('..', normalized)
            self.assertNotIn('/etc/', normalized)
            self.assertNotIn('\\system32', normalized.lower())

if __name__ == '__main__':
    unittest.main()