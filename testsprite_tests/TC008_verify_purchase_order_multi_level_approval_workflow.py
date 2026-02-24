import requests
import time

BASE_URL = "http://127.0.0.1:8000"
AUTH_URL = f"{BASE_URL}/api/token/"
PURCHASE_ORDERS_URL = f"{BASE_URL}/api/purchase_orders/"
PURCHASE_INVOICES_URL = f"{BASE_URL}/api/purchase_invoices/"

USERNAME = "boss"
PASSWORD = "Mm02022006"
TIMEOUT = 30


def authenticate():
    resp = requests.post(
        AUTH_URL,
        json={"username": USERNAME, "password": PASSWORD},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    token = resp.json().get("access")
    assert token, "Authentication failed, no access token received."
    return token


def test_purchase_order_multi_level_approval_workflow():
    token = authenticate()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    purchase_order_data = {
        "supplier": 1,  # Assuming supplier with ID 1 exists
        "order_date": "2026-02-12",
        "expected_delivery": "2026-02-19",
        "items": [
            {
                "product": 1,  # Assuming product with ID 1 exists
                "quantity": 10,
                "unit_price": 100.00
            }
        ],
        "notes": "Test purchase order for multi-level approval workflow.",
        "status": "draft"  # initial status (assuming)
    }

    po_id = None
    try:
        # Step 1: Create purchase order (draft)
        create_resp = requests.post(
            PURCHASE_ORDERS_URL,
            json=purchase_order_data,
            headers=headers,
            timeout=TIMEOUT,
        )
        create_resp.raise_for_status()
        po = create_resp.json()
        po_id = po.get("id")
        assert po_id, "Created purchase order has no ID."
        assert po.get("status") == "draft" or po.get("status") == "pending", "PO initial status is not draft or pending."

        # Step 2: Submit PO for first-level approval (assumed endpoint PATCH to update status)
        approval_level_1_status = "approval_1_pending"
        update_resp_1 = requests.patch(
            f"{PURCHASE_ORDERS_URL}{po_id}/",
            json={"status": approval_level_1_status},
            headers=headers,
            timeout=TIMEOUT,
        )
        update_resp_1.raise_for_status()
        po_updated_1 = update_resp_1.json()
        assert po_updated_1.get("status") == approval_level_1_status, "PO status not updated to first-level approval pending."

        # Simulate first-level approval by patching status to second level approval pending
        approval_level_2_status = "approval_2_pending"
        update_resp_2 = requests.patch(
            f"{PURCHASE_ORDERS_URL}{po_id}/",
            json={"status": approval_level_2_status},
            headers=headers,
            timeout=TIMEOUT,
        )
        update_resp_2.raise_for_status()
        po_updated_2 = update_resp_2.json()
        assert po_updated_2.get("status") == approval_level_2_status, "PO status not updated to second-level approval pending."

        # Simulate final approval by patching status to approved
        approved_status = "approved"
        update_resp_final = requests.patch(
            f"{PURCHASE_ORDERS_URL}{po_id}/",
            json={"status": approved_status},
            headers=headers,
            timeout=TIMEOUT,
        )
        update_resp_final.raise_for_status()
        po_final = update_resp_final.json()
        assert po_final.get("status") == approved_status, "PO status not updated to approved."

        # Step 3: Convert approved PO to Purchase Invoice
        convert_invoice_resp = requests.post(
            f"{PURCHASE_INVOICES_URL}",
            json={
                "purchase_order": po_id,
                "invoice_date": "2026-02-13",
                "notes": "Invoice generated from approved PO",
                "items": purchase_order_data["items"],
            },
            headers=headers,
            timeout=TIMEOUT,
        )
        convert_invoice_resp.raise_for_status()
        invoice = convert_invoice_resp.json()
        invoice_id = invoice.get("id")
        assert invoice_id, "Invoice creation failed, no ID returned."
        assert invoice.get("purchase_order") == po_id, "Invoice does not link to original PO."
        assert invoice.get("status") == "draft" or invoice.get("status") == "pending", "Invoice initial status unexpected."

        # Optionally approve or post invoice if workflow requires (not specified in docs)
        # This step can be extended if needed.

    finally:
        # Cleanup: delete created invoice and PO to keep environment clean
        if 'invoice_id' in locals():
            try:
                resp_invoice_del = requests.delete(
                    f"{PURCHASE_INVOICES_URL}{invoice_id}/",
                    headers=headers,
                    timeout=TIMEOUT,
                )
                if resp_invoice_del.status_code not in (204, 200):
                    print(f"Warning: Failed to delete purchase invoice {invoice_id}")
            except Exception:
                pass
        if po_id:
            try:
                resp_po_del = requests.delete(
                    f"{PURCHASE_ORDERS_URL}{po_id}/",
                    headers=headers,
                    timeout=TIMEOUT,
                )
                if resp_po_del.status_code not in (204, 200):
                    print(f"Warning: Failed to delete purchase order {po_id}")
            except Exception:
                pass


test_purchase_order_multi_level_approval_workflow()
