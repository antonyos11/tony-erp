import pytest
from rest_framework.test import APIClient

@pytest.mark.django_db
def test_create_customer():
    client = APIClient()
    # Authenticate using JWT token (assumed to be obtained beforehand)
    # For demonstration, replace 'your_jwt_token_here' with a valid token
    jwt_token = "your_jwt_token_here"
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {jwt_token}')
    
    url = "http://localhost:8000/api/customers/"
    payload = {
        "name": "Test Customer",
        "email": "test.customer@example.com",
        "phone": "+1234567890",
        "address": "123 Test Lane, Test City"
    }

    response = client.post(url, payload, format='json')
    assert response.status_code == 201, f"Expected 201 Created, got {response.status_code}"
    data = response.json()
    assert "id" in data, "Response JSON should contain 'id'"
    assert data["name"] == payload["name"]
    assert data["email"] == payload["email"]
    assert data["phone"] == payload["phone"]
    assert data["address"] == payload["address"]

test_create_customer()