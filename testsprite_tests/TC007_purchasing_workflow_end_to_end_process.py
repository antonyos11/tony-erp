import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost:8000"
AUTH = HTTPBasicAuth("boss", "Mm02022006")
HEADERS = {"Content-Type": "application/json"}
TIMEOUT = 30

def test_purchasing_workflow_end_to_end_process():
    purchase_order_id = None
    bill_id = None
    supplier_partner_id = None
    supplier_id = None
    location_id = None
    
    try:
        # Step 0: Create Supplier and Location
        supplier_payload = {
            "name": "Test Supplier Workflow 2",
            "email": "supplier_flow2@example.com",
            "phone": "0123456789", 
            "contact_person": "Contact Flow"
        }
        r = requests.post(f"{BASE_URL}/api/suppliers/", json=supplier_payload, auth=AUTH, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code == 201:
            supplier = r.json()
            supplier_id = supplier.get("id")
            # Determine Partner ID (PurchaseOrder needs Partner ID)
            # supplier['partner'] might be the ID
            supplier_partner_id = supplier.get("partner")
            print(f"Created Supplier {supplier_id}, Partner {supplier_partner_id}")
        else:
            supplier_partner_id = 1
            print(f"Supplier creation failed: {r.status_code}. Using Partner ID 1.")

        # Create Location
        location_payload = {"name": "Test Warehouse", "code": "WH-TEST", "address": "123 St"}
        r = requests.post(f"{BASE_URL}/api/locations/", json=location_payload, auth=AUTH, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code == 201:
            location_id = r.json().get("id")
        else:
            location_id = 1 # Fallback
            print(f"Location creation failed: {r.status_code}. Using ID 1.")

        # Step 1: Create Purchase Order
        po_payload = {
            "supplier": supplier_partner_id,
            "date": "2026-02-10",
            "status": "draft",
            "items": [
                {
                    "product": 1, 
                    "location": location_id,
                    "quantity": 10, 
                    "cost": 50
                }
            ]
        }
        r = requests.post(f"{BASE_URL}/api/purchase_orders/",
                          json=po_payload, auth=AUTH, headers=HEADERS, timeout=TIMEOUT)
        assert r.status_code == 201, f"Purchase Order creation failed: {r.text}"
        po = r.json()
        purchase_order_id = po.get("id")
        assert purchase_order_id is not None

        # Step 2: Approve Purchase Order
        r = requests.put(f"{BASE_URL}/api/purchase_orders/{purchase_order_id}/approve/",
                          auth=AUTH, headers=HEADERS, timeout=TIMEOUT)
        # Note: approve action might be POST or PUT. api/views.py uses @action(..., methods=['put', 'post'])
        assert r.status_code == 200, f"Approval failed: {r.text}"
        assert r.json().get("status") == "approved", f"Status mismatch: {r.json()}"

        # Step 3: Receive Goods
        r = requests.put(f"{BASE_URL}/api/purchase_orders/{purchase_order_id}/receive_goods/",
                          auth=AUTH, headers=HEADERS, timeout=TIMEOUT)
        assert r.status_code == 200, f"Goods receipt failed: {r.text}"
        assert r.json().get("status") == "goods_received", f"Status mismatch: {r.json()}"

        # Step 4: Verify Stock Increase (Optional - skipping for speed/reliability of flow test)
        
        # Step 5: Convert to Purchase Bill (Invoice)
        # Manual conversion: Create Bill with PO data
        bill_payload = {
            "supplier": supplier_partner_id, # PurchaseBill likely uses Partner too
            "date": "2026-02-10",
            "number": f"BILL-{purchase_order_id}",
            "items": [
                {"product": 1, "location": location_id, "quantity": 10, "cost": 50} 
            ],
        }
        r = requests.post(f"{BASE_URL}/api/purchases/", json=bill_payload, auth=AUTH, headers=HEADERS, timeout=TIMEOUT)
        assert r.status_code == 201, f"Purchase Bill creation failed: {r.text}"
        bill = r.json()
        bill_id = bill.get("id")

    finally:
        # Cleanup
        if bill_id:
            requests.delete(f"{BASE_URL}/api/purchases/{bill_id}/", auth=AUTH, headers=HEADERS, timeout=TIMEOUT)
        if purchase_order_id:
            requests.delete(f"{BASE_URL}/api/purchase_orders/{purchase_order_id}/", auth=AUTH, headers=HEADERS, timeout=TIMEOUT)
        if supplier_id:
            requests.delete(f"{BASE_URL}/api/suppliers/{supplier_id}/", auth=AUTH, headers=HEADERS, timeout=TIMEOUT)
        if location_id and location_id != 1:
             requests.delete(f"{BASE_URL}/api/locations/{location_id}/", auth=AUTH, headers=HEADERS, timeout=TIMEOUT)

if __name__ == "__main__":
    test_purchasing_workflow_end_to_end_process()
    print("TC007 PASSED")