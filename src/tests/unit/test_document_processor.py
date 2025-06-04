"""Tests for document processing service."""
import io
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from src.models.document import FileType
from src.services.processing.document_processor import (
    DocumentProcessingError,
    DocumentProcessor,
)


@pytest.fixture
def mock_s3_service():
    """Mock S3 service."""
    mock = MagicMock()
    mock.upload_file = MagicMock()
    return mock


@pytest.fixture
def document_processor(mock_s3_service):
    """Create document processor instance."""
    return DocumentProcessor(s3_service=mock_s3_service)


@pytest.fixture
def sample_image_bytes():
    """Create sample image bytes."""
    image = Image.new("RGB", (100, 100), color="white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def sample_pdf_bytes():
    """Create sample PDF bytes."""
    # This is a minimal valid PDF
    return b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /Resources 4 0 R /MediaBox [0 0 612 792] >>
endobj
4 0 obj
<< /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >>
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000203 00000 n
trailer
<< /Size 5 /Root 1 0 R >>
startxref
320
%%EOF"""


class TestDocumentProcessor:
    """Test document processor functionality."""

    def test_process_image_success(
        self, document_processor, sample_image_bytes, mock_s3_service
    ):
        """Test successful image processing."""
        file_id = "test-file-123"

        pages = document_processor.process_document(
            sample_image_bytes, FileType.PNG, file_id
        )

        assert len(pages) == 1
        assert pages[0].file_id == file_id
        assert pages[0].page_number == 1
        assert pages[0].page_id == f"{file_id}_page_1"
        assert pages[0].s3_key == f"processed/{file_id}/page_1.png"

        # Verify S3 upload was called
        mock_s3_service.upload_file.assert_called_once()

    def test_process_jpeg_success(
        self, document_processor, sample_image_bytes, mock_s3_service
    ):
        """Test JPEG processing."""
        file_id = "test-jpeg-123"

        pages = document_processor.process_document(
            sample_image_bytes, FileType.JPEG, file_id
        )

        assert len(pages) == 1
        assert pages[0].file_id == file_id
        assert pages[0].page_number == 1

    @patch("src.services.processing.document_processor.convert_from_bytes")
    def test_process_pdf_success(
        self, mock_convert, document_processor, sample_pdf_bytes, mock_s3_service
    ):
        """Test successful PDF processing."""
        # Mock PDF conversion
        mock_image1 = Image.new("RGB", (100, 100), color="white")
        mock_image2 = Image.new("RGB", (100, 100), color="gray")
        mock_convert.return_value = [mock_image1, mock_image2]

        file_id = "test-pdf-123"

        pages = document_processor.process_document(
            sample_pdf_bytes, FileType.PDF, file_id
        )

        assert len(pages) == 2
        assert pages[0].page_number == 1
        assert pages[1].page_number == 2
        assert pages[0].page_id == f"{file_id}_page_1"
        assert pages[1].page_id == f"{file_id}_page_2"

        # Verify S3 uploads
        assert mock_s3_service.upload_file.call_count == 2

    def test_process_csv_success(self, document_processor):
        """Test CSV processing."""
        csv_content = b"name,amount\nJohn Doe,100\nJane Smith,200"
        file_id = "test-csv-123"

        pages = document_processor.process_document(csv_content, FileType.CSV, file_id)

        assert len(pages) == 1
        assert pages[0].page_number == 1
        assert pages[0].extraction_result is not None
        assert "csv_content" in pages[0].extraction_result
        assert "John Doe" in pages[0].extraction_result["csv_content"]

    def test_process_unsupported_file_type(self, document_processor):
        """Test processing unsupported file type."""
        with pytest.raises(DocumentProcessingError) as exc_info:
            document_processor.process_document(b"content", "unsupported", "test-id")

        assert "Unsupported file type" in str(exc_info.value)

    def test_resize_large_image(self, document_processor):
        """Test resizing large images."""
        # Create large image
        large_image = Image.new("RGB", (5000, 5000), color="white")

        resized = document_processor._resize_image(large_image)

        assert resized.size[0] <= 4096
        assert resized.size[1] <= 4096
        # Check aspect ratio is maintained
        assert abs(resized.size[0] / resized.size[1] - 1.0) < 0.01

    def test_resize_small_image(self, document_processor):
        """Test that small images are not resized."""
        small_image = Image.new("RGB", (100, 100), color="white")

        resized = document_processor._resize_image(small_image)

        assert resized.size == (100, 100)

    def test_image_to_bytes(self, document_processor):
        """Test image to bytes conversion."""
        image = Image.new("RGB", (100, 100), color="red")

        image_bytes = document_processor._image_to_bytes(image)

        assert isinstance(image_bytes, bytes)
        assert len(image_bytes) > 0

        # Verify it's a valid PNG
        reloaded = Image.open(io.BytesIO(image_bytes))
        assert reloaded.format == "PNG"

    @patch("pdf2image.pdfinfo_from_path")
    def test_get_page_count_pdf(
        self, mock_pdfinfo, document_processor, sample_pdf_bytes
    ):
        """Test getting page count for PDF."""
        mock_pdfinfo.return_value = {"Pages": 5}

        count = document_processor.get_page_count(sample_pdf_bytes, FileType.PDF)

        assert count == 5

    def test_get_page_count_image(self, document_processor, sample_image_bytes):
        """Test getting page count for image."""
        count = document_processor.get_page_count(sample_image_bytes, FileType.PNG)
        assert count == 1

    def test_get_page_count_csv(self, document_processor):
        """Test getting page count for CSV."""
        csv_content = b"name,amount\nJohn,100"
        count = document_processor.get_page_count(csv_content, FileType.CSV)
        assert count == 1

    def test_process_document_without_s3(self, sample_image_bytes):
        """Test processing without S3 service."""
        processor = DocumentProcessor(s3_service=None)
        file_id = "test-no-s3"

        pages = processor.process_document(sample_image_bytes, FileType.PNG, file_id)

        assert len(pages) == 1
        assert pages[0].image_data is not None  # Image stored as hex string
        assert pages[0].s3_key is None

    def test_process_corrupted_image(self, document_processor):
        """Test processing corrupted image."""
        corrupted_bytes = b"not an image"

        with pytest.raises(DocumentProcessingError) as exc_info:
            document_processor.process_document(
                corrupted_bytes, FileType.JPEG, "test-id"
            )

        assert "Failed to process image" in str(exc_info.value)

    @patch("src.services.processing.document_processor.convert_from_bytes")
    def test_process_corrupted_pdf(self, mock_convert, document_processor):
        """Test processing corrupted PDF."""
        mock_convert.side_effect = Exception("Invalid PDF")

        with pytest.raises(DocumentProcessingError) as exc_info:
            document_processor.process_document(b"not a pdf", FileType.PDF, "test-id")

        assert "Failed to process PDF" in str(exc_info.value)
