import requests
from requests.auth import HTTPBasicAuth

base_url = "http://localhost:8000"
username = "boss"
password = "Mm02022006"
timeout = 30

def test_pos_order_creation_and_thermal_printing():
    auth = HTTPBasicAuth(username, password)
    headers = {"Content-Type": "application/json"}

    # Corrected payload for creating a POS order using 'product_id' instead of 'product_barcode'
    pos_order_payload = {
        "customer_id": None,  # Assuming optional or use a valid customer ID if required
        "lines": [
            {
                "product_id": 1,  # Changed from 'product_barcode' to 'product_id'
                "quantity": 2,
                "price": 50.0,
                "discount": 0,
                "tax": 5
            }
        ],
        "payment": {
            "method": "cash",
            "amount": 105.0
        },
        "notes": "Test order created via API with barcode scanning support"
    }

    order_id = None
    try:
        # 1. Create POS order
        # ✅ FIX: المسار الصحيح هو /complete-order/ وليس /orders/create/
        create_order_url = f"{base_url}/pos/api/complete-order/"
        create_resp = requests.post(create_order_url, json=pos_order_payload, auth=auth, headers=headers, timeout=timeout)
        assert create_resp.status_code == 201, f"Expected HTTP 201 for order creation, got {create_resp.status_code}"
        create_data = create_resp.json()
        assert "id" in create_data, "Response missing order ID"
        order_id = create_data["id"]
        assert create_data.get("lines") and len(create_data["lines"]) == len(pos_order_payload["lines"]), "Order lines mismatch"
        
        # 2. Verify thermal invoice printing functionality
        print_status_url = f"{base_url}/pos/api/orders/{order_id}/print-status/"
        print_resp = requests.get(print_status_url, auth=auth, headers=headers, timeout=timeout)
        if print_resp.status_code == 200:
            print_data = print_resp.json()
            assert print_data.get("thermal_invoice_printed") is True, "Thermal invoice printing failed or not confirmed"
        else:
            order_details_url = f"{base_url}/pos/api/orders/{order_id}/"
            order_resp = requests.get(order_details_url, auth=auth, headers=headers, timeout=timeout)
            assert order_resp.status_code == 200, f"Failed to get order details for printing verification, got {order_resp.status_code}"
            order_details = order_resp.json()
            assert order_details.get("thermal_invoice_printed") or order_details.get("print_status") == "printed", \
                "Thermal invoice printing not confirmed in order details"

        # 3. Verify order listing includes the newly created order
        list_orders_url = f"{base_url}/pos/api/orders/list/"
        list_resp = requests.get(list_orders_url, auth=auth, headers=headers, timeout=timeout)
        assert list_resp.status_code == 200, f"Expected HTTP 200 for order list, got {list_resp.status_code}"
        list_data = list_resp.json()
        orders = list_data if isinstance(list_data, list) else list_data.get("results", [])
        assert any(order.get("id") == order_id for order in orders), "Created order not found in order listing"
    finally:
        # Cleanup: Delete the created POS order
        if order_id:
            delete_order_url = f"{base_url}/pos/api/orders/{order_id}/"
            del_resp = requests.delete(delete_order_url, auth=auth, headers=headers, timeout=timeout)
            assert del_resp.status_code in (200, 204), f"Failed to delete test POS order with ID {order_id}"

test_pos_order_creation_and_thermal_printing()
