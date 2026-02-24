import requests

BASE_URL = "http://localhost:8000"
USERNAME = "boss"
PASSWORD = "Mm02022006"
TIMEOUT = 30

def test_create_new_product():
    # Step 1: Obtain JWT access token
    login_url = f"{BASE_URL}/api/token/"
    login_payload = {"username": USERNAME, "password": PASSWORD}
    login_response = requests.post(login_url, json=login_payload, timeout=TIMEOUT)
    assert login_response.status_code == 200, f"Login failed: {login_response.text}"
    access_token = login_response.json().get("access")
    assert access_token, "No access token received"
    
    # Step 2: Create product with all required fields
    url = f"{BASE_URL}/api/products/"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    payload = {
        "sku": "TESTSKU123",
        "name": "Test Product 123",
        "description": "A product created during automated test.",
        "price": "19.99",
        "cost": "10.00",
        "product_type": "finished",  # Required field
        "purchase_uom": "unit",
        "usage_uom": "unit",
        "conversion_factor": "1.0"
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT)
        assert response.status_code == 201, f"Expected status code 201, got {response.status_code}. Response: {response.text}"
        data = response.json()
        assert "id" in data, "Response JSON does not contain product ID"
        assert data["name"] == payload["name"], "Product name mismatch"
        assert data.get("sku") == payload["sku"], "Product SKU mismatch"
    except requests.RequestException as e:
        assert False, f"Request failed: {e}"

test_create_new_product()
