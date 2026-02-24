import requests
import time

BASE_URL = "http://127.0.0.1:8000"
TOKEN_URL = f"{BASE_URL}/api/token/"
REFRESH_URL = f"{BASE_URL}/api/token/refresh/"
TIMEOUT = 30


def test_post_api_token_refresh_refresh_jwt_access_token():
    # Step 1: Obtain valid JWT tokens using correct credentials
    auth_data = {"username": "superadmin", "password": "admin123"}
    try:
        resp = requests.post(TOKEN_URL, json=auth_data, timeout=TIMEOUT)
    except requests.RequestException as e:
        assert False, f"Exception during obtaining token: {e}"
    assert resp.status_code == 200, f"Expected 200 on token obtain but got {resp.status_code}"
    tokens = resp.json()
    assert "access" in tokens and "refresh" in tokens, "Token response missing access or refresh token"
    refresh_token = tokens["refresh"]

    # Step 2: Use valid refresh token to request new access token (success case)
    refresh_payload = {"refresh": refresh_token}
    try:
        resp_refresh = requests.post(REFRESH_URL, json=refresh_payload, timeout=TIMEOUT)
    except requests.RequestException as e:
        assert False, f"Exception during refreshing token: {e}"
    assert resp_refresh.status_code == 200, f"Expected 200 on token refresh with valid token but got {resp_refresh.status_code}"
    refresh_resp_json = resp_refresh.json()
    assert "access" in refresh_resp_json and isinstance(refresh_resp_json["access"], str) and refresh_resp_json["access"], "Refresh response missing or invalid access token"

    time.sleep(0.2)  # delay between requests to respect rate limits

    # Step 3: Use invalid refresh token to check proper error handling (error case)
    invalid_refresh_payload = {"refresh": refresh_token[:-5] + "abcde"}  # tampered token, invalid refresh
    try:
        resp_invalid = requests.post(REFRESH_URL, json=invalid_refresh_payload, timeout=TIMEOUT)
    except requests.RequestException as e:
        assert False, f"Exception during refreshing token with invalid token: {e}"

    # According to PRD: POST /api/token/refresh/ with invalid refresh token -> response 401 (implied)
    assert resp_invalid.status_code == 401, f"Expected 401 on token refresh with invalid token but got {resp_invalid.status_code}"

    # Optionally validate error message presence
    error_json = {}
    try:
        error_json = resp_invalid.json()
    except Exception:
        pass
    assert isinstance(error_json, dict), "Error response is not a JSON object"

test_post_api_token_refresh_refresh_jwt_access_token()