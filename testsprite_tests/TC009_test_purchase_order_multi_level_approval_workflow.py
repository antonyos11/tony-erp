import requests
import time

BASE_URL = "http://localhost:8000"
AUTH_URL = f"{BASE_URL}/api/token/"
PURCHASE_ORDER_API = f"{BASE_URL}/purchases/api/purchase_orders/"
APPROVALS_API = f"{BASE_URL}/approvals/api/purchase_order_approvals/"
INVOICE_API = f"{BASE_URL}/purchases/api/purchase_invoices/"
TIMEOUT = 30

USERNAME = "boss"
PASSWORD = "Mm02022006"


def get_jwt_token():
    try:
        resp = requests.post(
            AUTH_URL,
            json={"username": USERNAME, "password": PASSWORD},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        tokens = resp.json()
        return tokens.get("access")
    except Exception as e:
        raise RuntimeError(f"Failed to get JWT token: {e}")


def create_purchase_order(headers):
    # Minimal required fields for purchase order creation based on typical data:
    # Assuming fields: supplier (id), order_date, items (list), total_amount
    # Since supplier record may be needed, will create with placeholder ids and data
    po_payload = {
        "supplier": 1,  # Assuming supplier with ID=1 exists; else test will fail
        "order_date": "2026-02-12",
        "due_date": "2026-02-19",
        "items": [
            {
                "product": 1,  # Assuming product with ID=1 exists; else test will fail
                "quantity": 5,
                "unit_price": 100.0,
                "tax": 15.0,
                "discount": 0.0,
            }
        ],
        "notes": "Test purchase order for multi-level approval workflow",
    }

    try:
        resp = requests.post(PURCHASE_ORDER_API, json=po_payload, headers=headers, timeout=TIMEOUT)
        resp.raise_for_status()
        po = resp.json()
        assert "id" in po, "Purchase order creation response missing 'id'"
        return po["id"], po
    except Exception as e:
        raise RuntimeError(f"Failed to create purchase order: {e}")


def get_purchase_order(headers, po_id):
    url = f"{PURCHASE_ORDER_API}{po_id}/"
    resp = requests.get(url, headers=headers, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def delete_purchase_order(headers, po_id):
    url = f"{PURCHASE_ORDER_API}{po_id}/"
    try:
        resp = requests.delete(url, headers=headers, timeout=TIMEOUT)
        if resp.status_code not in (204, 200, 202, 404):
            raise RuntimeError(f"Unexpected delete status code: {resp.status_code}")
    except Exception as e:
        # Log but don't raise to allow cleanup continuation
        print(f"Warning: Failed to delete purchase order {po_id}: {e}")


def approve_purchase_order(headers, po_id, level):
    # Assuming the approval endpoint requires purchase_order id and approval level, plus approval action
    # Hypothetical URL and payload for approval based on multi-level approval
    # Approvals URL example: /approvals/api/purchase_order_approvals/
    # POST with data: {"purchase_order": po_id, "level": level, "action": "approve", "comments": "..."}
    payload = {
        "purchase_order": po_id,
        "level": level,
        "action": "approve",
        "comments": f"Approval at level {level}",
    }
    try:
        resp = requests.post(APPROVALS_API, json=payload, headers=headers, timeout=TIMEOUT)
        resp.raise_for_status()
        approval_resp = resp.json()
        assert approval_resp.get("status") in ("approved", "pending", "rejected", None), "Unexpected approval status"
        return approval_resp
    except Exception as e:
        raise RuntimeError(f"Failed to approve purchase order at level {level}: {e}")


def get_purchase_invoice(headers, purchase_order_id):
    # We get invoices filtered by purchase_order, assuming this endpoint supports filtering with query params
    params = {"purchase_order": purchase_order_id}
    try:
        resp = requests.get(INVOICE_API, headers=headers, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        invoices = resp.json()
        return invoices
    except Exception as e:
        raise RuntimeError(f"Failed to get invoices for purchase order {purchase_order_id}: {e}")


def convert_po_to_invoice(headers, po_id):
    # Assuming endpoint to convert PO to invoice is:
    # POST /purchases/api/purchase_orders/{id}/convert_to_invoice/
    url = f"{PURCHASE_ORDER_API}{po_id}/convert_to_invoice/"
    try:
        resp = requests.post(url, headers=headers, timeout=TIMEOUT)
        resp.raise_for_status()
        invoice = resp.json()
        assert "id" in invoice, "Invoice creation response missing 'id'"
        return invoice
    except Exception as e:
        raise RuntimeError(f"Failed to convert purchase order {po_id} to invoice: {e}")


def test_purchase_order_multi_level_approval_workflow():
    token = get_jwt_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    po_id = None
    try:
        # Step 1: Create purchase order
        po_id, po_data = create_purchase_order(headers)
        assert po_data["supplier"] == 1
        assert po_data["items"][0]["quantity"] == 5

        # Step 2: Initial status should be 'pending' or equivalent
        current_po = get_purchase_order(headers, po_id)
        assert current_po.get("status") in ("pending", "draft", "awaiting_approval"), f"Unexpected initial status: {current_po.get('status')}"

        # Step 3: Process multi-level approvals
        # Assume multi-level approval 2 levels for the test
        approval_resp_1 = approve_purchase_order(headers, po_id, level=1)
        # After first approval, status often goes to second level or pending second approval
        po_after_1 = get_purchase_order(headers, po_id)
        assert po_after_1.get("status") in ("pending_approval_level_2", "awaiting_approval", "approved", "partially_approved"), \
            f"Unexpected status after level 1 approval: {po_after_1.get('status')}"

        approval_resp_2 = approve_purchase_order(headers, po_id, level=2)
        po_after_2 = get_purchase_order(headers, po_id)
        # After final approval, status should be 'approved' or equivalent
        assert po_after_2.get("status") in ("approved", "fully_approved"), f"Unexpected status after level 2 approval: {po_after_2.get('status')}"

        # Step 4: Convert approved purchase order to purchase invoice
        invoice = convert_po_to_invoice(headers, po_id)
        assert invoice["purchase_order"] == po_id
        assert invoice.get("status") in ("draft", "posted", "completed", None)

        # Step 5: Retrieve and verify invoice linked to PO
        invoices = get_purchase_invoice(headers, po_id)
        # invoices may be a list/dict, accept both
        invoice_list = []
        if isinstance(invoices, dict):
            # If dict with results
            invoice_list = invoices.get("results", [])
        elif isinstance(invoices, list):
            invoice_list = invoices
        assert any(inv.get("id") == invoice["id"] for inv in invoice_list), "Invoice linked to PO not found in list"

    finally:
        if po_id:
            delete_purchase_order(headers, po_id)


test_purchase_order_multi_level_approval_workflow()