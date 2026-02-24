import requests

BASE_URL = "http://localhost:8000"
AUTH_ENDPOINT = "/api/token/"
PURCHASE_ORDERS_ENDPOINT = "/purchases/api/v1/orders/"
PURCHASE_ORDER_CONFIRM_ENDPOINT = "/purchases/api/v1/orders/{id}/confirm/"

USERNAME = "boss"
PASSWORD = "Mm02022006"
TIMEOUT = 30


def test_purchases_orders_confirm_api():
    # Authenticate and get JWT token
    try:
        auth_resp = requests.post(
            BASE_URL + AUTH_ENDPOINT,
            json={"username": USERNAME, "password": PASSWORD},
            timeout=TIMEOUT,
        )
        assert auth_resp.status_code == 200, f"Auth failed: {auth_resp.text}"
        tokens = auth_resp.json()
        access_token = tokens.get("access")
        assert access_token, "Access token not present in auth response"
    except Exception as e:
        raise AssertionError(f"Authentication request failed: {e}")

    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    # Create a supplier to use for purchase order (since supplier required to create order)
    # Supplier uses Partner Model filtered by partner_type=supplier, but from doc,
    # supplier creation endpoint: /purchases/api/v1/suppliers/ requires "name" and optional phone/email
    supplier_data = {
        "name": "Test Supplier for Order"
    }

    supplier_id = None
    order_id = None
    try:
        supplier_resp = requests.post(
            BASE_URL + "/purchases/api/v1/suppliers/",
            json=supplier_data,
            headers=headers,
            timeout=TIMEOUT,
        )
        assert supplier_resp.status_code == 201, f"Supplier creation failed: {supplier_resp.text}"
        supplier = supplier_resp.json()
        supplier_id = supplier.get("id")
        assert supplier_id, "Supplier ID not returned"

        # Create a draft purchase order, the schema isn't fully specified,
        # but usually an order requires at least supplier reference, and line items.
        # We'll create minimal draft order with supplier id.
        # Assume that the order creation at /purchases/api/v1/orders/ supports POST with supplier field.
        order_payload = {
            "supplier": supplier_id,
            "status": "draft",  # force draft status if possible
            "lines": [
                # At minimum one line item is usually required, but no details provided.
                # For safety, try minimal empty lines list and see if API accepts.
            ]
        }

        # Creating minimal order with empty lines or no lines if API accepts
        order_resp = requests.post(
            BASE_URL + PURCHASE_ORDERS_ENDPOINT,
            json=order_payload,
            headers=headers,
            timeout=TIMEOUT,
        )
        assert order_resp.status_code == 201, f"Purchase order creation failed: {order_resp.text}"
        order = order_resp.json()
        order_id = order.get("id")
        assert order_id, "Order ID not returned"

        # Confirm the draft order
        confirm_resp = requests.post(
            BASE_URL + PURCHASE_ORDER_CONFIRM_ENDPOINT.format(id=order_id),
            headers=headers,
            timeout=TIMEOUT,
        )
        assert confirm_resp.status_code == 200, f"Confirming order failed: {confirm_resp.text}"
        confirmed_order = confirm_resp.json()

        # Verify order status updated accordingly (should not be draft anymore)
        updated_status = confirmed_order.get("status")
        assert updated_status is not None, "Order status not in confirm response"
        assert updated_status != "draft", f"Order status still draft after confirm: {updated_status}"

    finally:
        # Cleanup: delete the created purchase order if exists
        if order_id is not None:
            try:
                del_order_resp = requests.delete(
                    BASE_URL + PURCHASE_ORDERS_ENDPOINT + f"{order_id}/",
                    headers=headers,
                    timeout=TIMEOUT,
                )
                # 204 expected if deleted successfully
                assert del_order_resp.status_code in (204, 200, 202), f"Failed to delete order {order_id}: {del_order_resp.text}"
            except Exception:
                pass
        # Cleanup: delete created supplier if exists
        if supplier_id is not None:
            try:
                del_supplier_resp = requests.delete(
                    BASE_URL + "/purchases/api/v1/suppliers/" + f"{supplier_id}/",
                    headers=headers,
                    timeout=TIMEOUT,
                )
                assert del_supplier_resp.status_code in (204, 200, 202), f"Failed to delete supplier {supplier_id}: {del_supplier_resp.text}"
            except Exception:
                pass


test_purchases_orders_confirm_api()