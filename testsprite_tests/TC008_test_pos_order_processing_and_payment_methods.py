import requests
import json

BASE_URL = "http://localhost:8000"
AUTH_URL = f"{BASE_URL}/api/token/"
POS_API_PREFIX = "/pos/api"
TIMEOUT = 30

USERNAME = "boss"
PASSWORD = "Mm02022006"


def test_pos_order_processing_and_payment_methods():
    # Authenticate and get JWT token
    auth_payload = {"username": USERNAME, "password": PASSWORD}
    try:
        auth_resp = requests.post(AUTH_URL, json=auth_payload, timeout=TIMEOUT)
        assert auth_resp.status_code == 200, f"Auth failed: {auth_resp.text}"
        tokens = auth_resp.json()
        access_token = tokens.get("access")
        assert access_token, "No access token received"
    except Exception as e:
        assert False, f"Authentication request failed: {e}"

    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    created_shift_id = None
    created_order_id = None

    try:
        # 1. Open a POS shift
        shift_open_url = f"{BASE_URL}{POS_API_PREFIX}/shift/open/"
        shift_open_payload = {
            "branch": 1,  # Assuming branch id=1 exists; else adjust accordingly
            "cashier": USERNAME,
            "start_cash": 100.0
        }
        resp = requests.post(shift_open_url, json=shift_open_payload, headers=headers, timeout=TIMEOUT)
        assert resp.status_code == 201, f"Shift open failed: {resp.text}"
        shift_data = resp.json()
        created_shift_id = shift_data.get("id")
        assert created_shift_id, "Shift ID not returned"

        # 2. Create a POS sales order with barcode scanning and discounts
        order_create_url = f"{BASE_URL}{POS_API_PREFIX}/orders/"
        # Example barcode and product assumed; adjust barcode to known product barcode if needed
        order_payload = {
            "shift": created_shift_id,
            "customer": None,
            "items": [
                {
                    "barcode": "1234567890123",
                    "quantity": 2,
                    "discount": 5.0
                },
                {
                    "barcode": "9876543210987",
                    "quantity": 1,
                    "discount": 0
                }
            ],
            "notes": "Test order for TC008"
        }
        resp = requests.post(order_create_url, json=order_payload, headers=headers, timeout=TIMEOUT)
        assert resp.status_code == 201, f"Order creation failed: {resp.text}"
        order_data = resp.json()
        created_order_id = order_data.get("id")
        assert created_order_id, "Order ID not returned"
        assert "items" in order_data and len(order_data["items"]) == 2, "Order items count mismatch"

        # 3. Apply payment with multiple methods (cash + card)
        payment_url = f"{BASE_URL}{POS_API_PREFIX}/payments/"
        payment_payload = {
            "order": created_order_id,
            "payments": [
                {"method": "cash", "amount": 50.0},
                {"method": "card", "amount": 45.0}
            ]
        }
        resp = requests.post(payment_url, json=payment_payload, headers=headers, timeout=TIMEOUT)
        assert resp.status_code == 201, f"Payment processing failed: {resp.text}"
        payment_data = resp.json()
        assert "id" in payment_data, "Payment ID not returned"
        assert abs(sum(p["amount"] for p in payment_payload["payments"]) - payment_data.get("total_paid", 0)) < 0.01, "Paid amount mismatch"

        # 4. Close the shift
        shift_close_url = f"{BASE_URL}{POS_API_PREFIX}/shift/close/"
        shift_close_payload = {"id": created_shift_id}
        resp = requests.post(shift_close_url, json=shift_close_payload, headers=headers, timeout=TIMEOUT)
        assert resp.status_code == 200, f"Shift close failed: {resp.text}"
        close_data = resp.json()
        assert close_data.get("status") in ["closed", "completed"], "Shift not properly closed"

    finally:
        # Cleanup: delete created order and close shift if still open
        if created_order_id:
            try:
                del_order_url = f"{BASE_URL}{POS_API_PREFIX}/orders/{created_order_id}/"
                del_resp = requests.delete(del_order_url, headers=headers, timeout=TIMEOUT)
                # Deletion might be successful or maybe not allowed; ignore failure but log
            except Exception:
                pass
        if created_shift_id:
            try:
                # Attempt to close shift if not closed
                shift_status_url = f"{BASE_URL}{POS_API_PREFIX}/shift/{created_shift_id}/"
                status_resp = requests.get(shift_status_url, headers=headers, timeout=TIMEOUT)
                if status_resp.status_code == 200:
                    shift_status = status_resp.json().get("status")
                    if shift_status != "closed":
                        shift_close_url = f"{BASE_URL}{POS_API_PREFIX}/shift/close/"
                        requests.post(shift_close_url, json={"id": created_shift_id}, headers=headers, timeout=TIMEOUT)
            except Exception:
                pass


test_pos_order_processing_and_payment_methods()