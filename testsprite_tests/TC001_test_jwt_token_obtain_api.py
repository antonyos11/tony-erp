import requests

BASE_URL = "http://localhost:8000"

def test_jwt_token_obtain_api():
    url = f"{BASE_URL}/api/token/"
    payload = {
        "username": "boss",
        "password": "Mm02022006"
    }
    headers = {
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        assert False, f"Request to obtain JWT token failed: {e}"
    data = response.json()
    assert "access" in data and isinstance(data["access"], str) and data["access"], "Access token missing or invalid"
    assert "refresh" in data and isinstance(data["refresh"], str) and data["refresh"], "Refresh token missing or invalid"

test_jwt_token_obtain_api()