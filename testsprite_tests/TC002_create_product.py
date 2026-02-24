import requests
import json
import sys

BASE_URL = "http://localhost:8000"
USERNAME = "boss"
PASSWORD = "Mm02022006"

def get_auth_token():
    url = f"{BASE_URL}/api/token/"
    response = requests.post(url, json={"username": USERNAME, "password": PASSWORD})
    if response.status_code == 200:
        return response.json()["access"]
    else:
        print(f"Login failed: {response.text}")
        sys.exit(1)

def test_create_product():
    token = get_auth_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    product_data = {
        "name": "Test Product",
        "description": "A test product description",
        "price": 19.99,
        "sku": "TP-1000",
        "category": None,
        "quantity": 100
    }

    # Create product
    print("Creating product...")
    response = requests.post(
        f"{BASE_URL}/api/products/",
        json=product_data,
        headers=headers
    )
    
    if response.status_code != 201:
        print(f"Failed to create product. Status: {response.status_code}, Response: {response.text}")
        
    assert response.status_code == 201, f"Expected status 201 but got {response.status_code}"
    resp_data = response.json()
    assert "id" in resp_data, "Response JSON should contain the product ID"
    product_id = resp_data["id"]
    print(f"Product created with ID: {product_id}")

    try:
        # Verify product stored properly by fetching detail
        print("Fetching product details...")
        detail_response = requests.get(f"{BASE_URL}/api/products/{product_id}/", headers=headers)
        assert detail_response.status_code == 200, f"Expected status 200 but got {detail_response.status_code}"
        detail_data = detail_response.json()
        assert detail_data["name"] == product_data["name"]
        print("Product details verified.")
        
    finally:
        # Clean up: delete the created product
        print("Deleting product...")
        del_response = requests.delete(f"{BASE_URL}/api/products/{product_id}/", headers=headers)
        assert del_response.status_code in (204, 200, 202), f"Expected delete status 204/200/202 but got {del_response.status_code}"
        print("Product deleted.")

if __name__ == "__main__":
    test_create_product()