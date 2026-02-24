import requests
from bs4 import BeautifulSoup
import time

BASE_URL = "http://127.0.0.1:8000"
LOGIN_URL = f"{BASE_URL}/accounts/login/"
SALES_INVOICE_CREATE_URL = f"{BASE_URL}/sales/invoices/create/"
SALES_INVOICES_URL = f"{BASE_URL}/sales/invoices/"

USERNAME = "superadmin"
PASSWORD = "admin123"
TIMEOUT = 30


def test_post_sales_invoices_create_submit_new_sales_invoice():
    with requests.Session() as session:
        # Step 1: Get login page to retrieve CSRF token
        login_page = session.get(LOGIN_URL, timeout=TIMEOUT)
        assert login_page.status_code == 200, f"Failed to get login page, status {login_page.status_code}"
        soup = BeautifulSoup(login_page.text, "html.parser")
        csrf_input = soup.find("input", attrs={"name": "csrfmiddlewaretoken"})
        assert csrf_input and csrf_input["value"], "CSRF token not found on login page"
        csrf_token = csrf_input["value"]

        # Step 2: POST login data
        login_data = {
            "username": USERNAME,
            "password": PASSWORD,
            "csrfmiddlewaretoken": csrf_token
        }
        headers = {
            "Referer": LOGIN_URL
        }
        login_response = session.post(LOGIN_URL, data=login_data, headers=headers, timeout=TIMEOUT, allow_redirects=False)
        assert login_response.status_code in (302, 303), f"Login failed, expected redirect, got {login_response.status_code}"

        # Wait a bit to respect rate limits
        time.sleep(1)

        # Prepare valid sales invoice creation payload
        # Since we do not have explicit customer or item IDs from the PRD, we must create or fetch them.
        # We'll attempt to get the first customer and a product/item to use in items. 
        # However, since only session auth and sales endpoints are specified, and no API for customers/items is documented, 
        # we will create a minimal valid payload with plausible dummy data.

        # For robust testing ideally we would create or fetch customer & items,
        # but here create a dummy valid payload and test response code 302 means success.

        valid_payload = {
            # Assumed fields, per PRD request_schema:
            "customer": "1",  # Assuming a customer with ID 1 exists for test; string for form POST
            "items": '[]',    # Since no detail about form structure, send empty JSON array string or minimal
            "status": "draft"
        }

        # The items field should be an array, but for form POST it should be passed correctly.
        # We try JSON string or form style. We'll try JSON string since no form formats specified.

        # Let's construct multipart/form-data or application/x-www-form-urlencoded as typical form POST
        # We'll send items as JSON string. 

        # Step 3: POST valid sales invoice creation request
        headers = {
            "Referer": SALES_INVOICE_CREATE_URL,
            "Content-Type": "application/x-www-form-urlencoded"
        }

        # Attempt minimal valid input: customer=1, items is a JSON array string with at least one item.
        # Create dummy item for test: a list of dicts with minimal required fields (unspecified in PRD, so generic)
        import json
        items_list = [
            {
                "product": 1,  # Using 1 as dummy product ID
                "quantity": 1,
                "unit_price": "100.00"
            }
        ]
        valid_payload = {
            "customer": "1",
            "items": json.dumps(items_list),
            "status": "draft"
        }
        create_response = session.post(SALES_INVOICE_CREATE_URL, data=valid_payload, headers=headers, timeout=TIMEOUT, allow_redirects=False)

        # Success is expected to return 302 redirect (to invoice detail)
        assert create_response.status_code == 302, f"Valid invoice creation failed, expected 302 redirect, got {create_response.status_code}"

        # Extract invoice ID from redirect Location header if possible
        location = create_response.headers.get("Location")
        invoice_id = None
        if location:
            # Typical redirect location might be '/sales/invoices/{id}/'
            import re
            m = re.search(r"/sales/invoices/(\d+)/", location)
            if m:
                invoice_id = m.group(1)

        # Wait to respect rate limits
        time.sleep(1)

        # Step 4: POST invalid sales invoice creation request (missing required items)
        # Construct invalid payload without items field
        invalid_payload = {
            "customer": "1",
            "status": "draft"
        }
        invalid_response = session.post(SALES_INVOICE_CREATE_URL, data=invalid_payload, headers=headers, timeout=TIMEOUT, allow_redirects=False)

        # Expect a 400 validation error
        assert invalid_response.status_code == 400, f"Invalid invoice creation did not return 400, got {invalid_response.status_code}"

        # Step 5: Cleanup - delete the created invoice if possible
        # No DELETE endpoint documented in PRD for sales invoices, so skipping cleanup

# Call the test function
test_post_sales_invoices_create_submit_new_sales_invoice()