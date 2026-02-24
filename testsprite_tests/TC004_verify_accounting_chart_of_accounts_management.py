import requests
import json

BASE_URL = "http://127.0.0.1:8000"
AUTH_URL = f"{BASE_URL}/api/token/"
ACCOUNTS_SEARCH_URL = f"{BASE_URL}/api/accounting/accounts/search/"
ACCOUNTS_IMPORT_URL = f"{BASE_URL}/api/accounting/accounts/import/"
ACCOUNTS_EXPORT_URL = f"{BASE_URL}/api/accounting/accounts/export/"
ACCOUNTS_URL = f"{BASE_URL}/api/accounting/accounts/"

USERNAME = "boss"
PASSWORD = "Mm02022006"


def get_jwt_token():
    auth_payload = {"username": USERNAME, "password": PASSWORD}
    resp = requests.post(AUTH_URL, json=auth_payload, timeout=30)
    resp.raise_for_status()
    token = resp.json().get("access")
    assert token, "Authentication failed, no access token received"
    return token


def test_verify_accounting_chart_of_accounts_management():
    token = get_jwt_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Step 1: Create a new account (POST)
    # Using a minimal valid payload for account creation assuming type, code, name are required
    create_payload = {
        "code": "9999",
        "name": "Test Account Root",
        "type": "assets",
        "parent": None
    }
    try:
        create_resp = requests.post(ACCOUNTS_URL, json=create_payload, headers=headers, timeout=30)
        assert create_resp.status_code == 201, f"Account creation failed: {create_resp.text}"
        created_account = create_resp.json()
        account_id = created_account.get("id")
        assert account_id, "Created account does not have an ID"

        # Step 2: Update the created account (PUT)
        update_payload = {
            "code": "9999",
            "name": "Test Account Root Updated",
            "type": "assets",
            "parent": None
        }
        update_resp = requests.put(f"{ACCOUNTS_URL}{account_id}/", json=update_payload, headers=headers, timeout=30)
        assert update_resp.status_code == 200, f"Account update failed: {update_resp.text}"
        updated_account = update_resp.json()
        assert updated_account.get("name") == "Test Account Root Updated", "Account name update did not persist"

        # Step 3: Create a child account to verify hierarchical structure
        child_payload = {
            "code": "999901",
            "name": "Test Child Account",
            "type": "assets",
            "parent": account_id
        }
        create_child_resp = requests.post(ACCOUNTS_URL, json=child_payload, headers=headers, timeout=30)
        assert create_child_resp.status_code == 201, f"Child account creation failed: {create_child_resp.text}"
        child_account = create_child_resp.json()
        child_id = child_account.get("id")
        assert child_id, "Created child account does not have an ID"
        assert child_account.get("parent") == account_id, "Child account parent relationship not set correctly"

        # Step 4: Search accounts and verify our created ones are in the list
        search_resp = requests.get(ACCOUNTS_SEARCH_URL, headers=headers, timeout=30)
        assert search_resp.status_code == 200, f"Accounts search failed: {search_resp.text}"
        accounts = search_resp.json()
        found_account = any(acc.get("id") == account_id for acc in (accounts if isinstance(accounts, list) else accounts.get("results", [])))
        found_child = any(acc.get("id") == child_id for acc in (accounts if isinstance(accounts, list) else accounts.get("results", [])))
        assert found_account, "Created account not found in search results"
        assert found_child, "Created child account not found in search results"

        # Step 5: Export accounts CSV/Excel (assuming GET with proper Accept or extension)
        export_resp = requests.get(ACCOUNTS_EXPORT_URL, headers=headers, timeout=30)
        # Expect 200 or 204 for export; content should be CSV or Excel
        assert export_resp.status_code == 200, f"Accounts export failed: {export_resp.text}"
        content_type = export_resp.headers.get("Content-Type", "").lower()
        assert "csv" in content_type or "excel" in content_type or "spreadsheet" in content_type, "Export content type not CSV or Excel"

        # Step 6: Import accounts (POST) - testing upload with minimal valid data in CSV
        # Prepare a sample CSV payload as bytes for import (assuming import accepts file upload named 'file')
        # Because we cannot create an actual file, use multipart with file-like content:
        csv_content = "code,name,type,parent\n9998,Imported Account,assets,\n"
        files = {
            "file": ("import.csv", csv_content, "text/csv")
        }
        import_resp = requests.post(ACCOUNTS_IMPORT_URL, headers=headers, files=files, timeout=30)
        assert import_resp.status_code in (200, 201), f"Accounts import failed: {import_resp.text}"

    finally:
        # Cleanup: delete created child and parent accounts
        # Delete child account if created
        try:
            if 'child_id' in locals():
                del_child_resp = requests.delete(f"{ACCOUNTS_URL}{child_id}/", headers=headers, timeout=30)
                # Accept 204 No Content or 200 OK for delete success
                assert del_child_resp.status_code in (200, 204), f"Child account deletion failed: {del_child_resp.text}"
        except Exception:
            pass
        # Delete parent account
        try:
            if 'account_id' in locals():
                del_parent_resp = requests.delete(f"{ACCOUNTS_URL}{account_id}/", headers=headers, timeout=30)
                assert del_parent_resp.status_code in (200, 204), f"Parent account deletion failed: {del_parent_resp.text}"
        except Exception:
            pass


test_verify_accounting_chart_of_accounts_management()
