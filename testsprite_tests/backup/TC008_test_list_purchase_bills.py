import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost:8000"
USERNAME = "boss"
PASSWORD = "Mm02022006"
TIMEOUT = 30

def test_list_purchase_bills():
    url = f"{BASE_URL}/api/purchases/"
    try:
        response = requests.get(url, auth=HTTPBasicAuth(USERNAME, PASSWORD), timeout=TIMEOUT)
        assert response.status_code == 200, f"Expected status code 200 but got {response.status_code}"
        json_data = response.json()
        assert isinstance(json_data, dict), "Response JSON is not a dictionary"
        assert 'results' in json_data, "Key 'results' not found in response JSON"
        results = json_data['results']
        assert isinstance(results, list), "Response JSON 'results' is not a list"
        if len(results) > 0:
            sample = results[0]
            assert isinstance(sample, dict), "Purchase bill item is not a dictionary"
            expected_keys = ['id', 'supplier', 'date']
            for key in expected_keys:
                assert key in sample, f"Expected key '{key}' not found in purchase bill item"
    except requests.RequestException as e:
        assert False, f"Request to {url} failed: {e}"
    except ValueError as e:
        assert False, f"Failed to decode JSON response: {e}"

test_list_purchase_bills()
