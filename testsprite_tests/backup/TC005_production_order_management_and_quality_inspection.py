import requests
from requests.auth import HTTPBasicAuth

base_url = "http://localhost:8000/api/"
timeout = 30
auth = HTTPBasicAuth("boss", "Mm02022006")

def test_production_order_management_and_quality_inspection():
    headers = {"Content-Type": "application/json"}

    # Added 'product' field as typically required for production orders
    production_order_payload = {
        "name": "Test Production Order",
        "description": "Test production order creation",
        "status": "pending",
        "product": 1  # Placeholder product ID, needs to exist in system
    }

    raw_material_issue_payload = {
        "material": "Test Raw Material",
        "quantity": 10,
        "production_order": None  # Will assign after production order creation
    }

    production_process_payload = {
        "production_order": None,  # Will assign after production order creation
        "process_name": "Test Process",
        "status": "in_progress"
    }

    quality_inspection_payload = {
        "production_order": None,  # Will assign after production order creation
        "inspection_result": "passed",
        "remarks": "Quality inspection passed"
    }

    # Helper to delete resource by URL
    def delete_resource(url):
        try:
            resp = requests.delete(url, auth=auth, timeout=timeout)
            assert resp.status_code in (200, 204, 202)
        except Exception:
            pass

    production_order_url = f"{base_url}production/orders/"
    raw_material_issue_url = f"{base_url}production/raw-material-issues/"
    production_process_url = f"{base_url}production/processes/"
    quality_inspection_url = f"{base_url}production/quality-inspections/"

    production_order_id = None
    raw_material_issue_id = None
    production_process_id = None
    quality_inspection_id = None

    # Create production order
    try:
        resp = requests.post(production_order_url, json=production_order_payload, headers=headers, auth=auth, timeout=timeout)
        assert resp.status_code == 201, f"Failed to create production order: {getattr(resp, 'text', str(resp))}"
        prod_order = resp.json()
        production_order_id = prod_order.get("id")
        assert production_order_id is not None
        raw_material_issue_payload["production_order"] = production_order_id
        production_process_payload["production_order"] = production_order_id
        quality_inspection_payload["production_order"] = production_order_id

        # Create raw material issue
        resp = requests.post(raw_material_issue_url, json=raw_material_issue_payload, headers=headers, auth=auth, timeout=timeout)
        assert resp.status_code == 201, f"Failed to create raw material issue: {getattr(resp, 'text', str(resp))}"
        raw_material_issue = resp.json()
        raw_material_issue_id = raw_material_issue.get("id")
        assert raw_material_issue_id is not None

        # Validate raw material issue linked to production order
        assert raw_material_issue.get("production_order") == production_order_id

        # Create production process
        resp = requests.post(production_process_url, json=production_process_payload, headers=headers, auth=auth, timeout=timeout)
        assert resp.status_code == 201, f"Failed to create production process: {getattr(resp, 'text', str(resp))}"
        production_process = resp.json()
        production_process_id = production_process.get("id")
        assert production_process_id is not None

        # Validate production process linked to production order
        assert production_process.get("production_order") == production_order_id

        # Create quality inspection
        resp = requests.post(quality_inspection_url, json=quality_inspection_payload, headers=headers, auth=auth, timeout=timeout)
        assert resp.status_code == 201, f"Failed to create quality inspection: {getattr(resp, 'text', str(resp))}"
        quality_inspection = resp.json()
        quality_inspection_id = quality_inspection.get("id")
        assert quality_inspection_id is not None

        # Validate quality inspection linked to production order
        assert quality_inspection.get("production_order") == production_order_id

        # Retrieve production order to check consistency and inventory consumption simulation
        resp = requests.get(f"{production_order_url}{production_order_id}/", auth=auth, timeout=timeout)
        assert resp.status_code == 200, f"Failed to retrieve production order details: {getattr(resp, 'text', str(resp))}"
        order_details = resp.json()
        assert order_details.get("id") == production_order_id

        # Retrieve raw material issues linked to production order
        resp = requests.get(raw_material_issue_url, params={"production_order": production_order_id}, auth=auth, timeout=timeout)
        assert resp.status_code == 200
        issues_list = resp.json()
        assert any(issue.get("id") == raw_material_issue_id for issue in issues_list)

        # Retrieve production processes linked to production order
        resp = requests.get(production_process_url, params={"production_order": production_order_id}, auth=auth, timeout=timeout)
        assert resp.status_code == 200
        processes_list = resp.json()
        assert any(proc.get("id") == production_process_id for proc in processes_list)

        # Retrieve quality inspections linked to production order
        resp = requests.get(quality_inspection_url, params={"production_order": production_order_id}, auth=auth, timeout=timeout)
        assert resp.status_code == 200
        inspections_list = resp.json()
        assert any(insp.get("id") == quality_inspection_id for insp in inspections_list)

    finally:
        # Cleanup created resources
        if quality_inspection_id is not None:
            delete_resource(f"{quality_inspection_url}{quality_inspection_id}/")
        if production_process_id is not None:
            delete_resource(f"{production_process_url}{production_process_id}/")
        if raw_material_issue_id is not None:
            delete_resource(f"{raw_material_issue_url}{raw_material_issue_id}/")
        if production_order_id is not None:
            delete_resource(f"{production_order_url}{production_order_id}/")

test_production_order_management_and_quality_inspection()
