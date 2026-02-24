import requests
from requests.exceptions import RequestException, Timeout

BASE_URL = "http://localhost:8000"
AUTH_URL = f"{BASE_URL}/api/token/"
USER_MANAGEMENT_API = f"{BASE_URL}/users/api/users/"

USERNAME = "boss"
PASSWORD = "Mm02022006"
TIMEOUT = 30

def get_jwt_token(username, password):
    try:
        response = requests.post(
            AUTH_URL,
            json={"username": username, "password": password},
            timeout=TIMEOUT
        )
        response.raise_for_status()
        token = response.json().get("access")
        assert token, "Access token not found in auth response"
        return token
    except (RequestException, AssertionError) as e:
        raise RuntimeError(f"Failed to get JWT token: {e}")

def test_validate_role_based_access_control_permissions():
    # 1. Authenticate and get JWT token for boss user (expected admin privileges)
    token = get_jwt_token(USERNAME, PASSWORD)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # 2. Verify that boss user can access user management list endpoint (role with permissions)
    try:
        r = requests.get(USER_MANAGEMENT_API, headers=headers, timeout=TIMEOUT)
        assert r.status_code == 200, f"Expected 200 OK for boss user, got {r.status_code}"
        users = r.json()
        assert isinstance(users, list), "Expected response to be a list of users"
    except Exception as e:
        raise AssertionError(f"Boss user should have access to user list: {e}")

    # 3. Attempt to create a user as boss (assuming boss role can create users)
    new_user_payload = {
        "username": "test_role_user",
        "password": "TestPass123!",
        "email": "test_role_user@example.com",
        "first_name": "Test",
        "last_name": "RoleUser",
        "is_active": True,
        "groups": []  # Assuming groups controls role assignment
    }
    created_user_id = None
    try:
        create_resp = requests.post(
            USER_MANAGEMENT_API,
            headers=headers,
            json=new_user_payload,
            timeout=TIMEOUT
        )
        assert create_resp.status_code in (201, 200), f"Expected user creation success, got {create_resp.status_code}"
        created_user = create_resp.json()
        created_user_id = created_user.get("id")
        assert created_user_id, "Created user ID not found"

        # 4. Test access with a less privileged user token - create user with limited permissions role
        # Here, simulate limited user by obtaining a token for a user with restricted role
        # For this test, we must attempt authentication as limited user and test access denial

        # Simulating limited user auth (assuming a limited user exists: 'limiteduser'/'LimitedPass1')
        limited_username = "limiteduser"
        limited_password = "LimitedPass1"

        try:
            limited_token = get_jwt_token(limited_username, limited_password)
        except RuntimeError:
            # Limited user does not exist or can't authenticate; skip this part
            limited_token = None

        if limited_token:
            limited_headers = {
                "Authorization": f"Bearer {limited_token}",
                "Content-Type": "application/json"
            }
            # Test limited user GET access (should be forbidden or limited)
            limited_get_resp = requests.get(USER_MANAGEMENT_API, headers=limited_headers, timeout=TIMEOUT)
            # Assuming role-based access denies access to user list with 403 or 401
            assert limited_get_resp.status_code in (401, 403), \
                f"Limited user should NOT have access to user list, got {limited_get_resp.status_code}"

            # Test limited user attempting to create user (should be forbidden)
            limited_post_resp = requests.post(
                USER_MANAGEMENT_API,
                headers=limited_headers,
                json=new_user_payload,
                timeout=TIMEOUT,
            )
            assert limited_post_resp.status_code in (401, 403), \
                f"Limited user should NOT be allowed to create user, got {limited_post_resp.status_code}"

    finally:
        # Cleanup: delete the created user if created
        if created_user_id:
            try:
                del_resp = requests.delete(
                    f"{USER_MANAGEMENT_API}{created_user_id}/",
                    headers=headers,
                    timeout=TIMEOUT
                )
                assert del_resp.status_code in (204, 200), f"Failed to delete test user, got {del_resp.status_code}"
            except Exception as ex:
                print(f"Warning: could not delete test user id {created_user_id}: {ex}")

test_validate_role_based_access_control_permissions()