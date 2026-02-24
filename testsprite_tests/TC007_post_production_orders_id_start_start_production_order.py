import requests
from bs4 import BeautifulSoup
import time

BASE_URL = "http://127.0.0.1:8000"
USERNAME = "superadmin"
PASSWORD = "admin123"
TIMEOUT = 30

session = requests.Session()

def login():
    # GET login page to get csrf token
    resp = session.get(f"{BASE_URL}/accounts/login/", timeout=TIMEOUT)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    csrf_token_tag = soup.find("input", dict(name="csrfmiddlewaretoken"))
    assert csrf_token_tag is not None, "CSRF token not found on login page"
    csrfmiddlewaretoken = csrf_token_tag.get("value")

    login_data = {
        "username": USERNAME,
        "password": PASSWORD,
        "csrfmiddlewaretoken": csrfmiddlewaretoken,
    }
    headers = {
        "Referer": f"{BASE_URL}/accounts/login/"
    }
    resp2 = session.post(f"{BASE_URL}/accounts/login/", data=login_data, headers=headers, timeout=TIMEOUT,
                         allow_redirects=False)
    assert resp2.status_code == 302, f"Login failed, expected redirect, got {resp2.status_code}"
    assert "sessionid" in session.cookies, "Session cookie not set after login"
    time.sleep(1)

def create_production_order():
    # Need to create a production order to test start
    # First get BOM list page to select a BOM id
    resp_bom_list = session.get(f"{BASE_URL}/production/bom/", timeout=TIMEOUT)
    resp_bom_list.raise_for_status()
    # Parse BOM IDs from the page
    soup = BeautifulSoup(resp_bom_list.text, "html.parser")
    bom_links = soup.select("a[href*='/production/bom/']")
    bom_id = None
    for a in bom_links:
        href = a.get("href")
        # Expecting links like /production/bom/{id}/ or similar
        parts = href.strip("/").split("/")
        for p in parts:
            if p.isdigit():
                bom_id = int(p)
                break
        if bom_id:
            break
    # If no BOM found on the HTML page, fallback to GET /production/api/bom/ is guarded? According to instructions must use page /production/bom/
    if not bom_id:
        raise RuntimeError("No BOM id found to create production order")
    # Get create form to get csrf token
    resp_create = session.get(f"{BASE_URL}/production/orders/create/", timeout=TIMEOUT)
    resp_create.raise_for_status()
    soup = BeautifulSoup(resp_create.text, "html.parser")
    csrf_token_tag = soup.find("input", dict(name="csrfmiddlewaretoken"))
    assert csrf_token_tag is not None, "CSRF token not found on production order create page"
    csrfmiddlewaretoken = csrf_token_tag.get("value")

    post_data = {
        "bom": str(bom_id),
        "quantity": "1",
        "csrfmiddlewaretoken": csrfmiddlewaretoken
    }
    headers = {
        "Referer": f"{BASE_URL}/production/orders/create/"
    }
    resp_post = session.post(f"{BASE_URL}/production/orders/create/", data=post_data, headers=headers, timeout=TIMEOUT,
                             allow_redirects=False)
    assert resp_post.status_code == 302, f"Failed to create production order, status {resp_post.status_code}"
    location = resp_post.headers.get("Location")
    assert location, "Redirect location header missing after production order create"

    # Extract production order ID from redirect location, expect something like /production/orders/{id}/ or view detail
    import re
    match = re.search(r"/production/orders/(\d+)/", location)
    assert match, f"Could not find production order ID in redirect location: {location}"
    order_id = int(match.group(1))
    time.sleep(1)
    return order_id

def start_production_order(order_id):
    # Get the production order detail page to get csrf token
    resp_detail = session.get(f"{BASE_URL}/production/orders/{order_id}/", timeout=TIMEOUT)
    resp_detail.raise_for_status()
    soup = BeautifulSoup(resp_detail.text, "html.parser")
    csrf_token_tag = soup.find("input", dict(name="csrfmiddlewaretoken"))
    if csrf_token_tag:
        csrfmiddlewaretoken = csrf_token_tag.get("value")
    else:
        # maybe no csrf token on detail page? Then try to start without csrf on POST?
        csrfmiddlewaretoken = None

    headers = {}
    post_data = {}
    if csrfmiddlewaretoken:
        post_data["csrfmiddlewaretoken"] = csrfmiddlewaretoken
        headers["Referer"] = f"{BASE_URL}/production/orders/{order_id}/"

    resp_start = session.post(f"{BASE_URL}/production/orders/{order_id}/start/", data=post_data, headers=headers,
                              timeout=TIMEOUT, allow_redirects=False)
    return resp_start

def get_production_order_status(order_id):
    resp = session.get(f"{BASE_URL}/production/api/orders/", timeout=TIMEOUT)
    resp.raise_for_status()
    json_orders = resp.json()
    # look for order with order_id
    for o in json_orders:
        if o.get("id") == order_id:
            return o.get("status") or o.get("state") or o.get("order_status") or o.get("order_state")
    # fallback: get detail page and parse status
    resp_detail = session.get(f"{BASE_URL}/production/orders/{order_id}/", timeout=TIMEOUT)
    resp_detail.raise_for_status()
    # parse status from HTML detail page: search for textual indicators like Pending or In Progress
    soup = BeautifulSoup(resp_detail.text, "html.parser")
    text = soup.get_text().lower()
    if "pending" in text:
        return "Pending"
    if "in progress" in text:
        return "In Progress"
    if "completed" in text:
        return "Completed"
    return None

def delete_production_order(order_id):
    # No explicit DELETE endpoint given in PRD, so we skip deletion
    # If there is no delete API, we cannot delete created production orders. Just pass.
    pass

def test_post_production_orders_id_start():
    try:
        login()

        order_id = create_production_order()
        assert order_id is not None, "Created production order ID is None"

        # Confirm initial status is Pending
        status_before = get_production_order_status(order_id)
        assert status_before and status_before.lower() == "pending", f"Expected order status to be Pending but was '{status_before}'"

        # Start production order
        resp_start = start_production_order(order_id)
        assert resp_start.status_code == 302, f"Expected redirect status 302 on start production but got {resp_start.status_code}"
        location = resp_start.headers.get("Location")
        assert location, "Redirect location header missing after starting production order"

        # Confirm status transitioned to In Progress
        time.sleep(1)
        status_after = get_production_order_status(order_id)
        assert status_after and status_after.lower() in ["in progress", "inprogress"], f"Expected order status to be In Progress but was '{status_after}'"

    finally:
        # Cleanup the created production order if a deletion endpoint existed
        delete_production_order(order_id)

test_post_production_orders_id_start()
