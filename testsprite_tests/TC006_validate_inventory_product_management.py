import requests

BASE_URL = "http://127.0.0.1:8000"
AUTH_URL = f"{BASE_URL}/api/token/"
PRODUCTS_URL = f"{BASE_URL}/inventory/api/products/"
BARCODE_LOOKUP_URL = f"{BASE_URL}/inventory/api/barcode/lookup/"

USERNAME = "boss"
PASSWORD = "Mm02022006"

TIMEOUT = 30


def get_jwt_token():
    try:
        response = requests.post(
            AUTH_URL,
            json={"username": USERNAME, "password": PASSWORD},
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        token = response.json().get("access")
        assert token, "No access token in auth response"
        return token
    except (requests.RequestException, AssertionError) as e:
        raise RuntimeError(f"Authentication failed: {e}")


def test_inventory_product_management():
    token = get_jwt_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    product_id = None
    try:
        # Create a new product (POST)
        create_payload = {
            "name": "Test Product TC006",
            "sku": "TC006SKU001",
            "barcode": "1234567890123",
            "product_type": "finished",  # Assuming valid types: raw_material, semi_finished, finished
            "unit_of_measure": "pcs",
            "price": 15.99,
            "description": "Test product created during TC006",
        }

        create_resp = requests.post(
            PRODUCTS_URL,
            headers=headers,
            json=create_payload,
            timeout=TIMEOUT,
        )
        assert create_resp.status_code == 201, f"Product creation failed: {create_resp.text}"
        product = create_resp.json()
        product_id = product.get("id")
        assert product_id, "Created product response missing ID"

        # Retrieve the created product (GET)
        get_resp = requests.get(f"{PRODUCTS_URL}{product_id}/", headers=headers, timeout=TIMEOUT)
        assert get_resp.status_code == 200, f"Product retrieval failed: {get_resp.text}"
        get_product = get_resp.json()
        assert get_product["name"] == create_payload["name"]
        assert get_product["sku"] == create_payload["sku"]
        assert get_product["barcode"] == create_payload["barcode"]
        assert get_product["product_type"] == create_payload["product_type"]

        # Update product - change product type and price (PUT)
        update_payload = {
            "name": create_payload["name"],
            "sku": create_payload["sku"],
            "barcode": create_payload["barcode"],
            "product_type": "semi_finished",
            "unit_of_measure": "pcs",
            "price": 19.99,
            "description": "Updated description for TC006",
        }

        update_resp = requests.put(
            f"{PRODUCTS_URL}{product_id}/",
            headers=headers,
            json=update_payload,
            timeout=TIMEOUT,
        )
        assert update_resp.status_code == 200, f"Product update failed: {update_resp.text}"
        updated_product = update_resp.json()
        assert updated_product["product_type"] == "semi_finished"
        assert updated_product["price"] == 19.99
        assert updated_product["description"] == "Updated description for TC006"

        # Barcode lookup (GET) - query by barcode parameter
        params = {"barcode": create_payload["barcode"]}
        barcode_resp = requests.get(BARCODE_LOOKUP_URL, headers=headers, params=params, timeout=TIMEOUT)

        # Expected 200 with a list or object containing product info or 404 if not found
        assert barcode_resp.status_code in (200, 404), f"Barcode lookup unexpected status: {barcode_resp.text}"
        if barcode_resp.status_code == 200:
            # Validate barcode in response
            bcode_data = barcode_resp.json()
            if isinstance(bcode_data, list):
                assert any(p["barcode"] == create_payload["barcode"] for p in bcode_data), "Barcode not found in response"
            elif isinstance(bcode_data, dict):
                assert bcode_data.get("barcode") == create_payload["barcode"], "Barcode mismatch in response"

        # Delete the product (DELETE)
        del_resp = requests.delete(f"{PRODUCTS_URL}{product_id}/", headers=headers, timeout=TIMEOUT)
        assert del_resp.status_code in (204, 200, 202), f"Product deletion failed: {del_resp.text}"

        # Verify deletion by checking GET returns 404
        get_after_del = requests.get(f"{PRODUCTS_URL}{product_id}/", headers=headers, timeout=TIMEOUT)
        assert get_after_del.status_code == 404, "Deleted product still accessible"

    finally:
        # Cleanup if product still exists (e.g. if test failed before deletion)
        if product_id:
            _ = requests.delete(f"{PRODUCTS_URL}{product_id}/", headers=headers, timeout=TIMEOUT)


test_inventory_product_management()
