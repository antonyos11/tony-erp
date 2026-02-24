import requests

BASE_URL = "http://localhost:8000"
AUTH_URL = f"{BASE_URL}/api/token/"
JWT_USERNAME = "boss"
JWT_PASSWORD = "Mm02022006"
TIMEOUT = 30

def test_rest_api_jwt_authentication_and_swagger_documentation():
    # Step 1: Obtain JWT token with valid credentials
    auth_payload = {"username": JWT_USERNAME, "password": JWT_PASSWORD}
    try:
        auth_response = requests.post(AUTH_URL, json=auth_payload, timeout=TIMEOUT)
    except requests.RequestException as e:
        assert False, f"Auth request failed: {e}"
    assert auth_response.status_code == 200, f"Unexpected status code for auth: {auth_response.status_code}"
    try:
        auth_data = auth_response.json()
    except Exception as e:
        assert False, f"Auth response JSON decode failed: {e}"
    access_token = auth_data.get("access")
    refresh_token = auth_data.get("refresh")
    assert access_token, "Access token not found in auth response"
    assert refresh_token, "Refresh token not found in auth response"

    headers_auth = {"Authorization": f"Bearer {access_token}"}

    # Step 2: Verify access control: access a protected API endpoint with and without token
    protected_endpoints = [
        "/api/sales/customers/",      # sales API example
        "/api/inventory/products/",   # inventory API example
        "/api/accounting/chart-of-accounts/",  # accounting API example
    ]

    for endpoint in protected_endpoints:
        url = BASE_URL + endpoint
        # Without token - expect 401 or 403 or 404 (unauthorized/forbidden/not found)
        try:
            resp_no_auth = requests.get(url, timeout=TIMEOUT)
        except requests.RequestException as e:
            assert False, f"Request to {endpoint} without token failed: {e}"
        assert resp_no_auth.status_code in (401, 403, 404), (
            f"Expected 401/403/404 without token for {endpoint}, got {resp_no_auth.status_code}"
        )
        # With token - expect 200 OK or 204 No Content (if empty)
        try:
            resp_auth = requests.get(url, headers=headers_auth, timeout=TIMEOUT)
        except requests.RequestException as e:
            assert False, f"Request to {endpoint} with token failed: {e}"
        assert resp_auth.status_code == 200, (
            f"Expected 200 with token for {endpoint}, got {resp_auth.status_code}"
        )

    # Step 3: Check Swagger/OpenAPI documentation availability and correctness
    swagger_urls = [
        "/api/schema/",          # Default drf-spectacular OpenAPI schema endpoint
        "/swagger/",             # Swagger UI (if enabled)
        "/redoc/",               # Redoc UI (if enabled)
    ]

    for endpoint in swagger_urls:
        url = BASE_URL + endpoint
        try:
            resp = requests.get(url, timeout=TIMEOUT)
        except requests.RequestException as e:
            assert False, f"Swagger endpoint {endpoint} request failed: {e}"

        # The /api/schema/ returns JSON OpenAPI schema with application/json content-type
        if endpoint == "/api/schema/":
            assert resp.status_code == 200, f"OpenAPI schema endpoint status code: {resp.status_code}"
            content_type = resp.headers.get("Content-Type", "")
            assert "application/json" in content_type, f"Expected application/json content-type, got {content_type}"
            try:
                schema = resp.json()
            except Exception as e:
                assert False, f"Failed to decode OpenAPI JSON schema: {e}"
            # Basic checks on schema content
            assert schema.get("openapi", "").startswith("3"), "OpenAPI version is not 3.x in schema"
            assert "paths" in schema and isinstance(schema["paths"], dict), "OpenAPI schema missing 'paths' dict"
            # Spot check that authentication endpoints exist in paths
            token_path_found = any(
                path.startswith("/api/token") or path.startswith("api/token") for path in schema["paths"].keys()
            )
            assert token_path_found, "OpenAPI schema does not document /api/token endpoint"

        # For swagger UI and redoc, expect 200 and html content-type if enabled
        else:
            if resp.status_code == 404:
                # These UIs may not be enabled/configured, skip assertion on 404
                continue
            assert resp.status_code == 200, f"Swagger UI endpoint {endpoint} status: {resp.status_code}"
            content_type = resp.headers.get("Content-Type", "")
            assert "text/html" in content_type, f"Expected text/html content-type for {endpoint}, got: {content_type}"

    # Step 4: Check health check and admin panel accessibility basics

    # Health check: expected 200, no auth needed
    try:
        health_resp = requests.get(f"{BASE_URL}/health/live/", timeout=TIMEOUT)
    except requests.RequestException as e:
        assert False, f"Health check request failed: {e}"
    assert health_resp.status_code == 200, f"Health check failed with status: {health_resp.status_code}"

    # Admin panel: without auth expect redirect or 302, with auth may require session not JWT, so only check public access response status
    try:
        admin_resp = requests.get(f"{BASE_URL}/admin/", timeout=TIMEOUT)
    except requests.RequestException as e:
        assert False, f"Admin panel request failed: {e}"
    # Admin panel generally redirects to login if unauthorized
    assert admin_resp.status_code in (200, 302), f"Unexpected admin panel status code: {admin_resp.status_code}"


test_rest_api_jwt_authentication_and_swagger_documentation()
