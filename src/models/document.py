"""Document processing models."""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class FileType(str, Enum):
    """Supported file types."""

    JPEG = "jpeg"
    JPG = "jpg"
    PNG = "png"
    PDF = "pdf"
    CSV = "csv"


class ProcessingStatus(str, Enum):
    """Document processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIALLY_FAILED = "partially_failed"


class UploadedFile(BaseModel):
    """Uploaded file metadata."""

    file_id: str = Field(..., description="Unique file identifier")
    original_name: str = Field(..., description="Original file name")
    file_type: FileType = Field(..., description="File type")
    file_size: int = Field(..., description="File size in bytes")
    s3_key: str = Field(..., description="S3 storage key")
    s3_url: Optional[str] = Field(None, description="S3 presigned URL")
    uploaded_by: str = Field(..., description="User who uploaded the file")
    uploaded_at: datetime = Field(default_factory=datetime.now)
    page_count: Optional[int] = Field(None, description="Number of pages (for PDFs)")

    @field_validator("file_size")
    @classmethod
    def validate_file_size(cls, v: int) -> int:
        """Validate file size (max 20MB)."""
        max_size = 20 * 1024 * 1024  # 20MB
        if v > max_size:
            raise ValueError(f"File size exceeds maximum of {max_size} bytes")
        return v


class DocumentPage(BaseModel):
    """Single page of a document for processing."""

    page_id: str = Field(..., description="Unique page identifier")
    file_id: str = Field(..., description="Parent file ID")
    page_number: int = Field(..., description="Page number (1-indexed)")
    image_data: Optional[str] = Field(
        None, description="Base64 encoded image data"
    )  # For API calls
    s3_key: Optional[str] = Field(None, description="S3 key for page image")
    processing_status: ProcessingStatus = Field(
        ProcessingStatus.PENDING, description="Page processing status"
    )
    extraction_result: Optional[Dict[str, Any]] = Field(
        None, description="Raw extraction result from Gemini"
    )
    error_message: Optional[str] = Field(None, description="Error message if failed")
    processed_at: Optional[datetime] = Field(None)


class FileUploadRequest(BaseModel):
    """Request to upload files."""

    files: List[str] = Field(
        ..., description="List of file names to get upload URLs for"
    )
    batch_id: Optional[str] = Field(None, description="Associated batch ID")

    @field_validator("files")
    @classmethod
    def validate_file_count(cls, v: List[str]) -> List[str]:
        """Validate number of files (max 20)."""
        if len(v) > 20:
            raise ValueError("Maximum 20 files allowed per upload")
        return v


class FileUploadResponse(BaseModel):
    """Response with presigned upload URLs."""

    upload_urls: Dict[str, str] = Field(
        ..., description="Map of filename to presigned upload URL"
    )
    file_ids: Dict[str, str] = Field(
        ..., description="Map of filename to assigned file ID"
    )
    batch_id: str = Field(..., description="Batch ID for this upload")
    expires_at: datetime = Field(..., description="When URLs expire")


class CompleteUploadRequest(BaseModel):
    """Request to complete file upload."""

    batch_id: str = Field(..., description="Batch ID")
    file_metadata: List[Dict[str, Any]] = Field(..., description="File metadata")


class ProcessingTask(BaseModel):
    """Task for processing a document."""

    task_id: str = Field(..., description="Celery task ID")
    file_id: str = Field(..., description="File to process")
    page_numbers: Optional[List[int]] = Field(
        None, description="Specific pages to process"
    )
    status: ProcessingStatus = Field(ProcessingStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = Field(None)
    completed_at: Optional[datetime] = Field(None)
    result: Optional[Dict[str, Any]] = Field(None)
    error: Optional[str] = Field(None)


class GeminiExtractionRequest(BaseModel):
    """Request to Gemini API for extraction."""

    image_data: str = Field(..., description="Base64 encoded image")
    prompt: str = Field(..., description="Extraction prompt")
    document_type: Optional[str] = Field(None, description="Hint about document type")
    include_confidence: bool = Field(
        True, description="Whether to include confidence scores"
    )


class GeminiExtractionResponse(BaseModel):
    """Response from Gemini API."""

    payment_info: Optional[Dict[str, Any]] = Field(None)
    payer_info: Optional[Dict[str, Any]] = Field(None)
    contact_info: Optional[Dict[str, Any]] = Field(None)
    confidence_scores: Optional[Dict[str, float]] = Field(None)
    document_type: Optional[str] = Field(None)
    raw_response: Optional[Dict[str, Any]] = Field(
        None, description="Raw API response for debugging"
    )
