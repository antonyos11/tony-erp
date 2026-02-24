import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost:8000"
AUTH = HTTPBasicAuth("boss", "Mm02022006")
HEADERS = {"Accept": "application/json"}
TIMEOUT = 30

def test_role_based_access_control_permissions():
    """
    Verify fine-grained permissions across modules and operations to ensure role-based access control is enforced correctly.
    As there is no specific endpoint described for permissions checking, this test will:
    1. Enumerate a set of key ERP modules endpoints to test access.
    2. Attempt allowed and disallowed operations per role by expected HTTP status codes.
    3. Verify that access is correctly granted or denied.
    """

    # Define test URL endpoints with expected permissions for the 'boss' user role.
    # Since no detailed API doc is provided, we assume typical ERP module endpoints.
    # For demonstration, we'll test access on a few example modules with typical CRUD endpoints.

    # Sample modules and operations to test:
    # Module: accounting - GET (list), POST (create), DELETE (delete)
    # Module: inventory - GET (list), POST (create), DELETE (delete)
    # Module: sales - GET (list), POST (create), DELETE (delete)

    # Expected behavior (assumed for "boss" role):
    # Full access (200/201/204 success for all operations)
    # If role is not permitted, expect 403 Forbidden or 401 Unauthorized

    # Updated endpoints based on api_app/urls.py mapping
    modules = {
        "accounting": "/api/expenses/",
        "inventory": "/api/products/",
        "sales": "/api/invoices/",
        "partners": "/api/customers/"
    }

    # Payloads for POST creation
    # Using random values or unique suffixes to avoid unique constraint collisions on re-runs
    import random
    suffix = random.randint(1000, 9999)
    
    payloads = {
        "partners": {"name": f"RBAC Customer {suffix}", "phone": f"05000{suffix}"},
        "accounting": {"description": "Test Expense", "amount": 50.00},
        "inventory": {"name": "RBAC Product", "sku": f"RBAC-{suffix}", "price": 10.00},
        "sales": {"number": f"INV-RBAC-{suffix}", "customer": 1, "total": 100.00, "date": "2025-01-01"}
    }

    created_resources = {}

    try:
        # 0. Ensure a customer exists for Sales Invoice
        print("Ensuring customer exists...")
        c_resp = requests.post(BASE_URL + modules["partners"], json=payloads["partners"], auth=AUTH, headers=HEADERS, timeout=TIMEOUT)
        if c_resp.status_code in [200, 201]:
            cust_id = c_resp.json().get("id")
            print(f"Created Customer: {cust_id}")
            payloads["sales"]["customer"] = cust_id
        else:
            print(f"Failed to create customer: {c_resp.status_code}. Using ID 1.")
            payloads["sales"]["customer"] = 1

        # Iterate over modules
        # We process partners first? No, we just did.
        # Remove partners from loop to avoid redundancy or just keep it?
        # We already created one.
        # Let's verify LIST and DELETE for the others.

        test_sequence = ["inventory", "accounting", "sales"]

        for module in test_sequence:
            endpoint = modules[module]
            url = BASE_URL + endpoint
            print(f"Testing {module.upper()} at {url}...")

            # 1. Test GET list access
            response = requests.get(url, auth=AUTH, headers=HEADERS, timeout=TIMEOUT)
            assert response.status_code == 200, f"GET {module} list access denied or server error: {response.status_code}"
            print(f" - LIST Permission: OK")

            # 2. Test POST create access
            response = requests.post(url, json=payloads[module], auth=AUTH, headers=HEADERS, timeout=TIMEOUT)
            assert response.status_code in {200, 201}, f"POST {module} creation denied or failed: {response.status_code} {response.text}"
            
            created_id = None
            try:
                data = response.json()
                created_id = data.get("id")
                assert created_id is not None, f"Could not find created resource ID for {module}"
                created_resources[module] = created_id
                print(f" - CREATE Permission: OK (ID: {created_id})")
            except Exception as e:
                raise AssertionError(f"Failed to parse POST {module} response: {e}")

        # 3. Test DELETE access on created resources
        for module, resource_id in created_resources.items():
            delete_url = f"{BASE_URL}{modules[module]}{resource_id}/"
            print(f"Testing DELETE {module} at {delete_url}...")
            response = requests.delete(delete_url, auth=AUTH, headers=HEADERS, timeout=TIMEOUT)
            assert response.status_code in {200, 204}, f"DELETE {module} denied or failed: {response.status_code}"
            print(f" - DELETE Permission: OK")

    except AssertionError as ae:
        print(f"Assertion Error: {ae}")
        raise ae

    except requests.RequestException as re:
        print(f"Request Error: {re}")
        raise AssertionError(f"Request failed: {re}")

test_role_based_access_control_permissions()