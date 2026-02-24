import requests

BASE_URL = "http://127.0.0.1:8000"
TIMEOUT = 30

def test_post_api_token_verify_verify_jwt_token_validity():
    token_url = f"{BASE_URL}/api/token/"
    verify_url = f"{BASE_URL}/api/token/verify/"

    # Step 1: Obtain valid JWT tokens with valid credentials
    auth_payload = {
        "username": "superadmin",
        "password": "admin123"
    }
    try:
        response = requests.post(token_url, json=auth_payload, timeout=TIMEOUT)
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
        tokens = response.json()
        assert "access" in tokens and "refresh" in tokens, "Tokens missing in response"
        valid_access_token = tokens["access"]
    except requests.RequestException as e:
        assert False, f"Request to obtain JWT tokens failed: {e}"

    headers = {"Content-Type": "application/json"}

    # Step 2: Verify valid access token - expect 200 with empty response body
    verify_payload_valid = {"token": valid_access_token}
    try:
        verify_resp = requests.post(verify_url, json=verify_payload_valid, headers=headers, timeout=TIMEOUT)
        assert verify_resp.status_code == 200, f"Expected 200 OK for valid token verify, got {verify_resp.status_code}"
        # Should be empty JSON object
        assert verify_resp.json() == {}, "Expected empty JSON object for valid token verify"
    except requests.RequestException as e:
        assert False, f"Request to verify valid JWT token failed: {e}"

    # Step 3: Tamper the valid access token (e.g., change a character)
    tampered_token = valid_access_token[:-1] + ("A" if valid_access_token[-1] != "A" else "B")
    verify_payload_tampered = {"token": tampered_token}
    try:
        verify_resp_tampered = requests.post(verify_url, json=verify_payload_tampered, headers=headers, timeout=TIMEOUT)
        assert verify_resp_tampered.status_code == 401, (
            f"Expected 401 Unauthorized for tampered token verify, got {verify_resp_tampered.status_code}"
        )
        # Do not strictly assert error message content, as it may be empty or absent
    except requests.RequestException as e:
        assert False, f"Request to verify tampered JWT token failed: {e}"

test_post_api_token_verify_verify_jwt_token_validity()
