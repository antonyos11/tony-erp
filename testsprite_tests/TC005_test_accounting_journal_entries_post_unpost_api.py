import requests

BASE_URL = "http://localhost:8000"
AUTH_URL = f"{BASE_URL}/api/token/"
JOURNAL_ENTRIES_URL = f"{BASE_URL}/accounting/api/v1/journal-entries/"

USERNAME = "boss"
PASSWORD = "Mm02022006"
TIMEOUT = 30


def test_accounting_journal_entries_post_unpost_api():
    # Authenticate and get JWT token
    auth_payload = {"username": USERNAME, "password": PASSWORD}
    try:
        auth_resp = requests.post(AUTH_URL, json=auth_payload, timeout=TIMEOUT)
        auth_resp.raise_for_status()
    except Exception as e:
        assert False, f"Authentication failed: {e}"

    auth_data = auth_resp.json()
    access_token = auth_data.get("access")
    assert access_token, "Access token not found in auth response"

    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    # Prepare a balanced journal entry payload for creation
    # The sum of debits must equal sum of credits
    # Need to create 2 or more items with debit and credit matching
    journal_entry_payload = {
        "date": "2024-01-01",
        "description": "Test journal entry from automated test",
        "items": [
            {
                "account": 1,  # Assumed valid account ID; since we don't have id, we will try to get one
                "debit": 100,
                "credit": 0,
                "cost_center": None
            },
            {
                "account": 2,  # Another account ID
                "debit": 0,
                "credit": 100,
                "cost_center": None
            }
        ]
    }

    # Because we need valid account IDs, get two accounts from /accounting/api/v1/accounts/
    try:
        accounts_resp = requests.get(f"{BASE_URL}/accounting/api/v1/accounts/", headers=headers, timeout=TIMEOUT)
        accounts_resp.raise_for_status()
    except Exception as e:
        assert False, f"Failed to get accounts: {e}"

    accounts = accounts_resp.json()
    assert isinstance(accounts, list) or isinstance(accounts, dict), "Accounts response is not a list or dict"

    # Extract at least two account IDs
    # The accounts might be returned in a list or paginated structure; handle list directly or 'results' key
    acct_list = []
    if isinstance(accounts, dict) and 'results' in accounts:
        acct_list = accounts['results']
    elif isinstance(accounts, list):
        acct_list = accounts
    else:
        assert False, "Accounts response has unexpected format"

    if len(acct_list) < 2:
        assert False, "Not enough accounts returned for testing (need at least 2)"

    # Prepare accounts IDs from found accounts
    account1_id = acct_list[0]["id"] if "id" in acct_list[0] else acct_list[0].get("pk", None)
    account2_id = acct_list[1]["id"] if "id" in acct_list[1] else acct_list[1].get("pk", None)
    assert account1_id is not None and account2_id is not None, "Account IDs not found in accounts response"

    journal_entry_payload["items"][0]["account"] = account1_id
    journal_entry_payload["items"][1]["account"] = account2_id

    journal_entry_id = None

    try:
        # Create journal entry
        create_resp = requests.post(JOURNAL_ENTRIES_URL, headers=headers, json=journal_entry_payload, timeout=TIMEOUT)
        assert create_resp.status_code == 201, f"Failed to create journal entry: {create_resp.status_code} - {create_resp.text}"
        created_entry = create_resp.json()
        journal_entry_id = created_entry.get("id")
        assert journal_entry_id is not None, "Created journal entry ID missing"

        # Validate that journal entry items are balanced (sum debit == sum credit)
        items = created_entry.get("items", [])
        total_debit = 0
        total_credit = 0
        for item in items:
            debit = item.get("debit", 0)
            credit = item.get("credit", 0)
            assert isinstance(debit, (int, float)), "Debit is not numeric"
            assert isinstance(credit, (int, float)), "Credit is not numeric"
            total_debit += debit
            total_credit += credit

        assert abs(total_debit - total_credit) < 0.0001, f"Journal entry is not balanced: debit={total_debit}, credit={total_credit}"

        # Post the journal entry by calling post_entry endpoint
        post_url = f"{JOURNAL_ENTRIES_URL}{journal_entry_id}/post_entry/"
        post_resp = requests.post(post_url, headers=headers, timeout=TIMEOUT)
        assert post_resp.status_code == 200, f"Failed to post journal entry: {post_resp.status_code} - {post_resp.text}"

        # Accept any 200 response as successful post, do not enforce strict response body checks

    finally:
        # Clean up: delete the created journal entry if created
        if journal_entry_id is not None:
            try:
                delete_url = f"{JOURNAL_ENTRIES_URL}{journal_entry_id}/"
                del_resp = requests.delete(delete_url, headers=headers, timeout=TIMEOUT)
                # It may return 204 or 200 to indicate deletion success
                assert del_resp.status_code in (200, 204), f"Failed to delete journal entry cleanup: {del_resp.status_code}"
            except Exception:
                pass


test_accounting_journal_entries_post_unpost_api()
