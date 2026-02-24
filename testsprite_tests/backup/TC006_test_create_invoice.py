import requests

BASE_URL = "http://localhost:8000"
USERNAME = "boss"
PASSWORD = "Mm02022006"
TIMEOUT = 30

def test_create_invoice():
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

    # Step 2: Create or use existing partners.Customer (Invoice FK uses partners.Customer)
    # Note: Invoice model uses partners.Customer FK, not crm.Customer
    customer_payload = {
        "name": "عميل اختبار الفاتورة",
        "phone": "01234567890",
        "email": "invoice.customer@test.com"
    }
    customer_id = None
    invoice_id = None
    location_id = None
    product_id = None

    try:
        # Create partners customer using /api/customers/
        customer_resp = requests.post(
            f"{BASE_URL}/api/customers/",
            json=customer_payload,
            headers=headers,
            timeout=TIMEOUT,
        )
        assert customer_resp.status_code == 201, f"Failed to create customer: {customer_resp.text}"
        customer_data = customer_resp.json()
        customer_id = customer_data.get("id")
        assert customer_id is not None, "Customer ID is missing in response"

        # Step 3: Fetch at least one product
        products_resp = requests.get(
            f"{BASE_URL}/api/products/",
            headers=headers,
            timeout=TIMEOUT,
        )
        assert products_resp.status_code == 200, f"Failed to get products: {products_resp.text}"
        products = products_resp.json()
        products_list = products if isinstance(products, list) else products.get("results", [])
        
        # Create a test product if none exists
        if len(products_list) == 0:
            product_payload = {
                "sku": "TEST-INV-PROD",
                "name": "Test Invoice Product",
                "price": "100.00",
                "cost": "50.00",
                "product_type": "finished"
            }
            product_resp = requests.post(f"{BASE_URL}/api/products/", json=product_payload, headers=headers, timeout=TIMEOUT)
            assert product_resp.status_code == 201, f"Failed to create product: {product_resp.text}"
            product_id = product_resp.json().get("id")
        else:
            product_id = products_list[0].get("id")
        
        assert product_id is not None, "Product ID missing"
        
        # Step 4: Get a location for invoice items
        locations_resp = requests.get(f"{BASE_URL}/api/locations/", headers=headers, timeout=TIMEOUT)
        assert locations_resp.status_code == 200, f"Failed to get locations: {locations_resp.text}"
        locations = locations_resp.json()
        locations_list = locations if isinstance(locations, list) else locations.get("results", [])
        assert len(locations_list) > 0, "No locations available - cannot create invoice items"
        location_id = locations_list[0].get("id")

        # Step 5: Create invoice with nested items using partners.Customer ID
        # Note: Invoice model uses partners.Customer FK, so we need to create or use existing partners.Customer
        # For now, we'll try with the ID directly - if it fails, it confirms the FK mismatch issue
        invoice_payload = {
            "customer": customer_id,
            "date": "2026-01-23",
            "due_date": "2026-02-23",
            "items": [  # Nested items
                {
                    "product": product_id,
                    "location": location_id,
                    "quantity": 2,
                    "price": "100.00"
                }
            ],
            "discount": "0.00"
        }

        # Create invoice
        invoice_resp = requests.post(
            f"{BASE_URL}/api/invoices/",
            json=invoice_payload,
            headers=headers,
            timeout=TIMEOUT,
        )
        # Note: This might fail with 500 if customer FK is mismatched
        # In that case, we'd need to create partners.Customer or modify Invoice model
        assert invoice_resp.status_code == 201, f"Failed to create invoice: {invoice_resp.text}"
        invoice_data = invoice_resp.json()
        invoice_id = invoice_data.get("id")
        assert invoice_id is not None, "Invoice ID is missing in response"

        # Step 6: Verify invoice was created
        invoice_detail_resp = requests.get(
            f"{BASE_URL}/api/invoices/{invoice_id}/",
            headers=headers,
            timeout=TIMEOUT,
        )
        assert invoice_detail_resp.status_code == 200, f"Failed to get invoice details: {invoice_detail_resp.text}"
        invoice_detail = invoice_detail_resp.json()
        assert invoice_detail.get("customer") == customer_id, "Customer linkage incorrect"

    except AssertionError:
        raise
    except Exception as e:
        raise AssertionError(f"Request failed: {e}")
    finally:
        # Cleanup: Delete created records
        if invoice_id is not None:
            try:
                requests.delete(f"{BASE_URL}/api/invoices/{invoice_id}/", headers=headers, timeout=TIMEOUT)
            except Exception:
                pass

        if customer_id is not None:
            try:
                requests.delete(f"{BASE_URL}/api/customers/{customer_id}/", headers=headers, timeout=TIMEOUT)
            except Exception:
                pass

test_create_invoice()
