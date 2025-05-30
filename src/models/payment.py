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

    def to_legacy_format(self) -> dict:
        """Convert to legacy donation format for backward compatibility."""
        legacy = {
            # Payment info mappings
            "Check No.": self.payment_info.check_no,
            "Gift Amount": str(self.payment_info.amount),
            "Check Date": self.payment_info.check_date,
            "Deposit Date": self.payment_info.deposit_date,
            "Deposit Method": self.payment_info.deposit_method or "ATM Deposit",
            "Memo": self.payment_info.memo,
            # Payer info mappings
            "Salutation": self.payer_info.salutation,
            "Organization Name": self.payer_info.organization_name,
            # Contact info mappings
            "Address - Line 1": self.contact_info.address_line_1,
            "City": self.contact_info.city,
            "State": self.contact_info.state,
            "ZIP": self.contact_info.zip,
            # Handle donor name from aliases or organization
            "Donor Name": None,
            "First Name": None,
            "Last Name": None,
            "Full Name": None,
            # Legacy fields that don't have direct mappings
            "customerLookup": None,
        }

        # Set donor name based on payer type
        if self.payer_info.organization_name:
            legacy["Donor Name"] = self.payer_info.organization_name
            legacy["Organization Name"] = self.payer_info.organization_name
        elif self.payer_info.aliases and len(self.payer_info.aliases) > 0:
            # Use first alias as donor name
            primary_name = self.payer_info.aliases[0]
            legacy["Donor Name"] = primary_name

            # Try to extract first/last name from primary alias
            name_parts = primary_name.split()
            if len(name_parts) >= 2:
                # Handle "Last, First" format
                if "," in primary_name:
                    last_first = primary_name.split(",", 1)
                    if len(last_first) == 2:
                        legacy["Last Name"] = last_first[0].strip()
                        legacy["First Name"] = last_first[1].strip()
                else:
                    # Assume "First Last" format
                    legacy["First Name"] = name_parts[0]
                    legacy["Last Name"] = " ".join(name_parts[1:])
            elif len(name_parts) == 1:
                legacy["Last Name"] = name_parts[0]

        return legacy

    @classmethod
    def from_legacy_format(cls, legacy_data: dict) -> "PaymentRecord":
        """Create PaymentRecord from legacy donation format."""
        # Determine payment method
        payment_method = PaymentMethod.HANDWRITTEN_CHECK  # Default
        if legacy_data.get("Payment Method"):
            method_map = {
                "handwritten check": PaymentMethod.HANDWRITTEN_CHECK,
                "printed check": PaymentMethod.PRINTED_CHECK,
                "online payment": PaymentMethod.ONLINE_PAYMENT,
            }
            payment_method = method_map.get(legacy_data["Payment Method"].lower(), PaymentMethod.HANDWRITTEN_CHECK)

        # Extract amount
        amount_str = legacy_data.get("Gift Amount", "0")
        try:
            amount = float(str(amount_str).replace("$", "").replace(",", ""))
        except ValueError:
            amount = 0.0

        # Determine payment date
        payment_date = legacy_data.get("Check Date") or legacy_data.get("Deposit Date") or ""

        # Build aliases from name fields
        aliases = []
        donor_name = legacy_data.get("Donor Name")
        if donor_name:
            aliases.append(donor_name)

        # Add variations based on first/last name
        first_name = legacy_data.get("First Name")
        last_name = legacy_data.get("Last Name")
        if first_name and last_name:
            aliases.extend(
                [
                    f"{first_name} {last_name}",
                    f"{last_name}, {first_name}",
                ]
            )

        # Determine if organization
        org_name = legacy_data.get("Organization Name")

        return cls(
            payment_info=PaymentInfo(
                payment_method=payment_method,
                check_no=legacy_data.get("Check No."),
                payment_ref=legacy_data.get("Payment Ref"),
                amount=amount,
                payment_date=payment_date,
                check_date=legacy_data.get("Check Date"),
                postmark_date=legacy_data.get("Postmark Date"),
                deposit_date=legacy_data.get("Deposit Date"),
                deposit_method=legacy_data.get("Deposit Method"),
                memo=legacy_data.get("Memo"),
            ),
            payer_info=PayerInfo(
                aliases=aliases if not org_name else None,
                salutation=legacy_data.get("Salutation"),
                organization_name=org_name,
            ),
            contact_info=ContactInfo(
                address_line_1=legacy_data.get("Address - Line 1"),
                city=legacy_data.get("City"),
                state=legacy_data.get("State"),
                zip=legacy_data.get("ZIP"),
                email=legacy_data.get("Email"),
                phone=legacy_data.get("Phone"),
            ),
            source_document_type=legacy_data.get("source_document_type"),
        )
