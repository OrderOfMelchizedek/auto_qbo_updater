"""Test the customers/all endpoint format changes."""

from unittest.mock import Mock

import pytest


class TestCustomerAllEndpoint:
    """Test the /qbo/customers/all endpoint returns proper format."""

    def test_customers_all_includes_name_and_address(self, client, app):
        """Test that customers/all returns 'name' and 'address' fields."""
        # Mock QBO service
        mock_qbo_service = Mock()
        app.qbo_service = mock_qbo_service

        # Mock customer data
        mock_customers = [
            {
                "Id": "1",
                "DisplayName": "Test Customer",
                "GivenName": "Test",
                "FamilyName": "Customer",
                "CompanyName": "Test Corp",
                "PrimaryEmailAddr": {"Address": "test@example.com"},
                "BillAddr": {
                    "Line1": "123 Test St",
                    "City": "Test City",
                    "CountrySubDivisionCode": "TS",
                    "PostalCode": "12345",
                },
                "Active": True,
            },
            {"Id": "2", "DisplayName": "Another Customer", "BillAddr": {}, "Active": True},  # Empty address
        ]

        mock_qbo_service.get_all_customers.return_value = mock_customers

        # Simulate authenticated session
        with client.session_transaction() as sess:
            sess["qbo_authenticated"] = True

        response = client.get("/qbo/customers/all")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["count"] == 2

        # Find customers by ID since they're sorted
        customer1 = next(c for c in data["customers"] if c["id"] == "1")
        customer2 = next(c for c in data["customers"] if c["id"] == "2")

        # Check first customer has all expected fields
        assert customer1["id"] == "1"
        assert customer1["name"] == "Test Customer"  # Frontend expects 'name'
        assert customer1["displayName"] == "Test Customer"  # Also keep displayName
        assert customer1["address"] == "123 Test St, Test City, TS, 12345"
        assert customer1["email"] == "test@example.com"

        # Check second customer with empty address
        assert customer2["name"] == "Another Customer"
        assert customer2["address"] == "No address on file"

    def test_customers_all_sorted_by_display_name(self, client, app):
        """Test that customers are sorted by display name."""
        mock_qbo_service = Mock()
        app.qbo_service = mock_qbo_service

        mock_customers = [
            {"Id": "1", "DisplayName": "Zebra Company", "Active": True},
            {"Id": "2", "DisplayName": "Alpha Corp", "Active": True},
            {"Id": "3", "DisplayName": "Beta Industries", "Active": True},
        ]

        mock_qbo_service.get_all_customers.return_value = mock_customers

        with client.session_transaction() as sess:
            sess["qbo_authenticated"] = True

        response = client.get("/qbo/customers/all")

        assert response.status_code == 200
        data = response.get_json()

        # Check sorting
        names = [c["name"] for c in data["customers"]]
        assert names == ["Alpha Corp", "Beta Industries", "Zebra Company"]

    def test_customers_all_handles_missing_fields(self, client, app):
        """Test handling of customers with missing optional fields."""
        mock_qbo_service = Mock()
        app.qbo_service = mock_qbo_service

        mock_customers = [
            {
                "Id": "1",
                "DisplayName": "Minimal Customer",
                # No other fields
            }
        ]

        mock_qbo_service.get_all_customers.return_value = mock_customers

        with client.session_transaction() as sess:
            sess["qbo_authenticated"] = True

        response = client.get("/qbo/customers/all")

        assert response.status_code == 200
        data = response.get_json()

        customer = data["customers"][0]
        assert customer["name"] == "Minimal Customer"
        assert customer["address"] == "No address on file"
        assert customer["givenName"] is None
        assert customer["familyName"] is None
        assert customer["companyName"] is None
        assert customer["email"] is None
        assert customer["active"] is True  # Default value
