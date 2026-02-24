import requests
import re
import time

BASE_URL = "http://127.0.0.1:8000"
USERNAME = "superadmin"
PASSWORD = "admin123"
TIMEOUT = 30

def extract_csrf_token(text):
    match = re.search(r'name=["\']csrfmiddlewaretoken["\'] value=["\'](.+?)["\']', text)
    assert match, "CSRF token input not found"
    return match.group(1)

def extract_bom_id_from_links(text):
    # Find all hrefs like /production/bom/<id>/
    matches = re.findall(r'href=["\'](/production/bom/(\d+)/)["\']', text)
    if matches:
        return int(matches[0][1])
    else:
        # Try to find generic /production/bom/<id>
        matches = re.findall(r'/production/bom/(\d+)/', text)
        if matches:
            return int(matches[0])
    return None

def test_post_production_orders_create_submit_new_production_order():
    session = requests.Session()

    # Step 1: GET the login page to retrieve CSRF token
    login_page = session.get(f"{BASE_URL}/accounts/login/", timeout=TIMEOUT)
    assert login_page.status_code == 200, "Failed to load login page"
    csrf_token = extract_csrf_token(login_page.text)

    # Step 2: POST to login page with username, password and CSRF token to authenticate
    login_data = {
        "username": USERNAME,
        "password": PASSWORD,
        "csrfmiddlewaretoken": csrf_token
    }
    headers = {
        "Referer": f"{BASE_URL}/accounts/login/"
    }
    login_response = session.post(f"{BASE_URL}/accounts/login/", data=login_data, headers=headers, timeout=TIMEOUT, allow_redirects=False)
    assert login_response.status_code in (200, 302), f"Login failed with status code {login_response.status_code}"

    # Small delay to respect rate limits
    time.sleep(1)

    # Step 3: GET BOM list page to find a valid BOM ID to use in production order
    bom_list_resp = session.get(f"{BASE_URL}/production/bom/", timeout=TIMEOUT)
    assert bom_list_resp.status_code == 200, "Failed to retrieve BOM list"
    bom_id = extract_bom_id_from_links(bom_list_resp.text)
    assert bom_id is not None, "No BOM ID found for creating production order"

    # Step 4: Test valid POST to /production/orders/create/ with correct data
    create_order_url = f"{BASE_URL}/production/orders/create/"
    # Get CSRF token for the POST request from the create page form (recommended)
    create_order_form = session.get(create_order_url, timeout=TIMEOUT)
    assert create_order_form.status_code == 200, "Failed to get production order create form"
    csrf_token_create = extract_csrf_token(create_order_form.text)

    valid_payload = {
        "bom": str(bom_id),
        "quantity": "10",
        "csrfmiddlewaretoken": csrf_token_create,
    }
    headers_create = {
        "Referer": create_order_url
    }
    response_valid = session.post(create_order_url, data=valid_payload, headers=headers_create, timeout=TIMEOUT, allow_redirects=False)
    # Expect a 302 redirect to order detail if success
    assert response_valid.status_code == 302, f"Valid production order creation did not redirect, got {response_valid.status_code}"
    location = response_valid.headers.get("Location", "")
    assert location.startswith("/production/orders/"), "Redirect location is not to production order detail"

    # Extract created production order ID from redirect location for cleanup if needed
    created_order_id = None
    try:
        created_order_id = int(location.rstrip("/").split("/")[-1])
    except Exception:
        created_order_id = None

    # Step 5: Test invalid POST to /production/orders/create/ with missing 'bom' field (should return 400)
    # Need fresh CSRF token from create form again for new POST
    create_order_form = session.get(create_order_url, timeout=TIMEOUT)
    assert create_order_form.status_code == 200, "Failed to refresh production order create form"
    csrf_token_create_invalid = extract_csrf_token(create_order_form.text)

    invalid_payload = {
        "quantity": "5",
        "csrfmiddlewaretoken": csrf_token_create_invalid,
    }
    headers_create_invalid = {
        "Referer": create_order_url
    }
    response_invalid = session.post(create_order_url, data=invalid_payload, headers=headers_create_invalid, timeout=TIMEOUT, allow_redirects=False)
    # Expect a 400 validation error (likely with content explaining error)
    assert response_invalid.status_code == 400, f"Invalid production order creation did not return 400, got {response_invalid.status_code}"

    session.close()

test_post_production_orders_create_submit_new_production_order()
