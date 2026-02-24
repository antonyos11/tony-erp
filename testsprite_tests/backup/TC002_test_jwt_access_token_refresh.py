import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost:8000"
USERNAME = "boss"
PASSWORD = "Mm02022006"
TOKEN_ENDPOINT = "/api/token/"
REFRESH_ENDPOINT = "/api/token/refresh/"
TIMEOUT = 30

def test_jwt_access_token_refresh():
    try:
        # Step 1: Obtain initial token pair (access and refresh)
        auth_payload = {
            "username": USERNAME,
            "password": PASSWORD
        }
        auth_response = requests.post(
            BASE_URL + TOKEN_ENDPOINT,
            json=auth_payload,
            auth=HTTPBasicAuth(USERNAME, PASSWORD),
            timeout=TIMEOUT
        )
        assert auth_response.status_code == 200, f"Token obtain failed: {auth_response.text}"
        tokens = auth_response.json()
        assert "access" in tokens, "Access token not returned"
        assert "refresh" in tokens, "Refresh token not returned"
        refresh_token = tokens["refresh"]

        # Step 2: Use refresh token to get new access token
        refresh_payload = {
            "refresh": refresh_token
        }
        refresh_response = requests.post(
            BASE_URL + REFRESH_ENDPOINT,
            json=refresh_payload,
            auth=HTTPBasicAuth(USERNAME, PASSWORD),
            timeout=TIMEOUT
        )
        assert refresh_response.status_code == 200, f"Token refresh failed: {refresh_response.text}"
        refresh_data = refresh_response.json()
        assert "access" in refresh_data, "New access token not returned"
        new_access_token = refresh_data["access"]

        # The new access token should be different from the old one
        assert new_access_token != tokens["access"], "Refreshed access token is same as old access token"

    except requests.RequestException as e:
        assert False, f"HTTP request failed: {str(e)}"

test_jwt_access_token_refresh()