import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost:8000/api"
AUTH = HTTPBasicAuth("boss", "Mm02022006")
TIMEOUT = 30

def test_accounting_journal_entries_and_financial_reports():
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    # ✅ FIX: إزالة التكرار في المسار
    # ❌ الخطأ: BASE_URL = "http://localhost:8000/api" ثم يضيف /api/accounting/
    # ✅ الصحيح: استخدام المسار الصحيح مباشرة
    journal_entries_url = f"http://localhost:8000/accounting/api/journal-entries/"
    trial_balance_url = f"http://localhost:8000/accounting/api/trial-balance/"
    financial_statements_url = f"http://localhost:8000/accounting/api/financial-statements/"

    # Fetch account IDs for 'Cash' and 'Sales Revenue'
    accounts_url = f"http://localhost:8000/accounting/api/accounts/"
    response_accounts = requests.get(
        accounts_url,
        headers=headers,
        auth=AUTH,
        timeout=TIMEOUT
    )
    assert response_accounts.status_code == 200, f"Failed to get accounts: {response_accounts.status_code} {response_accounts.text}"
    accounts_list = response_accounts.json().get("results", [])

    # Find accounts by name
    def find_account_id(name):
        for account in accounts_list:
            if account.get("name", "").lower() == name.lower():
                return account.get("id")
        return None

    cash_account_id = find_account_id("Cash")
    sales_revenue_account_id = find_account_id("Sales Revenue")

    assert cash_account_id is not None, "Cash account not found in accounts list."
    assert sales_revenue_account_id is not None, "Sales Revenue account not found in accounts list."

    # Sample journal entry payload for double-entry bookkeeping
    journal_entry_payload = {
        "date": "2026-02-06",
        "description": "Test double-entry journal entry",
        "items": [
            {
                "account": cash_account_id,
                "debit": 1000,
                "credit": 0,
                "description": "Debit cash"
            },
            {
                "account": sales_revenue_account_id,
                "debit": 0,
                "credit": 1000,
                "description": "Credit sales revenue"
            }
        ]
    }

    created_entry_id = None
    try:
        # Create a new journal entry
        response = requests.post(
            journal_entries_url,
            json=journal_entry_payload,
            headers=headers,
            auth=AUTH,
            timeout=TIMEOUT
        )
        assert response.status_code == 201, f"Journal entry creation failed: {response.status_code} {response.text}"
        entry_data = response.json()
        created_entry_id = entry_data.get("id")
        assert created_entry_id is not None, "Created journal entry has no 'id'."

        # Retrieve the created journal entry
        get_entry_url = f"{journal_entries_url}{created_entry_id}/"
        response_get = requests.get(
            get_entry_url,
            headers=headers,
            auth=AUTH,
            timeout=TIMEOUT
        )
        assert response_get.status_code == 200, f"Failed to retrieve created journal entry: {response_get.status_code} {response_get.text}"
        retrieved_entry = response_get.json()
        assert retrieved_entry.get("id") == created_entry_id, "Retrieved journal entry id mismatch."
        assert retrieved_entry.get("description") == journal_entry_payload["description"], "Journal entry description mismatch."
        items = retrieved_entry.get("items", [])
        assert len(items) == 2, "Journal entry items length mismatch."
        # Validate debit and credit totals
        total_debit = sum(item.get("debit", 0) for item in items)
        total_credit = sum(item.get("credit", 0) for item in items)
        assert total_debit == total_credit, "Debits and credits are not balanced in journal entry."

        # Test trial balance endpoint
        response_trial = requests.get(
            trial_balance_url,
            headers=headers,
            auth=AUTH,
            timeout=TIMEOUT
        )
        assert response_trial.status_code == 200, f"Trial balance request failed: {response_trial.status_code} {response_trial.text}"
        trial_balance_data = response_trial.json()
        assert "accounts" in trial_balance_data, "Trial balance data missing 'accounts' key."
        # Basic check: The sum of all debit balances should equal sum of credit balances
        total_trial_debit = 0
        total_trial_credit = 0
        for account in trial_balance_data["accounts"]:
            total_trial_debit += float(account.get("debit", 0))
            total_trial_credit += float(account.get("credit", 0))
        assert abs(total_trial_debit - total_trial_credit) < 0.01, "Trial balance debits and credits do not match."

        # Test financial statements endpoint
        response_financial = requests.get(
            financial_statements_url,
            headers=headers,
            auth=AUTH,
            timeout=TIMEOUT
        )
        assert response_financial.status_code == 200, f"Financial statements request failed: {response_financial.status_code} {response_financial.text}"
        financial_data = response_financial.json()
        # Check presence of common financial statement keys
        assert "balance_sheet" in financial_data or "income_statement" in financial_data, "Financial statements data missing expected keys."

    finally:
        # Clean up: Delete the created journal entry if possible
        if created_entry_id:
            try:
                delete_url = f"{journal_entries_url}{created_entry_id}/"
                del_response = requests.delete(
                    delete_url,
                    headers=headers,
                    auth=AUTH,
                    timeout=TIMEOUT
                )
                assert del_response.status_code in (200, 204), f"Failed to delete journal entry: {del_response.status_code} {del_response.text}"
            except Exception as e:
                print(f"Cleanup failed: Could not delete journal entry ID {created_entry_id}: {e}")

test_accounting_journal_entries_and_financial_reports()
