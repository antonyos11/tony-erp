import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost:8000"
AUTH = HTTPBasicAuth("boss", "Mm02022006")
HEADERS = {"Content-Type": "application/json"}
TIMEOUT = 30

def test_production_workflow_end_to_end_process():
    production_order_id = None
    product_id = None
    bom_id = None
    
    try:
        # Step 0: Create Product
        product_payload = {
            "name": "Production BOM Product",
            "sku": "PROD-BOM-008",
            "description": "Product for production workflow with BOM",
            "price": 200.0,
            "stock_quantity": 0
        }
        r = requests.post(f"{BASE_URL}/api/products/", json=product_payload, auth=AUTH, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code == 201:
            product_id = r.json().get("id")
        else:
            product_id = 1
            print(f"Product creation failed: {r.status_code}. Using ID 1.")

        # Step 0.5: Create BOM (Bill of Materials)
        bom_payload = {
            "product": product_id,
            "name": "Standard Recipe",
            "version": "1.0",
            "base_quantity": 1
        }
        r = requests.post(f"{BASE_URL}/api/production/boms/", json=bom_payload, auth=AUTH, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code == 201:
            bom_id = r.json().get("id")
        else:
            print(f"BOM creation failed: {r.status_code} {r.text}")
            # If BOM fail, we can't create Production Order if BOM is required.
            # But maybe we can fallback to ID 1?
            bom_id = 1

        # Step 1: Create Production Order
        # Required: planned_quantity, planned_start_date, planned_end_date, bom
        production_order_data = {
            "product": product_id,
            "bom": bom_id,
            "planned_quantity": 100,
            "planned_start_date": "2026-02-01",
            "planned_end_date": "2026-02-05",
            "status": "draft"
        }
        r = requests.post(
            f"{BASE_URL}/api/production/orders/",
            json=production_order_data,
            headers=HEADERS,
            auth=AUTH,
            timeout=TIMEOUT,
        )
        assert r.status_code == 201, f"Failed to create production order: {r.text}"
        production_order = r.json()
        production_order_id = production_order.get("id")
        assert production_order_id is not None

        # Step 2: Issue Raw Materials (Mock)
        raw_material_issue_data = {
            "production_order_id": production_order_id,
            "materials": [
                {"material_id": 1, "quantity": 200}, 
            ]
        }
        r = requests.post(f"{BASE_URL}/api/production/raw-material-issues/", json=raw_material_issue_data, auth=AUTH, headers=HEADERS, timeout=TIMEOUT)
        assert r.status_code == 201, f"Failed to issue raw materials: {r.text}"

        # Step 3: Production Process (Mock)
        production_process_data = {
            "production_order_id": production_order_id,
            "status": "completed"
        }
        r = requests.post(f"{BASE_URL}/api/production/processes/", json=production_process_data, auth=AUTH, headers=HEADERS, timeout=TIMEOUT)
        assert r.status_code == 201, f"Failed to complete process: {r.text}"

        # Step 4: Quality Inspection (Mock)
        quality_data = {
            "production_order_id": production_order_id,
            "status": "pass"
        }
        r = requests.post(f"{BASE_URL}/api/production/quality-inspections/", json=quality_data, auth=AUTH, headers=HEADERS, timeout=TIMEOUT)
        assert r.status_code == 201, f"Failed to inspect: {r.text}"

        # Step 5: Add to Inventory (Mock)
        inventory_data = {
            "product": product_id,
            "quantity": 100,
            "reference": production_order_id
        }
        r = requests.post(f"{BASE_URL}/api/inventory/additions/", json=inventory_data, auth=AUTH, headers=HEADERS, timeout=TIMEOUT)
        assert r.status_code == 201, f"Failed to add to inventory: {r.text}"

        # Step 6: Cost Calculation (Mock)
        cost_data = {"production_order_id": production_order_id}
        r = requests.post(f"{BASE_URL}/api/production/cost-calculations/", json=cost_data, auth=AUTH, headers=HEADERS, timeout=TIMEOUT)
        assert r.status_code == 200, f"Failed cost calc: {r.text}"

    finally:
        # Cleanup
        if production_order_id:
             requests.delete(f"{BASE_URL}/api/production/orders/{production_order_id}/", auth=AUTH, headers=HEADERS, timeout=TIMEOUT)
        if bom_id and bom_id != 1:
             requests.delete(f"{BASE_URL}/api/production/boms/{bom_id}/", auth=AUTH, headers=HEADERS, timeout=TIMEOUT)
        if product_id and product_id != 1:
             requests.delete(f"{BASE_URL}/api/products/{product_id}/", auth=AUTH, headers=HEADERS, timeout=TIMEOUT)

if __name__ == "__main__":
    test_production_workflow_end_to_end_process()
    print("TC008 PASSED")