"""Letter generation models."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class OrganizationInfo(BaseModel):
    """Organization information for letters."""

    name: str = Field(..., description="Organization name")
    address_line1: str = Field(..., description="Address line 1")
    address_line2: Optional[str] = Field(None, description="Address line 2")
    city: str = Field(..., description="City")
    state: str = Field(..., description="State")
    postal_code: str = Field(..., description="ZIP code")
    phone: Optional[str] = Field(None, description="Phone number")
    email: Optional[str] = Field(None, description="Email address")
    ein: str = Field(..., description="Federal Tax ID (EIN)")
    treasurer_name: str = Field(..., description="Treasurer name")
    treasurer_title: str = Field("Treasurer", description="Treasurer title")
    mission_statement: Optional[str] = Field(
        None, description="Mission statement for letters"
    )
    logo_url: Optional[str] = Field(None, description="Logo URL for letterhead")


class LetterData(BaseModel):
    """Data for generating a letter."""

    organization: OrganizationInfo = Field(..., description="Organization info")
    donor_name: str = Field(..., description="Donor name")
    donor_address: Optional[str] = Field(None, description="Donor address")
    amount: str = Field(..., description="Donation amount")
    payment_date: str = Field(..., description="Payment date")
    check_number: Optional[str] = Field(None, description="Check number")
    custom_message: Optional[str] = Field(None, description="Custom message")


class LetterTemplate(BaseModel):
    """Letter template information."""

    template_id: str = Field(..., description="Template identifier")
    name: str = Field(..., description="Template name")
    display_name: Optional[str] = Field(None, description="Display name")
    description: str = Field(..., description="Template description")
    html_template: Optional[str] = Field(None, description="HTML template content")
    merge_fields: List[str] = Field(
        default_factory=list, description="Available merge fields"
    )
    fields: Optional[List[str]] = Field(None, description="Required template fields")
    preview_image: Optional[str] = Field(None, description="Preview image URL")
    is_default: bool = Field(False, description="Is default template")
    created_by: str = Field("system", description="Creator")


class GeneratedLetter(BaseModel):
    """Generated letter information."""

    donation_id: str = Field(..., description="Associated donation ID")
    recipient_name: str = Field(..., description="Letter recipient name")
    recipient_email: Optional[str] = Field(None, description="Recipient email")
    template_name: str = Field(..., description="Template used")
    pdf_content: Optional[bytes] = Field(None, description="PDF content")
    file_url: Optional[str] = Field(None, description="Stored file URL")
    generated_at: datetime = Field(default_factory=datetime.now)
    sent_at: Optional[datetime] = Field(None, description="When email was sent")


class LetterGenerationRequest(BaseModel):
    """Request to generate letters."""

    donation_ids: List[str] = Field(..., description="Donation IDs")
    template_name: str = Field("default_letter.html", description="Template to use")
    organization_info: OrganizationInfo = Field(..., description="Organization info")
    send_email: bool = Field(False, description="Send via email if address available")
    custom_data: Optional[dict] = Field(None, description="Custom data for template")


class LetterBatchResult(BaseModel):
    """Result of batch letter generation."""

    total_requested: int = Field(..., description="Total letters requested")
    successfully_generated: int = Field(..., description="Successfully generated")
    failed: int = Field(..., description="Failed to generate")
    letters: List[GeneratedLetter] = Field(
        default_factory=list, description="Generated letters"
    )
    errors: List[dict] = Field(default_factory=list, description="Error details")


class LetterBatch(BaseModel):
    """Batch of generated letters."""

    batch_id: str = Field(..., description="Batch identifier")
    template_id: str = Field(..., description="Template used")
    letters: List[GeneratedLetter] = Field(
        default_factory=list, description="Generated letters"
    )
    total_count: int = Field(0, description="Total letter count")
    created_by: str = Field(..., description="User who created batch")
    created_at: datetime = Field(default_factory=datetime.now)
