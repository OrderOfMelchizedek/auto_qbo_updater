"""
End-to-end tests to validate frontend compatibility with V3 enriched format.
These tests ensure the frontend can properly handle V3 format data.
"""

import json
import re
from pathlib import Path

import pytest


class TestFrontendV3Compatibility:
    """Test frontend JavaScript compatibility with V3 enriched format."""

    @pytest.fixture
    def frontend_js_content(self):
        """Load the frontend JavaScript content."""
        js_path = Path("/Users/svaug/dev/svl_apps/fom_to_qbo_automation/src/static/js/app.js")
        with open(js_path, "r") as f:
            return f.read()

    def test_frontend_uses_v3_field_access_patterns(self, frontend_js_content):
        """Test that frontend JavaScript uses V3 field access patterns."""
        # Must use V3 nested structure access
        v3_patterns = [
            r"donation\.payer_info",
            r"donation\.payment_info",
            r"payerInfo\s*=.*donation\.payer_info",
            r"paymentInfo\s*=.*donation\.payment_info",
            r"\.customer_lookup",
            r"\.qb_address_line_1",
            r"\.check_no_or_payment_ref",
            r"\.match_status",
        ]

        for pattern in v3_patterns:
            matches = re.search(pattern, frontend_js_content, re.IGNORECASE)
            assert matches, f"Frontend missing V3 pattern: {pattern}"

    def test_frontend_avoids_legacy_field_access(self, frontend_js_content):
        """Test that frontend avoids direct legacy field access."""
        # Check for problematic legacy patterns (while allowing some in comments)
        legacy_patterns = [
            r'donation\[[\'""]Donor Name[\'""]\]',
            r'donation\[[\'""]Gift Amount[\'""]\]',
            r'donation\[[\'""]Check Date[\'""]\]',
            r'donation\[[\'""]Check No\.[\'""]\]',
            r"donation\.qbCustomerStatus(?!\s*=.*match_status)",  # Allow if mapping from match_status
            r"donation\.internalId(?!\s*=.*internal_id)",  # Allow if mapping from internal_id
        ]

        for pattern in legacy_patterns:
            matches = re.findall(pattern, frontend_js_content, re.IGNORECASE)
            # Filter out comments and conversion contexts
            problematic_matches = []
            for match in matches:
                # Find the line containing this match
                lines = frontend_js_content.split("\n")
                for line in lines:
                    if match in line:
                        # Skip if it's a comment
                        if line.strip().startswith("//") or line.strip().startswith("*"):
                            continue
                        # Skip if it's in a V3 conversion context
                        if "payer_info" in line or "payment_info" in line or "getValue()" in line:
                            continue
                        problematic_matches.append(line.strip())

            assert (
                not problematic_matches
            ), f"Found problematic legacy pattern '{pattern}' in lines: {problematic_matches}"

    def test_frontend_field_mappings_are_v3_compliant(self, frontend_js_content):
        """Test that frontend field mappings use V3 structure."""
        # Look for fieldMappings array
        field_mappings_match = re.search(r"fieldMappings\s*=\s*\[(.*?)\]", frontend_js_content, re.DOTALL)
        assert field_mappings_match, "Frontend missing fieldMappings array"

        field_mappings_content = field_mappings_match.group(1)

        # Must have V3-style getValue functions
        v3_get_value_patterns = [
            r"payerInfo\.customer_lookup",
            r"paymentInfo\.check_no_or_payment_ref",
            r"paymentInfo\.amount",
            r"paymentInfo\.payment_date",
            r"payerInfo\.qb_address_line_1",
            r"payerInfo\.qb_city",
            r"payerInfo\.qb_state",
            r"payerInfo\.qb_zip",
        ]

        for pattern in v3_get_value_patterns:
            assert re.search(pattern, field_mappings_content), f"Missing V3 getValue pattern: {pattern}"

    def test_frontend_editing_updates_v3_structure(self, frontend_js_content):
        """Test that frontend editing updates V3 structure correctly."""
        # Look for editing logic that updates donation structure
        editing_section = re.search(r"switch\s*\(\s*mapping\.field\s*\).*?break;.*?}", frontend_js_content, re.DOTALL)
        assert editing_section, "Frontend missing V3 editing switch statement"

        editing_content = editing_section.group(0)

        # Must update V3 structure fields
        v3_update_patterns = [
            r"donation\.payer_info\.customer_lookup",
            r"donation\.payment_info\.check_no_or_payment_ref",
            r"donation\.payment_info\.amount",
            r"donation\.payment_info\.payment_date",
            r"donation\.payer_info\.qb_address_line_1",
            r"donation\.payer_info\.qb_city",
            r"donation\.payer_info\.qb_state",
            r"donation\.payer_info\.qb_zip",
            r"donation\.payment_info\.memo",
        ]

        for pattern in v3_update_patterns:
            assert re.search(pattern, editing_content), f"Missing V3 update pattern: {pattern}"

    def test_frontend_status_indicators_use_v3_fields(self, frontend_js_content):
        """Test that status indicators use V3 fields."""
        # Look for status indicator logic
        status_section = re.search(r"// Customer status indicator.*?statusHtml", frontend_js_content, re.DOTALL)
        assert status_section, "Frontend missing status indicator section"

        status_content = status_section.group(0)

        # Must use V3 status fields
        assert "match_status" in status_content, "Status indicators must use match_status"
        assert "qbo_customer_id" in status_content, "Status indicators must use qbo_customer_id"
        assert "payer_info" in status_content, "Status indicators must access payer_info"

    def test_frontend_action_buttons_use_v3_identifiers(self, frontend_js_content):
        """Test that action buttons use V3 identifiers."""
        # Look for action button creation
        actions_section = re.search(r"// Show QBO actions.*?actionsHtml", frontend_js_content, re.DOTALL)
        assert actions_section, "Frontend missing actions section"

        actions_content = actions_section.group(0)

        # Must use V3 identifier
        v3_id_patterns = [r"donation\.internal_id", r"donationId\s*=.*donation\.internal_id"]

        found_v3_id = any(re.search(pattern, actions_content) for pattern in v3_id_patterns)
        assert found_v3_id, "Action buttons must use V3 internal_id"

    def test_frontend_customer_modal_uses_v3_data(self, frontend_js_content):
        """Test that customer modal uses V3 data structure."""
        # Look for customer modal population
        modal_section = re.search(
            r"// Set form fields using V3 format.*?getElementById.*?value", frontend_js_content, re.DOTALL
        )
        assert modal_section, "Frontend missing V3 customer modal section"

        modal_content = modal_section.group(0)

        # Must use V3 payer_info structure
        v3_modal_patterns = [
            r"payerInfo\s*=.*donation\.payer_info",
            r"payerInfo\.customer_lookup",
            r"payerInfo\.qb_address_line_1",
            r"payerInfo\.qb_city",
            r"payerInfo\.qb_state",
            r"payerInfo\.qb_zip",
        ]

        for pattern in v3_modal_patterns:
            assert re.search(pattern, modal_content), f"Missing V3 modal pattern: {pattern}"

    def test_sample_v3_data_structure_compatibility(self):
        """Test that a sample V3 data structure would work with frontend expectations."""
        # Sample V3 enriched payment
        sample_v3_payment = {
            "payer_info": {
                "customer_lookup": "John Smith",
                "first_name": "John",
                "last_name": "Smith",
                "full_name": "John Smith",
                "qb_organization_name": "",
                "qb_address_line_1": "123 Main St",
                "qb_city": "Anytown",
                "qb_state": "CA",
                "qb_zip": "12345",
                "qb_email": ["john@example.com"],
                "qb_phone": ["555-1234"],
                "address_needs_update": False,
                "extracted_address": {"line_1": "123 Main St", "city": "Anytown", "state": "CA", "zip": "12345"},
            },
            "payment_info": {
                "check_no_or_payment_ref": "123456",
                "amount": 100.00,
                "payment_date": "2025-01-01",
                "deposit_date": "2025-01-02",
                "deposit_method": "ATM Deposit",
                "memo": "Test donation",
            },
            "match_status": "New",
            "qbo_customer_id": None,
            "match_method": "",
            "match_confidence": "",
            "internal_id": "payment_12345",
        }

        # Verify structure has all fields frontend expects

        # Payer info fields
        payer_info = sample_v3_payment["payer_info"]
        required_payer_fields = [
            "customer_lookup",
            "qb_address_line_1",
            "qb_city",
            "qb_state",
            "qb_zip",
            "qb_email",
            "qb_phone",
            "address_needs_update",
        ]
        for field in required_payer_fields:
            assert field in payer_info, f"Missing required payer field: {field}"

        # Payment info fields
        payment_info = sample_v3_payment["payment_info"]
        required_payment_fields = ["check_no_or_payment_ref", "amount", "payment_date", "memo"]
        for field in required_payment_fields:
            assert field in payment_info, f"Missing required payment field: {field}"

        # Top-level fields
        required_top_fields = ["match_status", "qbo_customer_id", "internal_id"]
        for field in required_top_fields:
            assert field in sample_v3_payment, f"Missing required top-level field: {field}"

        # Verify data types
        assert isinstance(payer_info["customer_lookup"], str)
        assert isinstance(payer_info["qb_email"], list)
        assert isinstance(payer_info["qb_phone"], list)
        assert isinstance(payer_info["address_needs_update"], bool)
        assert isinstance(payment_info["amount"], (int, float))
        assert isinstance(sample_v3_payment["match_status"], str)

        # Verify JSON serialization works
        json_str = json.dumps(sample_v3_payment)
        deserialized = json.loads(json_str)
        assert deserialized == sample_v3_payment

    def test_frontend_table_headers_compatibility(self):
        """Test that table headers are compatible with V3 data display."""
        # Read HTML template
        html_path = Path("/Users/svaug/dev/svl_apps/fom_to_qbo_automation/src/templates/index.html")
        with open(html_path, "r") as f:
            html_content = f.read()

        # Find table headers
        table_header_match = re.search(r"<thead>.*?</thead>", html_content, re.DOTALL)
        assert table_header_match, "Could not find table headers in HTML"

        headers_content = table_header_match.group(0)

        # Expected headers that work with V3 data
        expected_headers = [
            "Customer Lookup",  # maps to payer_info.customer_lookup
            "Donor Name",  # maps to payer_info.customer_lookup or full_name
            "Check No.",  # maps to payment_info.check_no_or_payment_ref
            "Gift Amount",  # maps to payment_info.amount
            "Check Date",  # maps to payment_info.payment_date
            "Address",  # maps to payer_info.qb_address_line_1
            "City",  # maps to payer_info.qb_city
            "State",  # maps to payer_info.qb_state
            "ZIP",  # maps to payer_info.qb_zip
            "Memo",  # maps to payment_info.memo
            "QBO Status",  # maps to match_status + status indicators
            "Actions",  # uses internal_id for button data-id
        ]

        for header in expected_headers:
            assert header in headers_content, f"Missing expected header: {header}"

    def test_no_legacy_conversion_functions_in_frontend(self, frontend_js_content):
        """Test that frontend doesn't contain legacy conversion functions."""
        # Forbidden conversion patterns
        forbidden_patterns = [
            r"function.*convertTo.*Legacy",
            r"function.*legacyFormat",
            r"function.*enrichedToLegacy",
            r"\.toLegacyFormat",
            r"DataAdapter",  # No data adapter should be needed
        ]

        for pattern in forbidden_patterns:
            matches = re.findall(pattern, frontend_js_content, re.IGNORECASE)
            assert not matches, f"Found forbidden legacy conversion pattern: {pattern}"

    def test_frontend_consistently_uses_v3_throughout(self, frontend_js_content):
        """Test that frontend consistently uses V3 format throughout all functions."""
        # Find all function definitions
        function_matches = re.finditer(r"function\s+(\w+)\s*\(", frontend_js_content)
        functions = [match.group(1) for match in function_matches]

        # Key functions that must use V3 format
        critical_functions = ["renderDonationTable", "saveChanges", "manualMatchCustomer", "createNewCustomerInline"]

        for func_name in critical_functions:
            if func_name in functions:
                # Extract function content
                func_start = frontend_js_content.find(f"function {func_name}")
                if func_start == -1:
                    continue

                # Find the function body (simplified - just look for reasonable chunk)
                func_content = frontend_js_content[func_start : func_start + 2000]

                # Critical functions should use V3 patterns
                if func_name == "renderDonationTable":
                    assert "payer_info" in func_content, f"{func_name} must use payer_info"
                    assert "payment_info" in func_content, f"{func_name} must use payment_info"

                # Should not use legacy patterns directly
                legacy_indicators = ['donation["Donor Name"]', "donation.qbCustomerStatus"]
                for indicator in legacy_indicators:
                    # Allow if it's in a conversion/compatibility context
                    if indicator in func_content and "payer_info" not in func_content:
                        pytest.fail(f"{func_name} uses legacy pattern {indicator} without V3 context")
