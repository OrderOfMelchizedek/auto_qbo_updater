"""Test customer creation response format."""

from unittest.mock import Mock, patch

import pytest
from flask import json


class TestCustomerCreationResponse:
    """Test that customer creation returns the expected format."""

    def test_create_customer_response_format(self, client, app):
        """Test that create customer returns both lowercase and uppercase properties."""
        # Mock QBO service
        mock_qbo_service = Mock()
        app.qbo_service = mock_qbo_service

        # Mock successful customer creation
        mock_new_customer = {
            "Id": "NEW123",
            "DisplayName": "New Test Customer",
            "SyncToken": "0",
            "GivenName": "New",
            "FamilyName": "Customer",
            "PrimaryEmailAddr": {"Address": "new@example.com"},
        }
        mock_qbo_service.create_customer.return_value = mock_new_customer

        # Setup session with donation
        with client.session_transaction() as sess:
            sess["qbo_authenticated"] = True
            sess["donations"] = [
                {"internalId": "donation_1", "Donor Name": "New Test Customer", "Gift Amount": "100.00"}
            ]

        # Create customer
        response = client.post(
            "/qbo/customer/create/donation_1",
            json={"DisplayName": "New Test Customer", "GivenName": "New", "FamilyName": "Customer"},
        )

        assert response.status_code == 200
        data = response.get_json()

        # Check response format
        assert data["success"] is True
        assert data["message"] == "Customer created successfully"

        # Check customer object has both formats
        customer = data["customer"]
        assert customer["id"] == "NEW123"  # lowercase
        assert customer["Id"] == "NEW123"  # uppercase (for frontend compatibility)
        assert customer["displayName"] == "New Test Customer"  # lowercase
        assert customer["DisplayName"] == "New Test Customer"  # uppercase
        assert customer["syncToken"] == "0"

    def test_create_customer_updates_donation(self, client, app):
        """Test that creating a customer updates the donation in session."""
        # Mock QBO service
        mock_qbo_service = Mock()
        app.qbo_service = mock_qbo_service

        # Mock successful customer creation
        mock_new_customer = {"Id": "NEW456", "DisplayName": "Another Customer"}
        mock_qbo_service.create_customer.return_value = mock_new_customer

        # Setup session
        with client.session_transaction() as sess:
            sess["qbo_authenticated"] = True
            sess["donations"] = [
                {
                    "internalId": "donation_2",
                    "Donor Name": "Another Customer",
                    "Gift Amount": "50.00",
                    "qbCustomerStatus": "New",
                }
            ]

        # Create customer
        response = client.post("/qbo/customer/create/donation_2", json={})

        assert response.status_code == 200

        # Check donation was updated in session
        with client.session_transaction() as sess:
            donation = sess["donations"][0]
            assert donation["qboCustomerId"] == "NEW456"
            assert donation["qbCustomerStatus"] == "Created"
            assert donation["matchMethod"] == "Created"
            assert donation["matchConfidence"] == "New"

    def test_create_customer_handles_failure(self, client, app):
        """Test error handling when customer creation fails."""
        # Mock QBO service
        mock_qbo_service = Mock()
        app.qbo_service = mock_qbo_service

        # Mock failed customer creation
        mock_qbo_service.create_customer.return_value = None

        # Setup session
        with client.session_transaction() as sess:
            sess["qbo_authenticated"] = True
            sess["donations"] = [{"internalId": "donation_3", "Donor Name": "Failed Customer"}]

        # Try to create customer
        response = client.post("/qbo/customer/create/donation_3", json={})

        assert response.status_code == 500
        data = response.get_json()
        assert data["error"] == "Failed to create customer"
