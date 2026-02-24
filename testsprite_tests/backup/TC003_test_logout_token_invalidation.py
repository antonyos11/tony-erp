import requests

BASE_URL = "http://localhost:8000"
USERNAME = "boss"
PASSWORD = "Mm02022006"
TIMEOUT = 30

def test_logout_token_invalidation():
    try:
        # Step 1: Obtain JWT token pair with valid credentials
        login_url = f"{BASE_URL}/api/token/"
        login_payload = {"username": USERNAME, "password": PASSWORD}
        login_headers = {"Content-Type": "application/json"}
        login_response = requests.post(login_url, json=login_payload, headers=login_headers, timeout=TIMEOUT)
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        tokens = login_response.json()
        access_token = tokens.get("access")
        refresh_token = tokens.get("refresh")
        assert access_token, "No access token received"
        assert refresh_token, "No refresh token received"

        # Step 2: Logout and invalidate the token by sending refresh token in payload
        # IMPORTANT: Must include access token in Authorization header for authentication
        logout_url = f"{BASE_URL}/api/logout/"
        logout_headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"  # Required for authentication
        }
        logout_payload = {"refresh_token": refresh_token}  # Updated key name
        logout_response = requests.post(logout_url, headers=logout_headers, json=logout_payload, timeout=TIMEOUT)
        assert logout_response.status_code in (200, 204), f"Logout failed: {logout_response.text}"

        # Step 3: Verify that the refresh token is blacklisted
        # NOTE: JWT access tokens are stateless and remain valid until expiry
        # Only the refresh token can be blacklisted
        # Try to use refresh token to get a new access token - should fail
        refresh_url = f"{BASE_URL}/api/token/refresh/"
        refresh_payload = {"refresh": refresh_token}
        refresh_response = requests.post(refresh_url, json=refresh_payload, timeout=TIMEOUT)
        # Refresh should fail because token is blacklisted
        assert refresh_response.status_code in (401, 403), \
            f"Refresh token not blacklisted, still works: {refresh_response.status_code} - {refresh_response.text}"

    except requests.RequestException as e:
        raise AssertionError(f"HTTP request failed: {e}")

test_logout_token_invalidation()
