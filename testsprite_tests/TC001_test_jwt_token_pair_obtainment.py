import requests
from requests.auth import HTTPBasicAuth

def test_jwt_token_pair_obtainment():
    base_url = "http://localhost:8000"
    url = f"{base_url}/api/token/"
    username = "boss"
    password = "Mm02022006"
    headers = {
        "Content-Type": "application/json",
    }
    payload = {
        "username": username,
        "password": password
    }
    try:
        response = requests.post(url, json=payload, headers=headers, auth=HTTPBasicAuth(username, password), timeout=30)
        # If server expects basic token for auth header, usually it's one or the other.
        # Here we use HTTPBasicAuth just to comply with the given authType instructions.
        # The payload carries the username and password per API doc.
    except requests.RequestException as e:
        assert False, f"Request failed: {e}"

    assert response.status_code == 200, f"Expected 200 OK but got {response.status_code}"
    try:
        data = response.json()
    except ValueError:
        assert False, "Response is not valid JSON."

    assert "access" in data, "Response JSON does not contain 'access' token."
    assert "refresh" in data, "Response JSON does not contain 'refresh' token."
    assert isinstance(data["access"], str) and data["access"], "'access' token is invalid."
    assert isinstance(data["refresh"], str) and data["refresh"], "'refresh' token is invalid."

test_jwt_token_pair_obtainment()