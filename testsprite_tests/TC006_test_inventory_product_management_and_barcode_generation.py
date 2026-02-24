import requests
import uuid


BASE_URL = "http://localhost:8000"
AUTH_URL = f"{BASE_URL}/api/token/"
INVENTORY_API_BASE = f"{BASE_URL}/inventory/api/"
TIMEOUT = 30


def get_jwt_token(username: str, password: str) -> str:
    resp = requests.post(
        AUTH_URL,
        json={"username": username, "password": password},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    token = resp.json().get("access")
    assert token, "JWT access token not found in response"
    return token


def test_inventory_product_management_and_barcode_generation():
    username = "boss"
    password = "Mm02022006"
    token = get_jwt_token(username, password)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    created_product_id = None
    created_category_id = None

    try:
        # Step 1: Create a product category
        category_data = {
            "name": f"TestCategory-{uuid.uuid4().hex[:8]}",
            "description": "Category for testing product management",
        }
        category_resp = requests.post(
            f"{INVENTORY_API_BASE}categories/",
            json=category_data,
            headers=headers,
            timeout=TIMEOUT,
        )
        category_resp.raise_for_status()
        category_resp_json = category_resp.json()
        created_category_id = category_resp_json.get("id")
        assert created_category_id, "Category ID not returned."

        # Step 2: Create a product type; assuming product types are fixed and we will use 'finished'
        product_type = "finished"

        # Step 3: Create a new product with SKU, category, product_type, barcode generation flag or barcode field
        # We set barcode to None or let the system generate it

        product_sku = f"SKU-{uuid.uuid4().hex[:8]}"
        product_name = f"TestProduct-{uuid.uuid4().hex[:6]}"
        product_data = {
            "sku": product_sku,
            "name": product_name,
            "category": created_category_id,
            "product_type": product_type,
            "barcode": None,  # Let system generate barcode
            "description": "Test product created by automated test",
            "uom": "pcs",  # Assuming the system requires unit of measure abbreviation
            "price": "15.50",  # Assuming price is string float-compatible
        }
        product_resp = requests.post(
            f"{INVENTORY_API_BASE}products/",
            json=product_data,
            headers=headers,
            timeout=TIMEOUT,
        )
        product_resp.raise_for_status()
        product_resp_json = product_resp.json()
        created_product_id = product_resp_json.get("id")
        assert created_product_id, "Product ID not returned."
        assert product_resp_json.get("sku") == product_sku
        assert product_resp_json.get("category") == created_category_id
        assert product_resp_json.get("product_type") == product_type

        # Check if barcode generated (barcode field should be non-empty, string)
        barcode_value = product_resp_json.get("barcode")
        assert barcode_value and isinstance(barcode_value, str), "Barcode not generated or invalid."

        # Step 4: Retrieve the product by ID and verify details
        get_product_resp = requests.get(
            f"{INVENTORY_API_BASE}products/{created_product_id}/",
            headers=headers,
            timeout=TIMEOUT,
        )
        get_product_resp.raise_for_status()
        get_product_data = get_product_resp.json()
        assert get_product_data["id"] == created_product_id
        assert get_product_data["sku"] == product_sku
        assert get_product_data["category"] == created_category_id
        assert get_product_data["product_type"] == product_type
        assert get_product_data.get("barcode") == barcode_value

        # Step 5: Update the product's name and description
        updated_name = product_name + "-Updated"
        updated_description = "Updated description by test"
        update_data = {
            "name": updated_name,
            "description": updated_description,
        }
        update_resp = requests.patch(
            f"{INVENTORY_API_BASE}products/{created_product_id}/",
            json=update_data,
            headers=headers,
            timeout=TIMEOUT,
        )
        update_resp.raise_for_status()
        updated_product = update_resp.json()
        assert updated_product["name"] == updated_name
        assert updated_product["description"] == updated_description

        # Step 6: Generate or re-generate barcode via API if such endpoint exists
        # The PRD does not explicitly mention a separate barcode generation endpoint,
        # so if there is an action endpoint, we test it; if not, we skip this step.

        # Let's try GET /products/{id}/barcode/ if exists (hypothetical)
        barcode_generate_resp = requests.get(
            f"{INVENTORY_API_BASE}products/{created_product_id}/barcode/",
            headers=headers,
            timeout=TIMEOUT,
        )
        if barcode_generate_resp.status_code in (200, 201):
            barcode_generate_json = barcode_generate_resp.json()
            new_barcode = barcode_generate_json.get("barcode")
            assert new_barcode and isinstance(new_barcode, str)
        else:
            # No separate barcode generation endpoint - ignore
            pass

        # Step 7: Delete the product and category to clean up will be done in finally

    finally:
        # Cleanup - delete product if created
        if created_product_id:
            del_product_resp = requests.delete(
                f"{INVENTORY_API_BASE}products/{created_product_id}/",
                headers=headers,
                timeout=TIMEOUT,
            )
            # Accept 204 No Content or 200 OK
            assert del_product_resp.status_code in (200, 204, 404)

        # Cleanup - delete category if created
        if created_category_id:
            del_category_resp = requests.delete(
                f"{INVENTORY_API_BASE}categories/{created_category_id}/",
                headers=headers,
                timeout=TIMEOUT,
            )
            assert del_category_resp.status_code in (200, 204, 404)


test_inventory_product_management_and_barcode_generation()
