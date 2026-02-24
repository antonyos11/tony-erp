import requests

BASE_URL = "http://localhost:8000"
AUTH_URL = f"{BASE_URL}/api/token/"
ACTIVE_EMPLOYEES_URL = f"{BASE_URL}/hr/api/v1/employees/active/"
AUTH_CREDENTIALS = {"username": "boss", "password": "Mm02022006"}
TIMEOUT = 30

def test_hr_employees_active_list_api():
    # Obtain JWT token
    try:
        auth_resp = requests.post(AUTH_URL, json=AUTH_CREDENTIALS, timeout=TIMEOUT)
        assert auth_resp.status_code == 200, f"Auth failed with status {auth_resp.status_code}"
        token = auth_resp.json().get("access")
        assert token and isinstance(token, str), "Access token missing or invalid"
    except Exception as e:
        raise AssertionError(f"Authentication request failed: {e}")

    headers = {"Authorization": f"Bearer {token}"}

    # Request active employees list
    try:
        resp = requests.get(ACTIVE_EMPLOYEES_URL, headers=headers, timeout=TIMEOUT)
        assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}"
        data = resp.json()
        assert isinstance(data, list), "Response is not a list of employees"
        # Check that all employees are active (may have a field like 'status' or 'is_active')
        for emp in data:
            # Assume that active employees have a field 'status' == 'active' or 'is_active' == True
            if 'status' in emp:
                assert emp['status'].lower() == 'active', f"Found non-active employee with status {emp['status']}"
            elif 'is_active' in emp:
                assert emp['is_active'] is True, f"Found non-active employee with is_active={emp['is_active']}"
            else:
                # If no recognizable field for active status, fail
                assert False, "Employee object lacks 'status' or 'is_active' fields"
    except Exception as e:
        raise AssertionError(f"Failed verifying active employees list: {e}")

    # Verify RBAC by attempting to access with invalid or no token should be done here,
    # but since instructions specify only boss token usage, we limit to positive test.

test_hr_employees_active_list_api()