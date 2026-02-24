import requests

BASE_URL = "http://localhost:8000"
AUTH_URL = f"{BASE_URL}/api/token/"
BRANCHES_LIST_URL = f"{BASE_URL}/branches/api/list/"
USERNAME = "boss"
PASSWORD = "Mm02022006"
TIMEOUT = 30

def test_branches_list_api():
    # Step 1: Obtain JWT token
    try:
        auth_response = requests.post(
            AUTH_URL,
            json={"username": USERNAME, "password": PASSWORD},
            timeout=TIMEOUT
        )
        assert auth_response.status_code == 200, f"Auth failed with status {auth_response.status_code}"
        auth_json = auth_response.json()
        assert "access" in auth_json, "Access token missing in auth response"
        token = auth_json["access"]
    except requests.RequestException as e:
        raise AssertionError(f"Authentication request failed: {e}")

    headers = {
        "Authorization": f"Bearer {token}"
    }

    # Step 2: Call branches list endpoint
    try:
        response = requests.get(BRANCHES_LIST_URL, headers=headers, timeout=TIMEOUT)
    except requests.RequestException as e:
        raise AssertionError(f"Request to branches list API failed: {e}")

    assert response.status_code == 200, f"Branches list API returned status {response.status_code}"

    try:
        branches = response.json()
    except ValueError:
        raise AssertionError("Branches list API response is not valid JSON")

    # Validate that the response is a list (or an object containing list)
    assert isinstance(branches, (list, dict)), "Branches response is not a list or dict"

    # If response is dict, check for a key that holds list of branches (e.g., 'results' or 'branches')
    if isinstance(branches, dict):
        # common keys could be 'results', 'branches', or just validate keys
        possible_keys = ['results', 'branches', 'data']
        branch_list = None
        for key in possible_keys:
            if key in branches and isinstance(branches[key], list):
                branch_list = branches[key]
                break
        if branch_list is not None:
            branches = branch_list
        else:
            # response dict but no list found, accept if it's empty
            branches = []

    assert isinstance(branches, list), "Branches data is not a list after extraction"

    # Optionally check each branch has expected fields (like id, name)
    if branches:
        branch = branches[0]
        assert isinstance(branch, dict), "Branch item is not a dict"
        # We do not have exact schema, but for a branch typically includes 'id' and 'name'
        assert "id" in branch, "Branch item missing 'id' field"
        assert "name" in branch, "Branch item missing 'name' field"

test_branches_list_api()