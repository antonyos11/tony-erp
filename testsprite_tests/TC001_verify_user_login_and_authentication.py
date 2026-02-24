import requests

BASE_URL = "http://127.0.0.1:8000"
TOKEN_URL = f"{BASE_URL}/api/token/"


def test_verify_user_login_and_authentication():
    timeout = 30

    # Test valid credentials
    valid_credentials = {"username": "boss", "password": "Mm02022006"}
    try:
        resp_valid = requests.post(TOKEN_URL, json=valid_credentials, timeout=timeout)
        assert resp_valid.status_code == 200, f"Expected 200, got {resp_valid.status_code}"
        json_valid = resp_valid.json()
        assert "access" in json_valid, "Response missing access token"
        access_token = json_valid["access"]
        assert isinstance(access_token, str) and len(access_token) > 0, "Invalid access token"
    except (requests.RequestException, AssertionError) as e:
        raise AssertionError(f"Valid login failed: {e}")

    headers = {"Authorization": f"Bearer {access_token}"}

    # Optional: If there is a 2FA verification step endpoint with JWT token, test it here.
    # Since no 2FA endpoint URL is provided in the code summary, we skip actual 2FA requests.
    # We can attempt to call a protected endpoint to validate token usage.

    protected_endpoint = f"{BASE_URL}/dashboard-api/api/kpis/"
    try:
        resp_protected = requests.get(protected_endpoint, headers=headers, timeout=timeout, allow_redirects=False)
        assert resp_protected.status_code in (200, 302), (
            f"Expected 200 or 302 for authorized access, got {resp_protected.status_code}"
        )
    except (requests.RequestException, AssertionError) as e:
        raise AssertionError(f"Accessing protected endpoint with valid token failed: {e}")

    # Test invalid credentials
    invalid_credentials = {"username": "boss", "password": "WrongPassword123!"}
    try:
        resp_invalid = requests.post(TOKEN_URL, json=invalid_credentials, timeout=timeout)
        assert resp_invalid.status_code == 401, f"Expected 401, got {resp_invalid.status_code}"
        json_invalid = resp_invalid.json()
        # The response should indicate failure; optionally validate detail/error field
        assert "access" not in json_invalid, "Invalid login should not provide access token"
    except (requests.RequestException, AssertionError) as e:
        raise AssertionError(f"Invalid login test failed: {e}")

    # Test 2FA: Since the PRD mentions django-otp for 2FA but no exact endpoint given,
    # We assume 2FA is integrated into login flow or a separate endpoint.
    # Without endpoint info, we cannot test 2FA verification step.

    # Instead, validate that access token is required to access protected resources;
    # test access with no token and with invalid token.

    # Access protected endpoint without token
    try:
        resp_no_token = requests.get(protected_endpoint, timeout=timeout, allow_redirects=False)
        # Expect 401 Unauthorized or 403 Forbidden if no token provided
        assert resp_no_token.status_code in (401, 403), (
            f"Expected 401 or 403 without token, got {resp_no_token.status_code}"
        )
    except (requests.RequestException, AssertionError) as e:
        raise AssertionError(f"Accessing protected endpoint without token failed: {e}")

    # Access protected endpoint with invalid token
    headers_invalid = {"Authorization": "Bearer invalidtoken123"}
    try:
        resp_invalid_token = requests.get(protected_endpoint, headers=headers_invalid, timeout=timeout, allow_redirects=False)
        assert resp_invalid_token.status_code in (401, 403), (
            f"Expected 401 or 403 with invalid token, got {resp_invalid_token.status_code}"
        )
    except (requests.RequestException, AssertionError) as e:
        raise AssertionError(f"Accessing protected endpoint with invalid token failed: {e}")


test_verify_user_login_and_authentication()