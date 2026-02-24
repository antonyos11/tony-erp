import requests

BASE_URL = "http://localhost:8000"
AUTH_URL = f"{BASE_URL}/api/token/"
KPIS_URL = f"{BASE_URL}/dashboard-api/api/kpis/"
TIMEOUT = 30

def test_dashboard_kpis_data_api():
    # Step 1: Obtain JWT token
    auth_payload = {"username": "boss", "password": "Mm02022006"}
    try:
        auth_response = requests.post(AUTH_URL, json=auth_payload, timeout=TIMEOUT)
        auth_response.raise_for_status()
    except requests.RequestException as e:
        assert False, f"Authentication request failed: {e}"
    auth_data = auth_response.json()
    assert "access" in auth_data and isinstance(auth_data["access"], str), "Access token not in auth response"
    token = auth_data["access"]

    headers = {
        "Authorization": f"Bearer {token}"
    }

    # Step 2: Request dashboard KPIs data
    try:
        kpis_response = requests.get(KPIS_URL, headers=headers, timeout=TIMEOUT)
        kpis_response.raise_for_status()
    except requests.RequestException as e:
        assert False, f"Request to KPIs endpoint failed: {e}"

    assert kpis_response.status_code == 200, f"Expected status code 200, got {kpis_response.status_code}"

    data = kpis_response.json()
    # Validate presence of top level keys
    required_top_keys = {"sales", "inventory", "financial", "customer", "operational"}
    assert isinstance(data, dict), "Response data is not a JSON object"
    missing_keys = required_top_keys - data.keys()
    assert not missing_keys, f"Missing KPI categories in response: {missing_keys}"

    # Further validate the structure is not empty for each key
    for key in required_top_keys:
        assert data[key] is not None and data[key] != {}, f"KPI section '{key}' is empty or null"

test_dashboard_kpis_data_api()