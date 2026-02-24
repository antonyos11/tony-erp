import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost:8000"
TIMEOUT = 30
AUTH = HTTPBasicAuth("boss", "Mm02022006")
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
}


def test_verify_sales_invoice_creation_and_approval():
    invoice_id = None
    try:
        # Step 1: Create a sales invoice at /api/invoices/
        create_url = f"{BASE_URL}/api/invoices/"
        invoice_payload = {
            # Minimal required fields based on typical invoice schema:
            # Since no specific fields are given, use plausible example fields:
            "customer_name": "Test Customer",
            "invoice_date": "2026-02-06",
            "due_date": "2026-03-06",
            "items": [
                {
                    "description": "Product A",
                    "quantity": 2,
                    "unit_price": 50.0,
                    "tax_rate": 0.15
                }
            ],
            "currency": "SAR",
            "notes": "Test invoice creation"
        }

        response = requests.post(create_url, json=invoice_payload, headers=HEADERS, auth=AUTH, timeout=TIMEOUT)
        assert response.status_code == 201, f"Invoice creation failed with status {response.status_code} and body {response.text}"
        invoice_data = response.json()
        invoice_id = invoice_data.get("id")
        assert invoice_id is not None, "Invoice ID is missing in creation response"

        # Validate required fields present in response
        assert invoice_data.get("customer_name") == invoice_payload["customer_name"]
        assert invoice_data.get("items") and isinstance(invoice_data["items"], list)
        assert invoice_data.get("status") in ["draft", "pending", "created", "unapproved"], "Unexpected initial invoice status"

        # Step 2: Approve the invoice at /api/invoices/{id}/approve/
        approve_url = f"{BASE_URL}/api/invoices/{invoice_id}/approve/"
        approve_response = requests.post(approve_url, headers=HEADERS, auth=AUTH, timeout=TIMEOUT)
        assert approve_response.status_code == 200, f"Invoice approval failed with status {approve_response.status_code} and body {approve_response.text}"
        approve_data = approve_response.json()

        # Validate approved status and linked accounting entries posted
        assert approve_data.get("id") == invoice_id
        assert approve_data.get("status") == "approved", f"Invoice status after approval is {approve_data.get('status')}, expected 'approved'"
        assert "accounting_entries_posted" in approve_data and approve_data["accounting_entries_posted"] is True, "Accounting entries not posted after approval"

    finally:
        # Cleanup: Delete the created invoice if it was created
        if invoice_id:
            delete_url = f"{BASE_URL}/api/invoices/{invoice_id}/"
            try:
                requests.delete(delete_url, headers=HEADERS, auth=AUTH, timeout=TIMEOUT)
            except Exception:
                pass  # ignore cleanup exceptions


test_verify_sales_invoice_creation_and_approval()
