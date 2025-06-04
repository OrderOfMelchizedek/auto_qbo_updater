"""Unit tests for donation models."""
from datetime import date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.models.donation import (
    Address,
    ConfidenceLevel,
    ContactInfo,
    DocumentType,
    DonationDeduplicationKey,
    ExtractedDonation,
    PayerInfo,
    PaymentInfo,
    PaymentMethod,
)


def test_payment_info_validation():
    """Test PaymentInfo model validation."""
    # Valid payment info
    payment = PaymentInfo(
        amount=Decimal("100.50"),
        check_number="1234",
        payment_date=date.today(),
        payment_method=PaymentMethod.CHECK,
    )
    assert payment.amount == Decimal("100.50")
    assert payment.check_number == "1234"

    # Test check number cleaning
    payment = PaymentInfo(
        amount=Decimal("50.00"),
        check_number="00001234",
    )
    assert payment.check_number == "1234"

    # Test invalid amount
    with pytest.raises(ValidationError):
        PaymentInfo(amount=Decimal("-10.00"))

    with pytest.raises(ValidationError):
        PaymentInfo(amount=Decimal("0"))


def test_address_validation():
    """Test Address model validation."""
    # Valid address
    address = Address(
        street1="123 Main St",
        city="Springfield",
        state="IL",
        postal_code="62701",
    )
    assert address.postal_code == "62701"

    # Test ZIP code cleaning
    address = Address(postal_code="12345-6789")
    assert address.postal_code == "123456789"

    # Test ZIP with leading zeros
    address = Address(postal_code="01234")
    assert address.postal_code == "01234"


def test_contact_info_validation():
    """Test ContactInfo model validation."""
    # Valid contact info
    contact = ContactInfo(
        email="donor@example.com",
        phone="555-123-4567",
    )
    assert contact.email == "donor@example.com"

    # Invalid email
    with pytest.raises(ValidationError):
        ContactInfo(email="not-an-email")


def test_extracted_donation():
    """Test ExtractedDonation model."""
    donation = ExtractedDonation(
        payment_info=PaymentInfo(amount=Decimal("100.00")),
        payer_info=PayerInfo(name="John Doe"),
        contact_info=ContactInfo(),
        document_type=DocumentType.CHECK,
        confidence_scores={"amount": ConfidenceLevel.HIGH},
        source_file="check_001.jpg",
    )

    assert donation.payment_info.amount == Decimal("100.00")
    assert donation.payer_info.name == "John Doe"
    assert donation.document_type == DocumentType.CHECK
    assert isinstance(donation.extraction_timestamp, datetime)


def test_donation_deduplication_key():
    """Test DonationDeduplicationKey."""
    key1 = DonationDeduplicationKey(
        check_number="1234",
        amount=Decimal("100.00"),
    )
    key2 = DonationDeduplicationKey(
        check_number="1234",
        amount=Decimal("100.00"),
    )
    key3 = DonationDeduplicationKey(
        check_number="5678",
        amount=Decimal("100.00"),
    )

    # Same keys should be equal
    assert key1 == key2
    assert hash(key1) == hash(key2)

    # Different keys should not be equal
    assert key1 != key3
    assert hash(key1) != hash(key3)

    # Should work in sets
    keys_set = {key1, key2, key3}
    assert len(keys_set) == 2  # key1 and key2 are duplicates
