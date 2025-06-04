"""QuickBooks integration models."""
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MatchConfidence(str, Enum):
    """Confidence levels for QuickBooks customer matching."""

    HIGH = "high"  # Exact match or very close
    MEDIUM = "medium"  # Good match with minor differences
    LOW = "low"  # Weak match, manual review recommended
    NO_MATCH = "no_match"  # No suitable match found


class QBCustomer(BaseModel):
    """QuickBooks customer model."""

    id: str = Field(..., description="QuickBooks customer ID")
    display_name: str = Field(..., description="Customer display name")
    company_name: Optional[str] = Field(None, description="Company name")
    given_name: Optional[str] = Field(None, description="First name")
    family_name: Optional[str] = Field(None, description="Last name")
    email: Optional[str] = Field(None, description="Primary email")
    phone: Optional[str] = Field(None, description="Primary phone")
    billing_address: Optional[Dict[str, Any]] = Field(
        None, description="Billing address"
    )
    is_active: bool = Field(True, description="Customer active status")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional QB metadata"
    )


class CustomerMatch(BaseModel):
    """Result of matching a donor to QuickBooks customer."""

    qb_customer: Optional[QBCustomer] = Field(
        None, description="Matched QuickBooks customer"
    )
    confidence: MatchConfidence = Field(..., description="Match confidence level")
    score: float = Field(0.0, description="Match score (0-100)")
    match_reasons: List[str] = Field(
        default_factory=list, description="Reasons for the match"
    )


class QBSalesReceipt(BaseModel):
    """QuickBooks sales receipt model for donations."""

    customer_id: str = Field(..., description="QuickBooks customer ID")
    txn_date: str = Field(..., description="Transaction date (YYYY-MM-DD)")
    payment_method: str = Field(..., description="Payment method")
    deposit_to_account: str = Field(..., description="Deposit account ID")
    total_amount: Decimal = Field(..., description="Total receipt amount")
    line_items: List[Dict[str, Any]] = Field(..., description="Receipt line items")
    custom_fields: Optional[List[Dict[str, Any]]] = Field(
        None, description="Custom fields"
    )
    memo: Optional[str] = Field(None, description="Receipt memo")


class QBSyncResult(BaseModel):
    """Result of syncing donations to QuickBooks."""

    donation_id: str = Field(..., description="Internal donation ID")
    qb_receipt_id: Optional[str] = Field(None, description="Created QB receipt ID")
    qb_customer_id: Optional[str] = Field(None, description="QB customer ID used")
    success: bool = Field(..., description="Whether sync was successful")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    action_taken: str = Field(
        ..., description="Action taken (created, updated, skipped)"
    )
    timestamp: datetime = Field(default_factory=datetime.now)


class AddressUpdateDecision(BaseModel):
    """Decision on whether to update a customer's address."""

    should_update: bool = Field(..., description="Whether address should be updated")
    similarity_score: float = Field(..., description="Similarity score (0-100)")
    changes: List[str] = Field(
        default_factory=list, description="List of fields that would change"
    )
    current_address: Optional[Dict[str, Any]] = Field(
        None, description="Current address"
    )
    proposed_address: Optional[Dict[str, Any]] = Field(
        None, description="Proposed new address"
    )


class QBBatchSyncRequest(BaseModel):
    """Request to sync a batch of donations to QuickBooks."""

    batch_id: str = Field(..., description="Donation batch ID")
    donation_ids: List[str] = Field(..., description="IDs of donations to sync")
    deposit_account_id: Optional[str] = Field(None, description="QB deposit account ID")
    auto_create_customers: bool = Field(
        True, description="Auto-create customers if no match"
    )
    update_addresses: bool = Field(
        True, description="Update customer addresses if significantly different"
    )


class QBConfig(BaseModel):
    """QuickBooks configuration for a user/company."""

    company_id: str = Field(..., description="QuickBooks company ID")
    default_income_account_id: Optional[str] = Field(
        None, description="Default income account for donations"
    )
    default_deposit_account_id: Optional[str] = Field(
        None, description="Default deposit account"
    )
    payment_method_mappings: Dict[str, str] = Field(
        default_factory=dict,
        description="Map internal payment methods to QB payment methods",
    )
    custom_field_mappings: Dict[str, str] = Field(
        default_factory=dict, description="Map internal fields to QB custom fields"
    )
