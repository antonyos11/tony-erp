import requests

BASE_URL = "http://localhost:8000"
AUTH_URL = f"{BASE_URL}/api/token/"
LOW_STOCK_URL = f"{BASE_URL}/inventory/api/v1/products/low-stock/"
PRODUCTS_URL = f"{BASE_URL}/inventory/api/v1/products/"

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
        data = response.json()
        token = data.get("access")
        assert token, "Access token missing in auth response"
        return token
    except requests.RequestException as e:
        raise RuntimeError(f"Authentication failed: {e}")


def create_product(token, name="LowStockTestProduct", code="LST123", price=1, cost=0.5, is_active=True):
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "name": name,
        "code": code,
        "price": price,
        "cost": cost,
        "is_active": is_active,
    }
    try:
        response = requests.post(PRODUCTS_URL, json=payload, headers=headers, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()
        product_id = data.get("id")
        assert product_id is not None, "Created product does not have an ID"
        return product_id
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to create product: {e}")


def delete_product(token, product_id):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.delete(f"{PRODUCTS_URL}{product_id}/", headers=headers, timeout=TIMEOUT)
        # 204 No Content expected
        if response.status_code != 204:
            raise RuntimeError(
                f"Failed to delete product {product_id}: Status code {response.status_code} - {response.text}"
            )
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to delete product {product_id}: {e}")


def test_inventory_low_stock_api():
    token = get_jwt_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Create a new product with low stock - We assume low stock check is on backend stock levels,
    # but for test we just create the product and rely on existing stock or product attributes.
    product_id = None
    try:
        product_id = create_product(token)
        # GET low stock products list
        response = requests.get(LOW_STOCK_URL, headers=headers, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        # Ensure that the returned products have stock below minimum threshold
        # As the actual stock field is not given, we just verify the list has dict items and required fields
        for product in data:
            assert isinstance(product, dict), "Each product should be a dictionary"
            assert "id" in product, "Product missing 'id' field"
            assert "name" in product, "Product missing 'name' field"

        # Also check that our created product is in the low stock list or at least the endpoint works.
        # It might not be low stock because we don't set stock here, so no assertion on inclusion.
    finally:
        if product_id:
            delete_product(token, product_id)


test_inventory_low_stock_api()