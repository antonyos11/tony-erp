import requests

BASE_URL = "http://localhost:8000"
AUTH_URL = f"{BASE_URL}/api/token/"
SEARCH_ENDPOINT = f"{BASE_URL}/sales/api/customers/search/"
AUTH_CREDENTIALS = {"username": "boss", "password": "Mm02022006"}
TIMEOUT = 30

def test_sales_customers_search_api():
    # Obtain JWT token
    try:
        auth_resp = requests.post(AUTH_URL, json=AUTH_CREDENTIALS, timeout=TIMEOUT)
        auth_resp.raise_for_status()
        tokens = auth_resp.json()
        access_token = tokens.get("access")
        assert access_token, "Access token not found in auth response"
    except requests.RequestException as e:
        raise AssertionError(f"Authentication failed: {e}")

    headers = {"Authorization": f"Bearer {access_token}"}

    # Define queries to test for each type: name, phone, and all
    queries = [
        {"q": "John", "type": "name"},     # Example search by name
        {"q": "5551234", "type": "phone"}, # Example search by phone
        {"q": "Smith", "type": "all"},     # Example search by all types
    ]

    for query_params in queries:
        try:
            resp = requests.get(SEARCH_ENDPOINT, headers=headers, params=query_params, timeout=TIMEOUT)
            resp.raise_for_status()
        except requests.RequestException as e:
            raise AssertionError(f"GET request failed for params {query_params}: {e}")

        data = resp.json()
        assert isinstance(data, dict), f"Expected dict response for params {query_params}"
        # Try to get the list of customers from common keys
        customers = None
        for key in ['results', 'customers', 'data', 'items']:
            if key in data and isinstance(data[key], list):
                customers = data[key]
                break
        if customers is None:
            # If none of common keys found, and the dict is list-like (rare), try values
            if isinstance(data, list):
                customers = data
            else:
                raise AssertionError(f"No customer list found in response for params {query_params}")

        assert isinstance(customers, list), f"Expected list of customers in response under recognized key for params {query_params}"

        # Validate that each returned customer matches the search query roughly by key
        for customer in customers:
            assert isinstance(customer, dict), "Each customer should be a dictionary"
            # Minimal keys check: expecting at least "name" or "phone"
            has_name = "name" in customer and isinstance(customer["name"], str)
            has_phone = "phone" in customer and isinstance(customer["phone"], str)
            assert has_name or has_phone, "Customer missing required 'name' or 'phone' fields"

            q_lower = query_params["q"].lower()
            search_type = query_params["type"]

            if search_type == "name":
                assert has_name and q_lower in customer["name"].lower(), (
                    f"Customer name does not match search query '{query_params['q']}': {customer}"
                )
            elif search_type == "phone":
                assert has_phone and q_lower in customer["phone"].lower(), (
                    f"Customer phone does not match search query '{query_params['q']}': {customer}"
                )
            else:  # type == "all"
                match = False
                if has_name and q_lower in customer["name"].lower():
                    match = True
                if not match and has_phone and q_lower in customer["phone"].lower():
                    match = True
                assert match, (
                    f"Customer does not match search query '{query_params['q']}' for type 'all': {customer}"
                )

test_sales_customers_search_api()
