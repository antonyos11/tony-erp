import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost:8000"
USERNAME = "boss"
PASSWORD = "Mm02022006"
TIMEOUT = 30

def test_ecommerce_product_catalog_and_order_management():
    auth = HTTPBasicAuth(USERNAME, PASSWORD)
    headers = {"Accept": "application/json", "Content-Type": "application/json"}

    # Step 1: Retrieve product catalog
    products_url = f"{BASE_URL}/api/ecommerce/products/"
    try:
        r = requests.get(products_url, auth=auth, headers=headers, timeout=TIMEOUT)
        r.raise_for_status()
        products_data = r.json()
        assert isinstance(products_data, dict) or isinstance(products_data, list), "Products response is not JSON object or list"
    except Exception as e:
        assert False, f"Failed to retrieve product catalog: {e}"

    # Step 2: Retrieve product categories
    categories_url = f"{BASE_URL}/api/ecommerce/categories/"
    try:
        r = requests.get(categories_url, auth=auth, headers=headers, timeout=TIMEOUT)
        r.raise_for_status()
        categories_data = r.json()
        assert isinstance(categories_data, dict) or isinstance(categories_data, list), "Categories response is not JSON object or list"
    except Exception as e:
        assert False, f"Failed to retrieve product categories: {e}"

    # Prepare a product for cart operations - create if no product exists
    product_id = None
    if isinstance(products_data, list) and len(products_data) > 0:
        # Use existing product
        product = products_data[0]
        product_id = product.get("id")
    else:
        # Create a product (POST) - assuming minimal fields required: name, category, price
        # Find a category id for product if categories exist
        category_id = categories_data[0].get("id") if (isinstance(categories_data, list) and len(categories_data)>0) else None

        product_payload = {
            "name": "Test Product from API",
            "sku": "TP-001",
            "description": "Test product description",
            "price": 9.99,
            "category": category_id,
            "is_active": True,
            "stock": 10
        }
        try:
            r = requests.post(products_url, auth=auth, headers=headers, json=product_payload, timeout=TIMEOUT)
            r.raise_for_status()
            created_product = r.json()
            product_id = created_product.get("id")
            assert product_id is not None, "Created product ID is None"
        except Exception as e:
            assert False, f"Failed to create a test product: {e}"

    assert product_id is not None, "No product id available for cart testing"

    # Define helper to clean up created product at the end if needed
    def delete_product(pid):
        try:
            r = requests.delete(f"{products_url}{pid}/", auth=auth, headers=headers, timeout=TIMEOUT)
            if r.status_code not in [204, 200, 202]:
                # Might be 404 if already deleted or unavailable
                pass
        except Exception:
            pass

    # Step 3: Add product to cart
    cart_url = f"{BASE_URL}/api/ecommerce/cart/"
    cart_product = {
        "product_id": product_id,
        "quantity": 2
    }
    cart_id = None
    try:
        r = requests.post(cart_url, auth=auth, headers=headers, json=cart_product, timeout=TIMEOUT)
        if r.status_code == 201 or r.status_code == 200:
            cart_resp = r.json()
            cart_id = cart_resp.get("id")
            assert cart_id is not None, "Cart item creation failed to return id"
        else:
            # If API doesn't allow POST (maybe only PUT or PATCH), handle gracefully
            assert False, f"Failed to add product to cart: Status {r.status_code}: {r.text}"
    except Exception as e:
        assert False, f"Exception adding product to cart: {e}"

    # Step 4: Retrieve cart contents
    try:
        r = requests.get(cart_url, auth=auth, headers=headers, timeout=TIMEOUT)
        r.raise_for_status()
        cart_list = r.json()
        assert isinstance(cart_list, list) or isinstance(cart_list, dict), "Cart response unexpected format"
    except Exception as e:
        assert False, f"Failed to retrieve cart contents: {e}"

    # Step 5: Update cart item quantity if cart_id available
    if cart_id is not None:
        update_payload = {"quantity": 3}
        try:
            r = requests.put(f"{cart_url}{cart_id}/", auth=auth, headers=headers, json=update_payload, timeout=TIMEOUT)
            r.raise_for_status()
            updated_item = r.json()
            assert updated_item.get("quantity") == 3, "Cart item quantity not updated correctly"
        except Exception as e:
            assert False, f"Failed to update cart item quantity: {e}"

    # Step 6: Create order from cart
    orders_url = f"{BASE_URL}/api/ecommerce/orders/"
    order_payload = {
        "cart_id": cart_id,
        "payment_method": "paymob",
        "shipping_address": "123 Test St, Test City",
        "billing_address": "123 Test St, Test City"
    }
    order_id = None
    try:
        r = requests.post(orders_url, auth=auth, headers=headers, json=order_payload, timeout=TIMEOUT)
        r.raise_for_status()
        order_resp = r.json()
        order_id = order_resp.get("id")
        assert order_id is not None, "Order creation did not return an ID"
    except Exception as e:
        assert False, f"Failed to create order: {e}"

    # Step 7: Retrieve order details
    if order_id is not None:
        try:
            r = requests.get(f"{orders_url}{order_id}/", auth=auth, headers=headers, timeout=TIMEOUT)
            r.raise_for_status()
            order_detail = r.json()
            assert order_detail.get("id") == order_id, "Order details do not match created order"
        except Exception as e:
            assert False, f"Failed to retrieve order details: {e}"

    # Cleanup: Delete created cart item, order, product if possible
    try:
        if cart_id is not None:
            requests.delete(f"{cart_url}{cart_id}/", auth=auth, headers=headers, timeout=TIMEOUT)
    except Exception:
        pass

    try:
        if order_id is not None:
            requests.delete(f"{orders_url}{order_id}/", auth=auth, headers=headers, timeout=TIMEOUT)
    except Exception:
        pass

    if product_id is not None and (isinstance(products_data, list) == False or len(products_data) == 0):
        # Only delete if product was created by us
        delete_product(product_id)

test_ecommerce_product_catalog_and_order_management()
