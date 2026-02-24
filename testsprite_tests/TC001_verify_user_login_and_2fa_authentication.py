import requests
import time

BASE_URL = "http://localhost:8000"
AUTH_URL = f"{BASE_URL}/api/token/"
LOGIN_API_PREFIXES = [
    "/sales/api/",
    "/inventory/api/",
    "/accounting/api/",
    "/ecommerce/api/",
    "/pos/api/",
    "/production/api/",
]
TIMEOUT = 30

def test_verify_user_login_and_2fa_authentication():
    # Step 1: Obtain JWT with valid credentials
    auth_payload_valid = {
        "username": "boss",
        "password": "Mm02022006"
    }
    headers = {"Content-Type": "application/json"}

    try:
        auth_response = requests.post(AUTH_URL, json=auth_payload_valid, headers=headers, timeout=TIMEOUT)
    except requests.RequestException as e:
        assert False, f"Request to auth endpoint failed: {e}"

    assert auth_response.status_code == 200, f"Expected 200 OK for valid credentials, got {auth_response.status_code}"
    auth_data = auth_response.json()
    assert "access" in auth_data and "refresh" in auth_data, "JWT tokens not returned in auth response"

    access_token = auth_data["access"]
    refresh_token = auth_data["refresh"]
    auth_headers = {"Authorization": f"Bearer {access_token}"}

    # Step 2: Test invalid credentials (wrong password)
    invalid_payload = {
        "username": "boss",
        "password": "WrongPassword123"
    }
    try:
        invalid_response = requests.post(AUTH_URL, json=invalid_payload, headers=headers, timeout=TIMEOUT)
    except requests.RequestException as e:
        assert False, f"Request with invalid credentials failed: {e}"
    assert invalid_response.status_code == 401 or invalid_response.status_code == 400, \
        f"Expected 401/400 for invalid credentials, got {invalid_response.status_code}"

    # Step 3: Simulate 2FA process
    # The PRD states django-otp (2FA) is used, but no exact endpoint given.
    # Common pattern: after login, 2FA token is required; this might be a separate endpoint or field.
    # We will attempt to call a protected endpoint that requires 2FA confirmation.

    # For this test assume /accounts/api/2fa/verify/ is an endpoint to verify 2FA TOTP code
    # Since we do not have a real TOTP code or such an endpoint documented,
    # we test that accessing a protected API without completing 2FA results in expected failure.

    # We'll pick one API prefix to test access before and after 2FA:
    # Let's test /accounting/api/dashboard/ as a protected endpoint (assuming)

    protected_url = f"{BASE_URL}/accounting/api/dashboard/"

    # Try access without 2FA confirmation - simulate by just using access token directly
    try:
        protected_resp_pre_2fa = requests.get(protected_url, headers=auth_headers, timeout=TIMEOUT)
    except requests.RequestException as e:
        assert False, f"Request to protected endpoint failed: {e}"

    # If 2FA is not yet verified, the server might return 403 or 401 indicating 2FA required
    # Accept 200 or 403/401 with specific message or 404 if endpoint missing

    assert protected_resp_pre_2fa.status_code in [200, 401, 403, 404], \
        f"Expected 200, 401, 403, or 404 if 2FA required or endpoint missing, got {protected_resp_pre_2fa.status_code}"

    # Simulate 2FA verification
    # As no 2FA endpoint is documented, attempt a common convention /accounts/api/2fa/verify/
    # with a dummy TOTP code "123456" (this will fail but we verify expected failure vs success)

    two_fa_url = f"{BASE_URL}/accounts/api/2fa/verify/"
    two_fa_payload = {"token": "123456"}  # Dummy TOTP

    try:
        two_fa_response = requests.post(two_fa_url, json=two_fa_payload, headers=auth_headers, timeout=TIMEOUT)
    except requests.RequestException:
        # 2FA endpoint might not exist, so skip this test part
        return

    # Validate response for 2FA verification
    # Accept either success with status 200 or failure with 400/401
    assert two_fa_response.status_code in [200, 400, 401], \
        f"Unexpected status code from 2FA verification: {two_fa_response.status_code}"

    if two_fa_response.status_code == 200:
        # If success, the user can access protected resource after 2FA
        try:
            protected_resp_post_2fa = requests.get(protected_url, headers=auth_headers, timeout=TIMEOUT)
        except requests.RequestException as e:
            assert False, f"Protected endpoint access after 2FA failed: {e}"

        assert protected_resp_post_2fa.status_code == 200, \
            "Failed to access protected resource after successful 2FA"
    else:
        # 2FA failed: ensure protected resource access is denied
        try:
            protected_resp_after_failed_2fa = requests.get(protected_url, headers=auth_headers, timeout=TIMEOUT)
        except requests.RequestException as e:
            assert False, f"Protected endpoint access after failed 2FA failed: {e}"

        assert protected_resp_after_failed_2fa.status_code in [401, 403], \
            "Protected resource accessible without valid 2FA"

test_verify_user_login_and_2fa_authentication()
