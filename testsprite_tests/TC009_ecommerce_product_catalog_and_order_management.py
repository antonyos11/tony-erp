import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost:8000"
AUTH = HTTPBasicAuth("boss", "Mm02022006")
HEADERS = {"Content-Type": "application/json"}
TIMEOUT = 30


def test_ecommerce_product_catalog_and_order_management():
    # Step 1: Retrieve product categories
    # ✅ FIX: المسار الصحيح هو /categories/ وليس /product-categories/
    categories_url = f"{BASE_URL}/store/api/categories/"
    categories_resp = requests.get(categories_url, auth=AUTH, headers=HEADERS, timeout=TIMEOUT)
    assert categories_resp.status_code == 200, f"Failed to get categories: {categories_resp.text}"
    categories_data = categories_resp.json()
    assert isinstance(categories_data, list), "Categories data should be a list"

    # Step 2: Retrieve product catalog
    products_url = f"{BASE_URL}/store/api/products/"
    products_resp = requests.get(products_url, auth=AUTH, headers=HEADERS, timeout=TIMEOUT)
    assert products_resp.status_code == 200, f"Failed to get products: {products_resp.text}"
    products_data = products_resp.json()
    assert isinstance(products_data, list), "Products data should be a list"
    assert len(products_data) > 0, "No products found in catalog"

    # Pick a product to add to cart
    product = None
    for p in products_data:
        if "id" in p:
            product = p
            break
    assert product is not None, "No product with 'id' found to add to cart"
    product_id = product["id"]

    # Step 3: Add product to shopping cart
    cart_url = f"{BASE_URL}/store/api/cart/"
    add_to_cart_payload = {
        "items": [
            {
                "product_id": product_id,
                "quantity": 1
            }
        ]
    }
    # Create or reset cart by posting items (assuming POST to /cart/ adds items)
    cart_resp = requests.post(cart_url, json=add_to_cart_payload, auth=AUTH, headers=HEADERS, timeout=TIMEOUT)
    assert cart_resp.status_code in (200, 201), f"Failed to add product to cart: {cart_resp.text}"
    cart_data = cart_resp.json()
    assert "items" in cart_data, "Cart response missing items"
    assert any(item.get("product_id") == product_id for item in cart_data["items"]), "Product not added to cart"

    # Step 4: Retrieve shopping cart contents and verify
    cart_get_resp = requests.get(cart_url, auth=AUTH, headers=HEADERS, timeout=TIMEOUT)
    assert cart_get_resp.status_code == 200, f"Failed to get cart contents: {cart_get_resp.text}"
    cart_contents = cart_get_resp.json()
    assert "items" in cart_contents, "Cart contents missing items"
    assert any(item.get("product_id") == product_id for item in cart_contents["items"]), "Product missing from cart"

    # Step 5: Create an order from the cart
    orders_url = f"{BASE_URL}/store/api/orders/"
    order_payload = {
        "items": [
            {
                "product_id": product_id,
                "quantity": 1
            }
        ],
        "payment_method": "paymob",
        # Additional fields might be required, such as customer info, address, etc.
    }
    order_resp = requests.post(orders_url, json=order_payload, auth=AUTH, headers=HEADERS, timeout=TIMEOUT)
    assert order_resp.status_code in (200, 201), f"Failed to create order: {order_resp.text}"
    order_data = order_resp.json()
    assert "id" in order_data, "Order response missing id"
    order_id = order_data["id"]

    try:
        # Step 6: Retrieve the order and verify details
        order_get_url = f"{orders_url}{order_id}/"
        order_get_resp = requests.get(order_get_url, auth=AUTH, headers=HEADERS, timeout=TIMEOUT)
        assert order_get_resp.status_code == 200, f"Failed to get order: {order_get_resp.text}"
        order_details = order_get_resp.json()
        assert order_details.get("id") == order_id, "Order ID mismatch"
        assert "items" in order_details, "Order details missing items"
        assert any(item.get("product_id") == product_id for item in order_details["items"]), "Order does not include product"

        # Step 7: Simulate payment gateway integration (PayMob)
        # Assuming there's a payment URL or payment processing endpoint - since not explicitly in PRD, simulate by PATCH order with payment status
        payment_payload = {
            "payment_status": "paid",
            "payment_gateway": "paymob",
            "transaction_reference": "test_txn_12345"
        }
        payment_resp = requests.patch(order_get_url, json=payment_payload, auth=AUTH, headers=HEADERS, timeout=TIMEOUT)
        assert payment_resp.status_code == 200, f"Failed to update payment status: {payment_resp.text}"
        payment_data = payment_resp.json()
        assert payment_data.get("payment_status") == "paid", "Payment status not updated to paid"

    finally:
        # Cleanup: Delete the created order
        delete_order_resp = requests.delete(order_get_url, auth=AUTH, headers=HEADERS, timeout=TIMEOUT)
        assert delete_order_resp.status_code in (200, 204), f"Failed to delete order: {delete_order_resp.text}"


test_ecommerce_product_catalog_and_order_management()
