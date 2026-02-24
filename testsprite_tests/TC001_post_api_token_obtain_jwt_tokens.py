import requests
from requests.exceptions import RequestException

BASE_URL = "http://127.0.0.1:8000"
TOKEN_ENDPOINT = "/api/token/"
TIMEOUT = 30

def test_post_api_token_obtain_jwt_tokens():
    url = BASE_URL + TOKEN_ENDPOINT
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    # Test valid credentials
    valid_payload = {
        "username": "superadmin",
        "password": "admin123"
    }
    try:
        valid_response = requests.post(url, json=valid_payload, headers=headers, timeout=TIMEOUT)
    except RequestException as e:
        assert False, f"Request with valid credentials failed: {e}"
    assert valid_response.status_code == 200, f"Expected status 200 for valid credentials, got {valid_response.status_code}"
    response_json = valid_response.json()
    assert "access" in response_json, "Response missing 'access' token for valid credentials"
    assert "refresh" in response_json, "Response missing 'refresh' token for valid credentials"
    assert isinstance(response_json["access"], str) and len(response_json["access"]) > 0, "'access' token is empty or not a string"
    assert isinstance(response_json["refresh"], str) and len(response_json["refresh"]) > 0, "'refresh' token is empty or not a string"
    
    # Test invalid credentials
    invalid_payload = {
        "username": "superadmin",
        "password": "wrongpassword123"
    }
    try:
        invalid_response = requests.post(url, json=invalid_payload, headers=headers, timeout=TIMEOUT)
    except RequestException as e:
        assert False, f"Request with invalid credentials failed: {e}"
    # Expect 401 Unauthorized with invalid credentials
    assert invalid_response.status_code == 401, f"Expected status 401 for invalid credentials, got {invalid_response.status_code}"
    invalid_response_text = invalid_response.text.lower()
    assert "invalid credentials" in invalid_response_text, "Invalid credentials response does not indicate 'Invalid credentials'"

test_post_api_token_obtain_jwt_tokens()
