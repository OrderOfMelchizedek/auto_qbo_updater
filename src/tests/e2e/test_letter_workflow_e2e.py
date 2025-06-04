"""End-to-end tests for letter generation workflow."""
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from src.app import app


@pytest.fixture
def authenticated_client():
    """Create test client with authentication mocked."""
    with patch("src.api.dependencies.auth.verify_jwt_token") as mock_verify:
        mock_verify.return_value = {"sub": "test_user", "email": "test@example.com"}
        client = TestClient(app)
        yield client


@pytest.fixture
def test_organization_data():
    """Test organization data for E2E tests."""
    return {
        "name": "E2E Test Foundation",
        "address_line1": "100 Test Ave",
        "city": "Testopolis",
        "state": "TE",
        "postal_code": "00000",
        "ein": "11-1111111",
        "treasurer_name": "E2E Treasurer",
        "treasurer_title": "CFO",
    }


class TestLetterGenerationE2E:
    """End-to-end tests for complete letter generation workflow."""

    def test_get_available_templates(self, authenticated_client):
        """Test retrieving available letter templates."""
        response = authenticated_client.get(
            "/api/letters/templates", headers={"Authorization": "Bearer test_token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) >= 2

        # Verify template structure
        template = data["data"][0]
        assert "template_id" in template
        assert "name" in template
        assert "description" in template
        assert "merge_fields" in template

    def test_generate_single_letter(self, authenticated_client, test_organization_data):
        """Test generating a single letter."""
        request_data = {
            "donation_ids": ["test_donation_1"],
            "template_name": "default_letter.html",
            "organization_info": test_organization_data,
            "send_email": False,
        }

        response = authenticated_client.post(
            "/api/letters/generate",
            json=request_data,
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total_count"] == 1
        assert len(data["data"]["letters"]) == 1

        # Verify letter structure
        letter = data["data"]["letters"][0]
        assert letter["donation_id"] == "test_donation_1"
        assert letter["recipient_name"] == "Donor test_donation_1"
        assert letter["template_name"] == "default_letter.html"

    def test_generate_batch_letters(self, authenticated_client, test_organization_data):
        """Test generating multiple letters in batch."""
        request_data = {
            "donation_ids": ["donation_1", "donation_2", "donation_3"],
            "template_name": "simple_letter.html",
            "organization_info": test_organization_data,
            "send_email": False,
        }

        response = authenticated_client.post(
            "/api/letters/generate",
            json=request_data,
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total_count"] == 3
        assert len(data["data"]["letters"]) == 3

        # Verify batch ID
        assert data["data"]["batch_id"].startswith("batch_")

    def test_preview_letter(self, authenticated_client, test_organization_data):
        """Test previewing a letter before generation."""
        request_data = {
            "donation_ids": ["preview_donation"],
            "template_name": "default_letter.html",
            "organization_info": test_organization_data,
            "custom_data": {"custom_message": "This is a preview test"},
        }

        response = authenticated_client.post(
            "/api/letters/preview",
            json=request_data,
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify HTML content
        html_content = data["data"]
        assert "E2E Test Foundation" in html_content
        assert "11-1111111" in html_content
        assert "This is a preview test" in html_content

    def test_create_custom_template(self, authenticated_client):
        """Test creating a custom letter template."""
        template_data = {
            "name": "Custom E2E Template",
            "description": "Template created during E2E test",
            "html_template": "<html><body>Hello {{donor_name}}</body></html>",
            "merge_fields": ["donor_name", "amount", "date"],
        }

        response = authenticated_client.post(
            "/api/letters/templates",
            json=template_data,
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["template_id"].startswith("template_")
        assert data["data"]["created_by"] == "test_user"

    def test_download_letter(self, authenticated_client):
        """Test downloading a generated letter."""
        # First generate a letter
        with patch("src.api.endpoints.letters.S3Service") as mock_s3_class:
            mock_s3 = Mock()
            mock_s3.download_file.return_value = b"%PDF-1.4 test content"
            mock_s3_class.return_value = mock_s3

            response = authenticated_client.get(
                "/api/letters/download/test_letter_id",
                headers={"Authorization": "Bearer test_token"},
            )

            # Should get PDF response
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/pdf"
            assert "attachment" in response.headers["content-disposition"]
            assert response.content == b"%PDF-1.4 test content"

    def test_get_letter_batch_not_found(self, authenticated_client):
        """Test retrieving non-existent letter batch."""
        response = authenticated_client.get(
            "/api/letters/batches/non_existent_batch",
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_download_letter_not_found(self, authenticated_client):
        """Test downloading non-existent letter."""
        with patch("src.api.endpoints.letters.S3Service") as mock_s3_class:
            mock_s3 = Mock()
            mock_s3.download_file.side_effect = Exception("File not found")
            mock_s3_class.return_value = mock_s3

            response = authenticated_client.get(
                "/api/letters/download/non_existent_letter",
                headers={"Authorization": "Bearer test_token"},
            )

            assert response.status_code == 404

    def test_generate_letters_with_custom_data(
        self, authenticated_client, test_organization_data
    ):
        """Test generating letters with custom template data."""
        request_data = {
            "donation_ids": ["custom_donation"],
            "template_name": "default_letter.html",
            "organization_info": test_organization_data,
            "send_email": False,
            "custom_data": {
                "custom_message": "Thank you for supporting our annual campaign!",
                "campaign_year": "2024",
            },
        }

        response = authenticated_client.post(
            "/api/letters/generate",
            json=request_data,
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_error_handling_invalid_template(
        self, authenticated_client, test_organization_data
    ):
        """Test error handling for invalid template."""
        request_data = {
            "donation_ids": ["test_donation"],
            "template_name": "non_existent_template.html",
            "organization_info": test_organization_data,
        }

        # Should still succeed - falls back to default template
        response = authenticated_client.post(
            "/api/letters/generate",
            json=request_data,
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 200

    def test_unauthorized_access(self):
        """Test accessing endpoints without authentication."""
        client = TestClient(app)

        # Test various endpoints
        endpoints = [
            ("GET", "/api/letters/templates"),
            ("POST", "/api/letters/generate"),
            ("GET", "/api/letters/batches/test"),
            ("GET", "/api/letters/download/test"),
            ("POST", "/api/letters/templates"),
            ("POST", "/api/letters/preview"),
        ]

        for method, endpoint in endpoints:
            if method == "GET":
                response = client.get(endpoint)
            else:
                response = client.post(endpoint, json={})

            assert response.status_code == 401

    def test_complete_workflow(self, authenticated_client, test_organization_data):
        """Test complete letter generation workflow."""
        # Step 1: Get available templates
        templates_response = authenticated_client.get(
            "/api/letters/templates", headers={"Authorization": "Bearer test_token"}
        )
        assert templates_response.status_code == 200
        templates = templates_response.json()["data"]
        default_template = next(t for t in templates if t["is_default"])

        # Step 2: Preview a letter
        preview_request = {
            "donation_ids": [],  # Empty for default preview
            "template_name": default_template["template_id"] + ".html",
            "organization_info": test_organization_data,
        }

        preview_response = authenticated_client.post(
            "/api/letters/preview",
            json=preview_request,
            headers={"Authorization": "Bearer test_token"},
        )
        assert preview_response.status_code == 200

        # Step 3: Generate letters
        generate_request = {
            "donation_ids": ["workflow_1", "workflow_2"],
            "template_name": default_template["template_id"] + ".html",
            "organization_info": test_organization_data,
        }

        generate_response = authenticated_client.post(
            "/api/letters/generate",
            json=generate_request,
            headers={"Authorization": "Bearer test_token"},
        )
        assert generate_response.status_code == 200
        batch_data = generate_response.json()["data"]

        # Step 4: Verify batch was created
        assert batch_data["total_count"] == 2
        assert len(batch_data["letters"]) == 2

        # Step 5: Attempt to retrieve batch (will fail as we don't have DB yet)
        batch_response = authenticated_client.get(
            f"/api/letters/batches/{batch_data['batch_id']}",
            headers={"Authorization": "Bearer test_token"},
        )
        assert batch_response.status_code == 404  # Expected until DB implemented
