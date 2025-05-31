"""
Pydantic models for payment data extraction using Gemini structured outputs.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, validator


class PaymentMethod(str, Enum):
    """Types of payment methods supported."""

    HANDWRITTEN_CHECK = "handwritten_check"
    PRINTED_CHECK = "printed_check"
    ONLINE_PAYMENT = "online_payment"


class DepositMethod(str, Enum):
    """Methods for depositing payments."""

    ATM_DEPOSIT = "ATM Deposit"
    MOBILE_DEPOSIT = "Mobile Deposit"
    ONLINE = "Online"
    ONLINE_STRIPE = "Online - Stripe"
    ONLINE_PAYPAL = "Online - PayPal"


class PaymentInfo(BaseModel):
    """Payment transaction details."""

    payment_method: PaymentMethod = Field(
        description="Type of payment: handwritten_check, printed_check, or online_payment"
    )
    check_no: Optional[str] = Field(None, description="Check number (required for check payments)")
    payment_ref: Optional[str] = Field(None, description="Payment reference number (required for online payments)")
    amount: float = Field(gt=0, description="Payment amount in dollars")
    payment_date: Optional[str] = Field(None, description="Date payment was made (format: YYYY-MM-DD)")
    check_date: Optional[str] = Field(None, description="Date written on check (format: YYYY-MM-DD)")
    postmark_date: Optional[str] = Field(None, description="Postmark date from envelope (format: YYYY-MM-DD)")
    deposit_date: Optional[str] = Field(None, description="Date deposited to bank (format: YYYY-MM-DD)")
    deposit_method: Optional[str] = Field(None, description="Method of deposit")
    memo: Optional[str] = Field(None, description="Any memo or notes from check or envelope")

    @validator("check_no")
    def validate_check_no(cls, v, values):
        """Ensure check number is provided for check payments."""
        if "payment_method" in values and values["payment_method"] in [
            PaymentMethod.HANDWRITTEN_CHECK,
            PaymentMethod.PRINTED_CHECK,
        ]:
            if not v:
                raise ValueError("Check number is required for check payments")
        return v

    @validator("payment_ref")
    def validate_payment_ref(cls, v, values):
        """Ensure payment reference is provided for online payments."""
        if "payment_method" in values and values["payment_method"] == PaymentMethod.ONLINE_PAYMENT:
            if not v:
                raise ValueError("Payment reference is required for online payments")
        return v

    @validator("payment_date", "check_date", "postmark_date", "deposit_date")
    def validate_date_format(cls, v):
        """Validate date format is YYYY-MM-DD."""
        if v:
            try:
                datetime.strptime(v, "%Y-%m-%d")
            except ValueError:
                # Try to parse common formats and convert
                for fmt in ["%m/%d/%Y", "%m-%d-%Y", "%m/%d/%y", "%m-%d-%y"]:
                    try:
                        dt = datetime.strptime(v, fmt)
                        return dt.strftime("%Y-%m-%d")
                    except ValueError:
                        continue
                raise ValueError(f"Date must be in YYYY-MM-DD format, got: {v}")
        return v


class PayerInfo(BaseModel):
    """Information about the payer (individual or organization)."""

    aliases: Optional[List[str]] = Field(None, description="List of name variations for individual payers")
    salutation: Optional[str] = Field(None, description="Title/salutation (Mr., Ms., Dr., etc.)")
    organization_name: Optional[str] = Field(None, description="Organization name if applicable")

    @validator("organization_name", always=True)
    def validate_payer_type(cls, v, values):
        """Ensure either aliases or organization_name is provided."""
        # Check if we have any payer info at all
        aliases = values.get("aliases")
        has_aliases = aliases is not None and len(aliases) > 0
        has_org = v is not None and v.strip() if isinstance(v, str) else False

        if not has_aliases and not has_org:
            raise ValueError("Either aliases (for individuals) or organization_name must be provided")
        return v

    @validator("aliases")
    def clean_aliases(cls, v):
        """Remove duplicates and empty strings from aliases."""
        if v:
            # Remove empty strings and duplicates while preserving order
            seen = set()
            cleaned = []
            for alias in v:
                if alias and alias.strip() and alias not in seen:
                    seen.add(alias)
                    cleaned.append(alias.strip())
            return cleaned if cleaned else None
        return v


class ContactInfo(BaseModel):
    """Contact information for the payer."""

    address_line_1: Optional[str] = Field(None, description="Street address")
    city: Optional[str] = Field(None, description="City")
    state: Optional[str] = Field(None, description="Two-letter state code")
    zip: Optional[str] = Field(None, description="5-digit ZIP code as text")
    email: Optional[str] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")

    @validator("state")
    def validate_state(cls, v):
        """Ensure state is a 2-letter code."""
        if v:
            v = v.strip().upper()
            if len(v) != 2:
                # Try to extract 2-letter code from longer strings
                if len(v) > 2:
                    # Handle cases like "MI 49866" or "Michigan"
                    parts = v.split()
                    for part in parts:
                        if len(part) == 2 and part.isalpha():
                            return part
                return None  # Invalid state code
            return v
        return v

    @validator("zip")
    def validate_zip(cls, v):
        """Ensure ZIP code is properly formatted."""
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


class PaymentRecord(BaseModel):
    """Complete payment record combining all information."""

    payment_info: PaymentInfo
    payer_info: PayerInfo
    contact_info: ContactInfo
    source_document_type: Optional[str] = Field(
        None, description="Type of source document (check_image, envelope, user_record, csv)"
    )
