"""API request and response models."""
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Standard API response wrapper."""

    success: bool = Field(..., description="Whether the request was successful")
    data: Optional[T] = Field(None, description="Response data")
    error: Optional[str] = Field(None, description="Error message if failed")
    message: Optional[str] = Field(None, description="Additional message")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper."""

    items: List[T] = Field(..., description="Page items")
    total: int = Field(..., description="Total number of items")
    page: int = Field(1, description="Current page number")
    per_page: int = Field(20, description="Items per page")
    pages: int = Field(1, description="Total number of pages")

    model_config = {"arbitrary_types_allowed": True}


class BatchUploadRequest(BaseModel):
    """Request to start a batch upload."""

    file_names: List[str] = Field(
        ..., min_length=1, max_length=20, description="List of file names"
    )

    @property
    def file_count(self) -> int:
        """Get number of files."""
        return len(self.file_names)


class BatchProcessRequest(BaseModel):
    """Request to process uploaded files."""

    batch_id: str = Field(..., description="Batch ID to process")
    auto_deduplicate: bool = Field(
        True, description="Automatically deduplicate donations"
    )
    document_type_hint: Optional[str] = Field(
        None, description="Hint about document types"
    )


class DonationEditRequest(BaseModel):
    """Request to edit donation data."""

    donation_id: str = Field(..., description="Donation ID to edit")
    payment_info: Optional[Dict[str, Any]] = Field(None)
    payer_info: Optional[Dict[str, Any]] = Field(None)
    contact_info: Optional[Dict[str, Any]] = Field(None)


class QuickBooksSyncRequest(BaseModel):
    """Request to sync donations to QuickBooks."""

    donation_ids: List[str] = Field(..., description="List of donation IDs to sync")
    auto_create_customers: bool = Field(
        True, description="Auto-create customers if no match found"
    )
    update_addresses: bool = Field(
        True, description="Update addresses if significantly different"
    )
    deposit_account_id: Optional[str] = Field(
        None, description="QuickBooks deposit account ID"
    )


class HealthCheckResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    timestamp: str = Field(..., description="Current timestamp")
    services: Dict[str, bool] = Field(
        default_factory=dict, description="Status of dependent services"
    )


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error details"
    )
    request_id: Optional[str] = Field(None, description="Request ID for tracking")
