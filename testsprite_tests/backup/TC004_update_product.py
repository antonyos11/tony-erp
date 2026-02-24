import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost:8000"
AUTH = HTTPBasicAuth("boss", "Mm02022006")
HEADERS = {"Content-Type": "application/json"}

def test_update_product():
    product_id = None
    try:
        # Step 1: Create a product
        create_payload = {
            "name": "Test Product TC004",
            "description": "Initial description for update test",
            "price": "100.00",
            "sku": "TC004-UPDATE",
            "stock": 10
        }
        
        create_resp = requests.post(
            f"{BASE_URL}/api/products/",
            json=create_payload,
            headers=HEADERS,
            auth=AUTH
        )
        assert create_resp.status_code == 201, f"Failed to create product: {create_resp.text}"
        product_data = create_resp.json()
        product_id = product_data.get("id")
        assert product_id, "Created product has no ID."

        # Step 2: Update the product
        update_payload = {
            "name": "Updated Product TC004",
            "description": "This description has been updated.",
            "price": "150.00",
            "stock": 20
        }
        
        update_resp = requests.put(
            f"{BASE_URL}/api/products/{product_id}/",
            json=update_payload,
            headers=HEADERS,
            auth=AUTH
        )
        assert update_resp.status_code == 200, f"Update failed: {update_resp.text}"
        updated_data = update_resp.json()
        
        assert updated_data.get("name") == update_payload["name"]
        assert updated_data.get("description") == update_payload["description"]
        # Float comparison for price
        assert float(updated_data.get("price")) == float(update_payload["price"])
        
        # Check stock (handle stock/stock_quantity naming if needed)
        stock = updated_data.get("stock") if "stock" in updated_data else updated_data.get("stock_quantity")
        assert stock == update_payload["stock"]

        # Step 3: Verify with GET
        get_resp = requests.get(
            f"{BASE_URL}/api/products/{product_id}/",
            headers=HEADERS,
            auth=AUTH
        )
        assert get_resp.status_code == 200, f"Failed to get updated product: {get_resp.text}"
        final_data = get_resp.json()
        
        assert final_data.get("name") == update_payload["name"]
        assert float(final_data.get("price")) == float(update_payload["price"])

    finally:
        # Cleanup
        if product_id:
            requests.delete(
                f"{BASE_URL}/api/products/{product_id}/",
                headers=HEADERS,
                auth=AUTH
            )

if __name__ == "__main__":
    test_update_product()