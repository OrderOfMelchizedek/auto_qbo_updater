"""Tests for the Gemini service module."""
import os
import unittest
from pathlib import Path
from unittest.mock import Mock, mock_open, patch


class TestGeminiService(unittest.TestCase):
    """Test cases for Gemini service functions."""

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data="Explain in one sentence what makes a good API design.",
    )
    @patch("src.geminiservice.Path.exists")
    @patch("src.geminiservice.genai")
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-api-key"})
    def test_call_gemini_api_success(self, mock_genai, mock_exists, mock_file):
        """Test successful API call with mocked response."""
        from src.geminiservice import call_gemini_api

        # Mock that the prompt file exists
        mock_exists.return_value = True

        # Mock the model and response
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = (
            "A good API design is intuitive, consistent, and well-documented."
        )
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        # Call the function
        result = call_gemini_api()

        # Assertions
        self.assertIsInstance(result, str)
        self.assertEqual(
            result, "A good API design is intuitive, consistent, and well-documented."
        )
        mock_genai.configure.assert_called_once_with(api_key="test-api-key")
        mock_genai.GenerativeModel.assert_called_once_with(
            "gemini-2.5-flash-preview-05-20"
        )
        mock_model.generate_content.assert_called_once_with(
            "Explain in one sentence what makes a good API design."
        )

    @patch("builtins.open", new_callable=mock_open, read_data="Test prompt")
    @patch("src.geminiservice.Path.exists")
    @patch("src.geminiservice.genai")
    @patch.dict(
        os.environ, {"GEMINI_API_KEY": "test-api-key", "GEMINI_MODEL": "custom-model"}
    )
    def test_call_gemini_api_with_custom_model(
        self, mock_genai, mock_exists, mock_file
    ):
        """Test API call with custom model from environment."""
        from src.geminiservice import call_gemini_api

        # Mock that the prompt file exists
        mock_exists.return_value = True

        # Mock the model and response
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = "Test response"
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        # Call the function
        call_gemini_api()

        # Assertions
        mock_genai.GenerativeModel.assert_called_once_with("custom-model")

    @patch("src.geminiservice.genai")
    def test_call_gemini_api_missing_api_key(self, mock_genai):
        """Test error when API key is missing."""
        from src.geminiservice import call_gemini_api

        # Ensure GEMINI_API_KEY is not in environment
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError) as context:
                call_gemini_api()

            self.assertIn("GEMINI_API_KEY not found", str(context.exception))

    @patch("builtins.open", new_callable=mock_open, read_data="Test prompt")
    @patch("src.geminiservice.Path.exists")
    @patch("src.geminiservice.genai")
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-api-key"})
    def test_call_gemini_api_with_api_error(self, mock_genai, mock_exists, mock_file):
        """Test handling of API errors."""
        from src.geminiservice import call_gemini_api

        # Mock that the prompt file exists
        mock_exists.return_value = True

        # Mock the model to raise an exception
        mock_model = Mock()
        mock_model.generate_content.side_effect = Exception(
            "API Error: Rate limit exceeded"
        )
        mock_genai.GenerativeModel.return_value = mock_model

        # Call the function and expect an exception
        with self.assertRaises(Exception) as context:
            call_gemini_api()

        self.assertIn(
            "Error calling Gemini API: API Error: Rate limit exceeded",
            str(context.exception),
        )

    @patch("builtins.open", new_callable=mock_open, read_data="Test prompt")
    @patch("src.geminiservice.Path.exists")
    @patch("src.geminiservice.genai")
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-api-key"})
    def test_call_gemini_api_empty_response(self, mock_genai, mock_exists, mock_file):
        """Test handling of empty response from API."""
        from src.geminiservice import call_gemini_api

        # Mock that the prompt file exists
        mock_exists.return_value = True

        # Mock the model with empty response
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = ""
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        # Call the function
        result = call_gemini_api()

        # Assertions
        self.assertEqual(result, "")

    def test_load_prompt_success(self):
        """Test loading prompt from file successfully."""
        from src.geminiservice import load_prompt

        with patch("builtins.open", mock_open(read_data="This is a test prompt")):
            with patch("src.geminiservice.Path.exists", return_value=True):
                result = load_prompt("document_extraction_prompt")
                self.assertEqual(result, "This is a test prompt")

    def test_load_prompt_file_not_found(self):
        """Test error when prompt file doesn't exist."""
        from src.geminiservice import load_prompt

        with patch("src.geminiservice.Path.exists", return_value=False):
            with self.assertRaises(FileNotFoundError) as context:
                load_prompt("nonexistent_prompt")

            self.assertIn("Prompt file not found", str(context.exception))
            self.assertIn(".md or", str(context.exception))
            self.assertIn(".txt", str(context.exception))

    @patch("src.geminiservice.genai")
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-api-key"})
    def test_call_gemini_api_with_custom_prompt_name(self, mock_genai):
        """Test calling API with a custom prompt name."""
        from src.geminiservice import call_gemini_api

        with patch("builtins.open", mock_open(read_data="Custom test prompt")):
            with patch("src.geminiservice.Path.exists", return_value=True):
                # Mock the model and response
                mock_model = Mock()
                mock_response = Mock()
                mock_response.text = "Custom response"
                mock_model.generate_content.return_value = mock_response
                mock_genai.GenerativeModel.return_value = mock_model

                # Call the function with custom prompt name
                result = call_gemini_api("custom_prompt")

                # Assertions
                self.assertEqual(result, "Custom response")
                mock_model.generate_content.assert_called_once_with(
                    "Custom test prompt"
                )

    def test_load_prompt_md_file(self):
        """Test loading prompt from .md file."""
        from src.geminiservice import load_prompt

        md_content = "# Test Prompt\n\nThis is a markdown prompt."

        # Mock the path exists check to return True for .md, False for .txt
        with patch("src.geminiservice.Path.exists") as mock_exists:
            mock_exists.side_effect = (
                lambda: mock_exists.call_count == 1
            )  # True for first call (.md), False for second (.txt)

            with patch("builtins.open", mock_open(read_data=md_content)):
                result = load_prompt("test_prompt")
                self.assertEqual(result, md_content)

    def test_load_prompt_prefers_md_over_txt(self):
        """Test that .md files are preferred over .txt files."""
        from src.geminiservice import PROMPTS_DIR, load_prompt

        # Create temporary test files
        test_prompt_name = "test_preference"
        md_path = PROMPTS_DIR / f"{test_prompt_name}.md"

        # Mock both files existing
        with patch("src.geminiservice.Path.exists", return_value=True):
            # Mock opening the .md file (should be tried first)
            with patch("builtins.open", mock_open(read_data="MD content")) as mock_file:
                result = load_prompt(test_prompt_name)

                # Should have opened the .md file with UTF-8 encoding
                mock_file.assert_called_once_with(md_path, "r", encoding="utf-8")
                self.assertEqual(result, "MD content")

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data="Tell me what is in this image.",
    )
    @patch("src.geminiservice.Path.exists")
    @patch("src.geminiservice.Image.open")
    @patch("src.geminiservice.genai")
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-api-key"})
    def test_call_gemini_api_with_image_success(
        self, mock_genai, mock_image_open, mock_exists, mock_file
    ):
        """Test successful API call with image."""
        from src.geminiservice import call_gemini_api_with_image

        # Mock that both prompt and image files exist
        mock_exists.return_value = True

        # Mock the image
        mock_img = Mock()
        mock_image_open.return_value = mock_img

        # Mock the model and response
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = "I see a test image with some content."
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        # Call the function
        result = call_gemini_api_with_image(
            "image_analysis", "src/tests/test_files/2025-05-17 12.50.27-1.jpg"
        )

        # Assertions
        self.assertIsInstance(result, str)
        self.assertEqual(result, "I see a test image with some content.")
        mock_genai.configure.assert_called_once_with(api_key="test-api-key")
        mock_model.generate_content.assert_called_once_with(
            ["Tell me what is in this image.", mock_img]
        )

    @patch("src.geminiservice.genai")
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-api-key"})
    def test_call_gemini_api_with_image_file_not_found(self, mock_genai):
        """Test error when image file doesn't exist."""
        from src.geminiservice import call_gemini_api_with_image

        with patch("src.geminiservice.Path.exists") as mock_exists:
            # First call checks prompt (exists), second checks image (doesn't exist)
            mock_exists.side_effect = [True, False]

            with patch("builtins.open", mock_open(read_data="Test prompt")):
                with self.assertRaises(FileNotFoundError) as context:
                    call_gemini_api_with_image(
                        "image_analysis", "nonexistent_image.png"
                    )

                self.assertIn("Image file not found", str(context.exception))

    @patch("builtins.open", new_callable=mock_open, read_data="Test prompt")
    @patch("src.geminiservice.Path.exists")
    @patch("src.geminiservice.Image.open")
    @patch("src.geminiservice.genai")
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-api-key"})
    def test_call_gemini_api_with_image_api_error(
        self, mock_genai, mock_image_open, mock_exists, mock_file
    ):
        """Test handling of API errors when processing images."""
        from src.geminiservice import call_gemini_api_with_image

        # Mock that both files exist
        mock_exists.return_value = True

        # Mock the image
        mock_img = Mock()
        mock_image_open.return_value = mock_img

        # Mock the model to raise an exception
        mock_model = Mock()
        mock_model.generate_content.side_effect = Exception(
            "API Error: Invalid image format"
        )
        mock_genai.GenerativeModel.return_value = mock_model

        # Call the function and expect an exception
        with self.assertRaises(Exception) as context:
            call_gemini_api_with_image("image_analysis", "test_image.png")

        self.assertIn("Error calling Gemini API with image", str(context.exception))

    @patch("src.geminiservice.Path")
    def test_call_gemini_api_with_image_integration(self, mock_path_class):
        """Test integration with actual test image file path."""
        from src.geminiservice import call_gemini_api_with_image

        # Mock the Path class
        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = True
        mock_path_class.return_value = mock_path_instance
        mock_path_class.__truediv__ = lambda self, other: mock_path_instance

        # Test that the function can be called with the expected test file path
        test_image_path = (
            Path(__file__).parent / "test_files" / "2025-05-17 12.50.27-1.jpg"
        )

        with patch(
            "builtins.open", mock_open(read_data="Tell me what is in this image.")
        ):
            with patch("src.geminiservice.Image.open") as mock_image_open:
                with patch("src.geminiservice.genai") as mock_genai:
                    with patch.dict(os.environ, {"GEMINI_API_KEY": "test-api-key"}):
                        # Mock the image and API response
                        mock_img = Mock()
                        mock_image_open.return_value = mock_img

                        mock_model = Mock()
                        mock_response = Mock()
                        mock_response.text = "Test response"
                        mock_model.generate_content.return_value = mock_response
                        mock_genai.GenerativeModel.return_value = mock_model

                        # Call should succeed
                        result = call_gemini_api_with_image(
                            "document_extraction_prompt", str(test_image_path)
                        )
                        self.assertEqual(result, "Test response")

    @unittest.skipUnless(
        os.getenv("RUN_INTEGRATION_TESTS") == "true",
        "Skipping integration test. Set RUN_INTEGRATION_TESTS=true to run.",
    )
    def test_call_gemini_api_with_real_image(self):
        """Integration test with real Gemini API call and actual image file."""
        from src.geminiservice import call_gemini_api_with_image

        # This test uses the actual API and real image file
        image_path = "src/tests/test_files/test_batch_1/2025-05-17 12.50.27-1.jpg"

        # Check if the image file exists
        if not Path(image_path).exists():
            self.skipTest(f"Image file not found: {image_path}")

        try:
            # Make the actual API call
            result = call_gemini_api_with_image(
                "document_extraction_prompt", image_path
            )

            # Assertions
            self.assertIsInstance(result, str)
            self.assertGreater(len(result), 0, "Response should not be empty")

            # Print the result for manual verification
            print(f"\nGemini API Response for {image_path}:")
            print("-" * 50)
            print(result)
            print("-" * 50)

        except Exception as e:
            # If API key is not set or other issues, skip the test
            if "GEMINI_API_KEY not found" in str(e):
                self.skipTest("GEMINI_API_KEY not set")
            else:
                raise

    @patch("src.geminiservice.base64.b64encode")
    @patch("builtins.open", new_callable=mock_open)
    @patch("src.geminiservice.Path.exists")
    @patch("src.geminiservice.genai")
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-api-key"})
    def test_call_gemini_api_with_pdf_success(
        self, mock_genai, mock_exists, mock_file, mock_b64encode
    ):
        """Test successful API call with PDF document."""
        from src.geminiservice import call_gemini_api_with_pdf

        # Mock that both prompt and PDF files exist
        mock_exists.return_value = True

        # Mock file reading - first call reads prompt, second reads PDF
        mock_file.return_value.read.side_effect = [
            "Extract data from this PDF document.",  # Prompt file
            b"PDF file content",  # PDF file (binary)
        ]

        # Mock base64 encoding
        mock_b64encode.return_value = b"base64encodedpdf"

        # Mock the model and response
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = "I extracted data from the PDF document."
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        # Call the function
        result = call_gemini_api_with_pdf(
            "document_extraction", "src/tests/test_files/2025-05-17-12-48-17.pdf"
        )

        # Assertions
        self.assertIsInstance(result, str)
        self.assertEqual(result, "I extracted data from the PDF document.")
        mock_genai.configure.assert_called_once_with(api_key="test-api-key")

        # Check that the PDF was passed correctly
        expected_pdf_part = {
            "inline_data": {"mime_type": "application/pdf", "data": "base64encodedpdf"}
        }
        mock_model.generate_content.assert_called_once_with(
            [expected_pdf_part, "Extract data from this PDF document."]
        )

    @patch("src.geminiservice.genai")
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-api-key"})
    def test_call_gemini_api_with_pdf_file_not_found(self, mock_genai):
        """Test error when PDF file doesn't exist."""
        from src.geminiservice import call_gemini_api_with_pdf

        with patch("src.geminiservice.Path.exists") as mock_exists:
            # First call checks prompt (exists), second checks PDF (doesn't exist)
            mock_exists.side_effect = [True, False]

            with patch("builtins.open", mock_open(read_data="Test prompt")):
                with self.assertRaises(FileNotFoundError) as context:
                    call_gemini_api_with_pdf("document_extraction", "nonexistent.pdf")

                self.assertIn("PDF file not found", str(context.exception))

    @unittest.skipUnless(
        os.getenv("RUN_INTEGRATION_TESTS") == "true",
        "Skipping integration test. Set RUN_INTEGRATION_TESTS=true to run.",
    )
    def test_call_gemini_api_with_real_pdf(self):
        """Integration test with real Gemini API call and actual PDF file."""
        from src.geminiservice import call_gemini_api_with_pdf

        # This test uses the actual API and real PDF file
        pdf_path = "src/tests/test_files/test_batch_1/2025-05-17-12-48-17.pdf"

        # Check if the PDF file exists
        if not Path(pdf_path).exists():
            self.skipTest(f"PDF file not found: {pdf_path}")

        try:
            # Make the actual API call
            result = call_gemini_api_with_pdf("document_extraction_prompt", pdf_path)

            # Assertions
            self.assertIsInstance(result, str)
            self.assertGreater(len(result), 0, "Response should not be empty")

            # Print the result for manual verification
            print(f"\nGemini API Response for {pdf_path}:")
            print("-" * 50)
            print(result)
            print("-" * 50)

        except Exception as e:
            # If API key is not set or other issues, skip the test
            if "GEMINI_API_KEY not found" in str(e):
                self.skipTest("GEMINI_API_KEY not set")
            else:
                raise

    @patch("src.geminiservice.Path.stat")
    @patch("src.geminiservice.base64.b64encode")
    @patch("builtins.open", new_callable=mock_open)
    @patch("src.geminiservice.Path.exists")
    @patch("src.geminiservice.genai")
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-api-key"})
    def test_process_multiple_files_success(
        self, mock_genai, mock_exists, mock_file, mock_b64encode, mock_stat
    ):
        """Test successful processing of multiple files (PDFs and images)."""
        from src.geminiservice import process_multiple_files

        # Mock that all files exist
        mock_exists.return_value = True

        # Mock file stats (for size validation)
        mock_stat_result = Mock()
        mock_stat_result.st_size = 1024 * 1024  # 1MB (under the limit)
        mock_stat.return_value = mock_stat_result

        # Mock file reading
        mock_file.return_value.read.side_effect = [
            "Extract data from documents.",  # Prompt file
            b"PDF content 1",  # First PDF
            b"Image content 1",  # First image
            b"PDF content 2",  # Second PDF
        ]

        # Mock base64 encoding
        mock_b64encode.side_effect = [b"base64pdf1", b"base64img1", b"base64pdf2"]

        # Mock PIL Image for image files
        with patch("src.geminiservice.Image.open") as mock_img_open:
            mock_img = Mock()
            mock_img_open.return_value = mock_img

            # Mock the model and response
            mock_model = Mock()
            mock_response = Mock()
            mock_response.text = '{"files_processed": 3, "total_donations": 10}'
            mock_model.generate_content.return_value = mock_response
            mock_genai.GenerativeModel.return_value = mock_model

            # Test files
            files = ["test_file1.pdf", "test_file2.jpg", "test_file3.pdf"]

            # Call the function
            result = process_multiple_files("document_extraction_prompt", files)

            # Assertions
            self.assertIsInstance(result, str)
            self.assertIn("files_processed", result)
            mock_genai.configure.assert_called_once_with(api_key="test-api-key")

    @patch("src.geminiservice.genai")
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-api-key"})
    def test_process_multiple_files_empty_list(self, mock_genai):
        """Test error when no files are provided."""
        from src.geminiservice import process_multiple_files

        with self.assertRaises(ValueError) as context:
            process_multiple_files("document_extraction", [])

        self.assertIn("No files provided", str(context.exception))

    @patch("src.geminiservice.genai")
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-api-key"})
    def test_process_multiple_files_unsupported_format(self, mock_genai):
        """Test error when unsupported file format is provided."""
        from src.geminiservice import process_multiple_files

        with self.assertRaises(ValueError) as context:
            process_multiple_files(
                "document_extraction_prompt", ["test.txt", "test.docx"]
            )

        self.assertIn("Unsupported file format", str(context.exception))

    @patch("src.geminiservice.Image.open")
    @patch("src.geminiservice.base64.b64encode")
    @patch("builtins.open", new_callable=mock_open)
    @patch("src.geminiservice.Path.exists")
    @patch("src.geminiservice.genai")
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-api-key"})
    def test_process_multiple_files_some_missing(
        self, mock_genai, mock_exists, mock_file, mock_b64encode, mock_img_open
    ):
        """Test error when some files don't exist."""
        from src.geminiservice import process_multiple_files

        # Mock that some files don't exist - prompt exists, file1 exists,
        # file2 exists, missing doesn't
        mock_exists.side_effect = [True, True, True, False]

        # Mock file reading for prompt
        mock_file.return_value.read.return_value = "Test prompt"

        # Mock image
        mock_img = Mock()
        mock_img_open.return_value = mock_img

        with self.assertRaises(FileNotFoundError) as context:
            process_multiple_files(
                "document_extraction", ["file1.pdf", "file2.jpg", "missing.pdf"]
            )

        self.assertIn("File not found: missing.pdf", str(context.exception))

    @unittest.skipUnless(
        os.getenv("RUN_INTEGRATION_TESTS") == "true",
        "Skipping integration test. Set RUN_INTEGRATION_TESTS=true to run.",
    )
    def test_process_test_batch_1(self):
        """Integration test for test_batch_1 (1 PDF + 1 JPG)."""
        from src.geminiservice import process_multiple_files

        batch_dir = Path("src/tests/test_files/test_batch_1")
        files = [
            str(batch_dir / "2025-05-17-12-48-17.pdf"),
            str(batch_dir / "2025-05-17 12.50.27-1.jpg"),
        ]

        # Check if files exist
        for file in files:
            if not Path(file).exists():
                self.skipTest(f"Test file not found: {file}")

        try:
            result = process_multiple_files("document_extraction_prompt", files)

            # Assertions
            self.assertIsInstance(result, str)
            self.assertGreater(len(result), 0)

            print(f"\n{'='*50}")
            print("Test Batch 1 Results (1 PDF + 1 JPG):")
            print("=" * 50)
            print(result)
            print("=" * 50)

        except Exception as e:
            if "GEMINI_API_KEY not found" in str(e):
                self.skipTest("GEMINI_API_KEY not set")
            else:
                raise

    @unittest.skipUnless(
        os.getenv("RUN_INTEGRATION_TESTS") == "true",
        "Skipping integration test. Set RUN_INTEGRATION_TESTS=true to run.",
    )
    def test_process_test_batch_2(self):
        """Integration test for test_batch_2 (2 JPGs)."""
        from src.geminiservice import process_multiple_files

        batch_dir = Path("src/tests/test_files/test_batch_2")
        files = [
            str(batch_dir / "20250411_205258.jpg"),
            str(batch_dir / "20250411_205415.jpg"),
        ]

        # Check if files exist
        for file in files:
            if not Path(file).exists():
                self.skipTest(f"Test file not found: {file}")

        try:
            result = process_multiple_files("document_extraction_prompt", files)

            # Assertions
            self.assertIsInstance(result, str)
            self.assertGreater(len(result), 0)

            print(f"\n{'='*50}")
            print("Test Batch 2 Results (2 JPGs):")
            print("=" * 50)
            print(result)
            print("=" * 50)

        except Exception as e:
            if "GEMINI_API_KEY not found" in str(e):
                self.skipTest("GEMINI_API_KEY not set")
            else:
                raise

    @unittest.skipUnless(
        os.getenv("RUN_INTEGRATION_TESTS") == "true",
        "Skipping integration test. Set RUN_INTEGRATION_TESTS=true to run.",
    )
    def test_process_test_batch_3(self):
        """Integration test for test_batch_3 (2 PDFs)."""
        from src.geminiservice import process_multiple_files

        batch_dir = Path("src/tests/test_files/test_batch_3")
        files = [
            str(batch_dir / "2025-01-11-15-27-04.pdf"),
            str(batch_dir / "2025-01-11-15-36-44.pdf"),
        ]

        # Check if files exist
        for file in files:
            if not Path(file).exists():
                self.skipTest(f"Test file not found: {file}")

        try:
            result = process_multiple_files("document_extraction_prompt", files)

            # Assertions
            self.assertIsInstance(result, str)
            self.assertGreater(len(result), 0)

            print(f"\n{'='*50}")
            print("Test Batch 3 Results (2 PDFs):")
            print("=" * 50)
            print(result)
            print("=" * 50)

        except Exception as e:
            if "GEMINI_API_KEY not found" in str(e):
                self.skipTest("GEMINI_API_KEY not set")
            else:
                raise

    @unittest.skipUnless(
        os.getenv("RUN_INTEGRATION_TESTS") == "true",
        "Skipping integration test. Set RUN_INTEGRATION_TESTS=true to run.",
    )
    def test_process_test_batch_4(self):
        """Integration test for test_batch_4 (2 PDFs + 5 JPGs)."""
        from src.geminiservice import process_multiple_files

        batch_dir = Path("src/tests/test_files/test_batch_4")
        files = [
            str(batch_dir / "2025-03-01-16-45-21.pdf"),
            str(batch_dir / "20250207182439287.pdf"),
            str(batch_dir / "20250328_195721.jpg"),
            str(batch_dir / "20250328_195746.jpg"),
            str(batch_dir / "20250328_195802.jpg"),
            str(batch_dir / "20250328_195844.jpg"),
            str(batch_dir / "20250328_195901.jpg"),
        ]

        # Check if files exist
        for file in files:
            if not Path(file).exists():
                self.skipTest(f"Test file not found: {file}")

        try:
            result = process_multiple_files("document_extraction_prompt", files)

            # Assertions
            self.assertIsInstance(result, str)
            self.assertGreater(len(result), 0)

            print(f"\n{'='*50}")
            print("Test Batch 4 Results (2 PDFs + 5 JPGs):")
            print("=" * 50)
            print(result)
            print("=" * 50)

        except Exception as e:
            if "GEMINI_API_KEY not found" in str(e):
                self.skipTest("GEMINI_API_KEY not set")
            else:
                raise

    @patch("time.sleep")
    @patch("src.geminiservice.base64.b64encode")
    @patch("builtins.open", new_callable=mock_open)
    @patch("src.geminiservice.Path.exists")
    @patch("src.geminiservice.genai")
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-api-key"})
    def test_process_multiple_files_retry_on_error(
        self, mock_genai, mock_exists, mock_file, mock_b64encode, mock_sleep
    ):
        """Test retry mechanism with exponential backoff on API errors."""
        from src.geminiservice import process_multiple_files

        # Mock that all files exist
        mock_exists.return_value = True

        # Mock file reading
        mock_file.return_value.read.side_effect = [
            "Extract data from documents.",  # Prompt file
            b"PDF content 1",  # PDF file
        ]

        # Mock base64 encoding
        mock_b64encode.return_value = b"base64pdf1"

        # Mock the model to fail twice then succeed
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = '{"status": "success after retries"}'

        # First two calls fail, third succeeds
        mock_model.generate_content.side_effect = [
            Exception("500 Internal Server Error"),
            Exception("503 Service Unavailable"),
            mock_response,
        ]
        mock_genai.GenerativeModel.return_value = mock_model

        # Call the function
        result = process_multiple_files("document_extraction", ["test_file1.pdf"])

        # Assertions
        self.assertEqual(result, '{"status": "success after retries"}')
        self.assertEqual(mock_model.generate_content.call_count, 3)

        # Check sleep was called with exponential backoff
        self.assertEqual(mock_sleep.call_count, 2)
        mock_sleep.assert_any_call(1)  # 2^0 = 1 second
        mock_sleep.assert_any_call(2)  # 2^1 = 2 seconds

    @patch("time.sleep")
    @patch("src.geminiservice.base64.b64encode")
    @patch("builtins.open", new_callable=mock_open)
    @patch("src.geminiservice.Path.exists")
    @patch("src.geminiservice.genai")
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-api-key"})
    def test_process_multiple_files_max_retries_exceeded(
        self, mock_genai, mock_exists, mock_file, mock_b64encode, mock_sleep
    ):
        """Test that function fails after max retries are exceeded."""
        from src.geminiservice import process_multiple_files

        # Mock that all files exist
        mock_exists.return_value = True

        # Mock file reading
        mock_file.return_value.read.side_effect = [
            "Extract data from documents.",  # Prompt file
            b"PDF content 1",  # PDF file
        ]

        # Mock base64 encoding
        mock_b64encode.return_value = b"base64pdf1"

        # Mock the model to always fail
        mock_model = Mock()
        mock_model.generate_content.side_effect = [
            Exception("500 Internal Server Error"),
            Exception("500 Internal Server Error"),
            Exception("500 Internal Server Error"),
            Exception("500 Internal Server Error"),  # This shouldn't be called
        ]
        mock_genai.GenerativeModel.return_value = mock_model

        # Call the function and expect it to fail
        with self.assertRaises(Exception) as context:
            process_multiple_files("document_extraction", ["test_file1.pdf"])

        # Assertions
        self.assertIn(
            "Error calling Gemini API with multiple files", str(context.exception)
        )
        self.assertIn("500 Internal Server Error", str(context.exception))
        self.assertEqual(
            mock_model.generate_content.call_count, 3
        )  # Initial attempt + 2 retries

        # Check sleep was called with exponential backoff
        self.assertEqual(mock_sleep.call_count, 2)
        mock_sleep.assert_any_call(1)  # 2^0 = 1 second
        mock_sleep.assert_any_call(2)  # 2^1 = 2 seconds

    @patch("time.sleep")
    @patch("src.geminiservice.Image.open")
    @patch("src.geminiservice.base64.b64encode")
    @patch("builtins.open", new_callable=mock_open)
    @patch("src.geminiservice.Path.exists")
    @patch("src.geminiservice.genai")
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-api-key"})
    def test_process_multiple_files_no_retry_on_non_retriable_error(
        self,
        mock_genai,
        mock_exists,
        mock_file,
        mock_b64encode,
        mock_img_open,
        mock_sleep,
    ):
        """Test that non-retriable errors don't trigger retries."""
        from src.geminiservice import process_multiple_files

        # Mock that all files exist
        mock_exists.return_value = True

        # Mock file reading
        mock_file.return_value.read.side_effect = [
            "Extract data from documents.",  # Prompt file
        ]

        # Mock image
        mock_img = Mock()
        mock_img_open.return_value = mock_img

        # Mock the model to fail with a non-retriable error
        mock_model = Mock()
        mock_model.generate_content.side_effect = ValueError(
            "Invalid input: File too large"
        )
        mock_genai.GenerativeModel.return_value = mock_model

        # Call the function and expect it to fail immediately
        with self.assertRaises(Exception) as context:
            process_multiple_files("document_extraction", ["test_file1.jpg"])

        # Assertions
        self.assertIn(
            "Error calling Gemini API with multiple files", str(context.exception)
        )
        self.assertIn("Invalid input: File too large", str(context.exception))
        self.assertEqual(
            mock_model.generate_content.call_count, 1
        )  # Only initial attempt, no retries

        # Check sleep was NOT called
        mock_sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
