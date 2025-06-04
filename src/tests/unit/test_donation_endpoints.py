"""Unit tests for donation endpoints."""

import pytest
from fastapi.testclient import TestClient

from src.app import app

client = TestClient(app)


@pytest.fixture
def auth_headers():
    """Get authorization headers for testing."""
    from src.services.auth.jwt_handler import create_access_token

    token = create_access_token({"sub": "test_user", "role": "user"})
    return {"Authorization": f"Bearer {token}"}


def test_create_batch(auth_headers):
    """Test creating a donation batch."""
    response = client.post("/api/donations/batches", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "data" in data
    assert data["data"]["batch_id"] == "batch_123"
    assert data["data"]["status"] == "created"


def test_get_batch_not_found(auth_headers):
    """Test getting a non-existent batch."""
    response = client.get("/api/donations/batches/invalid_id", headers=auth_headers)

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_process_batch(auth_headers):
    """Test starting batch processing."""
    request_data = {
        "batch_id": "batch_123",
        "auto_deduplicate": True,
    }

    response = client.post(
        "/api/donations/batches/batch_123/process",
        json=request_data,
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "task_id" in data["data"]


def test_get_batch_donations(auth_headers):
    """Test getting donations in a batch."""
    response = client.get(
        "/api/donations/batches/batch_123/donations",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)


def test_update_donation_not_found(auth_headers):
    """Test updating a non-existent donation."""
    request_data = {
        "donation_id": "invalid_id",
        "payment_info": {"amount": "200.00"},
    }

    response = client.put(
        "/api/donations/donations/invalid_id",
        json=request_data,
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_search_donations(auth_headers):
    """Test searching donations."""
    filter_data = {
        "donor_name": "John Doe",
        "amount_min": "50.00",
    }

    response = client.post(
        "/api/donations/search",
        json=filter_data,
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)


def test_endpoints_require_auth():
    """Test that endpoints require authentication."""
    # Test various endpoints without auth headers
    endpoints = [
        ("POST", "/api/donations/batches"),
        ("GET", "/api/donations/batches/123"),
        ("POST", "/api/donations/search"),
    ]

    for method, endpoint in endpoints:
        if method == "GET":
            response = client.get(endpoint)
        else:
            response = client.post(endpoint, json={})

        assert response.status_code == 401
