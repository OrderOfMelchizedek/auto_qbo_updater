"""
Pydantic models for the final UI data combining extraction and QBO data.
"""

from typing import List, Optional, Union

from pydantic import BaseModel, Field

from .payment import PaymentInfo
from .qbo_customer import ContactUpdate, CustomerMatchResult, QBCustomer


class UIPayerInfo(BaseModel):
    """Final payer information combining extraction and QB data for UI display."""

    customer_lookup: Optional[str] = Field(None, description="QB customer ID if matched")
    salutation: Optional[str] = Field(None, description="Customer salutation")
    first_name: Optional[str] = Field(None, description="Customer first name")
    last_name: Optional[str] = Field(None, description="Customer last name")
    full_name: Optional[str] = Field(None, description="Customer full name")
    qb_organization_name: Optional[str] = Field(None, description="Organization name from QB")
    qb_address_line_1: Optional[str] = Field(None, description="QB address line 1")
    qb_city: Optional[str] = Field(None, description="QB city")
    qb_state: Optional[str] = Field(None, description="QB state")
    qb_zip: Optional[str] = Field(None, description="QB ZIP code")
    qb_email: Optional[Union[str, List[str]]] = Field(None, description="QB email(s)")
    qb_phone: Optional[Union[str, List[str]]] = Field(None, description="QB phone(s)")

    # Metadata about the matching and updates
    is_matched: bool = Field(False, description="Whether customer was matched in QB")
    match_confidence: Optional[float] = Field(None, description="Match confidence score")
    address_updated: bool = Field(False, description="Whether address was updated from extraction")
    contact_updated: bool = Field(False, description="Whether contact info was updated")
    is_new_customer: bool = Field(False, description="Whether this will create a new customer")


class UIPaymentInfo(BaseModel):
    """Final payment information for UI display."""

    check_no_or_payment_ref: str = Field(description="Check number or payment reference")
    amount: float = Field(description="Payment amount")
    payment_date: str = Field(description="Payment date")
    deposit_date: Optional[str] = Field(None, description="Deposit date")
    deposit_method: Optional[str] = Field(None, description="Deposit method")
    memo: Optional[str] = Field(None, description="Payment memo")


class UIPaymentRecord(BaseModel):
    """Final payment record for UI display combining all data."""

    payer_info: UIPayerInfo
    payment_info: UIPaymentInfo

    # Processing metadata
    processing_status: str = Field("pending", description="Processing status")
    warnings: List[str] = Field(default_factory=list, description="Any warnings or issues")
    extraction_source: Optional[str] = Field(None, description="Source of extraction data")
    last_updated: Optional[str] = Field(None, description="Last update timestamp")


class BatchProcessingResult(BaseModel):
    """Result of processing a batch of payment documents."""

    session_id: str = Field(description="Processing session ID")
    total_processed: int = Field(description="Total documents processed")
    successful_extractions: int = Field(description="Number of successful extractions")
    customer_matches: int = Field(description="Number of customer matches found")
    new_customers: int = Field(description="Number of new customers to create")
    address_updates: int = Field(description="Number of address updates needed")
    contact_updates: int = Field(description="Number of contact updates needed")

    records: List[UIPaymentRecord] = Field(description="Processed payment records")
    errors: List[str] = Field(default_factory=list, description="Processing errors")
    warnings: List[str] = Field(default_factory=list, description="Processing warnings")

    # Summary statistics
    total_amount: float = Field(0.0, description="Total amount of all payments")
    payment_methods: dict = Field(default_factory=dict, description="Count by payment method")
    processing_time_seconds: Optional[float] = Field(None, description="Total processing time")


class QBOSyncRequest(BaseModel):
    """Request to sync processed records with QuickBooks Online."""

    session_id: str = Field(description="Processing session ID")
    records_to_sync: List[str] = Field(description="Record IDs to sync")
    create_customers: bool = Field(True, description="Whether to create new customers")
    update_addresses: bool = Field(True, description="Whether to update customer addresses")
    update_contacts: bool = Field(True, description="Whether to update contact info")
    create_sales_receipts: bool = Field(True, description="Whether to create sales receipts")


class QBOSyncResult(BaseModel):
    """Result of syncing with QuickBooks Online."""

    session_id: str = Field(description="Processing session ID")
    customers_created: int = Field(0, description="Number of customers created")
    customers_updated: int = Field(0, description="Number of customers updated")
    sales_receipts_created: int = Field(0, description="Number of sales receipts created")

    successful_syncs: List[str] = Field(default_factory=list, description="Successfully synced record IDs")
    failed_syncs: List[dict] = Field(default_factory=list, description="Failed syncs with errors")
    warnings: List[str] = Field(default_factory=list, description="Sync warnings")

    sync_time_seconds: Optional[float] = Field(None, description="Total sync time")
