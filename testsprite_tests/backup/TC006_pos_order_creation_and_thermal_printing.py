import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost:8000/dashboard/dashboard"
USERNAME = "boss"
PASSWORD = "Mm02022006"
TIMEOUT = 30

def test_pos_order_creation_and_thermal_printing():
    auth = HTTPBasicAuth(USERNAME, PASSWORD)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    order_create_url = f"{BASE_URL}/api/pos/orders/create/"
    order_list_url = f"{BASE_URL}/api/pos/orders/list/"

    order_payload = {
        "lines": [
            {
                "product_barcode": "1234567890123",
                "quantity": 2,
                "price_unit": 10.50,
                "description": "Test Product with barcode"
            }
        ],
        "payment_method": "cash",
        "notes": "Test order with barcode scanning"
    }

    pos_order_id = None

    try:
        create_response = requests.post(order_create_url, json=order_payload, headers=headers, auth=auth, timeout=TIMEOUT)
        assert create_response.status_code in (200, 201), f"Expected 200 or 201 Created, got {create_response.status_code}"
        create_data = create_response.json()
        assert "id" in create_data, "Response missing order id"
        pos_order_id = create_data["id"]

        print_url = f"{BASE_URL}/api/pos/orders/{pos_order_id}/print/"
        print_response = requests.get(print_url, headers=headers, auth=auth, timeout=TIMEOUT)
        assert print_response.status_code == 200, f"Expected 200 OK for print request, got {print_response.status_code}"
        assert print_response.content, "Print response content is empty"

        list_response = requests.get(order_list_url, headers=headers, auth=auth, timeout=TIMEOUT)
        assert list_response.status_code == 200, f"Expected 200 OK from order list, got {list_response.status_code}"
        list_data = list_response.json()
        assert isinstance(list_data, list), "Order list response is not a list"
        order_ids = [order.get("id") for order in list_data if "id" in order]
        assert pos_order_id in order_ids, "Created order ID not found in order list"

    finally:
        if pos_order_id is not None:
            delete_url = f"{BASE_URL}/api/pos/orders/{pos_order_id}/"
            try:
                delete_response = requests.delete(delete_url, headers=headers, auth=auth, timeout=TIMEOUT)
                assert delete_response.status_code in (200, 204), f"Failed to delete order {pos_order_id}, status {delete_response.status_code}"
            except Exception:
                pass

test_pos_order_creation_and_thermal_printing()
