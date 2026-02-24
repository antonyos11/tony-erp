import requests

BASE_URL = "http://localhost:8000"
USERNAME = "boss"
PASSWORD = "Mm02022006"
TIMEOUT = 30

def test_jwt_token_refresh_api():
    # Step 1: Obtain JWT token pair with username and password
    auth_url = f"{BASE_URL}/api/token/"
    auth_payload = {"username": USERNAME, "password": PASSWORD}
    try:
        auth_response = requests.post(auth_url, json=auth_payload, timeout=TIMEOUT)
        assert auth_response.status_code == 200, f"Auth failed with status {auth_response.status_code} and body {auth_response.text}"
        tokens = auth_response.json()
        assert "access" in tokens and "refresh" in tokens, "Access or refresh token missing in auth response"
        refresh_token = tokens["refresh"]
    except requests.RequestException as e:
        assert False, f"Authentication request failed: {e}"

    # Step 2: Use refresh token to get new access token
    refresh_url = f"{BASE_URL}/api/token/refresh/"
    refresh_payload = {"refresh": refresh_token}
    headers = {"Authorization": f"Bearer {tokens['access']}"}
    try:
        refresh_response = requests.post(refresh_url, json=refresh_payload, headers=headers, timeout=TIMEOUT)
        assert refresh_response.status_code == 200, f"Token refresh failed with status {refresh_response.status_code} and body {refresh_response.text}"
        refresh_data = refresh_response.json()
        assert "access" in refresh_data, "New access token missing in refresh response"
        new_access_token = refresh_data["access"]
        assert isinstance(new_access_token, str) and len(new_access_token) > 0, "New access token invalid"
    except requests.RequestException as e:
        assert False, f"Refresh token request failed: {e}"

test_jwt_token_refresh_api()