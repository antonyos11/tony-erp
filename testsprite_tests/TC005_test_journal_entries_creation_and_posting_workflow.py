import requests

BASE_URL = "http://127.0.0.1:8000"
AUTH_URL = f"{BASE_URL}/api/token/"
JOURNAL_ENTRIES_URL = f"{BASE_URL}/api/accounting/journal-entries/"
HEADERS = {"Content-Type": "application/json"}
TIMEOUT = 30

def get_jwt_token():
    auth_payload = {"username": "boss", "password": "Mm02022006"}
    resp = requests.post(AUTH_URL, json=auth_payload, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()["access"]

def test_journal_entries_creation_and_posting_workflow():
    token = get_jwt_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Helper function to create a journal entry (manual or automatic)
    def create_journal_entry(data):
        r = requests.post(JOURNAL_ENTRIES_URL, json=data, headers=headers, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()

    # Helper to update posting status of journal entry
    def update_journal_entry_status(entry_id, status):
        url = f"{JOURNAL_ENTRIES_URL}{entry_id}/"
        r = requests.patch(url, json={"posting_status": status}, headers=headers, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()

    # Helper to create reversal entry for a journal entry
    def create_reversal_entry(original_entry_id):
        url = f"{JOURNAL_ENTRIES_URL}{original_entry_id}/reverse/"
        r = requests.post(url, headers=headers, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()

    manual_entry_payload = {
        "date": "2026-02-12",
        "description": "Manual journal entry test",
        "lines": [
            {"account": 101, "debit": 1000.00, "credit": 0.00, "description": "Debit line"},
            {"account": 202, "debit": 0.00, "credit": 1000.00, "description": "Credit line"}
        ],
        "type": "manual",
        "posting_status": "draft"
    }

    automatic_entry_payload = {
        "date": "2026-02-12",
        "description": "Automatic journal entry test",
        "lines": [
            {"account": 303, "debit": 500.00, "credit": 0.00, "description": "Debit line"},
            {"account": 404, "debit": 0.00, "credit": 500.00, "description": "Credit line"}
        ],
        "type": "automatic",
        "posting_status": "draft"
    }

    created_entries = []
    try:
        # Create manual journal entry
        manual_entry = create_journal_entry(manual_entry_payload)
        created_entries.append(manual_entry["id"])
        assert manual_entry["posting_status"] == "draft"
        assert manual_entry["type"] == "manual"
        assert abs(sum(line.get("debit",0) for line in manual_entry["lines"]) - sum(line.get("credit",0) for line in manual_entry["lines"])) < 0.01

        # Post manual entry: draft -> approved -> posted
        approved_manual_entry = update_journal_entry_status(manual_entry["id"], "approved")
        assert approved_manual_entry["posting_status"] == "approved"
        posted_manual_entry = update_journal_entry_status(manual_entry["id"], "posted")
        assert posted_manual_entry["posting_status"] == "posted"

        # Create automatic journal entry
        automatic_entry = create_journal_entry(automatic_entry_payload)
        created_entries.append(automatic_entry["id"])
        assert automatic_entry["posting_status"] == "draft"
        assert automatic_entry["type"] == "automatic"
        assert abs(sum(line.get("debit",0) for line in automatic_entry["lines"]) - sum(line.get("credit",0) for line in automatic_entry["lines"])) < 0.01

        # Post automatic entry: draft -> approved -> posted
        approved_automatic_entry = update_journal_entry_status(automatic_entry["id"], "approved")
        assert approved_automatic_entry["posting_status"] == "approved"
        posted_automatic_entry = update_journal_entry_status(automatic_entry["id"], "posted")
        assert posted_automatic_entry["posting_status"] == "posted"

        # Create reversal entry for posted manual entry
        reversal_entry = create_reversal_entry(manual_entry["id"])
        created_entries.append(reversal_entry["id"])
        assert reversal_entry["type"] == "reversal"
        assert reversal_entry["posting_status"] == "draft"
        assert abs(sum(line.get("debit",0) for line in reversal_entry["lines"]) - sum(line.get("credit",0) for line in reversal_entry["lines"])) < 0.01

        # Post reversal entry
        approved_reversal = update_journal_entry_status(reversal_entry["id"], "approved")
        assert approved_reversal["posting_status"] == "approved"
        posted_reversal = update_journal_entry_status(reversal_entry["id"], "posted")
        assert posted_reversal["posting_status"] == "posted"

    finally:
        # Cleanup - delete created entries
        for entry_id in created_entries:
            try:
                url = f"{JOURNAL_ENTRIES_URL}{entry_id}/"
                requests.delete(url, headers=headers, timeout=TIMEOUT)
            except:
                pass

test_journal_entries_creation_and_posting_workflow()
