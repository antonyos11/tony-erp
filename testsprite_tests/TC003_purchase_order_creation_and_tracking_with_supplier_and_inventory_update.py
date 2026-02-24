import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost:8000"
AUTH = HTTPBasicAuth("boss", "Mm02022006")
TIMEOUT = 30
HEADERS = {"Content-Type": "application/json"}


def test_purchase_order_creation_and_tracking_with_supplier_and_inventory_update():
    # Step 1: Create a supplier (needed for purchase order)
    supplier_payload = {
        "name": "Test Supplier",
        "contact_email": "supplier@test.com",
        "phone_number": "+971500000001",
        "address": "Test Address 123"
    }
    supplier_id = None
    purchase_order_id = None
    try:
        supplier_resp = requests.post(
            f"{BASE_URL}/api/suppliers/",
            auth=AUTH,
            headers=HEADERS,
            json=supplier_payload,
            timeout=TIMEOUT,
        )
        assert supplier_resp.status_code == 201, f"Failed to create supplier: {supplier_resp.text}"
        supplier = supplier_resp.json()
        supplier_id = supplier.get("id")
        assert supplier_id is not None, "Supplier ID not returned"

        # Step 2: Create product inventory item (needed for purchase order lines)
        product_payload = {
            "name": "Test Product",
            "sku": "TP-001",
            "description": "Product for testing purchase order",
            "unit_price": 100.0,
            "stock_quantity": 50,
            "warehouse_location": "Main Warehouse"
        }
        product_resp = requests.post(
            f"{BASE_URL}/api/products/",
            auth=AUTH,
            headers=HEADERS,
            json=product_payload,
            timeout=TIMEOUT,
        )
        assert product_resp.status_code == 201, f"Failed to create product: {product_resp.text}"
        product = product_resp.json()
        product_id = product.get("id")
        assert product_id is not None, "Product ID not returned"

        # Step 3: Create purchase order referencing supplier and product with line items
        purchase_order_payload = {
            "supplier": supplier_id,
            "order_date": "2026-01-21",
            "expected_delivery_date": "2026-01-30",
            "status": "draft",
            "lines": [
                {
                    "product_id": product_id,
                    "quantity": 10,
                    "unit_price": 95.0
                }
            ]
        }
        po_resp = requests.post(
            f"{BASE_URL}/api/purchase_orders/",
            auth=AUTH,
            headers=HEADERS,
            json=purchase_order_payload,
            timeout=TIMEOUT,
        )
        assert po_resp.status_code == 201, f"Failed to create purchase order: {po_resp.text}"
        purchase_order = po_resp.json()
        purchase_order_id = purchase_order.get("id")
        assert purchase_order_id is not None, "Purchase Order ID not returned"

        # Step 4: Approve the purchase order (simulate manager approval)
        approval_payload = {"status": "approved"}
        approve_resp = requests.put(
            f"{BASE_URL}/api/purchase_orders/{purchase_order_id}/",
            auth=AUTH,
            headers=HEADERS,
            json=approval_payload,
            timeout=TIMEOUT,
        )
        assert approve_resp.status_code == 200, f"Failed to approve purchase order: {approve_resp.text}"
        approved_po = approve_resp.json()
        assert approved_po.get("status") == "approved", "Purchase order status not updated to approved"

        # Step 5: Simulate receiving goods - update purchase order status and inventory
        receive_payload = {"status": "received"}
        receive_resp = requests.put(
            f"{BASE_URL}/api/purchase_orders/{purchase_order_id}/",
            auth=AUTH,
            headers=HEADERS,
            json=receive_payload,
            timeout=TIMEOUT,
        )
        assert receive_resp.status_code == 200, f"Failed to mark purchase order as received: {receive_resp.text}"
        received_po = receive_resp.json()
        assert received_po.get("status") == "received", "Purchase order status not updated to received"

        # Step 6: Verify that inventory stock quantity updated correctly
        product_get_resp = requests.get(
            f"{BASE_URL}/api/products/{product_id}/",
            auth=AUTH,
            headers=HEADERS,
            timeout=TIMEOUT
        )
        assert product_get_resp.status_code == 200, f"Failed to get product info: {product_get_resp.text}"
        updated_product = product_get_resp.json()
        expected_stock = product_payload["stock_quantity"] + purchase_order_payload["lines"][0]["quantity"]
        assert updated_product.get("stock_quantity") == expected_stock, (
            f"Inventory not updated correctly. Expected {expected_stock}, got {updated_product.get('stock_quantity')}"
        )

        # Step 7: Verify supplier data still exists and is correct
        supplier_get_resp = requests.get(
            f"{BASE_URL}/api/suppliers/{supplier_id}/",
            auth=AUTH,
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        assert supplier_get_resp.status_code == 200, f"Failed to get supplier info: {supplier_get_resp.text}"
        current_supplier = supplier_get_resp.json()
        assert current_supplier.get("name") == supplier_payload["name"], "Supplier name mismatch after purchase order processing"

    finally:
        # Cleanup: Delete purchase order if created
        if purchase_order_id is not None:
            requests.delete(
                f"{BASE_URL}/api/purchase_orders/{purchase_order_id}/",
                auth=AUTH,
                headers=HEADERS,
                timeout=TIMEOUT,
            )
        # Cleanup: Delete product if created
        if 'product_id' in locals():
            requests.delete(
                f"{BASE_URL}/api/products/{product_id}/",
                auth=AUTH,
                headers=HEADERS,
                timeout=TIMEOUT,
            )
        # Cleanup: Delete supplier if created
        if supplier_id is not None:
            requests.delete(
                f"{BASE_URL}/api/suppliers/{supplier_id}/",
                auth=AUTH,
                headers=HEADERS,
                timeout=TIMEOUT,
            )


test_purchase_order_creation_and_tracking_with_supplier_and_inventory_update()
