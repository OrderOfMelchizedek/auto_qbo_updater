"""
Unit tests to enforce V3 format usage and prevent legacy format regression.
"""

import json
from unittest.mock import Mock, patch

import pytest

from src.models.payment import ContactInfo, PayerInfo, PaymentInfo, PaymentRecord
from src.utils.enhanced_file_processor_v3_second_pass import EnhancedFileProcessorV3
from src.utils.payment_combiner_v2 import PaymentCombinerV2


class TestV3FormatEnforcement:
    """Enforce V3 enriched format throughout the application."""

    def test_payment_record_structure_is_v3_compliant(self):
        """Test that PaymentRecord follows V3 structure."""
        # Create a payment record
        payment = PaymentRecord(
            payer_info=PayerInfo(aliases=["John Doe"], organization_name="ACME Corp", salutation="Mr."),
            payment_info=PaymentInfo(
                payment_method="handwritten_check",
                check_no="100001",
                amount=100.00,
                check_date="2025-01-01",
                memo="Test donation",
            ),
            contact_info=ContactInfo(
                address_line_1="123 Main St",
                city="Anytown",
                state="CA",
                zip="12345",
                email="john@example.com",
                phone="555-1234",
            ),
        )

        # Verify structure
        assert hasattr(payment, "payer_info")
        assert hasattr(payment, "payment_info")
        assert hasattr(payment, "contact_info")

        # Verify payer_info structure
        assert hasattr(payment.payer_info, "aliases")
        assert hasattr(payment.payer_info, "organization_name")
        assert hasattr(payment.payer_info, "salutation")

        # Verify payment_info structure
        assert hasattr(payment.payment_info, "check_no")
        assert hasattr(payment.payment_info, "amount")
        assert hasattr(payment.payment_info, "check_date")
        assert hasattr(payment.payment_info, "memo")

        # Verify contact_info structure
        assert hasattr(payment.contact_info, "address_line_1")
        assert hasattr(payment.contact_info, "city")
        assert hasattr(payment.contact_info, "state")
        assert hasattr(payment.contact_info, "zip")
        assert hasattr(payment.contact_info, "email")
        assert hasattr(payment.contact_info, "phone")

    def test_payment_combiner_v2_output_format(self):
        """Test that PaymentCombinerV2 outputs correct V3 enriched format."""
        combiner = PaymentCombinerV2()

        # Create test payment record
        payment_record = PaymentRecord(
            payer_info=PayerInfo(aliases=["Jane Smith"], organization_name="", salutation="Ms."),
            payment_info=PaymentInfo(
                payment_method="handwritten_check",
                check_no="250001",
                amount=250.00,
                check_date="2025-01-15",
                memo="Monthly donation",
            ),
            contact_info=ContactInfo(
                address_line_1="456 Oak St",
                city="Springfield",
                state="IL",
                zip="62701",
                email="jane@example.com",
                phone="217-555-0123",
            ),
        )

        # Test without QBO customer
        result = combiner.combine_payment_data(payment_record, None, "New")

        # Verify V3 enriched format structure
        assert isinstance(result, dict)

        # Must have V3 top-level keys
        required_keys = ["payer_info", "payment_info", "match_status", "qbo_customer_id"]
        for key in required_keys:
            assert key in result, f"Missing required V3 key: {key}"

        # Verify payer_info structure
        payer_info = result["payer_info"]
        required_payer_keys = [
            "customer_lookup",
            "qb_address_line_1",
            "qb_city",
            "qb_state",
            "qb_zip",
            "qb_email",
            "qb_phone",
            "address_needs_update",
            "extracted_address",
        ]
        for key in required_payer_keys:
            assert key in payer_info, f"Missing required payer_info key: {key}"

        # Verify payment_info structure
        payment_info = result["payment_info"]
        required_payment_keys = [
            "check_no_or_payment_ref",
            "amount",
            "payment_date",
            "deposit_date",
            "deposit_method",
            "memo",
        ]
        for key in required_payment_keys:
            assert key in payment_info, f"Missing required payment_info key: {key}"

        # Verify values
        assert payer_info["customer_lookup"] == "Jane Smith"
        assert payer_info["qb_address_line_1"] == "456 Oak St"
        assert payer_info["qb_city"] == "Springfield"
        assert payer_info["qb_state"] == "IL"
        assert payer_info["qb_zip"] == "62701"
        assert payer_info["qb_email"] == ["jane@example.com"]
        assert payer_info["qb_phone"] == ["217-555-0123"]

        assert payment_info["check_no_or_payment_ref"] == "250001"
        assert payment_info["amount"] == 250.00
        assert payment_info["payment_date"] == "2025-01-15"
        assert payment_info["memo"] == "Monthly donation"

        assert result["match_status"] == "New"
        assert result["qbo_customer_id"] is None

    def test_payment_combiner_v2_with_qbo_customer(self):
        """Test PaymentCombinerV2 with QBO customer data."""
        combiner = PaymentCombinerV2()

        # Create test payment record
        payment_record = PaymentRecord(
            payer_info=PayerInfo(aliases=["Bob Johnson"], organization_name="", salutation="Mr."),
            payment_info=PaymentInfo(
                payment_method="handwritten_check", check_no="500001", amount=500.00, check_date="2025-02-01"
            ),
            contact_info=ContactInfo(
                address_line_1="789 Pine Ave", city="Columbus", state="OH", zip="43215", email="bob@example.com"
            ),
        )

        # Mock QBO customer
        qbo_customer = {
            "Id": "123",
            "DisplayName": "Johnson, Bob",
            "GivenName": "Bob",
            "FamilyName": "Johnson",
            "CompanyName": "",
            "BillAddr": {
                "Line1": "789 Pine Avenue",  # Slightly different format
                "City": "Columbus",
                "CountrySubDivisionCode": "OH",
                "PostalCode": "43215",
            },
            "PrimaryEmailAddr": {"Address": "bob.johnson@example.com"},  # Different email
            "SyncToken": "5",
        }

        # Test with QBO customer
        result = combiner.combine_payment_data(payment_record, qbo_customer, "Matched")

        # Verify enriched format with QBO data
        assert result["match_status"] == "Matched"
        assert result["qbo_customer_id"] == "123"
        assert result["qbo_sync_token"] == "5"

        # Verify QBO data is used
        payer_info = result["payer_info"]
        assert payer_info["customer_lookup"] == "Johnson, Bob"
        assert payer_info["first_name"] == "Bob"
        assert payer_info["last_name"] == "Johnson"
        assert payer_info["qb_address_line_1"] == "789 Pine Avenue"

        # Should detect email difference
        assert len(payer_info["qb_email"]) == 2  # Both emails included
        assert "bob@example.com" in payer_info["qb_email"]
        assert "bob.johnson@example.com" in payer_info["qb_email"]

    def test_enriched_format_serialization(self):
        """Test that enriched format can be properly serialized to JSON."""
        combiner = PaymentCombinerV2()

        # Create test data
        payment_record = PaymentRecord(
            payer_info=PayerInfo(aliases=["Test User"], organization_name="Test Org", salutation=""),
            payment_info=PaymentInfo(
                payment_method="handwritten_check", check_no="999888", amount=75.50, check_date="2025-03-01"
            ),
            contact_info=ContactInfo(address_line_1="321 Test St", city="Testville", state="TX", zip="75001"),
        )

        # Create enriched format
        enriched = combiner.combine_payment_data(payment_record, None, "New")

        # Test JSON serialization
        json_str = json.dumps(enriched)
        deserialized = json.loads(json_str)

        # Verify structure is preserved
        assert "payer_info" in deserialized
        assert "payment_info" in deserialized
        assert "match_status" in deserialized

        # Verify data integrity
        assert deserialized["payer_info"]["customer_lookup"] == "Test Org"
        assert deserialized["payment_info"]["amount"] == 75.50
        assert deserialized["match_status"] == "New"

    def test_no_legacy_field_names_in_v3_output(self):
        """Test that V3 components never output legacy field names."""
        combiner = PaymentCombinerV2()

        # Test with various inputs
        test_cases = [
            # Simple individual
            PaymentRecord(
                payer_info=PayerInfo(aliases=["John Doe"], organization_name="", salutation=""),
                payment_info=PaymentInfo(
                    payment_method="handwritten_check", check_no="123", amount=100.00, check_date="2025-01-01"
                ),
                contact_info=ContactInfo(),
            ),
            # Organization
            PaymentRecord(
                payer_info=PayerInfo(aliases=[], organization_name="Big Corp", salutation=""),
                payment_info=PaymentInfo(
                    payment_method="handwritten_check", check_no="456", amount=200.00, check_date="2025-01-01"
                ),
                contact_info=ContactInfo(),
            ),
            # Complex case
            PaymentRecord(
                payer_info=PayerInfo(aliases=["Alice Smith", "A. Smith"], organization_name="", salutation="Dr."),
                payment_info=PaymentInfo(
                    payment_method="handwritten_check",
                    check_no="789",
                    amount=300.00,
                    check_date="2025-01-01",
                    memo="Complex donation",
                ),
                contact_info=ContactInfo(address_line_1="123 Main", city="Springfield", state="ST", zip="12345"),
            ),
        ]

        legacy_field_names = [
            "Donor Name",
            "Gift Amount",
            "Check Date",
            "Check No.",
            "Address - Line 1",
            "City",
            "State",
            "ZIP",
            "Memo",
            "qbCustomerStatus",
            "internalId",
        ]

        for payment_record in test_cases:
            result = combiner.combine_payment_data(payment_record, None, "New")

            # Verify no legacy field names appear
            result_str = json.dumps(result)
            for legacy_field in legacy_field_names:
                assert legacy_field not in result_str, f"Found legacy field '{legacy_field}' in V3 output"

    def test_v3_format_completeness(self):
        """Test that V3 format includes all necessary fields for frontend."""
        combiner = PaymentCombinerV2()

        # Create comprehensive test data
        payment_record = PaymentRecord(
            payer_info=PayerInfo(
                aliases=["Complete User", "C. User"], organization_name="Complete Org", salutation="Dr."
            ),
            payment_info=PaymentInfo(
                payment_method="handwritten_check",
                check_no="111222",
                amount=999.99,
                check_date="2025-01-01",
                deposit_date="2025-01-02",
                payment_date="2025-01-01",
                memo="Complete test",
                deposit_method="ATM Deposit",
                payment_ref="REF999",
            ),
            contact_info=ContactInfo(
                address_line_1="999 Complete St",
                city="Completetown",
                state="CA",
                zip="90210",
                email="complete@example.com",
                phone="555-999-0000",
            ),
        )

        result = combiner.combine_payment_data(payment_record, None, "New")

        # Verify all fields needed for frontend are present

        # Identification fields
        assert "match_status" in result
        assert "qbo_customer_id" in result

        # Payer information for display and editing
        payer_info = result["payer_info"]
        frontend_payer_fields = [
            "customer_lookup",  # Main display name
            "qb_address_line_1",  # Address line 1
            "qb_city",  # City
            "qb_state",  # State
            "qb_zip",  # ZIP code
            "qb_email",  # Email list
            "qb_phone",  # Phone list
            "address_needs_update",  # Address mismatch flag
            "extracted_address",  # Original extracted address
        ]
        for field in frontend_payer_fields:
            assert field in payer_info, f"Missing frontend payer field: {field}"

        # Payment information for display and editing
        payment_info = result["payment_info"]
        frontend_payment_fields = [
            "check_no_or_payment_ref",  # Check number or reference
            "amount",  # Amount
            "payment_date",  # Payment/check date
            "deposit_date",  # Deposit date
            "memo",  # Memo
            "deposit_method",  # Deposit method
        ]
        for field in frontend_payment_fields:
            assert field in payment_info, f"Missing frontend payment field: {field}"

    def test_v3_format_handles_edge_cases(self):
        """Test that V3 format handles edge cases gracefully."""
        combiner = PaymentCombinerV2()

        # Test edge cases
        edge_cases = [
            # Empty/None values
            PaymentRecord(
                payer_info=PayerInfo(aliases=["Unknown"], organization_name="", salutation=""),
                payment_info=PaymentInfo(
                    payment_method="online_payment", payment_ref="ONLINE001", amount=0.01, check_date=""
                ),
                contact_info=ContactInfo(),
            ),
            # Very long strings
            PaymentRecord(
                payer_info=PayerInfo(
                    aliases=["A" * 200],  # Very long name
                    organization_name="B" * 300,  # Very long org name
                    salutation="C" * 50,
                ),
                payment_info=PaymentInfo(
                    payment_method="handwritten_check",
                    check_no="D" * 100,  # Very long check number
                    amount=999999.99,  # Large amount
                    check_date="2025-12-31",
                    memo="E" * 500,  # Very long memo
                ),
                contact_info=ContactInfo(
                    address_line_1="F" * 200,  # Very long address
                    city="G" * 100,
                    state="H" * 50,
                    zip="I" * 20,
                    email="very.long.email.address.that.goes.on.and.on@extremely.long.domain.name.example.com",
                    phone="+1-555-" + "0" * 20,  # Very long phone
                ),
            ),
            # Special characters
            PaymentRecord(
                payer_info=PayerInfo(
                    aliases=["José García-Smith", "Müller & Associates"],
                    organization_name="Café François & Co.",
                    salutation="Señor",
                ),
                payment_info=PaymentInfo(
                    payment_method="handwritten_check",
                    check_no="АВС123",  # Non-ASCII characters
                    amount=123.45,
                    check_date="2025-01-01",
                    memo="Special characters: àáâãäåæçèéêë",
                ),
                contact_info=ContactInfo(
                    address_line_1="123 Münster Straße",
                    city="São Paulo",
                    state="CA",
                    zip="12345-6789",
                    email="josé@café.com",
                    phone="+55 11 9999-8888",
                ),
            ),
        ]

        for i, payment_record in enumerate(edge_cases):
            try:
                result = combiner.combine_payment_data(payment_record, None, "New")

                # Should still have proper V3 structure
                assert "payer_info" in result
                assert "payment_info" in result
                assert "match_status" in result

                # Should be JSON serializable
                json.dumps(result)

            except Exception as e:
                pytest.fail(f"Edge case {i} failed: {e}")


