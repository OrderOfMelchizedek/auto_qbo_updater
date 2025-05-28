import unittest
import os
import sys
import tempfile

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from utils.csv_parser import CSVParser

class TestCSVParser(unittest.TestCase):
    def setUp(self):
        self.csv_parser = CSVParser()
        
        # Create a temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        
        # Create a test CSV file with comma delimiter
        self.test_csv_path = os.path.join(self.temp_dir, "test_donations.csv")
        with open(self.test_csv_path, 'w', newline='', encoding='utf-8') as f:
            f.write("donor_name,gift_amount,gift_date,address,city,state,zip,memo\n")
            f.write("John Doe,100.00,01/01/2025,123 Main St,Springfield,IL,62701,Test donation\n")
            f.write("Jane Smith,50.00,01/02/2025,456 Elm St,Springfield,IL,62701,Second test\n")
    
    def tearDown(self):
        # Clean up the temporary directory
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_parse_csv(self):
        """Test parsing a valid CSV file."""
        donations = self.csv_parser.parse(self.test_csv_path)
        
        # Check that we got the correct number of donations
        self.assertEqual(len(donations), 2)
        
        # Check the first donation's fields
        self.assertEqual(donations[0]['Donor Name'], 'John Doe')
        self.assertEqual(donations[0]['Gift Amount'], '100.00')
        self.assertEqual(donations[0]['Gift Date'], '01/01/2025')
        self.assertEqual(donations[0]['Address - Line 1'], '123 Main St')
        self.assertEqual(donations[0]['City'], 'Springfield')
        self.assertEqual(donations[0]['State'], 'IL')
        self.assertEqual(donations[0]['ZIP'], '62701')
        self.assertEqual(donations[0]['Memo'], 'Test donation')
        
        # Check that customerLookup was generated correctly
        self.assertEqual(donations[0]['customerLookup'], 'Doe, John')
    
    def test_parse_csv_semicolon_delimiter(self):
        """Test parsing a CSV with semicolon delimiter."""
        # Create a test CSV file with semicolon delimiter
        semicolon_csv_path = os.path.join(self.temp_dir, "semicolon_test.csv")
        with open(semicolon_csv_path, 'w', newline='', encoding='utf-8') as f:
            f.write("donor_name;gift_amount;gift_date\n")
            f.write("John Doe;100.00;01/01/2025\n")
        
        donations = self.csv_parser.parse(semicolon_csv_path)
        
        # Check that it was parsed correctly
        self.assertEqual(len(donations), 1)
        self.assertEqual(donations[0]['Donor Name'], 'John Doe')
        self.assertEqual(donations[0]['Gift Amount'], '100.00')
    
    def test_parse_csv_with_different_headers(self):
        """Test parsing a CSV with different header names."""
        # Create a test CSV with different header names
        different_headers_csv_path = os.path.join(self.temp_dir, "different_headers.csv")
        with open(different_headers_csv_path, 'w', newline='', encoding='utf-8') as f:
            f.write("name,amount,date,notes\n")
            f.write("John Doe,100.00,01/01/2025,Test donation\n")
        
        donations = self.csv_parser.parse(different_headers_csv_path)
        
        # Check that the mapping worked
        self.assertEqual(len(donations), 1)
        self.assertEqual(donations[0]['Donor Name'], 'John Doe')
        self.assertEqual(donations[0]['Gift Amount'], '100.00')
        self.assertEqual(donations[0]['Gift Date'], '01/01/2025')
        self.assertEqual(donations[0]['Memo'], 'Test donation')
    
    def test_parse_empty_csv(self):
        """Test parsing an empty CSV file."""
        # Create an empty CSV file
        empty_csv_path = os.path.join(self.temp_dir, "empty.csv")
        with open(empty_csv_path, 'w', newline='', encoding='utf-8') as f:
            f.write("donor_name,gift_amount,gift_date\n")
        
        donations = self.csv_parser.parse(empty_csv_path)
        
        # Should return an empty list
        self.assertEqual(len(donations), 0)
    
    def test_parse_invalid_csv(self):
        """Test parsing an invalid CSV file."""
        # Create an invalid CSV file
        invalid_csv_path = os.path.join(self.temp_dir, "invalid.csv")
        with open(invalid_csv_path, 'w', newline='', encoding='utf-8') as f:
            f.write("This is not a CSV file")
        
        donations = self.csv_parser.parse(invalid_csv_path)
        
        # Should return an empty list
        self.assertEqual(len(donations), 0)

if __name__ == '__main__':
    unittest.main()