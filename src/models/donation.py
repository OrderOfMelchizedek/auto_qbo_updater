"""Donation data models."""
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class DocumentType(str, Enum):
    """Supported document types."""

    CHECK = "check"
    ENVELOPE = "envelope"
    LETTER = "letter"
    CSV = "csv"
    UNKNOWN = "unknown"


class PaymentMethod(str, Enum):
    """Payment methods for donations."""

    CHECK = "check"
    CASH = "cash"
    CREDIT_CARD = "credit_card"
    ELECTRONIC = "electronic"
    OTHER = "other"


class ConfidenceLevel(str, Enum):
    """Confidence levels for extracted data."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PaymentInfo(BaseModel):
    """Payment information extracted from documents."""

    amount: Decimal = Field(..., description="Donation amount", decimal_places=2)
    check_number: Optional[str] = Field(None, description="Check or payment number")
    payment_date: Optional[date] = Field(None, description="Date of payment")
    payment_method: PaymentMethod = Field(
        PaymentMethod.CHECK, description="Method of payment"
    )
    memo: Optional[str] = Field(None, description="Memo or note on payment")

    @field_validator("check_number")
    @classmethod
    def clean_check_number(cls, v: Optional[str]) -> Optional[str]:
        """Strip leading zeros from check numbers if length > 4."""
        if v and len(v) > 4:
            return v.lstrip("0")
        return v

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        """Ensure amount is positive."""
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v


class PayerInfo(BaseModel):
    """Payer/donor information."""

    name: str = Field(..., description="Donor name (individual or organization)")
    organization: Optional[str] = Field(None, description="Organization name if any")
    aliases: List[str] = Field(
        default_factory=list, description="Alternative names or spellings"
    )


class Address(BaseModel):
    """Physical address model."""

    street1: Optional[str] = Field(None, description="Street address line 1")
    street2: Optional[str] = Field(None, description="Street address line 2")
    city: Optional[str] = Field(None, description="City")
    state: Optional[str] = Field(None, description="State/Province")
    postal_code: Optional[str] = Field(None, description="ZIP/Postal code")
    country: Optional[str] = Field(default="US", description="Country code")

    @field_validator("postal_code")
    @classmethod
    def validate_postal_code(cls, v: Optional[str]) -> Optional[str]:
        """Preserve leading zeros in ZIP codes."""
        if v:
            # Remove any non-alphanumeric characters
            cleaned = "".join(c for c in v if c.isalnum())
            # Validate US ZIP code format (5 or 9 digits)
            if cleaned.isdigit() and len(cleaned) in [5, 9]:
                return cleaned
        return v


class ContactInfo(BaseModel):
    """Contact information for donor."""

    address: Optional[Address] = Field(None, description="Physical address")
    email: Optional[str] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """Validate email format."""
        if v and "@" not in v:
            raise ValueError("Invalid email format")
        return v


class ExtractedDonation(BaseModel):
    """Raw donation data extracted from a document."""

    payment_info: PaymentInfo
    payer_info: PayerInfo
    contact_info: ContactInfo
    document_type: DocumentType = Field(
        DocumentType.UNKNOWN, description="Type of source document"
    )
    confidence_scores: dict[str, ConfidenceLevel] = Field(
        default_factory=dict, description="Confidence scores for each field"
    )
    source_file: str = Field(..., description="Source file name or path")
    page_number: Optional[int] = Field(None, description="Page number if multi-page")
    extraction_timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When extraction occurred",
    )


class DonationDeduplicationKey(BaseModel):
    """Key used for identifying duplicate donations."""

    check_number: Optional[str]
    amount: Decimal

    def __hash__(self) -> int:
        """Make the key hashable for use in sets/dicts."""
        return hash((self.check_number, str(self.amount)))


class MergedDonation(BaseModel):
    """Donation data after deduplication."""

    payment_info: PaymentInfo
    payer_info: PayerInfo
    contact_info: ContactInfo
    source_files: List[str] = Field(
        ..., description="All source files that contributed to this record"
    )
    merge_count: int = Field(1, description="Number of records merged")
    confidence_level: ConfidenceLevel = Field(
        ConfidenceLevel.HIGH, description="Overall confidence after merging"
    )
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class DonationBatch(BaseModel):
    """A batch of donations being processed."""

    batch_id: str = Field(..., description="Unique batch identifier")
    user_id: str = Field(..., description="User who created the batch")
    uploaded_files: List[str] = Field(..., description="List of uploaded file names")
    total_files: int = Field(..., description="Total number of files")
    processed_files: int = Field(0, description="Number of files processed")
    extracted_donations: List[ExtractedDonation] = Field(
        default_factory=list, description="Raw extracted donations"
    )
    merged_donations: List[MergedDonation] = Field(
        default_factory=list, description="Donations after deduplication"
    )
    status: str = Field("pending", description="Batch processing status")
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = Field(None)


class DonationFilter(BaseModel):
    """Filter criteria for querying donations."""

    batch_id: Optional[str] = None
    user_id: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    amount_min: Optional[Decimal] = None
    amount_max: Optional[Decimal] = None
    donor_name: Optional[str] = None
    check_number: Optional[str] = None
