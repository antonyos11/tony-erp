import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

# Function to obtain JWT token

def get_jwt_token(username, password):
    url = f"{BASE_URL}/api/token/"
    response = requests.post(url, json={"username": username, "password": password}, timeout=TIMEOUT)
    assert response.status_code == 200, f"Failed to obtain JWT token: {response.text}"
    data = response.json()
    access_token = data.get("access")
    assert access_token is not None, "Access token not found in response"
    return access_token


def test_list_branches():
    username = "boss"
    password = "Mm02022006"
    access_token = get_jwt_token(username, password)

    branches_url = f"{BASE_URL}/api/branches/"  # Updated to REST API endpoint
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"}

    # Define sample data for creating a new branch
    create_payload = {
        "code": "TEST-BR-001",  # Required field
        "name": "Test Branch",
        "address": "123 Test St, Test City",
        "phone": "1234567890",
        "email": "testbranch@example.com"
        # Note: manager should be User ID, not string. Leaving it null for now.
    }

    created_branch_id = None
    try:
        # Step 1: Create a new branch
        create_resp = requests.post(branches_url, json=create_payload, headers=headers, timeout=TIMEOUT)
        assert create_resp.status_code == 201, f"Branch creation failed: {create_resp.text}"
        created_branch = create_resp.json()
        created_branch_id = created_branch.get("id") or created_branch.get("pk")
        assert created_branch_id is not None, "Created branch ID not found in response"

        # Verify the returned data of the created branch matches input (at least for fields provided)
        for key in create_payload:
            assert key in created_branch, f"Key '{key}' missing in created branch data"
            # String fields: case insensitive comparison
            if isinstance(create_payload[key], str):
                assert create_payload[key].lower() == created_branch[key].lower()
            else:
                assert create_payload[key] == created_branch[key]

        # Step 2: List all branches
        list_resp = requests.get(branches_url, headers=headers, timeout=TIMEOUT)
        assert list_resp.status_code == 200, f"Failed to list branches: {list_resp.text}"
        branches_data = list_resp.json()
        
        # Handle both paginated and non-paginated responses
        if isinstance(branches_data, dict):
            branches_list = branches_data.get("results", [])
        else:
            branches_list = branches_data
        
        assert isinstance(branches_list, list), "Branches list is not a list"

        # Verify the created branch is included in the list
        branch_ids = {b.get("id") or b.get("pk") for b in branches_list}
        assert created_branch_id in branch_ids, "Created branch not found in list response"

        # Optionally verify required keys exist in each branch entry
        required_keys = {"id", "name"}
        for branch in branches_list:
            for key in required_keys:
                assert key in branch, f"Key '{key}' missing in branch item"

    finally:
        # Cleanup: delete the created branch if it was created
        if created_branch_id:
            delete_url = f"{branches_url}{created_branch_id}/"
            del_resp = requests.delete(delete_url, headers=headers, timeout=TIMEOUT)
            assert del_resp.status_code in (204, 200, 202), f"Failed to delete test branch: {del_resp.text}"


test_list_branches()
