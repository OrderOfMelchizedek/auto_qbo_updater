"""Letter generation models."""
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class LetterTemplate(BaseModel):
    """Letter template configuration."""

    template_id: str = Field(..., description="Unique template identifier")
    name: str = Field(..., description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    html_template: str = Field(..., description="Jinja2 HTML template")
    css_styles: Optional[str] = Field(None, description="CSS styles for the template")
    merge_fields: List[str] = Field(
        default_factory=list, description="Available merge fields"
    )
    is_default: bool = Field(False, description="Is this the default template")
    created_by: str = Field(..., description="User who created the template")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class LetterData(BaseModel):
    """Data for generating a letter."""

    # Organization info
    organization_name: str = Field(..., description="Organization name")
    organization_address: str = Field(..., description="Organization address")
    organization_ein: Optional[str] = Field(None, description="Organization EIN")
    organization_phone: Optional[str] = Field(None, description="Organization phone")

    # Donor info
    donor_name: str = Field(..., description="Donor name")
    donor_address: Optional[str] = Field(None, description="Donor address")

    # Donation info
    donation_amount: str = Field(..., description="Formatted donation amount")
    donation_date: str = Field(..., description="Formatted donation date")
    check_number: Optional[str] = Field(None, description="Check number")

    # Letter info
    letter_date: str = Field(
        default="",  # Will be set in __init__ if not provided
        description="Letter date",
    )
    tax_year: int = Field(
        default=0, description="Tax year"  # Will be set in __init__ if not provided
    )

    # IRS compliance
    no_goods_services_statement: str = Field(
        default="No goods or services were provided in exchange for this contribution.",
        description="IRS required statement",
    )

    # Additional fields
    custom_fields: Dict[str, Any] = Field(
        default_factory=dict, description="Custom merge fields"
    )

    @model_validator(mode="before")
    @classmethod
    def set_defaults(cls, values):
        """Set default values for date fields."""
        if isinstance(values, dict):
            if not values.get("letter_date"):
                values["letter_date"] = date.today().strftime("%B %d, %Y")
            if not values.get("tax_year"):
                values["tax_year"] = date.today().year
        return values


class LetterGenerationRequest(BaseModel):
    """Request to generate letters."""

    template_id: str = Field(..., description="Template to use")
    donation_ids: List[str] = Field(
        ..., description="Donations to generate letters for"
    )
    combine_pdf: bool = Field(True, description="Combine all letters into one PDF")
    include_cover_page: bool = Field(False, description="Include summary cover page")


class GeneratedLetter(BaseModel):
    """Generated letter result."""

    letter_id: str = Field(..., description="Unique letter ID")
    donation_id: str = Field(..., description="Associated donation ID")
    donor_name: str = Field(..., description="Donor name")
    html_content: str = Field(..., description="Generated HTML content")
    pdf_s3_key: Optional[str] = Field(None, description="S3 key for PDF version")
    pdf_url: Optional[str] = Field(None, description="Presigned URL for PDF download")
    generated_at: datetime = Field(default_factory=datetime.now)


class LetterBatch(BaseModel):
    """Batch of generated letters."""

    batch_id: str = Field(..., description="Unique batch ID")
    template_id: str = Field(..., description="Template used")
    letters: List[GeneratedLetter] = Field(
        default_factory=list, description="Individual letters"
    )
    combined_pdf_s3_key: Optional[str] = Field(
        None, description="S3 key for combined PDF"
    )
    combined_pdf_url: Optional[str] = Field(
        None, description="URL for combined PDF download"
    )
    total_count: int = Field(0, description="Total number of letters")
    created_by: str = Field(..., description="User who generated the batch")
    created_at: datetime = Field(default_factory=datetime.now)
