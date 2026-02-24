import requests

BASE_URL = "http://localhost:8000"
LOGIN_URL = f"{BASE_URL}/api/token/"
ACCOUNTING_API_PREFIX = "/accounting/api"
CHART_OF_ACCOUNTS_URL = f"{BASE_URL}{ACCOUNTING_API_PREFIX}/chart-of-accounts/"

USERNAME = "boss"
PASSWORD = "Mm02022006"
TIMEOUT = 30


def get_jwt_token():
    auth_data = {"username": USERNAME, "password": PASSWORD}
    response = requests.post(LOGIN_URL, json=auth_data, timeout=TIMEOUT)
    response.raise_for_status()
    tokens = response.json()
    assert "access" in tokens, "No access token in auth response"
    return tokens["access"]


def test_accounting_chart_of_accounts_management():
    token = get_jwt_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Sample payload to create a root account (Assets)
    root_account_data = {
        "name": "Assets",
        "code": "1000",
        "type": "assets",
        "parent": None,
        "description": "Root account for assets"
    }

    # Sample payload to create a child account under Assets
    child_account_data = {
        "name": "Cash",
        "code": "1010",
        "type": "assets",
        # parent id to be set after creating root account
        "description": "Cash account"
    }

    # Create root account
    root_id = None
    child_id = None
    try:
        resp_create_root = requests.post(CHART_OF_ACCOUNTS_URL, headers=headers, json=root_account_data, timeout=TIMEOUT)
        assert resp_create_root.status_code == 201, f"Failed to create root account, status {resp_create_root.status_code}"
        root_account = resp_create_root.json()
        root_id = root_account.get("id")
        assert root_id is not None, "Root account id missing from response"

        # Create child account with parent=root_id
        child_account_data["parent"] = root_id
        resp_create_child = requests.post(CHART_OF_ACCOUNTS_URL, headers=headers, json=child_account_data, timeout=TIMEOUT)
        assert resp_create_child.status_code == 201, f"Failed to create child account, status {resp_create_child.status_code}"
        child_account = resp_create_child.json()
        child_id = child_account.get("id")
        assert child_id is not None, "Child account id missing from response"
        assert child_account["parent"] == root_id, "Child account parent ID mismatch"

        # Retrieve both accounts, verify hierarchical structure
        resp_get_root = requests.get(f"{CHART_OF_ACCOUNTS_URL}{root_id}/", headers=headers, timeout=TIMEOUT)
        assert resp_get_root.status_code == 200, f"Failed to get root account, status {resp_get_root.status_code}"
        root_account_get = resp_get_root.json()
        assert root_account_get["id"] == root_id
        # The root account should reflect the child in some children field or confirmed by child parent mapping
        # Due to variability, also verify child parent
        resp_get_child = requests.get(f"{CHART_OF_ACCOUNTS_URL}{child_id}/", headers=headers, timeout=TIMEOUT)
        assert resp_get_child.status_code == 200, f"Failed to get child account, status {resp_get_child.status_code}"
        child_account_get = resp_get_child.json()
        assert child_account_get["parent"] == root_id

        # Update child account (e.g., rename)
        updated_name = "Cash on Hand"
        update_data = {"name": updated_name}
        resp_update_child = requests.patch(f"{CHART_OF_ACCOUNTS_URL}{child_id}/", headers=headers, json=update_data, timeout=TIMEOUT)
        assert resp_update_child.status_code == 200, f"Failed to update child account, status {resp_update_child.status_code}"
        updated_child = resp_update_child.json()
        assert updated_child["name"] == updated_name

        # Data validation: create account with duplicate code (should fail)
        dup_code_data = {
            "name": "Duplicate Code Account",
            "code": child_account_data["code"],  # same code "1010"
            "type": "assets",
            "parent": root_id,
            "description": "Should fail due to duplicate code"
        }
        resp_dup = requests.post(CHART_OF_ACCOUNTS_URL, headers=headers, json=dup_code_data, timeout=TIMEOUT)
        assert resp_dup.status_code in (400, 409), "Duplicate code creation did not fail as expected"

        # Data validation: create invalid account (missing required fields)
        invalid_data = {
            "name": "",
            "code": "",
            "type": "invalid_type",
        }
        resp_invalid = requests.post(CHART_OF_ACCOUNTS_URL, headers=headers, json=invalid_data, timeout=TIMEOUT)
        assert resp_invalid.status_code == 400, "Invalid account creation did not fail with 400"

    finally:
        # Cleanup created accounts if they exist
        if child_id:
            resp_del_child = requests.delete(f"{CHART_OF_ACCOUNTS_URL}{child_id}/", headers=headers, timeout=TIMEOUT)
            if resp_del_child.status_code not in (204, 200):
                print(f"Warning: Failed to delete child account {child_id}")
        if root_id:
            resp_del_root = requests.delete(f"{CHART_OF_ACCOUNTS_URL}{root_id}/", headers=headers, timeout=TIMEOUT)
            if resp_del_root.status_code not in (204, 200):
                print(f"Warning: Failed to delete root account {root_id}")


test_accounting_chart_of_accounts_management()