class TestV3ValidationRules:
    """Test validation rules for V3 format."""

    def test_v3_format_validation_rules(self):
        """Test that V3 format follows validation rules."""
        combiner = PaymentCombinerV2()

        # Valid payment record
        payment_record = PaymentRecord(
            payer_info=PayerInfo(aliases=["Valid User"], organization_name="", salutation=""),
            payment_info=PaymentInfo(
                payment_method="handwritten_check", check_no="123456", amount=100.00, check_date="2025-01-01"
            ),
            contact_info=ContactInfo(),
        )

        result = combiner.combine_payment_data(payment_record, None, "New")

        # Validation rules

        # 1. Required fields must be present
        assert "payer_info" in result
        assert "payment_info" in result
        assert "match_status" in result

        # 2. match_status must be valid
        assert result["match_status"] in ["New", "Matched"]

        # 3. qbo_customer_id must be None or string
        qbo_id = result["qbo_customer_id"]
        assert qbo_id is None or isinstance(qbo_id, str)

        # 4. payer_info fields must be proper types
        payer_info = result["payer_info"]
        assert isinstance(payer_info["customer_lookup"], str)
        assert isinstance(payer_info["qb_address_line_1"], str)
        assert isinstance(payer_info["qb_city"], str)
        assert isinstance(payer_info["qb_state"], str)
        assert isinstance(payer_info["qb_zip"], str)
        assert isinstance(payer_info["qb_email"], list)
        assert isinstance(payer_info["qb_phone"], list)
        assert isinstance(payer_info["address_needs_update"], bool)

        # 5. payment_info fields must be proper types
        payment_info = result["payment_info"]
        assert isinstance(payment_info["check_no_or_payment_ref"], str)
        assert isinstance(payment_info["amount"], (int, float))
        assert isinstance(payment_info["payment_date"], str)
        assert isinstance(payment_info["deposit_date"], str)
        assert isinstance(payment_info["memo"], str)
        assert isinstance(payment_info["deposit_method"], str)

        # 6. Amount must be non-negative
        assert payment_info["amount"] >= 0

    def test_v3_format_consistency_across_components(self):
        """Test that V3 format is consistent across all components."""
        # This test ensures that all V3 components produce the same format structure

        combiner = PaymentCombinerV2()

        # Create test payment
        payment_record = PaymentRecord(
            payer_info=PayerInfo(aliases=["Test"], organization_name="", salutation=""),
            payment_info=PaymentInfo(
                payment_method="handwritten_check", check_no="123", amount=100.00, check_date="2025-01-01"
            ),
            contact_info=ContactInfo(),
        )

        # Test different scenarios
        scenarios = [
            ("New customer", None, "New"),
            ("Matched customer", {"Id": "123", "DisplayName": "Test Customer"}, "Matched"),
        ]

        for desc, qbo_customer, match_status in scenarios:
            result = combiner.combine_payment_data(payment_record, qbo_customer, match_status)

            # All scenarios should have same top-level structure
            expected_keys = {"payer_info", "payment_info", "match_status", "qbo_customer_id"}
            assert set(result.keys()).issuperset(expected_keys), f"Missing keys in {desc}"

            # All scenarios should have same payer_info structure
            payer_keys = {
                "customer_lookup",
                "qb_address_line_1",
                "qb_city",
                "qb_state",
                "qb_zip",
                "qb_email",
                "qb_phone",
                "address_needs_update",
                "extracted_address",
            }
            assert set(result["payer_info"].keys()).issuperset(payer_keys), f"Missing payer_info keys in {desc}"

            # All scenarios should have same payment_info structure
            payment_keys = {
                "check_no_or_payment_ref",
                "amount",
                "payment_date",
                "deposit_date",
                "deposit_method",
                "memo",
            }
            assert set(result["payment_info"].keys()).issuperset(payment_keys), f"Missing payment_info keys in {desc}"
