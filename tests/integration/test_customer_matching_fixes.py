"""Test customer matching fixes."""

import json
from unittest.mock import MagicMock, patch

import pytest
from flask import session


class TestCustomerMatchingFixes:
    """Test that customer matching works correctly after fixes."""

    def test_qbo_auth_state_persistence(self, client, app, mock_qbo_service):
        """Test that QBO authentication state persists across requests."""
        # Simulate successful OAuth callback
        with client.session_transaction() as sess:
            sess["qbo_authenticated"] = True
            sess["qbo_company_id"] = "123456789"
            sess["session_id"] = "test-session"

        # Mock Redis token loading and ensure token is valid
        mock_auth_service = MagicMock()
        mock_auth_service.redis_client = MagicMock()
        mock_auth_service._load_tokens_from_redis = MagicMock()

        mock_qbo_service.auth_service = mock_auth_service
        mock_qbo_service.access_token = "test-token"
        mock_qbo_service.realm_id = "123456789"
        mock_qbo_service.environment = "sandbox"
        mock_qbo_service.get_token_info.return_value = {"is_valid": True, "expires_in_seconds": 3600}

        # Inject the mock into the app
        app.qbo_service = mock_qbo_service

        # Test auth status endpoint
        response = client.get("/qbo/auth-status")
        assert response.status_code == 200
        data = response.json
        assert data["authenticated"] is True
        assert data["company_id"] == "123456789"

        # Verify Redis token loading was called
        mock_auth_service._load_tokens_from_redis.assert_called()

    def test_async_upload_loads_tokens(self, client, app, mock_qbo_service):
        """Test that async upload loads tokens from Redis."""
        with client.session_transaction() as sess:
            sess["qbo_authenticated"] = True
            sess["session_id"] = "test-session"

        # Mock Redis and S3
        mock_auth_service = MagicMock()
        mock_auth_service.redis_client = MagicMock()
        mock_auth_service._load_tokens_from_redis = MagicMock()

        mock_qbo_service.auth_service = mock_auth_service
        mock_qbo_service.access_token = "test-token"
        mock_qbo_service.realm_id = "123456789"
        mock_qbo_service.environment = "sandbox"
        mock_qbo_service.token_expires_at = 9999999999

        # Inject the mock into the app
        app.qbo_service = mock_qbo_service

        with patch("src.routes.files.S3Storage") as mock_s3:
            mock_s3_instance = mock_s3.return_value
            mock_s3_instance.generate_key.return_value = "test-key"
            mock_s3_instance.upload_file.return_value = {"bucket": "test-bucket", "size": 1000}

            with patch("src.utils.tasks.process_files_task") as mock_task:
                mock_task.delay.return_value = MagicMock(id="task-123")

                # Create test file
                import io

                data = {"files": (io.BytesIO(b"test"), "test.jpg")}
                response = client.post("/upload-async", data=data, content_type="multipart/form-data")

                assert response.status_code == 200
                assert response.json["success"] is True

                # Verify tokens were loaded
                mock_qbo_service.auth_service._load_tokens_from_redis.assert_called()

                # Verify task was called with QBO config
                mock_task.delay.assert_called()
                call_args = mock_task.delay.call_args[1]
                assert call_args["qbo_config"] is not None
                assert call_args["qbo_config"]["access_token"] == "test-token"

    def test_save_route_exists(self, client):
        """Test that /save route exists and works."""
        with client.session_transaction() as sess:
            sess["session_id"] = "test-session"

        data = {"donations": [{"Donor Name": "Test Donor", "Gift Amount": "100"}]}
        response = client.post("/save", json=data)

        assert response.status_code == 200
        assert response.json["success"] is True

        # Verify donations were saved to session
        with client.session_transaction() as sess:
            assert sess["donations"] == data["donations"]

    def test_report_generate_route_exists(self, client):
        """Test that /report/generate route exists and returns correct format."""
        with client.session_transaction() as sess:
            sess["session_id"] = "test-session"
            sess["donations"] = [
                {
                    "Donor Name": "John Doe",
                    "Gift Amount": "100.00",
                    "Check # (if applicable)": "1234",
                    "Gift Date": "01/01/2025",
                    "Address - Line 1": "123 Main St",
                    "City": "Anytown",
                    "State": "CA",
                    "ZIP": "12345",
                }
            ]

        response = client.get("/report/generate")
        assert response.status_code == 200

        data = response.json
        assert data["success"] is True
        assert "report" in data
        assert "total" in data["report"]
        assert "entries" in data["report"]
        assert len(data["report"]["entries"]) == 1

        entry = data["report"]["entries"][0]
        assert entry["index"] == 1
        assert entry["donor_name"] == "John Doe"
        assert entry["amount"] == 100.0
        assert entry["check_no"] == "1234"
        assert "address" in entry

    def test_manual_customer_match(self, client, app, mock_qbo_service):
        """Test manual customer matching."""
        with client.session_transaction() as sess:
            sess["qbo_authenticated"] = True
            sess["donations"] = [{"internalId": "donation-1", "Donor Name": "John Doe", "Gift Amount": "100"}]

        # Mock customer lookup
        mock_customer = {"Id": "cust-123", "DisplayName": "John Doe Company"}
        mock_qbo_service.get_customer_by_id.return_value = mock_customer

        # Inject the mock into the app
        app.qbo_service = mock_qbo_service

        response = client.post("/qbo/customer/manual-match/donation-1", json={"customerId": "cust-123"})

        assert response.status_code == 200
        assert response.json["success"] is True

        # Verify donation was updated
        with client.session_transaction() as sess:
            donation = sess["donations"][0]
            assert donation["qboCustomerId"] == "cust-123"
            assert donation["qbCustomerStatus"] == "Matched"
            assert donation["customerLookup"] == "John Doe Company"
            assert donation["matchMethod"] == "Manual"

    def test_customer_lookup_format(self, client, app, mock_qbo_service):
        """Test that customerLookup is properly formatted as string."""
        with client.session_transaction() as sess:
            sess["qbo_authenticated"] = True
            sess["donations"] = [{"internalId": "d1", "Donor Name": "Test"}]

        mock_qbo_service.get_customer_by_id.return_value = {"Id": "123", "DisplayName": "Test Customer"}

        # Inject the mock into the app
        app.qbo_service = mock_qbo_service

        response = client.post("/qbo/customer/manual-match/d1", json={"customerId": "123"})

        assert response.status_code == 200

        with client.session_transaction() as sess:
            # Ensure customerLookup is a string, not an object
            assert isinstance(sess["donations"][0]["customerLookup"], str)
            assert sess["donations"][0]["customerLookup"] == "Test Customer"
