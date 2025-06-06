"""Tests for donation validation and deduplication logic."""
import pytest

from src.validation import DonationValidator


class TestDonationValidator:
    """Test suite for DonationValidator class."""

    @pytest.fixture
    def validator(self):
        """Create a DonationValidator instance."""
        return DonationValidator()

    def test_convert_to_proper_case(self, validator):
        """Test ALL CAPS to proper case conversion."""
        # Basic conversion
        assert validator.convert_to_proper_case("JOHN SMITH") == "John Smith"
        assert validator.convert_to_proper_case("123 MAIN STREET") == "123 Main Street"

        # Special cases
        assert validator.convert_to_proper_case("PO BOX 123") == "PO Box 123"
        assert validator.convert_to_proper_case("SMITH LLC") == "Smith LLC"
        assert validator.convert_to_proper_case("JOHN DOE JR") == "John Doe Jr"

        # Mixed case (should not change)
        assert validator.convert_to_proper_case("John Smith") == "John Smith"
        assert validator.convert_to_proper_case("mixed CASE") == "mixed CASE"

        # Empty/None
        assert validator.convert_to_proper_case("") == ""
        assert validator.convert_to_proper_case(None) is None

    def test_clean_check_number(self, validator):
        """Test check number cleaning."""
        assert validator.clean_check_number("001234") == "1234"
        assert validator.clean_check_number("0000123") == "123"
        assert validator.clean_check_number("1234") == "1234"
        assert validator.clean_check_number("000") == "0"
        assert validator.clean_check_number("") == ""
        assert validator.clean_check_number(None) is None

    def test_normalize_zip_code(self, validator):
        """Test ZIP code normalization."""
        # Add leading zeros
        assert validator.normalize_zip_code("1234") == "01234"
        assert validator.normalize_zip_code("123") == "00123"

        # Remove extensions
        assert validator.normalize_zip_code("12345-6789") == "12345"
        assert validator.normalize_zip_code("01234-5678") == "01234"

        # Clean non-digits
        assert validator.normalize_zip_code("12345 ") == "12345"
        assert validator.normalize_zip_code(" 01234") == "01234"

        # Already correct
        assert validator.normalize_zip_code("12345") == "12345"

        # Empty/None
        assert validator.normalize_zip_code("") == ""
        assert validator.normalize_zip_code(None) is None

    def test_validate_entry(self, validator):
        """Test single entry validation."""
        entry = {
            "PaymentInfo": {
                "Payment_Ref": "001234",
                "Payment_Method": "printed check",
                "Amount": "100.50",
            },
            "PayerInfo": {
                "Salutation": "MR",
                "Organization_Name": "SMITH FOUNDATION LLC",
                "Aliases": ["JOHN SMITH", "J SMITH"],
            },
            "ContactInfo": {
                "Address_Line_1": "123 MAIN STREET",
                "City": "NEW YORK",
                "State": "NY",
                "ZIP": "1234-5678",
                "Phone": "(555) 123-4567",
            },
        }

        validated = validator.validate_entry(entry)

        # Check PaymentInfo
        assert validated["PaymentInfo"]["Payment_Ref"] == "1234"
        assert validated["PaymentInfo"]["Amount"] == 100.50

        # Check PayerInfo
        assert validated["PayerInfo"]["Salutation"] == "Mr"
        assert validated["PayerInfo"]["Organization_Name"] == "Smith Foundation LLC"
        assert validated["PayerInfo"]["Aliases"] == ["John Smith", "J Smith"]

        # Check ContactInfo
        assert validated["ContactInfo"]["Address_Line_1"] == "123 Main Street"
        assert validated["ContactInfo"]["City"] == "New York"
        assert validated["ContactInfo"]["ZIP"] == "01234"
        assert validated["ContactInfo"]["Phone"] == "5551234567"

    def test_is_valid_entry(self, validator):
        """Test entry validity checking."""
        # Valid entry
        valid_entry = {"PaymentInfo": {"Payment_Ref": "1234", "Amount": 100.00}}
        assert validator.is_valid_entry(valid_entry) is True

        # Missing PaymentInfo
        assert validator.is_valid_entry({}) is False

        # Missing Payment_Ref
        missing_ref = {"PaymentInfo": {"Amount": 100.00}}
        assert validator.is_valid_entry(missing_ref) is False

        # Missing Amount
        missing_amount = {"PaymentInfo": {"Payment_Ref": "1234"}}
        assert validator.is_valid_entry(missing_amount) is False

        # Zero amount
        zero_amount = {"PaymentInfo": {"Payment_Ref": "1234", "Amount": 0}}
        assert validator.is_valid_entry(zero_amount) is False

        # Negative amount
        negative_amount = {"PaymentInfo": {"Payment_Ref": "1234", "Amount": -100}}
        assert validator.is_valid_entry(negative_amount) is False

    def test_deduplicate_entries_no_duplicates(self, validator):
        """Test deduplication when no duplicates exist."""
        entries = [
            {
                "PaymentInfo": {"Payment_Ref": "1234", "Amount": 100.00},
                "PayerInfo": {"Aliases": ["John Smith"]},
            },
            {
                "PaymentInfo": {"Payment_Ref": "5678", "Amount": 200.00},
                "PayerInfo": {"Aliases": ["Jane Doe"]},
            },
        ]

        result = validator.deduplicate_entries(entries)
        assert len(result) == 2
        assert result[0]["PaymentInfo"]["Payment_Ref"] == "1234"
        assert result[1]["PaymentInfo"]["Payment_Ref"] == "5678"

    def test_deduplicate_entries_with_duplicates(self, validator):
        """Test deduplication with duplicate entries."""
        entries = [
            {
                "PaymentInfo": {"Payment_Ref": "1234", "Amount": 100.00},
                "PayerInfo": {"Aliases": ["John Smith"]},
                "ContactInfo": {"Address_Line_1": "123 Main St"},
            },
            {
                "PaymentInfo": {"Payment_Ref": "1234", "Amount": 100.00},
                "PayerInfo": {"Organization_Name": "Smith Foundation"},
                "ContactInfo": {"City": "New York", "State": "NY"},
            },
            {
                "PaymentInfo": {"Payment_Ref": "5678", "Amount": 200.00},
                "PayerInfo": {"Aliases": ["Jane Doe"]},
            },
        ]

        result = validator.deduplicate_entries(entries)
        assert len(result) == 2  # Two unique entries after deduplication

        # Find the merged entry
        merged = next(e for e in result if e["PaymentInfo"]["Payment_Ref"] == "1234")

        # Should have data from both duplicates
        assert merged["PayerInfo"]["Aliases"] == ["John Smith"]
        assert merged["PayerInfo"]["Organization_Name"] == "Smith Foundation"
        assert merged["ContactInfo"]["Address_Line_1"] == "123 Main St"
        assert merged["ContactInfo"]["City"] == "New York"
        assert merged["ContactInfo"]["State"] == "NY"

    def test_deduplicate_entries_filters_invalid(self, validator):
        """Test that invalid entries are filtered during deduplication."""
        entries = [
            {"PaymentInfo": {"Payment_Ref": "1234", "Amount": 100.00}},
            {"PaymentInfo": {"Amount": 200.00}},  # Missing Payment_Ref
            {"PaymentInfo": {"Payment_Ref": "5678"}},  # Missing Amount
        ]

        result = validator.deduplicate_entries(entries)
        assert len(result) == 1  # Only one valid entry
        assert result[0]["PaymentInfo"]["Payment_Ref"] == "1234"

    def test_merge_entries_aliases(self, validator):
        """Test that aliases are properly merged."""
        entries = [
            {
                "PaymentInfo": {"Payment_Ref": "1234", "Amount": 100.00},
                "PayerInfo": {"Aliases": ["John Smith", "J Smith"]},
            },
            {
                "PaymentInfo": {"Payment_Ref": "1234", "Amount": 100.00},
                "PayerInfo": {"Aliases": ["John Smith", "John S"]},
            },
        ]

        result = validator.deduplicate_entries(entries)
        assert len(result) == 1

        # Should have all unique aliases
        aliases = set(result[0]["PayerInfo"]["Aliases"])
        assert aliases == {"John Smith", "J Smith", "John S"}

    def test_process_donations_complete_flow(self, validator):
        """Test the complete validation and deduplication flow."""
        raw_entries = [
            {
                "PaymentInfo": {
                    "Payment_Ref": "001234",
                    "Payment_Method": "printed check",
                    "Amount": "100.50",
                },
                "PayerInfo": {
                    "Organization_Name": "SMITH FOUNDATION",
                    "Aliases": ["JOHN SMITH"],
                },
                "ContactInfo": {"Address_Line_1": "123 MAIN STREET", "ZIP": "1234"},
            },
            {
                "PaymentInfo": {
                    "Payment_Ref": "001234",  # Duplicate
                    "Amount": "100.50",
                    "Payment_Date": "2024-01-15",
                },
                "ContactInfo": {"City": "NEW YORK", "State": "NY"},
            },
            {"PaymentInfo": {"Amount": "200.00"}},  # Invalid - missing Payment_Ref
        ]

        result = validator.process_donations(raw_entries)

        # Should have one valid entry (duplicates merged, invalid filtered)
        assert len(result) == 1

        entry = result[0]
        # Check validation was applied
        assert entry["PaymentInfo"]["Payment_Ref"] == "1234"  # Leading zeros removed
        assert (
            entry["PayerInfo"]["Organization_Name"] == "Smith Foundation"
        )  # Proper case
        assert entry["ContactInfo"]["ZIP"] == "01234"  # Normalized to 5 digits

        # Check merge happened
        assert entry["PaymentInfo"]["Payment_Date"] == "2024-01-15"  # From second entry
        assert (
            entry["ContactInfo"]["City"] == "New York"
        )  # From second entry, proper case
        assert entry["ContactInfo"]["State"] == "NY"  # From second entry
