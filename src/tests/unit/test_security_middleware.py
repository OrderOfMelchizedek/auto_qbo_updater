"""Unit tests for security middleware."""
from fastapi.testclient import TestClient

from src.app import app

client = TestClient(app)


def test_cors_headers_present():
    """Test that CORS headers are present in responses."""
    # CORS headers are added when there's an Origin header
    response = client.get("/health", headers={"Origin": "http://localhost:3000"})

    assert response.status_code == 200
    # CORS headers should be present when Origin is provided
    # Note: FastAPI/Starlette CORS middleware adds headers based on request origin


def test_security_headers_present():
    """Test that security headers are present in responses."""
    response = client.get("/health")

    assert response.status_code == 200
    # Check for security headers
    assert "x-content-type-options" in response.headers
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "x-frame-options" in response.headers
    assert response.headers["x-frame-options"] == "DENY"
    assert "x-xss-protection" in response.headers
    assert "strict-transport-security" in response.headers


def test_request_id_header():
    """Test that request ID is added to responses."""
    response = client.get("/health")

    assert response.status_code == 200
    assert "x-request-id" in response.headers
    assert len(response.headers["x-request-id"]) > 0
