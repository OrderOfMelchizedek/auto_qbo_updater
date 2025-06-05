"""Tests for structured output extraction from donation documents."""
import json
import os
import unittest
from pathlib import Path
from unittest.mock import Mock, mock_open, patch


class TestStructuredExtraction(unittest.TestCase):
    """Test cases for structured donation data extraction."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.test_files_dir = Path(__file__).parent / "test_files"
        cls.expected_schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "PaymentInfo": {
                        "type": "object",
                        "properties": {
                            "Payment_Ref": {"type": "string"},
                            "Payment_Method": {
                                "type": "string",
                                "enum": [
                                    "handwritten check",
                                    "printed check",
                                    "online payment",
                                ],
                            },
                            "Amount": {"type": "number"},
                            "Payment_Date": {"type": "string"},
                            "Check_Date": {"type": "string", "nullable": True},
                            "Postmark_Date": {"type": "string", "nullable": True},
                            "Deposit_Date": {"type": "string", "nullable": True},
                            "Deposit_Method": {"type": "string", "nullable": True},
                            "Memo": {"type": "string", "nullable": True},
                        },
                        "required": [
                            "Payment_Ref",
                            "Payment_Method",
                            "Amount",
                            "Payment_Date",
                        ],
                    },
                    "PayerInfo": {
                        "type": "object",
                        "properties": {
                            "Aliases": {"type": "array", "items": {"type": "string"}},
                            "Salutation": {"type": "string", "nullable": True},
                            "Organization_Name": {"type": "string", "nullable": True},
                        },
                    },
                    "ContactInfo": {
                        "type": "object",
                        "properties": {
                            "Address_Line_1": {"type": "string", "nullable": True},
                            "City": {"type": "string", "nullable": True},
                            "State": {"type": "string", "nullable": True},
                            "ZIP": {"type": "string", "nullable": True},
                            "Email": {"type": "string", "nullable": True},
                            "Phone": {"type": "string", "nullable": True},
                        },
                    },
                },
                "required": ["PaymentInfo", "PayerInfo", "ContactInfo"],
            },
        }

    def test_create_donation_extraction_schema(self):
        """Test that the schema creation function returns the correct structure."""
        from src.geminiservice import create_donation_extraction_schema

        schema = create_donation_extraction_schema()

        # Check top-level structure
        self.assertEqual(schema["type"], "array")
        self.assertIn("items", schema)

        # Check required fields in PaymentInfo
        payment_info_props = schema["items"]["properties"]["PaymentInfo"]["properties"]
        self.assertIn("Payment_Ref", payment_info_props)
        self.assertIn("Payment_Method", payment_info_props)
        self.assertIn("Amount", payment_info_props)
        self.assertIn("Payment_Date", payment_info_props)

        # Check enums
        payment_methods = payment_info_props["Payment_Method"]["enum"]
        self.assertIn("handwritten check", payment_methods)
        self.assertIn("printed check", payment_methods)
        self.assertIn("online payment", payment_methods)

    def test_extract_donations_basic_structure(self):
        """Test basic structure of extracted donations."""
        from src.geminiservice import extract_donations_from_documents

        # Mock response with valid structure
        mock_response = json.dumps(
            [
                {
                    "PaymentInfo": {
                        "Payment_Ref": "1234",
                        "Payment_Method": "handwritten check",
                        "Amount": 100.00,
                        "Payment_Date": "2025-06-01",
                    },
                    "PayerInfo": {
                        "Aliases": ["John Smith", "J. Smith"],
                        "Salutation": "Mr.",
                    },
                    "ContactInfo": {
                        "Address_Line_1": "123 Main St",
                        "City": "Anytown",
                        "State": "CA",
                        "ZIP": "12345",
                    },
                }
            ]
        )

        with patch(
            "src.geminiservice.process_multiple_files_structured",
            return_value=mock_response,
        ):
            result = extract_donations_from_documents(["test.jpg"])

            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 1)

            donation = result[0]
            self.assertIn("PaymentInfo", donation)
            self.assertIn("PayerInfo", donation)
            self.assertIn("ContactInfo", donation)

    def test_extract_donations_validation_missing_required_fields(self):
        """Test that validation catches missing required fields."""
        from src.geminiservice import extract_donations_from_documents

        # Mock response missing required Payment_Ref
        mock_response = json.dumps(
            [
                {
                    "PaymentInfo": {
                        "Payment_Method": "handwritten check",
                        "Amount": 100.00,
                        "Payment_Date": "2025-06-01",
                    },
                    "PayerInfo": {"Aliases": ["John Smith"]},
                    "ContactInfo": {},
                }
            ]
        )

        with patch(
            "src.geminiservice.process_multiple_files_structured",
            return_value=mock_response,
        ):
            with self.assertRaises(ValueError) as context:
                extract_donations_from_documents(["test.jpg"], validate_output=True)

            self.assertIn("Missing required payment fields", str(context.exception))

    def test_extract_donations_validation_org_vs_individual(self):
        """Test validation that either organization or aliases must be present."""
        from src.geminiservice import extract_donations_from_documents

        # Mock response with neither org name nor aliases
        mock_response = json.dumps(
            [
                {
                    "PaymentInfo": {
                        "Payment_Ref": "1234",
                        "Payment_Method": "printed check",
                        "Amount": 500.00,
                        "Payment_Date": "2025-06-01",
                    },
                    "PayerInfo": {},  # Missing both Organization_Name and Aliases
                    "ContactInfo": {},
                }
            ]
        )

        with patch(
            "src.geminiservice.process_multiple_files_structured",
            return_value=mock_response,
        ):
            with self.assertRaises(ValueError) as context:
                extract_donations_from_documents(["test.pdf"], validate_output=True)

            self.assertIn(
                "Either Organization_Name or Aliases must be provided",
                str(context.exception),
            )

    def test_extract_donations_multiple_payments(self):
        """Test extraction of multiple payments from a batch."""
        from src.geminiservice import extract_donations_from_documents

        mock_response = json.dumps(
            [
                {
                    "PaymentInfo": {
                        "Payment_Ref": "1234",
                        "Payment_Method": "handwritten check",
                        "Amount": 100.00,
                        "Payment_Date": "2025-06-01",
                        "Check_Date": "2025-05-30",
                    },
                    "PayerInfo": {"Aliases": ["John Smith"]},
                    "ContactInfo": {"City": "Boston", "State": "MA"},
                },
                {
                    "PaymentInfo": {
                        "Payment_Ref": "5678",
                        "Payment_Method": "online payment",
                        "Amount": 250.00,
                        "Payment_Date": "2025-06-02",
                        "Deposit_Method": "Stripe",
                    },
                    "PayerInfo": {"Organization_Name": "ABC Corp"},
                    "ContactInfo": {"Email": "donate@abc.com"},
                },
            ]
        )

        with patch(
            "src.geminiservice.process_multiple_files_structured",
            return_value=mock_response,
        ):
            result = extract_donations_from_documents(["batch.pdf"])

            self.assertEqual(len(result), 2)
            self.assertEqual(result[0]["PaymentInfo"]["Payment_Ref"], "1234")
            self.assertEqual(result[1]["PaymentInfo"]["Payment_Ref"], "5678")
            self.assertEqual(
                result[1]["PaymentInfo"]["Payment_Method"], "online payment"
            )

    @unittest.skipUnless(
        os.getenv("RUN_INTEGRATION_TESTS") == "true",
        "Skipping integration test. Set RUN_INTEGRATION_TESTS=true to run.",
    )
    def test_extract_from_actual_check_image(self):
        """Integration test with actual check image from test files."""
        from src.geminiservice import extract_donations_from_documents

        # Use actual test file
        test_file = self.test_files_dir / "test_batch_1" / "2025-05-17 12.50.27-1.jpg"

        if not test_file.exists():
            self.skipTest(f"Test file not found: {test_file}")

        try:
            result = extract_donations_from_documents([str(test_file)])

            # Basic structure validation
            self.assertIsInstance(result, list)
            self.assertGreater(len(result), 0)

            # Check first donation
            donation = result[0]
            self.assertIn("PaymentInfo", donation)
            self.assertIn("PayerInfo", donation)
            self.assertIn("ContactInfo", donation)

            # Validate payment info
            payment_info = donation["PaymentInfo"]
            self.assertIn("Payment_Ref", payment_info)
            self.assertIn("Amount", payment_info)
            self.assertIsInstance(payment_info["Amount"], (int, float))
            self.assertIn("Payment_Method", payment_info)
            self.assertIn(
                payment_info["Payment_Method"],
                ["handwritten check", "printed check", "online payment"],
            )

            # Log extracted data for manual verification
            print(f"\nExtracted donation data from {test_file.name}:")
            print(json.dumps(result, indent=2))

        except Exception as e:
            if "GEMINI_API_KEY not found" in str(e):
                self.skipTest("GEMINI_API_KEY not set")
            else:
                raise

    @unittest.skipUnless(
        os.getenv("RUN_INTEGRATION_TESTS") == "true",
        "Skipping integration test. Set RUN_INTEGRATION_TESTS=true to run.",
    )
    def test_extract_from_multiple_documents_batch(self):
        """Integration test with multiple documents from test batch."""
        from src.geminiservice import extract_donations_from_documents

        # Use files from test_batch_1
        batch_dir = self.test_files_dir / "test_batch_1"
        test_files = [
            str(batch_dir / "2025-05-17-12-48-17.pdf"),
            str(batch_dir / "2025-05-17 12.50.27-1.jpg"),
        ]

        # Check if files exist
        for file in test_files:
            if not Path(file).exists():
                self.skipTest(f"Test file not found: {file}")

        try:
            result = extract_donations_from_documents(test_files)

            # Should extract at least one donation per document
            self.assertIsInstance(result, list)
            self.assertGreaterEqual(len(result), 1)

            # Validate each donation
            for i, donation in enumerate(result):
                with self.subTest(donation_index=i):
                    # Check required structure
                    self.assertIn("PaymentInfo", donation)
                    self.assertIn("PayerInfo", donation)
                    self.assertIn("ContactInfo", donation)

                    # Check required payment fields
                    payment_info = donation["PaymentInfo"]
                    self.assertIn("Payment_Ref", payment_info)
                    self.assertIn("Payment_Method", payment_info)
                    self.assertIn("Amount", payment_info)
                    self.assertIn("Payment_Date", payment_info)

                    # Either org or individual
                    payer_info = donation["PayerInfo"]
                    has_org = bool(payer_info.get("Organization_Name"))
                    has_aliases = bool(payer_info.get("Aliases"))
                    self.assertTrue(
                        has_org or has_aliases,
                        "Must have either Organization_Name or Aliases",
                    )

            # Log extracted data
            print(f"\nExtracted {len(result)} donations from batch:")
            print(json.dumps(result, indent=2))

        except Exception as e:
            if "GEMINI_API_KEY not found" in str(e):
                self.skipTest("GEMINI_API_KEY not set")
            else:
                raise

    def test_process_multiple_files_structured_basic(self):
        """Test the structured processing function with mocked response."""
        from src.geminiservice import process_multiple_files_structured

        # Mock the necessary components
        def mock_getenv(key, default=None):
            if key == "GEMINI_API_KEY":
                return "test-api-key"
            elif key == "GEMINI_MODEL":
                return default
            return None

        with patch("src.geminiservice.os.getenv", side_effect=mock_getenv):
            with patch("src.geminiservice.genai.configure"):
                with patch(
                    "src.geminiservice.genai.GenerativeModel"
                ) as mock_model_class:
                    with patch(
                        "src.geminiservice.load_prompt", return_value="Test prompt"
                    ):
                        with patch("src.geminiservice.Path.exists", return_value=True):
                            with patch(
                                "builtins.open", mock_open(read_data=b"test data")
                            ):
                                with patch(
                                    "src.geminiservice.base64.b64encode",
                                    return_value=b"encoded",
                                ):
                                    # Set up mock model
                                    mock_model = Mock()
                                    mock_response = Mock()
                                    mock_response.text = '[{"PaymentInfo": {}}]'
                                    mock_model.generate_content.return_value = (
                                        mock_response
                                    )
                                    mock_model_class.return_value = mock_model

                                    # Test without schema (default generation)
                                    result = process_multiple_files_structured(
                                        "test_prompt", ["test.pdf"]
                                    )

                                    self.assertEqual(result, '[{"PaymentInfo": {}}]')

                                    # Verify model was created without generation_config
                                    mock_model_class.assert_called_with(
                                        "gemini-2.5-flash-preview-05-20"
                                    )

    def test_process_multiple_files_structured_with_schema(self):
        """Test structured processing with schema configuration."""
        from src.geminiservice import process_multiple_files_structured

        test_schema = {"type": "array", "items": {"type": "object"}}

        def mock_getenv(key, default=None):
            if key == "GEMINI_API_KEY":
                return "test-api-key"
            elif key == "GEMINI_MODEL":
                return default
            return None

        with patch("src.geminiservice.os.getenv", side_effect=mock_getenv):
            with patch("src.geminiservice.genai.configure"):
                with patch(
                    "src.geminiservice.genai.GenerativeModel"
                ) as mock_model_class:
                    with patch(
                        "src.geminiservice.load_prompt", return_value="Test prompt"
                    ):
                        with patch("src.geminiservice.Path.exists", return_value=True):
                            with patch(
                                "builtins.open", mock_open(read_data=b"test data")
                            ):
                                with patch(
                                    "src.geminiservice.base64.b64encode",
                                    return_value=b"encoded",
                                ):
                                    # Set up mock model
                                    mock_model = Mock()
                                    mock_response = Mock()
                                    mock_response.text = '[{"test": "data"}]'
                                    mock_model.generate_content.return_value = (
                                        mock_response
                                    )
                                    mock_model_class.return_value = mock_model

                                    # Test with schema
                                    result = process_multiple_files_structured(
                                        "test_prompt",
                                        ["test.pdf"],
                                        response_schema=test_schema,
                                        response_mime_type="application/json",
                                    )

                                    self.assertEqual(result, '[{"test": "data"}]')

                                    # Verify model was created with generation_config
                                    expected_config = {
                                        "response_mime_type": "application/json",
                                        "response_schema": test_schema,
                                    }
                                    mock_model_class.assert_called_with(
                                        "gemini-2.5-flash-preview-05-20",
                                        generation_config=expected_config,
                                    )

    def test_extract_donations_invalid_json_response(self):
        """Test handling of invalid JSON responses."""
        from src.geminiservice import extract_donations_from_documents

        # Mock response with invalid JSON
        with patch(
            "src.geminiservice.process_multiple_files_structured",
            return_value="Not valid JSON",
        ):
            with self.assertRaises(ValueError) as context:
                extract_donations_from_documents(["test.jpg"])

            self.assertIn("Invalid JSON response", str(context.exception))

    def test_extract_donations_with_all_optional_fields(self):
        """Test extraction with all optional fields populated."""
        from src.geminiservice import extract_donations_from_documents

        mock_response = json.dumps(
            [
                {
                    "PaymentInfo": {
                        "Payment_Ref": "9999",
                        "Payment_Method": "printed check",
                        "Amount": 1000.00,
                        "Payment_Date": "2025-06-01",
                        "Check_Date": "2025-05-30",
                        "Postmark_Date": "2025-05-31",
                        "Deposit_Date": "2025-06-02",
                        "Deposit_Method": "ATM Deposit",
                        "Memo": "For building fund",
                    },
                    "PayerInfo": {
                        "Aliases": ["Jane Doe", "J. Doe", "Doe, Jane"],
                        "Salutation": "Dr.",
                        "Organization_Name": "Doe Foundation",
                    },
                    "ContactInfo": {
                        "Address_Line_1": "456 Oak Ave",
                        "City": "Springfield",
                        "State": "IL",
                        "ZIP": "62701",
                        "Email": "jane@doefoundation.org",
                        "Phone": "(555) 123-4567",
                    },
                }
            ]
        )

        with patch(
            "src.geminiservice.process_multiple_files_structured",
            return_value=mock_response,
        ):
            result = extract_donations_from_documents(
                ["test.pdf"], validate_output=True
            )

            self.assertEqual(len(result), 1)
            donation = result[0]

            # Check all optional fields are present
            payment_info = donation["PaymentInfo"]
            self.assertEqual(payment_info["Check_Date"], "2025-05-30")
            self.assertEqual(payment_info["Postmark_Date"], "2025-05-31")
            self.assertEqual(payment_info["Memo"], "For building fund")

            # Check contact info
            contact_info = donation["ContactInfo"]
            self.assertEqual(contact_info["Email"], "jane@doefoundation.org")
            self.assertEqual(contact_info["ZIP"], "62701")


if __name__ == "__main__":
    unittest.main()
