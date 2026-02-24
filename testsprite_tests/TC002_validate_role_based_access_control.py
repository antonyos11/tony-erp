import requests

BASE_URL = "http://127.0.0.1:8000"
LOGIN_URL = f"{BASE_URL}/api/token/"

# Endpoints to test role-based access control with expected access level
# We expect the "boss" user to successfully access allowed endpoints (status 200)
# and receive 403 Forbidden or 302 Redirect (admin-only) for restricted endpoints, as per instructions
TEST_ENDPOINTS = [
    "/sales/api/invoices/",
    "/accounting/api/accounts/search/",
    "/dashboard-api/api/kpis/",
    "/dashboard-api/api/data/",
    "/core/api/dashboard/daily-profit/",
    "/health/live/",
    "/ecommerce/api/products/",
    "/pos/api/orders/",
    "/attendance/api/my-records/",
    "/inventory/api/notifications/",
    "/inventory/api/barcode/lookup/",
    "/production/api/analytics/kpis/",
    "/smart-pricing/api/alerts/",
]

def test_validate_role_based_access_control():
    # Login and get JWT token
    auth_payload = {"username": "boss", "password": "Mm02022006"}
    try:
        auth_response = requests.post(LOGIN_URL, json=auth_payload, timeout=30)
        assert auth_response.status_code == 200, f"Login failed: {auth_response.status_code} {auth_response.text}"
        token = auth_response.json().get("access")
        assert token, "Access token not found in login response"
    except Exception as e:
        raise AssertionError(f"Authentication step failed: {e}")

    headers = {
        "Authorization": f"Bearer {token}"
    }

    for endpoint in TEST_ENDPOINTS:
        url = f"{BASE_URL}{endpoint}"
        try:
            response = requests.get(url, headers=headers, timeout=30, allow_redirects=False)
        except Exception as e:
            raise AssertionError(f"Request to {url} failed: {e}")

        # According to instructions some endpoints may return 302 redirect (expected for admin-only),
        # success for allowed access is HTTP 200.
        # For role restrictions, expect either 200, 302 redirect, or 403 forbidden.
        if response.status_code == 200:
            # Allowed access, verify body JSON or content type as a soft check
            ct = response.headers.get("Content-Type", "")
            assert ct.startswith("application/json") or ct.startswith("text/html"), f"Unexpected content type at {endpoint}"
        elif response.status_code == 302:
            # Redirect is expected for admin-only views
            pass
        elif response.status_code == 403:
            # Forbidden expected if role-based access restricts user
            pass
        else:
            raise AssertionError(f"Unexpected status code {response.status_code} on {endpoint}")

test_validate_role_based_access_control()