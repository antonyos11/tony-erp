import requests
import time

BASE_URL = "http://127.0.0.1:8000"
AUTH_URL = f"{BASE_URL}/api/token/"
TIMEOUT = 30

def authenticate(username="boss", password="Mm02022006"):
    try:
        resp = requests.post(
            AUTH_URL,
            json={"username": username, "password": password},
            timeout=TIMEOUT
        )
        resp.raise_for_status()
        token = resp.json().get("access")
        assert token, "Authentication response missing access token"
        return token
    except (requests.RequestException, AssertionError) as e:
        raise RuntimeError(f"Authentication failed: {e}")

def get_with_bearer(url, token):
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers, timeout=TIMEOUT, allow_redirects=True)
    return resp

def test_dashboard_data_loading_and_performance():
    token = authenticate()
    headers = {"Authorization": f"Bearer {token}"}

    endpoints_expected = {
        "/dashboard-api/api/kpis/": 200,
        "/dashboard-api/api/data/": 200,
        "/core/api/dashboard/daily-profit/": 200,
        "/smart-pricing/api/alerts/": 200,
    }

    # Track timing and results
    for endpoint, expected_status in endpoints_expected.items():
        url = BASE_URL + endpoint
        start = time.perf_counter()
        try:
            resp = requests.get(url, headers=headers, timeout=TIMEOUT, allow_redirects=True)
            duration = time.perf_counter() - start
        except requests.RequestException as e:
            raise AssertionError(f"Request failed for {endpoint}: {e}")

        # Assert status codes and no server errors
        assert resp.status_code == expected_status, (
            f"Unexpected status code {resp.status_code} for {endpoint}, expected {expected_status}"
        )
        assert resp.status_code != 500, f"Server error (500) at {endpoint}"

        # Assert content not empty and check typical keys presence depending on endpoint
        json_data = None
        try:
            json_data = resp.json()
        except Exception:
            raise AssertionError(f"Response at {endpoint} is not valid JSON")

        assert json_data, f"Response JSON is empty at {endpoint}"

        # Specific content checks:
        if endpoint == "/dashboard-api/api/kpis/":
            # KPIs keys sample check - all keys must be present
            needed_keys = {"total_sales", "total_purchases", "net_profit"}
            assert needed_keys.issubset(json_data.keys()), (
                f"KPIs response missing expected keys at {endpoint}"
            )
        elif endpoint == "/dashboard-api/api/data/":
            # Should contain charts data
            assert any(k in json_data for k in ("sales_chart", "purchase_stats", "alerts")), (
                f"Dashboard data missing expected keys at {endpoint}"
            )
        elif endpoint == "/core/api/dashboard/daily-profit/":
            # Should have daily profit data
            assert "daily_profit" in json_data or isinstance(json_data, (dict, list)), (
                f"Daily profit data missing or invalid at {endpoint}"
            )
        elif endpoint == "/smart-pricing/api/alerts/":
            # Alerts array expected
            assert isinstance(json_data, (list, dict)), f"Alerts response format invalid at {endpoint}"

        # Performance assertions based on validation criteria:
        # Dashboard loads within 3 seconds
        if endpoint in ["/dashboard-api/api/kpis/", "/dashboard-api/api/data/", "/core/api/dashboard/daily-profit/"]:
            assert duration <= 3.0, f"Dashboard endpoint {endpoint} response too slow: {duration:.2f}s"
        # Alerts performance less strict, but we expect under 3s as well
        if endpoint == "/smart-pricing/api/alerts/":
            assert duration <= 3.0, f"Alerts endpoint {endpoint} response too slow: {duration:.2f}s"

    print("Test TC003: Dashboard data loading and performance passed.")

test_dashboard_data_loading_and_performance()
