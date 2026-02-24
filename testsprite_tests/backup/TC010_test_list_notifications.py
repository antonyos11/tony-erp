import requests

def get_jwt_token(username, password):
    """Helper function to obtain JWT access token"""
    base_url = "http://localhost:8000"
    url = f"{base_url}/api/token/"
    response = requests.post(url, json={"username": username, "password": password}, timeout=30)
    assert response.status_code == 200, f"Failed to obtain JWT token: {response.text}"
    data = response.json()
    access_token = data.get("access")
    assert access_token is not None, "Access token not found in response"
    return access_token

def test_list_notifications():
    base_url = "http://localhost:8000"
    notifications_endpoint = f"{base_url}/api/notifications/"  # Updated to REST API endpoint
    username = "boss"
    password = "Mm02022006"
    timeout = 30

    # Obtain JWT token
    access_token = get_jwt_token(username, password)
    headers = {"Authorization": f"Bearer {access_token}"}

    # Test 1: Basic GET request without query parameters
    try:
        response = requests.get(notifications_endpoint, headers=headers, timeout=timeout)
        response.raise_for_status()
        try:
            if not response.text.strip():
                # Empty response, allow if status code 204 or empty body
                data = None
            else:
                data = response.json()
        except requests.exceptions.JSONDecodeError:
            assert False, "Response is not valid JSON"

        if data is not None:
            assert isinstance(data, dict) or isinstance(data, list), "Response should be a dict or list"
            # Assuming notifications list is returned as a list or under a key
            # Check presence of notification items and pagination keys if any
            if isinstance(data, dict):
                # Check for pagination keys or results key
                has_pagination = any(k in data for k in ("count", "next", "previous", "results"))
                assert has_pagination, "Response dict should contain pagination keys like count, next, previous, or results"
                if "results" in data:
                    assert isinstance(data["results"], list), "'results' should be a list"
            elif isinstance(data, list):
                # List of notifications returned directly
                pass
    except requests.exceptions.RequestException as e:
        assert False, f"Request to list notifications failed: {e}"

    # Test 2: Test pagination with limit and offset (or page) parameters if supported
    # We'll try common pagination params for APIs: limit & offset or page
    pagination_params_sets = [
        {"limit": "5"},
        {"limit": "5", "offset": "0"},
        {"page": "1", "page_size": "5"},
        {"page": "1"}
    ]

    for params in pagination_params_sets:
        try:
            response = requests.get(notifications_endpoint, headers=headers, params=params, timeout=timeout)
            response.raise_for_status()
            try:
                if not response.text.strip():
                    page_data = None
                else:
                    page_data = response.json()
            except requests.exceptions.JSONDecodeError:
                assert False, f"Paginated response is not valid JSON for params {params}"

            if page_data is not None:
                assert isinstance(page_data, dict) or isinstance(page_data, list), "Paginated response should be dict or list"
                if isinstance(page_data, dict):
                    # Check pagination keys presence
                    has_pagination = any(k in page_data for k in ("count", "next", "previous", "results"))
                    assert has_pagination, f"Paginated response dict should contain pagination keys for params {params}"
                    if "results" in page_data:
                        assert isinstance(page_data["results"], list), "'results' should be a list in paginated response"
                        # Optionally, check that the number of results is not more than limit if specified
                        if "limit" in params:
                            assert len(page_data["results"]) <= int(params["limit"]), f"Number of results should not exceed limit {params['limit']}"
                elif isinstance(page_data, list):
                    # When list returned directly check size as per limit
                    if "limit" in params:
                        assert len(page_data) <= int(params["limit"])
        except requests.exceptions.RequestException as e:
            assert False, f"Pagination request failed with params {params}: {e}"

    # Test 3: Filtering notifications (if supported)
    # Since no filter keys specified in PRD, test with a dummy filter param to check for graceful handling
    filter_params = {"type": "real-time"}
    try:
        response = requests.get(notifications_endpoint, headers=headers, params=filter_params, timeout=timeout)
        if response.status_code == 400:
            # Acceptable if server rejects unknown filter param
            pass
        else:
            response.raise_for_status()
            try:
                if not response.text.strip():
                    filtered_data = None
                else:
                    filtered_data = response.json()
            except requests.exceptions.JSONDecodeError:
                assert False, "Filtered response is not valid JSON"
            # Should be dict or list, no error
            if filtered_data is not None:
                assert isinstance(filtered_data, dict) or isinstance(filtered_data, list)
    except requests.exceptions.RequestException as e:
        assert False, f"Filtering request failed: {e}"


test_list_notifications()
