import requests
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"
USERNAME = "boss"
PASSWORD = "Mm02022006"
TIMEOUT = 30

def test_approve_invoice():
    # Step 1: Obtain JWT access token
    login_url = f"{BASE_URL}/api/token/"
    login_payload = {"username": USERNAME, "password": PASSWORD}
    login_response = requests.post(login_url, json=login_payload, timeout=TIMEOUT)
    assert login_response.status_code == 200, f"Login failed: {login_response.text}"
    access_token = login_response.json().get("access")
    assert access_token, "No access token received"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }

    # Get real customer, product, and location IDs
    customer_id = None
    product_id = None
    location_id = None
    invoice_id = None

    try:
        # Get or create a customer
        customers_resp = requests.get(f"{BASE_URL}/api/customers/", headers=headers, timeout=TIMEOUT)
        assert customers_resp.status_code == 200, f"Failed to get customers: {customers_resp.text}"
        customers = customers_resp.json()
        customers_list = customers if isinstance(customers, list) else customers.get("results", [])
        if customers_list:
            customer_id = customers_list[0].get("id")
        else:
            # Create a customer
            customer_payload = {"name": "اختبار العميل", "phone": "0123456789"}
            customer_resp = requests.post(f"{BASE_URL}/api/customers/", json=customer_payload, headers=headers, timeout=TIMEOUT)
            assert customer_resp.status_code == 201, f"Failed to create customer: {customer_resp.text}"
            customer_id = customer_resp.json().get("id")

        # Get a product
        products_resp = requests.get(f"{BASE_URL}/api/products/", headers=headers, timeout=TIMEOUT)
        assert products_resp.status_code == 200, f"Failed to get products: {products_resp.text}"
        products = products_resp.json()
        products_list = products if isinstance(products, list) else products.get("results", [])
        if products_list:
            product_id = products_list[0].get("id")
        else:
            # Create a test product
            product_payload = {"sku": "TEST-APPROVE-PROD", "name": "Test Approve Product", "price": "100.00", "cost": "50.00", "product_type": "finished"}
            product_resp = requests.post(f"{BASE_URL}/api/products/", json=product_payload, headers=headers, timeout=TIMEOUT)
            assert product_resp.status_code == 201, f"Failed to create product: {product_resp.text}"
            product_id = product_resp.json().get("id")

        # Get a location
        locations_resp = requests.get(f"{BASE_URL}/api/locations/", headers=headers, timeout=TIMEOUT)
        assert locations_resp.status_code == 200, f"Failed to get locations: {locations_resp.text}"
        locations = locations_resp.json()
        locations_list = locations if isinstance(locations, list) else locations.get("results", [])
        assert len(locations_list) > 0, "No locations available"
        location_id = locations_list[0].get("id")

        # Prepare valid invoice data with nested items
        today_str = datetime.now().date().isoformat()
        due_date_str = (datetime.now().date() + timedelta(days=30)).isoformat()

        invoice_data = {
            "customer": customer_id,
            "date": today_str,
            "due_date": due_date_str,
            "items": [
                {
                    "product": product_id,
                    "location": location_id,
                    "quantity": 1,
                    "price": "100.00"
                }
            ],
            "discount": "0.00"
        }

        invoice_create_url = f"{BASE_URL}/api/invoices/"
        create_resp = requests.post(invoice_create_url, headers=headers, json=invoice_data, timeout=TIMEOUT)
        assert create_resp.status_code == 201, f"Failed to create invoice: {create_resp.text}"
        invoice = create_resp.json()
        invoice_id = invoice.get("id")
        assert invoice_id is not None, "Created invoice has no id"

        # Approve the created invoice using new approve action
        approve_url = f"{BASE_URL}/api/invoices/{invoice_id}/approve/"
        approve_resp = requests.post(approve_url, headers=headers, timeout=TIMEOUT)
        assert approve_resp.status_code == 200, f"Failed to approve invoice: {approve_resp.text}"
        
        approve_data = approve_resp.json()
        assert approve_data.get("success") == True, f"Approval response indicates failure: {approve_data}"

        # Get the invoice to verify approval fields updated
        get_resp = requests.get(f"{BASE_URL}/api/invoices/{invoice_id}/", headers=headers, timeout=TIMEOUT)
        assert get_resp.status_code == 200, f"Failed to get invoice: {get_resp.text}"
        invoice_after = get_resp.json()
        
        assert invoice_after.get("is_approved") == True, "Invoice not marked as approved"
        assert invoice_after.get("approved_by") is not None, "approved_by field not set"
        assert invoice_after.get("approved_at") is not None, "approved_at field not set"

    except AssertionError:
        raise
    except Exception as e:
        raise AssertionError(f"Request failed: {e}")
    finally:
        # Clean up: delete the created invoice if exists
        if invoice_id is not None:
            delete_url = f"{BASE_URL}/api/invoices/{invoice_id}/"
            try:
                requests.delete(delete_url, headers=headers, timeout=TIMEOUT)
            except Exception:
                pass

test_approve_invoice()
