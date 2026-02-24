import requests
import uuid

BASE_URL = "http://localhost:8000"
AUTH_URL = f"{BASE_URL}/api/token/"
PRODUCTS_URL = f"{BASE_URL}/inventory/api/v1/products/"
TIMEOUT = 30


def get_jwt_token():
    try:
        response = requests.post(
            AUTH_URL,
            json={"username": "boss", "password": "Mm02022006"},
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        assert "access" in data, "No access token in response"
        return data["access"]
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to obtain JWT token: {e}")


def test_inventory_products_crud_api():
    token = get_jwt_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Create a new product payload
    unique_code = f"SKU-{uuid.uuid4().hex[:8]}"
    product_data = {
        "name": "Test Product",
        "code": unique_code,
        "cost": 10.5,
        "price": 20.0,
        "is_active": True,
    }

    product_id = None

    try:
        # Create Product (POST)
        create_resp = requests.post(
            PRODUCTS_URL, json=product_data, headers=headers, timeout=TIMEOUT
        )
        assert create_resp.status_code == 201, f"Product creation failed: {create_resp.text}"
        created_product = create_resp.json()
        assert "id" in created_product, "Created product lacks 'id'"
        product_id = created_product["id"]
        assert created_product["name"] == product_data["name"]
        assert created_product.get("code") == product_data["code"]

        # List Products with filter (GET)
        params = {"search": product_data["name"]}
        list_resp = requests.get(PRODUCTS_URL, headers=headers, params=params, timeout=TIMEOUT)
        assert list_resp.status_code == 200, f"Product listing failed: {list_resp.text}"
        list_data = list_resp.json()
        # Expect at least one product matching the search
        assert isinstance(list_data, dict) and "results" in list_data, "Unexpected list response structure"
        found = any(p["id"] == product_id for p in list_data["results"])
        assert found, "Created product not found in list with search filter"

        # Retrieve Product Details (GET)
        detail_url = f"{PRODUCTS_URL}{product_id}/"
        detail_resp = requests.get(detail_url, headers=headers, timeout=TIMEOUT)
        assert detail_resp.status_code == 200, f"Product detail retrieval failed: {detail_resp.text}"
        detail_data = detail_resp.json()
        assert detail_data["id"] == product_id
        assert detail_data["name"] == product_data["name"]

        # Update Product (PUT)
        update_payload = {
            "name": "Test Product Updated",
            "code": unique_code,
            "cost": 11.0,
            "price": 22.0,
            "is_active": False,
        }
        update_resp = requests.put(detail_url, json=update_payload, headers=headers, timeout=TIMEOUT)
        assert update_resp.status_code == 200, f"Product update failed: {update_resp.text}"
        updated_product = update_resp.json()
        assert updated_product["name"] == update_payload["name"]
        assert updated_product.get("code") == update_payload["code"]
        assert updated_product["cost"] == update_payload["cost"]
        assert updated_product["price"] == update_payload["price"]
        assert updated_product["is_active"] == update_payload["is_active"]

    finally:
        # Delete Product (DELETE)
        if product_id is not None:
            delete_url = f"{PRODUCTS_URL}{product_id}/"
            try:
                delete_resp = requests.delete(delete_url, headers=headers, timeout=TIMEOUT)
                assert delete_resp.status_code == 204, f"Product deletion failed: {delete_resp.text}"
            except Exception as e:
                # Log or raise depending on test framework requirement, here we raise
                raise RuntimeError(f"Failed to delete product on cleanup: {e}")


test_inventory_products_crud_api()