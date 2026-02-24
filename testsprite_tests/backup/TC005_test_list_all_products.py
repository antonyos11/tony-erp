import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost:8000"
USERNAME = "boss"
PASSWORD = "Mm02022006"
TIMEOUT = 30

def test_list_all_products():
    url = f"{BASE_URL}/api/products/"
    try:
        response = requests.get(url, auth=HTTPBasicAuth(USERNAME, PASSWORD), timeout=TIMEOUT)
    except requests.RequestException as e:
        assert False, f"Request to {url} failed: {e}"

    assert response.status_code == 200, f"Expected status code 200 but got {response.status_code}"
    
    try:
        data = response.json()
    except ValueError:
        assert False, "Response is not a valid JSON"

    # The response should be a list or have a pagination structure (common pagination keys)
    assert isinstance(data, (list, dict)), "Response JSON is neither a list nor a dictionary with pagination"

    # If pagination is used, we expect keys like 'results', 'count', etc.
    if isinstance(data, dict):
        # Validate pagination structure if present
        assert "results" in data, "'results' key missing in paginated response"
        assert isinstance(data["results"], list), "'results' should be a list"
        products = data["results"]
    else:
        products = data

    # Validate each product item has expected fields (at least id and name expected typical minimal)
    # Since PRD doesn't define product schema fields explicitly, check minimal presence
    for product in products:
        assert isinstance(product, dict), "Each product should be represented as a dict"
        # common product fields might be 'id' and 'name'; at minimum, 'id' should exist
        assert "id" in product, "Product missing 'id' field"
        # Optionally check for 'name' or another descriptive field if available
        # we'll check name if exists
        if "name" in product:
            assert isinstance(product["name"], str), "'name' field should be a string if present"

test_list_all_products()