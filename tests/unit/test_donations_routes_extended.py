"""Test extended donation routes including /save and /report/generate."""

import json
from unittest.mock import MagicMock, patch

import pytest


class TestExtendedDonationsRoutes:
    """Test extended donation routes."""

    @pytest.fixture(autouse=True)
    def setup(self, app, client):
        """Set up test fixtures."""
        self.app = app
        self.client = client

    def _get_csrf_token(self):
        """Get CSRF token from session."""
        with self.client.session_transaction() as sess:
            return sess.get("csrf_token", "dummy-csrf-token")

    def test_save_changes_success(self):
        """Test save changes endpoint."""
        donations = [
            {"internalId": "1", "Donor Name": "Test Donor", "Gift Amount": "100.00"},
            {"internalId": "2", "Donor Name": "Another Donor", "Gift Amount": "50.00"},
        ]

        response = self.client.post(
            "/save",
            json={"donations": donations},
            headers={"X-CSRFToken": self._get_csrf_token()},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

        # Verify donations were saved to session
        with self.client.session_transaction() as sess:
            assert sess["donations"] == donations

    def test_save_changes_no_data(self):
        """Test save changes endpoint with no data."""
        response = self.client.post(
            "/save",
            json={},
            headers={"X-CSRFToken": self._get_csrf_token()},
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "No donation data provided" in data["message"]

    def test_generate_report_success(self):
        """Test generate report endpoint."""
        # Add donations to session
        with self.client.session_transaction() as sess:
            sess["donations"] = [
                {
                    "internalId": "1",
                    "Donor Name": "Test Donor",
                    "Gift Amount": "100.00",
                    "Check # (if applicable)": "1001",
                    "Gift Date": "2024-01-01",
                    "Gift Type": "Check",
                    "Fund": "General Fund",
                    "Notes": "Test note",
                },
                {
                    "internalId": "2",
                    "Donor Name": "Another Donor",
                    "Gift Amount": "50.00",
                    "Check # (if applicable)": "1002",
                    "Gift Date": "2024-01-02",
                    "Gift Type": "Cash",
                },
            ]

        response = self.client.get("/report/generate")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["report"]["total"] == 150.0
        assert len(data["report"]["entries"]) == 2
        assert data["report"]["entries"][0]["donor_name"] == "Test Donor"
        assert data["report"]["entries"][0]["amount"] == 100.0

    def test_generate_report_no_donations(self):
        """Test generate report endpoint with no donations."""
        response = self.client.get("/report/generate")
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "No donations to report" in data["message"]

    def test_generate_report_skip_invalid(self):
        """Test generate report skips invalid donations."""
        # Add donations with some invalid ones
        with self.client.session_transaction() as sess:
            sess["donations"] = [
                {
                    "internalId": "1",
                    "Donor Name": "Valid Donor",
                    "Gift Amount": "100.00",
                },
                {
                    "internalId": "2",
                    "Donor Name": "Invalid Donor",
                    "Gift Amount": "",  # Missing amount
                },
                {
                    "internalId": "3",
                    "Donor Name": "Invalid Marked",
                    "Gift Amount": "50.00",
                    "isInvalid": True,  # Marked as invalid
                },
            ]

        response = self.client.get("/report/generate")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["report"]["total"] == 100.0  # Only 1 valid donation
        assert len(data["report"]["entries"]) == 1
        assert data["report"]["entries"][0]["donor_name"] == "Valid Donor"
