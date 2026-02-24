import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost:8000/dashboard/dashboard"
AUTH = HTTPBasicAuth("boss", "Mm02022006")
HEADERS = {"Content-Type": "application/json"}
TIMEOUT = 30


def test_accounting_journal_entries_and_financial_reports():
    journal_entries_url = f"{BASE_URL}/accounting/journal-entries/"
    trial_balance_url = f"{BASE_URL}/accounting/trial-balance/"
    financial_statements_url = f"{BASE_URL}/accounting/financial-statements/"

    # Sample journal entry payload with double-entry bookkeeping
    journal_entry_payload = {
        "date": "2026-02-05",
        "reference": "UnitTest TC003 Entry",
        "description": "Testing double-entry journal entries",
        "items": [
            {
                "account": "1000",  # Assuming 1000 is Cash Account
                "debit": 1000.00,
                "credit": 0.00,
                "description": "Cash received"
            },
            {
                "account": "4000",  # Assuming 4000 is Revenue Account
                "debit": 0.00,
                "credit": 1000.00,
                "description": "Revenue earned"
            }
        ]
    }

    created_entry_id = None

    try:
        # Create a new journal entry
        resp_create = requests.post(
            journal_entries_url,
            auth=AUTH,
            headers=HEADERS,
            json=journal_entry_payload,
            timeout=TIMEOUT,
        )
        assert resp_create.status_code == 201, f"Create journal entry failed with {resp_create.status_code}: {resp_create.text}"
        created_entry = resp_create.json()
        assert "id" in created_entry, "Created journal entry response missing 'id'"
        created_entry_id = created_entry["id"]

        # Retrieve the created journal entry by its ID
        resp_get = requests.get(
            f"{journal_entries_url}{created_entry_id}/",
            auth=AUTH,
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        assert resp_get.status_code == 200, f"Get journal entry failed with {resp_get.status_code}: {resp_get.text}"
        journal_entry = resp_get.json()
        assert journal_entry["id"] == created_entry_id
        assert journal_entry["reference"] == journal_entry_payload["reference"]
        assert abs(float(sum(item["debit"] for item in journal_entry["items"])) - float(sum(item["credit"] for item in journal_entry["items"]))) < 0.01, "Journal entry items not balanced"

        # Test trial balance endpoint
        resp_trial_balance = requests.get(
            trial_balance_url,
            auth=AUTH,
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        assert resp_trial_balance.status_code == 200, f"Trial balance request failed with {resp_trial_balance.status_code}: {resp_trial_balance.text}"
        trial_balance_data = resp_trial_balance.json()
        assert isinstance(trial_balance_data, dict), "Trial balance response is not a JSON object"
        assert "balances" in trial_balance_data, "Trial balance response missing 'balances' key"

        # Test financial statements endpoint
        resp_fin_statements = requests.get(
            financial_statements_url,
            auth=AUTH,
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        assert resp_fin_statements.status_code == 200, f"Financial statements request failed with {resp_fin_statements.status_code}: {resp_fin_statements.text}"
        fin_statements_data = resp_fin_statements.json()
        assert isinstance(fin_statements_data, dict), "Financial statements response is not a JSON object"
        # Assuming expected keys usually in financial statements
        expected_keys = {"balance_sheet", "income_statement", "cash_flow"}
        assert expected_keys.intersection(fin_statements_data.keys()), "Financial statements response missing expected financial keys"
    finally:
        if created_entry_id is not None:
            # Attempt to delete the created journal entry to clean up
            try:
                requests.delete(
                    f"{journal_entries_url}{created_entry_id}/",
                    auth=AUTH,
                    headers=HEADERS,
                    timeout=TIMEOUT,
                )
            except Exception:
                pass


test_accounting_journal_entries_and_financial_reports()
