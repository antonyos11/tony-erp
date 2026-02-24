import requests
from requests.exceptions import RequestException, Timeout

BASE_URL = "http://127.0.0.1:8000"
AUTH_URL = f"{BASE_URL}/api/token/"
TIMEOUT = 30

# Endpoints to test with expected HTTP 200
ENDPOINTS_200 = [
    "/sales/api/invoices/",
    "/accounting/api/accounts/search/",
    "/dashboard-api/api/kpis/",
    "/dashboard-api/api/data/",
    "/core/api/dashboard/daily-profit/",
    "/health/live/",
    "/ecommerce/api/products/",
    "/pos/api/orders/",
    "/attendance/api/my-records/",
    "/inventory/api/notifications/",
    "/inventory/api/barcode/lookup/",
    "/production/api/analytics/kpis/",
    "/smart-pricing/api/alerts/",
]

# Endpoints that may redirect (302) for admin only views - we will test 302 or 200 as acceptable
ENDPOINTS_MAY_302 = [
    # No explicit admin-only list given, assuming none outside above; if needed - add here
]

SWAGGER_URLS = [
    "/api/schema/",  # Standard drf-spectacular schema endpoint
    "/api/schema/swagger-ui/",  # swagger-ui page
    "/api/schema/redoc/",        # redoc page
]

def test_rest_api_authentication_and_swagger_documentation():
    try:
        # Step 1: Authenticate to get JWT access token
        auth_payload = {
            "username": "boss",
            "password": "Mm02022006"
        }
        auth_resp = requests.post(AUTH_URL, json=auth_payload, timeout=TIMEOUT)
        assert auth_resp.status_code == 200, f"Auth failed with status {auth_resp.status_code}"
        auth_data = auth_resp.json()
        assert "access" in auth_data, "Auth response missing 'access' token"
        access_token = auth_data["access"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Step 2: Access all listed endpoints with auth and expect 200 or proper response
        for endpoint in ENDPOINTS_200:
            url = BASE_URL + endpoint
            try:
                r = requests.get(url, headers=headers, timeout=TIMEOUT, allow_redirects=False)
            except Timeout:
                assert False, f"Timeout while accessing {url}"
            except RequestException as e:
                assert False, f"RequestException for {url}: {str(e)}"
            # Accept 200 or (if admin-restricted and not auth, 302)  but these endpoints are confirmed 200
            assert r.status_code == 200, f"Expected 200 at {url}, got {r.status_code}"

        # Step 3: Swagger documentation endpoints - no auth required usually, but test both with and without token
        # Check without auth
        for swagger_url in SWAGGER_URLS:
            url = BASE_URL + swagger_url
            try:
                r = requests.get(url, timeout=TIMEOUT)
                assert r.status_code in (200, 301, 302), f"Swagger URL {url} expected 200/301/302, got {r.status_code}"
                # Basic content check for swagger-ui and schema
                if swagger_url == "/api/schema/":
                    # Should return JSON OpenAPI schema
                    try:
                        json_data = r.json()
                        assert "openapi" in json_data or "swagger" in json_data, f"{url} does not contain OpenAPI schema"
                    except Exception as e:
                        assert False, f"{url} response is not valid JSON OpenAPI schema: {e}"
                else:
                    # swagger-ui or redoc pages should contain html text
                    text_lower = r.text.lower()
                    assert ("swagger" in text_lower or "redoc" in text_lower), f"{url} content does not look like swagger/redoc UI"
            except Timeout:
                assert False, f"Timeout while accessing {url} Swagger docs without auth"
            except RequestException as e:
                assert False, f"RequestException for Swagger URL {url} without auth: {str(e)}"

        # Check swagger endpoints also with auth headers if needed (some setups restrict docs otherwise)
        for swagger_url in SWAGGER_URLS:
            url = BASE_URL + swagger_url
            try:
                r = requests.get(url, headers=headers, timeout=TIMEOUT)
                assert r.status_code in (200, 301, 302), f"Swagger URL with auth {url} expected 200/301/302, got {r.status_code}"
            except Timeout:
                assert False, f"Timeout while accessing {url} Swagger docs with auth"
            except RequestException as e:
                assert False, f"RequestException for Swagger URL {url} with auth: {str(e)}"

    except AssertionError:
        raise
    except Exception as ex:
        assert False, f"Unexpected exception during test: {ex}"

test_rest_api_authentication_and_swagger_documentation()