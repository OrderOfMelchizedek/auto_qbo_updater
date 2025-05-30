"""Test the customer search endpoint."""

from unittest.mock import Mock, patch

import pytest


class TestCustomerSearchEndpoint:
    """Test the /qbo/customers/search endpoint."""

    def test_search_customers_success(self, client, app):
        """Test successful customer search."""
        # Mock QBO service
        mock_qbo_service = Mock()
        app.qbo_service = mock_qbo_service

        # Mock customer data
        mock_customers = [
            {
                "Id": "1",
                "DisplayName": "John Doe",
                "GivenName": "John",
                "FamilyName": "Doe",
                "CompanyName": None,
                "PrimaryEmailAddr": {"Address": "john@example.com"},
                "BillAddr": {
                    "Line1": "123 Main St",
                    "City": "Anytown",
                    "CountrySubDivisionCode": "CA",
                    "PostalCode": "12345",
                },
                "Active": True,
            },
            {
                "Id": "2",
                "DisplayName": "Jane Smith",
                "GivenName": "Jane",
                "FamilyName": "Smith",
                "CompanyName": "Smith Corp",
                "PrimaryEmailAddr": {"Address": "jane@smithcorp.com"},
                "BillAddr": {},
                "Active": True,
            },
            {
                "Id": "3",
                "DisplayName": "Bob Johnson",
                "GivenName": "Bob",
                "FamilyName": "Johnson",
                "CompanyName": None,
                "PrimaryEmailAddr": {},
                "BillAddr": None,
                "Active": False,
            },
        ]

        mock_qbo_service.get_all_customers.return_value = mock_customers

        # Simulate authenticated session
        with client.session_transaction() as sess:
            sess["qbo_authenticated"] = True

        # Test search for "john"
        response = client.get("/qbo/customers/search?q=john")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["count"] == 2  # John Doe and Bob Johnson
        assert data["total"] == 3
        assert len(data["customers"]) == 2

        # Check customer format
        john_doe = next(c for c in data["customers"] if c["id"] == "1")
        assert john_doe["name"] == "John Doe"
        assert john_doe["displayName"] == "John Doe"
        assert john_doe["address"] == "123 Main St, Anytown, CA, 12345"
        assert john_doe["email"] == "john@example.com"
        assert john_doe["active"] is True

    def test_search_customers_no_auth(self, client, app):
        """Test search endpoint requires authentication."""
        response = client.get("/qbo/customers/search?q=test")

        assert response.status_code == 401
        data = response.get_json()
        assert "error" in data
        assert "not authenticated" in data["error"].lower()

    def test_search_customers_empty_query(self, client, app):
        """Test search with empty query returns empty results."""
        mock_qbo_service = Mock()
        app.qbo_service = mock_qbo_service

        with client.session_transaction() as sess:
            sess["qbo_authenticated"] = True

        response = client.get("/qbo/customers/search?q=")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["customers"] == []
        assert data["count"] == 0

    def test_search_customers_case_insensitive(self, client, app):
        """Test search is case insensitive."""
        mock_qbo_service = Mock()
        app.qbo_service = mock_qbo_service

        mock_customers = [
            {
                "Id": "1",
                "DisplayName": "UPPERCASE CUSTOMER",
                "GivenName": "UPPERCASE",
                "FamilyName": "CUSTOMER",
                "Active": True,
            }
        ]

        mock_qbo_service.get_all_customers.return_value = mock_customers

        with client.session_transaction() as sess:
            sess["qbo_authenticated"] = True

        # Search with lowercase
        response = client.get("/qbo/customers/search?q=uppercase")

        assert response.status_code == 200
        data = response.get_json()
        assert data["count"] == 1
        assert data["customers"][0]["displayName"] == "UPPERCASE CUSTOMER"

    def test_search_customers_by_email(self, client, app):
        """Test searching customers by email address."""
        mock_qbo_service = Mock()
        app.qbo_service = mock_qbo_service

        mock_customers = [
            {
                "Id": "1",
                "DisplayName": "Test Customer",
                "PrimaryEmailAddr": {"Address": "unique@example.com"},
                "Active": True,
            }
        ]

        mock_qbo_service.get_all_customers.return_value = mock_customers

        with client.session_transaction() as sess:
            sess["qbo_authenticated"] = True

        response = client.get("/qbo/customers/search?q=unique@example")

        assert response.status_code == 200
        data = response.get_json()
        assert data["count"] == 1
        assert data["customers"][0]["email"] == "unique@example.com"

    def test_search_customers_limit_results(self, client, app):
        """Test search limits results to 20."""
        mock_qbo_service = Mock()
        app.qbo_service = mock_qbo_service

        # Create 25 customers all with "Test" in name
        mock_customers = [{"Id": str(i), "DisplayName": f"Test Customer {i}", "Active": True} for i in range(25)]

        mock_qbo_service.get_all_customers.return_value = mock_customers

        with client.session_transaction() as sess:
            sess["qbo_authenticated"] = True

        response = client.get("/qbo/customers/search?q=Test")

        assert response.status_code == 200
        data = response.get_json()
        assert len(data["customers"]) == 20  # Limited to 20
        assert data["count"] == 25  # But count shows total matches

    def test_search_customers_no_address(self, client, app):
        """Test customers without address show 'No address on file'."""
        mock_qbo_service = Mock()
        app.qbo_service = mock_qbo_service

        mock_customers = [{"Id": "1", "DisplayName": "No Address Customer", "BillAddr": None, "Active": True}]

        mock_qbo_service.get_all_customers.return_value = mock_customers

        with client.session_transaction() as sess:
            sess["qbo_authenticated"] = True

        response = client.get("/qbo/customers/search?q=Address")

        assert response.status_code == 200
        data = response.get_json()
        assert data["customers"][0]["address"] == "No address on file"
