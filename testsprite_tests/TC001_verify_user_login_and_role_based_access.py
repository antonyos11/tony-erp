import requests

BASE_URL = "http://localhost:8000"
USERNAME = "boss"
PASSWORD = "Mm02022006"
TIMEOUT = 30

def test_verify_user_login_and_role_based_access():
    try:
        # Step 1: Login with POST to get token
        login_url = f"{BASE_URL}/api/token/"
        payload = {"username": USERNAME, "password": PASSWORD}
        response = requests.post(login_url, json=payload, timeout=TIMEOUT)
        assert response.status_code == 200, f"Login failed with status code {response.status_code}. Response: {response.text}"
        auth_data = response.json()
        assert "access" in auth_data, f"Access token not found in login response. Keys found: {list(auth_data.keys())}"
        token = auth_data["access"]
        headers = {"Authorization": f"Bearer {token}"}

        # Step 2: Retrieve user info including roles and modules accessible
        user_info_url = f"{BASE_URL}/api/users/me/"
        response = requests.get(user_info_url, headers=headers, timeout=TIMEOUT)
        assert response.status_code == 200, f"User info retrieval failed with status code {response.status_code}"
        user_info = response.json()
        assert "username" in user_info and user_info["username"] == USERNAME, "Username mismatch"
        assert "roles" in user_info and isinstance(user_info["roles"], list) and len(user_info["roles"]) > 0, "No roles assigned"
        roles = user_info["roles"]

        # Step 3: For each role check the accessible modules
        modules_checked = False
        for role in roles:
            role_id = role.get("id") or role.get("role_id")
            assert role_id is not None, "Role ID not found"
            modules_url = f"{BASE_URL}/api/roles/{role_id}/modules/"
            response = requests.get(modules_url, headers=headers, timeout=TIMEOUT)
            assert response.status_code == 200, f"Failed to get modules for role {role_id}"
            modules = response.json()
            assert isinstance(modules, list), "Modules response is not a list"
            for module in modules:
                assert "name" in module, "Module missing 'name' field"
            modules_checked = True

        assert modules_checked, "No modules were checked for roles"

        # Optional Step 4: Attempt to access a restricted module not assigned and expect 403 Forbidden
        if user_info.get("is_superuser"):
            print("Skipping unauthorized access test for superuser")
            return

        all_modules_url = f"{BASE_URL}/api/modules/"
        response = requests.get(all_modules_url, headers=headers, timeout=TIMEOUT)
        assert response.status_code == 200, f"Failed to get all modules"
        all_modules = response.json()
        authorized_module_ids = set()
        for role in roles:
            role_id = role.get("id") or role.get("role_id")
            modules_url = f"{BASE_URL}/api/roles/{role_id}/modules/"
            resp = requests.get(modules_url, headers=headers, timeout=TIMEOUT)
            if resp.status_code == 200:
                for module in resp.json():
                    module_id = module.get("id")
                    if module_id:
                        authorized_module_ids.add(module_id)
        unauthorized_module = None
        for module in all_modules:
            if "id" in module and module["id"] not in authorized_module_ids:
                unauthorized_module = module
                break
        if unauthorized_module:
            unauthorized_module_url = f"{BASE_URL}/api/modules/{unauthorized_module['id']}/"
            resp = requests.get(unauthorized_module_url, headers=headers, timeout=TIMEOUT)
            assert resp.status_code in (401, 403), f"Unauthorized access to module {unauthorized_module['id']} not blocked"
    except requests.RequestException as e:
        assert False, f"HTTP request failed: {e}"
    except AssertionError as e:
        assert False, str(e)

test_verify_user_login_and_role_based_access()
