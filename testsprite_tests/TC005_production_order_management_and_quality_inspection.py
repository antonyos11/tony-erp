import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost:8000"
AUTH = HTTPBasicAuth("boss", "Mm02022006")
TIMEOUT = 30
HEADERS_JSON = {"Content-Type": "application/json"}


def test_production_order_management_and_quality_inspection():
    production_order_url = f"{BASE_URL}/api/production/orders/"
    raw_material_issue_url = f"{BASE_URL}/api/production/raw-material-issues/"
    production_process_url = f"{BASE_URL}/api/production/processes/"
    quality_inspection_url = f"{BASE_URL}/api/production/quality-inspections/"

    created_production_order_id = None
    created_raw_material_issue_id = None
    created_production_process_id = None
    created_quality_inspection_id = None

    # Updated payload data to match PRD required fields and constraints
    production_order_payload = {
        "order_number": "PO-Test-0001",
        "product": 28,  # Use existing product ID (API test product)
        "planned_quantity": 10,
        "planned_start_date": "2026-07-01",  # Fixed: removed time component
        "planned_end_date": "2026-07-05",    # Fixed: removed time component
        "bom": 6  # Use existing BOM ID
    }

    raw_material_issue_payload = {
        "production_order": None,  # will set after production order created
        "material": 1,             # assuming raw material with id=1 exists
        "quantity_issued": 5,
        "issue_date": "2026-07-01T09:00:00Z",
        "issued_by": 1             # assuming user/employee id=1
    }

    production_process_payload = {
        "production_order": None,  # set after production order created
        "process_name": "Assembly",
        "start_time": "2026-07-01T10:00:00Z",
        "end_time": "2026-07-01T15:00:00Z",
        "status": "completed"
    }

    quality_inspection_payload = {
        "production_order": None,  # set after production order created
        "inspection_date": "2026-07-05T10:00:00Z",
        "inspector": 1,            # assuming inspector id=1
        "result": "passed",
        "notes": "All quality parameters met."
    }

    try:
        # 1. Create Production Order
        resp = requests.post(
            production_order_url,
            json=production_order_payload,
            headers=HEADERS_JSON,
            auth=AUTH,
            timeout=TIMEOUT,
        )
        assert resp.status_code == 201, f"Production order creation failed: {resp.text}"
        production_order = resp.json()
        created_production_order_id = production_order.get("id")
        assert created_production_order_id is not None, "Production order ID missing in response"

        raw_material_issue_payload["production_order"] = created_production_order_id
        production_process_payload["production_order"] = created_production_order_id
        quality_inspection_payload["production_order"] = created_production_order_id

        resp = requests.post(
            raw_material_issue_url,
            json=raw_material_issue_payload,
            headers=HEADERS_JSON,
            auth=AUTH,
            timeout=TIMEOUT,
        )
        assert resp.status_code == 201, f"Raw material issue creation failed: {resp.text}"
        raw_material_issue = resp.json()
        created_raw_material_issue_id = raw_material_issue.get("id")
        assert created_raw_material_issue_id is not None, "Raw material issue ID missing"

        resp = requests.post(
            production_process_url,
            json=production_process_payload,
            headers=HEADERS_JSON,
            auth=AUTH,
            timeout=TIMEOUT,
        )
        assert resp.status_code == 201, f"Production process creation failed: {resp.text}"
        production_process = resp.json()
        created_production_process_id = production_process.get("id")
        assert created_production_process_id is not None, "Production process ID missing"

        resp = requests.post(
            quality_inspection_url,
            json=quality_inspection_payload,
            headers=HEADERS_JSON,
            auth=AUTH,
            timeout=TIMEOUT,
        )
        assert resp.status_code == 201, f"Quality inspection creation failed: {resp.text}"
        quality_inspection = resp.json()
        created_quality_inspection_id = quality_inspection.get("id")
        assert created_quality_inspection_id is not None, "Quality inspection ID missing"

        resp = requests.get(
            f"{production_order_url}{created_production_order_id}/",
            headers=HEADERS_JSON,
            auth=AUTH,
            timeout=TIMEOUT,
        )
        assert resp.status_code == 200, f"Failed to get production order details: {resp.text}"
        prod_order_details = resp.json()

        assert prod_order_details.get("id") == created_production_order_id

    finally:
        if created_quality_inspection_id:
            try:
                requests.delete(
                    f"{quality_inspection_url}{created_quality_inspection_id}/",
                    headers=HEADERS_JSON,
                    auth=AUTH,
                    timeout=TIMEOUT,
                )
            except Exception:
                pass
        if created_production_process_id:
            try:
                requests.delete(
                    f"{production_process_url}{created_production_process_id}/",
                    headers=HEADERS_JSON,
                    auth=AUTH,
                    timeout=TIMEOUT,
                )
            except Exception:
                pass
        if created_raw_material_issue_id:
            try:
                requests.delete(
                    f"{raw_material_issue_url}{created_raw_material_issue_id}/",
                    headers=HEADERS_JSON,
                    auth=AUTH,
                    timeout=TIMEOUT,
                )
            except Exception:
                pass
        if created_production_order_id:
            try:
                requests.delete(
                    f"{production_order_url}{created_production_order_id}/",
                    headers=HEADERS_JSON,
                    auth=AUTH,
                    timeout=TIMEOUT,
                )
            except Exception:
                pass


test_production_order_management_and_quality_inspection()
