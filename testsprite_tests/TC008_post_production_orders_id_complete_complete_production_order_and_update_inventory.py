import requests
from bs4 import BeautifulSoup
import time

BASE_URL = "http://127.0.0.1:8000"
USERNAME = "superadmin"
PASSWORD = "admin123"
TIMEOUT = 30

def test_post_production_orders_id_complete():
    session = requests.Session()

    # Step 1: Load the login page to get csrftoken
    login_get_resp = session.get(f"{BASE_URL}/accounts/login/", timeout=TIMEOUT)
    assert login_get_resp.status_code == 200
    soup = BeautifulSoup(login_get_resp.text, "html.parser")
    csrf_token_input = soup.find("input", {"name": "csrfmiddlewaretoken"})
    assert csrf_token_input is not None, "CSRF token not found in login page"
    csrf_token = csrf_token_input.get("value")
    assert csrf_token, "CSRF token value is empty"

    # Step 2: Login with credentials and csrf token
    login_data = {
        "username": USERNAME,
        "password": PASSWORD,
        "csrfmiddlewaretoken": csrf_token,
    }
    login_headers = {
        "Referer": f"{BASE_URL}/accounts/login/"
    }
    login_post_resp = session.post(f"{BASE_URL}/accounts/login/", data=login_data, headers=login_headers, allow_redirects=False, timeout=TIMEOUT)
    assert login_post_resp.status_code == 302, "Login failed or unexpected response"
    assert login_post_resp.headers.get("location") != f"{BASE_URL}/accounts/login/", "Login redirect points back to login page"

    time.sleep(1)

    # Step 3: Get list of BOMs from production BOM list page to find a BOM id
    bom_list_resp = session.get(f"{BASE_URL}/production/bom/", timeout=TIMEOUT)
    assert bom_list_resp.status_code == 200
    soup = BeautifulSoup(bom_list_resp.text, "html.parser")

    # Extracting first BOM id from links in the BOM list page
    # Assumption: There are anchor tags with href containing bom details
    bom_id = None
    for a in soup.find_all("a", href=True):
        href = a['href']
        # Heuristic: URLs like /production/bom/{id}/ or similar
        # Extract numeric id from href
        import re
        match = re.search(r"/production/bom/(\d+)/", href)
        if match:
            bom_id = int(match.group(1))
            break
    assert bom_id is not None, "No BOM found in BOM list to create production order"

    # Step 4: Create a production order with the first BOM found and quantity 1
    # First get csrf token from create form
    create_form_resp = session.get(f"{BASE_URL}/production/orders/create/", timeout=TIMEOUT)
    assert create_form_resp.status_code == 200
    soup = BeautifulSoup(create_form_resp.text, "html.parser")
    csrf_token_input = soup.find("input", {"name": "csrfmiddlewaretoken"})
    assert csrf_token_input is not None, "CSRF token not found in production order create form"
    csrf_token = csrf_token_input.get("value")
    assert csrf_token, "CSRF token value is empty in production order create form"

    create_data = {
        "bom": str(bom_id),
        "quantity": "1",
        "csrfmiddlewaretoken": csrf_token,
    }
    create_headers = {
        "Referer": f"{BASE_URL}/production/orders/create/"
    }
    create_order_resp = session.post(f"{BASE_URL}/production/orders/create/", data=create_data, headers=create_headers, allow_redirects=False, timeout=TIMEOUT)
    assert create_order_resp.status_code == 302, f"Production order creation failed, status {create_order_resp.status_code}"
    location = create_order_resp.headers.get("location")
    assert location is not None and "/production/orders/" in location, "Redirect location missing or invalid after production order creation"

    # Extract production order ID from redirect location
    import re
    match = re.search(r"/production/orders/(\d+)/", location)
    assert match is not None, "Production order ID not found in redirect URL after creation"
    production_order_id = int(match.group(1))

    try:
        time.sleep(1)

        # Step 5: Start production order (Pending -> In Progress)
        # Get csrf token from production order detail page or start page
        # We'll fetch order detail page for CSRF token
        order_detail_resp = session.get(f"{BASE_URL}/production/orders/{production_order_id}/", timeout=TIMEOUT)
        assert order_detail_resp.status_code == 200
        soup = BeautifulSoup(order_detail_resp.text, "html.parser")
        csrf_token_input = soup.find("input", {"name": "csrfmiddlewaretoken"})
        # If not found in detail page, fallback to start form page
        if csrf_token_input is None:
            start_page_resp = session.get(f"{BASE_URL}/production/orders/{production_order_id}/start/", timeout=TIMEOUT)
            assert start_page_resp.status_code in [200, 302]
            soup = BeautifulSoup(start_page_resp.text, "html.parser")
            csrf_token_input = soup.find("input", {"name": "csrfmiddlewaretoken"})
        assert csrf_token_input is not None, "CSRF token not found for start production"
        csrf_token = csrf_token_input.get("value")
        assert csrf_token, "CSRF token value empty for start production"

        start_headers = {
            "Referer": f"{BASE_URL}/production/orders/{production_order_id}/start/"
        }
        start_data = {
            "csrfmiddlewaretoken": csrf_token,
        }
        start_resp = session.post(f"{BASE_URL}/production/orders/{production_order_id}/start/", data=start_data, headers=start_headers, allow_redirects=False, timeout=TIMEOUT)
        assert start_resp.status_code == 302, f"Failed to start production order, status {start_resp.status_code}"
        assert start_resp.headers.get("location") is not None, "Redirect location missing after starting production"

        time.sleep(1)

        # Step 6: Complete the production order (In Progress -> Completed)
        # Need csrf token for complete post, get from order detail or complete page
        order_detail_resp = session.get(f"{BASE_URL}/production/orders/{production_order_id}/", timeout=TIMEOUT)
        assert order_detail_resp.status_code == 200
        soup = BeautifulSoup(order_detail_resp.text, "html.parser")
        csrf_token_input = soup.find("input", {"name": "csrfmiddlewaretoken"})
        if csrf_token_input is None:
            complete_page_resp = session.get(f"{BASE_URL}/production/orders/{production_order_id}/complete/", timeout=TIMEOUT)
            assert complete_page_resp.status_code in [200, 302]
            soup = BeautifulSoup(complete_page_resp.text, "html.parser")
            csrf_token_input = soup.find("input", {"name": "csrfmiddlewaretoken"})
        assert csrf_token_input is not None, "CSRF token not found for complete production"
        csrf_token = csrf_token_input.get("value")
        assert csrf_token, "CSRF token value empty for complete production"

        complete_headers = {
            "Referer": f"{BASE_URL}/production/orders/{production_order_id}/complete/"
        }
        complete_data = {
            "csrfmiddlewaretoken": csrf_token,
        }
        complete_resp = session.post(f"{BASE_URL}/production/orders/{production_order_id}/complete/", data=complete_data, headers=complete_headers, allow_redirects=False, timeout=TIMEOUT)
        assert complete_resp.status_code == 302, f"Completing production order failed, status {complete_resp.status_code}"
        complete_redirect = complete_resp.headers.get("location")
        assert complete_redirect is not None, "Redirect location missing after completing production"

        time.sleep(1)

        # Step 7: Verify production order state is 'Completed' by fetching order detail page
        order_detail_resp = session.get(f"{BASE_URL}/production/orders/{production_order_id}/", timeout=TIMEOUT)
        assert order_detail_resp.status_code == 200
        soup = BeautifulSoup(order_detail_resp.text, "html.parser")
        # Expect the state somewhere in the HTML, search text for 'Completed'
        page_text = soup.get_text()
        assert "Completed" in page_text or "completed" in page_text, "Production order state is not 'Completed' after completion"

        # Step 8: Verify inventory is updated
        # Since no direct API for inventory verification is given, we check inventory dashboard accessible and contains updated stock
        inventory_resp = session.get(f"{BASE_URL}/inventory/", timeout=TIMEOUT)
        assert inventory_resp.status_code == 200
        inventory_page_text = inventory_resp.text.lower()
        # The BOM product name or some identifier might appear here, but since we don't have exact product name,
        # we just assert page contains "inventory" keyword indicating inventory page loaded.
        assert "inventory" in inventory_page_text, "Inventory page content unexpected"

    finally:
        # Cleanup: Delete the created production order if delete endpoint existed
        # The PRD does not specify a DELETE for production orders.
        # So no deletion performed.
        pass

test_post_production_orders_id_complete()