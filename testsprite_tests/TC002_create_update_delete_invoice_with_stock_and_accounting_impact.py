import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost:8000"
AUTH = HTTPBasicAuth("boss", "Mm02022006")
TIMEOUT = 30
HEADERS = {"Content-Type": "application/json"}

def test_create_update_delete_invoice_with_stock_and_accounting_impact():
    invoice_id = None
    product_id = None
    customer_id = None
    location_id = None
    initial_stock_qty = None
    try:
        # Step 0: Get existing customer id
        customers_resp = requests.get(
            f"{BASE_URL}/api/customers/",
            headers=HEADERS,
            auth=AUTH,
            timeout=TIMEOUT
        )
        assert customers_resp.status_code == 200, f"Failed to get customers: {customers_resp.text}"
        customers = customers_resp.json()
        if isinstance(customers, list) and len(customers) > 0:
            customer_id = customers[0].get("id")
        else:
            # Create a customer if none exist
            customer_payload = {
                "name": "Fallback Customer TC002",
                "phone": "01234567890",
                "email": "fallback.customer@example.com"
            }
            create_cust_resp = requests.post(f"{BASE_URL}/api/customers/", json=customer_payload, headers=HEADERS, auth=AUTH)
            if create_cust_resp.status_code == 201:
                customer_id = create_cust_resp.json().get("id")
            else:
                raise AssertionError(f"Failed to create customer: {create_cust_resp.text}")
        
        assert customer_id is not None

        # Step 0b: Get existing location id
        locations_resp = requests.get(
            f"{BASE_URL}/api/locations/",
            headers=HEADERS,
            auth=AUTH,
            timeout=TIMEOUT
        )
        assert locations_resp.status_code == 200, f"Failed to get locations: {locations_resp.text}"
        locations = locations_resp.json()
        assert isinstance(locations, list) and len(locations) > 0, "No locations available for invoice creation"
        location_id = locations[0].get("id")
        assert location_id is not None

        # Step 1: Create a product to impact stock
        product_payload = {
            "name": "Test Product TC002",
            "sku": "TC002SKU001",
            "price": 100.0,
            "stock": 50  # initial stock quantity
        }
        product_resp = requests.post(
            f"{BASE_URL}/api/products/",
            json=product_payload,
            headers=HEADERS,
            auth=AUTH,
            timeout=TIMEOUT
        )
        assert product_resp.status_code == 201, f"Failed to create product: {product_resp.text}"
        product_data = product_resp.json()
        product_id = product_data.get("id")
        assert product_id is not None

        # Record initial stock level
        initial_stock_qty = product_data.get("stock", 0)

        # Step 2: Create an invoice with the product and quantity that impacts stock
        invoice_payload = {
            "customer": customer_id,
            "invoice_date": "2026-01-21",
            "items": [
                {
                    "product": product_id,
                    "quantity": 5,
                    "price": 100.0,
                    "location": location_id
                }
            ]
        }
        create_inv_resp = requests.post(
            f"{BASE_URL}/api/invoices/",
            json=invoice_payload,
            headers=HEADERS,
            auth=AUTH,
            timeout=TIMEOUT
        )
        assert create_inv_resp.status_code == 201, f"Failed to create invoice: {create_inv_resp.text}"
        invoice_data = create_inv_resp.json()
        invoice_id = invoice_data.get("id")
        assert invoice_id is not None

        # Step 3: Verify stock level deduction after invoice creation
        product_get_resp = requests.get(
            f"{BASE_URL}/api/products/{product_id}/",
            headers=HEADERS,
            auth=AUTH,
            timeout=TIMEOUT
        )
        assert product_get_resp.status_code == 200
        product_after_invoice = product_get_resp.json()
        expected_stock_after_invoice = initial_stock_qty - 5
        actual_stock_after_invoice = product_after_invoice.get("stock")
        assert actual_stock_after_invoice == expected_stock_after_invoice, \
            f"Stock level not reduced properly after invoice creation. Expected {expected_stock_after_invoice}, got {actual_stock_after_invoice}"

        # Step 4: Verify accounting entries created for the invoice
        accounting_resp = requests.get(
            f"{BASE_URL}/api/accounting/entries/",
            params={"invoice_id": invoice_id},
            headers=HEADERS,
            auth=AUTH,
            timeout=TIMEOUT
        )
        assert accounting_resp.status_code == 200
        entries = accounting_resp.json()
        assert isinstance(entries, list) and len(entries) > 0, "No accounting entries found for invoice"

        # Step 5: Update the invoice - change quantity of the same product
        update_payload = {
            "customer": customer_id,
            "items": [
                {
                    "product": product_id,
                    "quantity": 3,
                    "price": 100.0,
                    "location": location_id
                }
            ]
        }
        update_resp = requests.put(
            f"{BASE_URL}/api/invoices/{invoice_id}/",
            json=update_payload,
            headers=HEADERS,
            auth=AUTH,
            timeout=TIMEOUT
        )
        assert update_resp.status_code == 200, f"Failed to update invoice: {update_resp.text}"

        # Step 6: Verify stock level adjusted correctly for update
        product_get_resp_after_update = requests.get(
            f"{BASE_URL}/api/products/{product_id}/",
            headers=HEADERS,
            auth=AUTH,
            timeout=TIMEOUT
        )
        assert product_get_resp_after_update.status_code == 200
        product_after_update = product_get_resp_after_update.json()
        # Stock after update: initial stock - new quantity (3)
        expected_stock_after_update = initial_stock_qty - 3
        actual_stock_after_update = product_after_update.get("stock")
        assert actual_stock_after_update == expected_stock_after_update, \
            f"Stock level not updated properly after invoice update. Expected {expected_stock_after_update}, got {actual_stock_after_update}"

        # Step 7: Verify accounting entries updated for the invoice after change
        accounting_resp_updated = requests.get(
            f"{BASE_URL}/api/accounting/entries/",
            params={"invoice_id": invoice_id},
            headers=HEADERS,
            auth=AUTH,
            timeout=TIMEOUT
        )
        assert accounting_resp_updated.status_code == 200
        updated_entries = accounting_resp_updated.json()
        assert isinstance(updated_entries, list) and len(updated_entries) > 0, "No accounting entries found after invoice update"

        # Step 8: Delete the invoice
        delete_resp = requests.delete(
            f"{BASE_URL}/api/invoices/{invoice_id}/",
            headers=HEADERS,
            auth=AUTH,
            timeout=TIMEOUT
        )
        assert delete_resp.status_code in [200, 204], f"Failed to delete invoice: {delete_resp.text}"

        # Step 9: Verify stock reverted after invoice deletion
        product_get_resp_after_delete = requests.get(
            f"{BASE_URL}/api/products/{product_id}/",
            headers=HEADERS,
            auth=AUTH,
            timeout=TIMEOUT
        )
        assert product_get_resp_after_delete.status_code == 200
        product_after_delete = product_get_resp_after_delete.json()
        # Stock should be back to initial stock quantity
        actual_stock_after_delete = product_after_delete.get("stock")
        assert actual_stock_after_delete == initial_stock_qty, \
            f"Stock level not reverted after invoice deletion. Expected {initial_stock_qty}, got {actual_stock_after_delete}"

        # Step 10: Verify accounting entries removed after invoice deletion
        accounting_resp_after_delete = requests.get(
            f"{BASE_URL}/api/accounting/entries/",
            params={"invoice_id": invoice_id},
            headers=HEADERS,
            auth=AUTH,
            timeout=TIMEOUT
        )
        assert accounting_resp_after_delete.status_code == 200
        entries_after_delete = accounting_resp_after_delete.json()
        assert (isinstance(entries_after_delete, list) and len(entries_after_delete) == 0), \
            "Accounting entries not removed after invoice deletion"

    finally:
        # Cleanup invoice if still exists
        if invoice_id is not None:
            requests.delete(
                f"{BASE_URL}/api/invoices/{invoice_id}/",
                headers=HEADERS,
                auth=AUTH,
                timeout=TIMEOUT
            )
        # Cleanup product
        if product_id is not None:
            requests.delete(
                f"{BASE_URL}/api/products/{product_id}/",
                headers=HEADERS,
                auth=AUTH,
                timeout=TIMEOUT
            )

test_create_update_delete_invoice_with_stock_and_accounting_impact()
