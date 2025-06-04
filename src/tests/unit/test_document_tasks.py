"""Tests for document processing Celery tasks."""
from unittest.mock import MagicMock, patch

import pytest

from src.models.document import DocumentPage, FileType


@pytest.fixture
def sample_page():
    """Sample document page."""
    return DocumentPage(
        page_id="page_123",
        file_id="file_123",
        page_number=1,
        s3_key="processed/file_123/page_1.png",
    )


@pytest.fixture
def sample_extraction_result():
    """Sample extraction result."""
    return {
        "payment_info": {
            "payment_method": "check",
            "check_no": "1234",
            "amount": 100.00,
            "payment_date": "2025-01-15",
        },
        "payer_info": {
            "name": "John Doe",
            "aliases": ["John Doe"],
            "salutation": "Mr.",
        },
        "contact_info": {
            "address_line_1": "123 Main St",
            "city": "Anytown",
            "state": "CA",
            "zip": "12345",
        },
        "confidence_scores": {
            "amount": 1.0,
            "check_no": 0.95,
        },
        "document_type": "check",
    }


class TestDocumentTasks:
    """Test document processing tasks."""

    @patch("src.workers.tasks.document_tasks.process_single_document")
    def test_process_document_batch_success(self, mock_process_single):
        """Test successful batch processing."""
        # Import here to avoid issues with patching
        from src.workers.tasks.document_tasks import process_document_batch

        # Setup mock
        mock_process_single.s.return_value.apply_async.return_value.get.return_value = {
            "status": "success",
            "file_id": "file_123",
            "extraction_results": {},
        }

        # Create a mock for the group result
        with patch("src.workers.tasks.document_tasks.group") as mock_group:
            mock_result = MagicMock()
            mock_result.get.return_value = [
                {"status": "success", "file_id": "file_1"},
                {"status": "success", "file_id": "file_2"},
                {"status": "failed", "file_id": "file_3"},
            ]
            mock_group.return_value.apply_async.return_value = mock_result

            # Test batch processing
            result = process_document_batch(
                batch_id="batch_123",
                file_ids=["file_1", "file_2", "file_3"],
                user_id="user_123",
            )

            assert result["batch_id"] == "batch_123"
            assert result["total_files"] == 3
            assert result["successful"] == 2
            assert result["failed"] == 1

    @patch("src.workers.tasks.document_tasks.S3Service")
    @patch("src.workers.tasks.document_tasks.DocumentProcessor")
    @patch("src.workers.tasks.document_tasks.process_document_page")
    def test_process_single_document_success(
        self, mock_process_page, mock_processor_class, mock_s3_class
    ):
        """Test successful single document processing."""
        # Setup mock instances
        mock_s3 = MagicMock()
        mock_s3.download_file.return_value = b"fake image data"
        mock_s3_class.return_value = mock_s3

        mock_processor = MagicMock()
        mock_processor.process_document.return_value = [
            DocumentPage(
                page_id="page_1",
                file_id="file_123",
                page_number=1,
                s3_key="processed/file_123/page_1.png",
            )
        ]
        mock_processor_class.return_value = mock_processor

        mock_process_page.apply_async.return_value.get.return_value = {
            "status": "success",
            "extraction": {"payment_info": {"amount": 100}},
        }

        # Import and test
        from src.workers.tasks.document_tasks import process_single_document

        result = process_single_document(
            file_id="file_123", batch_id="batch_123", user_id="user_123"
        )

        assert result["status"] == "success"
        assert result["file_id"] == "file_123"
        assert result["page_count"] == 1

    @pytest.mark.skip(reason="Requires Redis connection - skipping in CI")
    @patch("src.workers.tasks.document_tasks.S3Service")
    def test_process_single_document_failure(self, mock_s3_class):
        """Test document processing failure."""
        # This test requires actual Redis connection since Celery tasks
        # use Redis for result backend
        pass

    @patch("src.workers.tasks.document_tasks.S3Service")
    @patch("src.workers.tasks.document_tasks.GeminiExtractor")
    def test_process_document_page_image(
        self, mock_extractor_class, mock_s3_class, sample_page, sample_extraction_result
    ):
        """Test processing an image page."""
        # Setup mocks
        mock_s3 = MagicMock()
        mock_s3.download_file.return_value = b"fake image data"
        mock_s3_class.return_value = mock_s3

        mock_extractor = MagicMock()
        mock_response = MagicMock()
        mock_response.model_dump.return_value = sample_extraction_result
        mock_extractor.extract_from_image.return_value = mock_response
        mock_extractor_class.return_value = mock_extractor

        from src.workers.tasks.document_tasks import process_document_page

        result = process_document_page(
            page_data=sample_page.model_dump(), file_type=FileType.PNG
        )

        assert result["status"] == "success"
        assert result["page_id"] == "page_123"
        assert result["extraction"] == sample_extraction_result

    def test_process_document_page_csv(self):
        """Test processing a CSV page."""
        from src.workers.tasks.document_tasks import process_document_page

        csv_page = DocumentPage(
            page_id="csv_page_1",
            file_id="csv_file_123",
            page_number=1,
            extraction_result={"csv_content": "name,amount\nJohn,100"},
        )

        result = process_document_page(
            page_data=csv_page.model_dump(), file_type=FileType.CSV
        )

        assert result["status"] == "success"
        assert result["extraction"]["csv_content"] == "name,amount\nJohn,100"

    def test_aggregate_page_results_success(self, sample_extraction_result):
        """Test successful aggregation of page results."""
        from src.workers.tasks.document_tasks import aggregate_page_results

        page_results = [
            {
                "status": "success",
                "extraction": sample_extraction_result,
            }
        ]

        result = aggregate_page_results(page_results)

        assert result["payment_info"] is not None
        assert result["payment_info"]["amount"] == 100.00
        assert result["payer_info"] is not None
        assert result["payer_info"]["name"] == "John Doe"
        assert result["contact_info"] is not None
        assert result["confidence_scores"] is not None

    def test_aggregate_page_results_no_success(self):
        """Test aggregation with no successful extractions."""
        from src.workers.tasks.document_tasks import aggregate_page_results

        page_results = [
            {"status": "failed", "error": "Extraction failed"},
            {"status": "failed", "error": "Another failure"},
        ]

        result = aggregate_page_results(page_results)

        assert result["payment_info"] is None
        assert result["payer_info"] is None
        assert result["contact_info"] is None
        assert "No successful extractions" in result["error"]

    @patch("celery.result.AsyncResult")
    def test_check_extraction_status(self, mock_async_result):
        """Test checking extraction task status."""
        from src.workers.tasks.document_tasks import check_extraction_status

        # Setup mock
        mock_result = MagicMock()
        mock_result.status = "SUCCESS"
        mock_result.ready.return_value = True
        mock_result.successful.return_value = True
        mock_result.result = {"extraction": "data"}
        mock_async_result.return_value = mock_result

        # Test status check
        result = check_extraction_status("task_123")

        assert result["task_id"] == "task_123"
        assert result["status"] == "SUCCESS"
        assert result["ready"] is True
        assert result["successful"] is True
        assert result["result"] == {"extraction": "data"}
