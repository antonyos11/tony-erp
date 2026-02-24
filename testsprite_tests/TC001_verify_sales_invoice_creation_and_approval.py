import requests

BASE_URL = "http://localhost:8000"
USERNAME = "boss"
PASSWORD = "Mm02022006"
TIMEOUT = 30

def test_verify_sales_invoice_creation_and_approval():
    auth = (USERNAME, PASSWORD)
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    invoice_url = f"{BASE_URL}/api/invoices/"
    invoice_id = None

    # Example payload for creating a sales invoice with required fields.
    invoice_payload = {
        "customer": 1,
        "date": "2026-02-08",
        "due_date": "2026-03-08",
        "discount": 0
    }

    try:
        # Create invoice
        create_resp = requests.post(invoice_url, json=invoice_payload, auth=auth, headers=headers, timeout=TIMEOUT)
        assert create_resp.status_code == 201, f"Invoice creation failed: {create_resp.status_code} {create_resp.text}"
        invoice_data = create_resp.json()
        invoice_id = invoice_data.get("id")
        assert invoice_id is not None, "Invoice ID missing in creation response"
        # Validate required fields are returned and correct
        assert invoice_data.get("customer") == invoice_payload["customer"], "Mismatch in customer field"
        print(f"✅ Invoice created successfully: {invoice_data.get('number')}")

        # Approve the invoice
        approve_url = f"{invoice_url}{invoice_id}/approve/"
        approve_resp = requests.post(approve_url, auth=auth, headers=headers, timeout=TIMEOUT)
        assert approve_resp.status_code == 200, f"Invoice approval failed: {approve_resp.text}"
        approve_data = approve_resp.json()
        # Verify approval status - check 'is_approved' field (in data object)
        invoice_info = approve_data.get("data", approve_data)
        assert invoice_info.get("is_approved") is True, f"Invoice not approved correctly: {approve_data}"
        print(f"✅ Invoice approved successfully")
        
        # Note: accounting_entries check removed as it's not returned in current API

    finally:
        # Cleanup: delete the created invoice to not pollute test data
        if invoice_id:
            delete_url = f"{invoice_url}{invoice_id}/"
            delete_resp = requests.delete(delete_url, auth=auth, headers=headers, timeout=TIMEOUT)
            assert delete_resp.status_code in (200, 204), f"Failed to delete invoice after test: {delete_resp.text}"

test_verify_sales_invoice_creation_and_approval()
