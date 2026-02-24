import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost:8000/dashboard/dashboard"
AUTH = HTTPBasicAuth("boss", "Mm02022006")
HEADERS = {"Content-Type": "application/json"}
TIMEOUT = 30


def test_hr_employee_attendance_and_payroll_processing():
    employee_url = f"{BASE_URL}/hr/employees/"
    attendance_url = f"{BASE_URL}/hr/attendance/"
    leave_request_url = f"{BASE_URL}/hr/leave-requests/"
    payroll_url = f"{BASE_URL}/hr/payroll/"

    employee_id = None
    attendance_id = None
    leave_request_id = None
    payroll_id = None

    try:
        # 1. Create an employee
        employee_payload = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "department": "HR",
            "position": "Developer"
        }
        resp = requests.post(employee_url, auth=AUTH, headers=HEADERS, json=employee_payload, timeout=TIMEOUT)
        assert resp.status_code == 201, f"Create employee failed: {repr(resp.text)}"
        employee_data = resp.json()
        employee_id = employee_data.get("id")
        assert employee_id, "No employee ID returned."

        # 2. Record attendance for the employee (check-in)
        attendance_payload = {
            "employee": employee_id,
            "date": "2024-06-01",
            "check_in_time": "08:00:00",
            "check_out_time": "17:00:00",
            "status": "Present"
        }
        resp = requests.post(attendance_url, auth=AUTH, headers=HEADERS, json=attendance_payload, timeout=TIMEOUT)
        assert resp.status_code == 201, f"Create attendance record failed: {repr(resp.text)}"
        attendance_data = resp.json()
        attendance_id = attendance_data.get("id")
        assert attendance_id, "No attendance ID returned."
        assert attendance_data.get("employee") == employee_id, "Attendance record employee mismatch."

        # 3. Create a leave request for the employee
        leave_payload = {
            "employee": employee_id,
            "start_date": "2024-06-10",
            "end_date": "2024-06-12",
            "leave_type": "Annual Leave",
            "reason": "Family event",
            "status": "Pending"
        }
        resp = requests.post(leave_request_url, auth=AUTH, headers=HEADERS, json=leave_payload, timeout=TIMEOUT)
        assert resp.status_code == 201, f"Create leave request failed: {repr(resp.text)}"
        leave_data = resp.json()
        leave_request_id = leave_data.get("id")
        assert leave_request_id, "No leave request ID returned."
        assert leave_data.get("employee") == employee_id, "Leave request employee mismatch."
        assert leave_data.get("status") == "Pending", "Leave request status mismatch."

        # 4. Trigger payroll calculation for the employee (usually POST or GET)
        payroll_payload = {
            "employee": employee_id,
            "month": "2024-06"
        }
        resp = requests.post(payroll_url, auth=AUTH, headers=HEADERS, json=payroll_payload, timeout=TIMEOUT)
        assert resp.status_code in (200, 201), f"Payroll calculation failed: {repr(resp.text)}"
        payroll_data = resp.json()
        payroll_id = payroll_data.get("id")
        assert payroll_id, "No payroll ID returned."
        assert payroll_data.get("employee") == employee_id, "Payroll employee mismatch."
        assert "total_pay" in payroll_data, "Payroll total_pay missing."

        # 5. Verify bank export file generation (assuming an export endpoint or field)
        # If the API returns a URL or file content for bank export, validate existence
        bank_export = payroll_data.get("bank_export_file") or payroll_data.get("bank_export_url")
        assert bank_export, "Bank export file/URL missing from payroll data."

        # Optionally, verify that the bank export file endpoint is accessible (if a URL)
        if isinstance(bank_export, str) and bank_export.startswith("http"):
            resp = requests.get(bank_export, auth=AUTH, timeout=TIMEOUT)
            assert resp.status_code == 200, f"Bank export file not accessible: {bank_export}"

    finally:
        # Cleanup leave request
        if leave_request_id:
            try:
                delete_url = f"{leave_request_url}{leave_request_id}/"
                resp = requests.delete(delete_url, auth=AUTH, timeout=TIMEOUT)
                assert resp.status_code in (204, 200), "Failed to delete leave request."
            except Exception:
                pass

        # Cleanup attendance record
        if attendance_id:
            try:
                delete_url = f"{attendance_url}{attendance_id}/"
                resp = requests.delete(delete_url, auth=AUTH, timeout=TIMEOUT)
                assert resp.status_code in (204, 200), "Failed to delete attendance record."
            except Exception:
                pass

        # Cleanup payroll record
        if payroll_id:
            try:
                delete_url = f"{payroll_url}{payroll_id}/"
                resp = requests.delete(delete_url, auth=AUTH, timeout=TIMEOUT)
                assert resp.status_code in (204, 200), "Failed to delete payroll record."
            except Exception:
                pass

        # Cleanup employee
        if employee_id:
            try:
                delete_url = f"{employee_url}{employee_id}/"
                resp = requests.delete(delete_url, auth=AUTH, timeout=TIMEOUT)
                assert resp.status_code in (204, 200), "Failed to delete employee."
            except Exception:
                pass


test_hr_employee_attendance_and_payroll_processing()
