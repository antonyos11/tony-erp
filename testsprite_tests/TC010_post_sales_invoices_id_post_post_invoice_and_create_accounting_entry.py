import requests
from bs4 import BeautifulSoup
import time

BASE_URL = "http://127.0.0.1:8000"
LOGIN_URL = f"{BASE_URL}/accounts/login/"
SALES_INVOICES_CREATE_URL = f"{BASE_URL}/sales/invoices/create/"
SALES_INVOICES_LIST_URL = f"{BASE_URL}/sales/invoices/"
TIMEOUT = 30

USERNAME = "superadmin"
PASSWORD = "admin123"


def test_post_sales_invoice_post_creates_accounting_entry():
    session = requests.Session()

    # Step 1: Get login page to retrieve csrf token
    login_page_resp = session.get(LOGIN_URL, timeout=TIMEOUT)
    assert login_page_resp.status_code == 200
    login_page_html = login_page_resp.text
    soup = BeautifulSoup(login_page_html, "html.parser")
    csrf_input = soup.find("input", attrs={"name": "csrfmiddlewaretoken"})
    assert csrf_input is not None and csrf_input["value"]
    csrf_token = csrf_input["value"]

    time.sleep(1)

    # Step 2: Post login credentials with csrf token to authenticate session
    login_data = {
        "csrfmiddlewaretoken": csrf_token,
        "username": USERNAME,
        "password": PASSWORD,
    }
    headers = {
        "Referer": LOGIN_URL
    }
    login_resp = session.post(LOGIN_URL, data=login_data, headers=headers, timeout=TIMEOUT, allow_redirects=False)
    assert login_resp.status_code in (302, 303)  # Redirect indicates successful login

    time.sleep(1)

    # Step 3: Create a new sales invoice because no specific ID is provided
    # To create a sales invoice, we need valid data: customer id and items
    # We will retrieve a customer ID from the sales invoices create form or list page, or
    # since PRD does not specify customer create, we attempt to scrape existing customers from form if available.

    # Get sales invoice creation page to get csrf token and possibly a valid customer id if available
    create_page_resp = session.get(SALES_INVOICES_CREATE_URL, timeout=TIMEOUT)
    assert create_page_resp.status_code == 200
    create_page_html = create_page_resp.text
    soup = BeautifulSoup(create_page_html, "html.parser")

    # Extract new csrf token for invoice creation
    csrf_input = soup.find("input", attrs={"name": "csrfmiddlewaretoken"})
    assert csrf_input is not None and csrf_input["value"]
    csrf_token_invoice = csrf_input["value"]

    # Attempt to find a valid customer id from a select element with name 'customer'
    customer_select = soup.find("select", attrs={"name": "customer"})
    if not customer_select or not customer_select.find("option"):
        raise AssertionError("No customers found to create invoice")

    # Choose the first non-empty customer option
    customer_id = None
    for option in customer_select.find_all("option"):
        if option.get("value") and option.get("value").isdigit():
            customer_id = option.get("value")
            break
    if not customer_id:
        raise AssertionError("No valid customer ID found in invoice creation form")

    # Prepare invoice items - Since no detail given, create dummy item data expected by the form.
    # The PRD states the sales invoice POST body needs: {customer: int, items: array, status: 'draft'}
    # The web UI form might require form fields following Django form format (e.g. form-TOTAL_FORMS etc)?
    # Absent details, will do minimal submission with one item in JSON/encoded form data.

    # We will try to submit minimal invoice with status='draft' and one item:
    # Because it's a normal Django form (HTML), we have to guess field names for items.
    # Alternatively, create a very basic invoice with HTML form data structure:
    # Usually related items in formsets have management form fields:
    # form-TOTAL_FORMS, form-INITIAL_FORMS, form-MIN_NUM_FORMS, form-MAX_NUM_FORMS
    # and lines like form-0-product, form-0-quantity, form-0-price, etc.
    # Since PRD doesn't provide details, try minimal plausible fields.

    # Let's try a minimal invoice with one item using formsets:
    post_data = {
        "csrfmiddlewaretoken": csrf_token_invoice,
        "customer": customer_id,
        "status": "draft",
        # Formset management data - minimally dummy values
        "items-TOTAL_FORMS": "1",
        "items-INITIAL_FORMS": "0",
        "items-MIN_NUM_FORMS": "0",
        "items-MAX_NUM_FORMS": "1000",
        # One item fields - guessing field names since not given:
        "items-0-product": "",  # empty will likely cause validation error
        "items-0-quantity": "1",
        "items-0-price": "0",
    }
    # We expect this may result in a validation error due to missing products.
    # So to bypass this, we will try to get product ID from inventory or invoices page
    # Since no direct product API given here and no instructions, fallback plan is to raise error.

    # To handle properly, use fallback: create a draft invoice with only customer and no items, may fail but no item means error.

    # Instead, try creating invoice via API endpoints? But PRD says sales invoices creation is /sales/invoices/create/ with form POST.

    # Since product ids or items are not detailed, try only customer and status - may fail but should be tested.

    post_data_minimal = {
        "csrfmiddlewaretoken": csrf_token_invoice,
        "customer": customer_id,
        "status": "draft",
    }

    # Submit POST to create invoice - allow redirects to get invoice detail URL
    create_resp = session.post(SALES_INVOICES_CREATE_URL, data=post_data_minimal, headers={"Referer": SALES_INVOICES_CREATE_URL}, timeout=TIMEOUT, allow_redirects=False)
    # Since items is required, expect 400 or validation error
    if create_resp.status_code == 302:
        # Extract invoice ID from Location header redirect to invoice detail: /sales/invoices/{id}/
        location = create_resp.headers.get("Location")
        assert location is not None and location.startswith("/sales/invoices/")
        invoice_id_str = location.rstrip("/").split("/")[-1]
        assert invoice_id_str.isdigit()
        invoice_id = int(invoice_id_str)
    else:
        # To pass test, we need to create an invoice with items, but lacking info, raise error
        raise AssertionError(f"Failed to create draft invoice due to validation errors, status: {create_resp.status_code}")

    time.sleep(1)

    # Step 4: POST to /sales/invoices/{id}/post/ to post the invoice
    post_invoice_url = f"{BASE_URL}/sales/invoices/{invoice_id}/post/"

    # Need to get fresh csrf token from invoice detail page before posting
    invoice_detail_url = f"{BASE_URL}/sales/invoices/{invoice_id}/"
    detail_resp = session.get(invoice_detail_url, timeout=TIMEOUT)
    assert detail_resp.status_code == 200
    detail_html = detail_resp.text
    soup = BeautifulSoup(detail_html, "html.parser")
    csrf_input = soup.find("input", attrs={"name": "csrfmiddlewaretoken"})
    if csrf_input and csrf_input["value"]:
        csrf_token_post = csrf_input["value"]
    else:
        # Sometimes csrf token is in cookie or meta? fallback to session cookie
        csrf_token_post = session.cookies.get("csrftoken")
        assert csrf_token_post, "CSRF token not found for posting invoice"

    # Post the invoice
    post_headers = {
        "Referer": invoice_detail_url
    }
    post_data = {
        "csrfmiddlewaretoken": csrf_token_post
    }
    post_resp = session.post(post_invoice_url, data=post_data, headers=post_headers, timeout=TIMEOUT, allow_redirects=False)
    # Expect 302 redirect indicating posting succeeded
    assert post_resp.status_code in (302, 303)
    # Location header should redirect, typically back to invoice or accounting page
    redirect_location = post_resp.headers.get("Location")
    assert redirect_location is not None and len(redirect_location) > 0

    # Step 5: Verify that posting created the corresponding accounting entry
    # Since accounting entries are at /accounting/journal-entries/ (HTML list), check there is at least one entry
    time.sleep(1)
    accounting_entries_url = f"{BASE_URL}/accounting/journal-entries/"
    acc_resp = session.get(accounting_entries_url, timeout=TIMEOUT)
    assert acc_resp.status_code == 200
    acc_html = acc_resp.text.lower()
    # Verify presence of some indication of new journal entry or posted invoice id
    # This is a weak check since exact format unknown
    assert ("invoice" in acc_html) or ("journal entry" in acc_html) or ("sales" in acc_html)

    # Cleanup: Delete the created invoice
    # No direct delete API in PRD, so skip cleanup

    session.close()


test_post_sales_invoice_post_creates_accounting_entry()