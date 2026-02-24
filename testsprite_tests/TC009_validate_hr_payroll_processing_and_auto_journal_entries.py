import requests
import json

BASE_URL = "http://127.0.0.1:8000"
AUTH_URL = f"{BASE_URL}/api/token/"
PAYROLL_CALC_URL = f"{BASE_URL}/hr/api/payrolls/calculate/"
PAYROLL_JOURNAL_URL = f"{BASE_URL}/hr/api/payroll/journal-entries/"
PAYSLIP_URL = f"{BASE_URL}/hr/api/payroll/payslips/"
BANK_EXPORT_URL = f"{BASE_URL}/hr/api/payroll/bank-file-export/"

USERNAME = "boss"
PASSWORD = "Mm02022006"
TIMEOUT = 30


def get_jwt_token():
    try:
        resp = requests.post(
            AUTH_URL,
            json={"username": USERNAME, "password": PASSWORD},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        token = resp.json().get("access")
        assert token, "No access token in auth response"
        return token
    except Exception as e:
        raise RuntimeError(f"Failed to authenticate: {str(e)}")


def test_validate_hr_payroll_processing_and_auto_journal_entries():
    token = get_jwt_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Step 1: Trigger automatic payroll calculation
    try:
        calc_payload = {
            # Payload data depends on API schema, assuming minimal or empty triggers calculation for all employees/pay period.
            # If required, add period or employee filters here.
        }
        resp_calc = requests.post(PAYROLL_CALC_URL, headers=headers, json=calc_payload, timeout=TIMEOUT)
        assert resp_calc.status_code == 200, f"Payroll calculation failed: {resp_calc.status_code} {resp_calc.text}"
        calc_data = resp_calc.json()
        assert "payroll_id" in calc_data or "calculation_result" in calc_data, "Payroll calculation response missing expected data"

        payroll_id = calc_data.get("payroll_id") or calc_data.get("calculation_result", {}).get("payroll_id")
        assert payroll_id, "Payroll ID not returned from calculation"

        # Step 2: Verify auto journal entries created for the payroll
        resp_journal = requests.get(f"{PAYROLL_JOURNAL_URL}?payroll_id={payroll_id}", headers=headers, timeout=TIMEOUT)
        assert resp_journal.status_code == 200, f"Failed to get payroll journal entries: {resp_journal.status_code} {resp_journal.text}"
        journal_entries = resp_journal.json()
        assert isinstance(journal_entries, list), "Journal entries response is not a list"
        assert len(journal_entries) > 0, "No journal entries found for payroll"

        # Check each journal entry balanced (debits == credits) if that info is in response
        for je in journal_entries:
            debit = je.get("debit_total")
            credit = je.get("credit_total")
            assert debit is not None and credit is not None, "Journal entry missing debit or credit totals"
            assert debit == credit, f"Journal entry not balanced: debit={debit}, credit={credit}"

        # Step 3: Generate pay slip for the payroll
        resp_payslip = requests.post(PAYSLIP_URL, headers=headers, json={"payroll_id": payroll_id}, timeout=TIMEOUT)
        assert resp_payslip.status_code == 200, f"Failed to generate pay slip: {resp_payslip.status_code} {resp_payslip.text}"
        payslip_data = resp_payslip.json()
        # Check for required payslip fields
        for field in ["employee", "pay_period", "gross_pay", "net_pay"]:
            assert field in payslip_data, f"Pay slip missing field: {field}"

        # Step 4: Export bank file for payroll payments
        resp_bank_export = requests.post(BANK_EXPORT_URL, headers=headers, json={"payroll_id": payroll_id}, timeout=TIMEOUT)
        assert resp_bank_export.status_code == 200, f"Failed bank file export: {resp_bank_export.status_code} {resp_bank_export.text}"

        # Bank file presumably returned as a downloadable file or file content in JSON
        content_type = resp_bank_export.headers.get("Content-Type", "")
        assert (
            "text/csv" in content_type or "application/octet-stream" in content_type or "application/json" in content_type
        ), f"Unexpected bank file export content-type: {content_type}"
        content = resp_bank_export.content
        assert len(content) > 0, "Bank file export returned empty content"

    except Exception as e:
        raise AssertionError(f"Test case TC009 failed: {str(e)}")


test_validate_hr_payroll_processing_and_auto_journal_entries()
