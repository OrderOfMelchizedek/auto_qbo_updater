"""
Pydantic models for QuickBooks Online customer data and matching.
"""

from typing import List, Optional, Union

from pydantic import BaseModel, Field, validator


class QBCustomer(BaseModel):
    """QuickBooks Online customer data."""

    customer_lookup: str = Field(description="Unique QB customer identifier")
    first_name: Optional[str] = Field(None, description="Customer first name")
    last_name: Optional[str] = Field(None, description="Customer last name")
    full_name: Optional[str] = Field(None, description="Customer full name")
    qb_organization_name: Optional[str] = Field(None, description="Organization name in QB")
    qb_address_line_1: Optional[str] = Field(None, description="QB address line 1")
    qb_city: Optional[str] = Field(None, description="QB city")
    qb_state: Optional[str] = Field(None, description="QB state")
    qb_zip: Optional[str] = Field(None, description="QB ZIP code")
    qb_email: Optional[Union[str, List[str]]] = Field(None, description="QB email(s)")
    qb_phone: Optional[Union[str, List[str]]] = Field(None, description="QB phone(s)")

    @validator("qb_zip")
    def validate_qb_zip(cls, v):
        """Ensure QB ZIP code is properly formatted."""
        if v:
            # Remove any non-numeric characters
            cleaned = "".join(c for c in v if c.isdigit())
            if len(cleaned) >= 5:
                # Take first 5 digits (ignore +4 extension)
                return cleaned[:5]
            elif len(cleaned) < 5:
                # Pad with leading zeros if needed
                return cleaned.zfill(5)
        return v

    @validator("qb_email", "qb_phone")
    def normalize_contact_lists(cls, v):
        """Ensure email and phone are consistently formatted as lists when multiple."""
        if v:
            if isinstance(v, str):
                return v.strip()
            elif isinstance(v, list):
                # Clean and deduplicate
                cleaned = [item.strip() for item in v if item and item.strip()]
                return cleaned if len(cleaned) > 1 else (cleaned[0] if cleaned else None)
        return v


class AddressComparison(BaseModel):
    """Result of address comparison between extracted and QB data."""

    needs_update: bool = Field(description="Whether QB address needs updating")
    similarity_score: float = Field(description="Address similarity score (0-1)")
    differences: List[str] = Field(description="List of differences found")
    recommended_action: str = Field(description="Recommended action to take")


class ContactUpdate(BaseModel):
    """Recommended updates for contact information."""

    email_updates: Optional[List[str]] = Field(None, description="New emails to add to QB")
    phone_updates: Optional[List[str]] = Field(None, description="New phones to add to QB")
    address_update: Optional[dict] = Field(None, description="New address to update in QB")
    update_reason: str = Field(description="Reason for the update")


class CustomerMatchResult(BaseModel):
    """Result of customer matching operation."""

    matched: bool = Field(description="Whether a customer match was found")
    confidence_score: float = Field(description="Match confidence (0-1)")
    qb_customer: Optional[QBCustomer] = Field(None, description="Matched QB customer data")
    match_method: str = Field(description="How the match was determined")
    alternatives: Optional[List[QBCustomer]] = Field(None, description="Alternative matches")
    needs_new_customer: bool = Field(False, description="Whether to create new customer")
