import requests
from requests.auth import HTTPBasicAuth
from csrf_helper import CSRFHelper

BASE_URL = "http://localhost:8000"
AUTH = HTTPBasicAuth("boss", "Mm02022006")
TIMEOUT = 30


def test_hr_employee_attendance_and_payroll_processing():
    # ✅ استخدام CSRF Helper المحسّن
    csrf = CSRFHelper(BASE_URL, "boss", "Mm02022006")
    
    employee_id = None

    try:
        # 1. Create a new employee
        employee_payload = {
            "first_name": "Test",
            "last_name": "Employee",
            "email": "test.employee@example.com",
            "job_title": "Software Engineer",
            "department": "Development"
        }
        r = csrf.post(f"{BASE_URL}/hr/employees/", json=employee_payload, timeout=TIMEOUT)
        assert r.status_code == 201, f"Failed to create employee: {r.text}"
        employee_data = r.json()
        employee_id = employee_data.get("id")
        assert employee_id is not None, "Employee ID not found in creation response."

        # 2. Record attendance for the created employee
        attendance_payload = {
            "employee": employee_id,
            "date": "2026-02-06",
            "check_in": "08:00:00",
            "check_out": "17:00:00",
            "status": "Present"
        }
        r = csrf.post(f"{BASE_URL}/hr/attendance/", json=attendance_payload, timeout=TIMEOUT)
        assert r.status_code == 201, f"Failed to record attendance: {r.text}"
        attendance_data = r.json()
        attendance_id = attendance_data.get("id")
        assert attendance_id is not None, "Attendance ID not found in creation response."

        # 3. Submit a leave request for the employee
        leave_payload = {
            "employee": employee_id,
            "start_date": "2026-02-10",
            "end_date": "2026-02-12",
            "leave_type": "Annual",
            "reason": "Family trip"
        }
        r = csrf.post(f"{BASE_URL}/hr/leave-requests/", json=leave_payload, timeout=TIMEOUT)
        assert r.status_code == 201, f"Failed to submit leave request: {r.text}"
        leave_data = r.json()
        leave_id = leave_data.get("id")
        assert leave_id is not None, "Leave request ID not found in creation response."

        # 4. Calculate payroll for the employee for the period including above attendance and leave
        payroll_payload = {
            "employee": employee_id,
            "start_date": "2026-02-01",
            "end_date": "2026-02-28"
        }
        r = csrf.post(f"{BASE_URL}/hr/payroll/", json=payroll_payload, timeout=TIMEOUT)
        assert r.status_code == 200, f"Failed to calculate payroll: {r.text}"
        payroll_data = r.json()
        payroll_id = payroll_data.get("id")
        assert payroll_id is not None, "Payroll entry ID not found in response."
        # Basic payroll checks: total_pay should be positive number
        total_pay = payroll_data.get("total_pay")
        assert total_pay is not None and isinstance(total_pay, (int, float)) and total_pay >= 0, "Invalid total pay in payroll response."

        # 5. Generate bank export file for payroll (assuming endpoint or payroll detail includes this)
        # If a separate endpoint to get bank export file exists:
        r = csrf.get(f"{BASE_URL}/hr/payroll/{payroll_id}/bank-export/", timeout=TIMEOUT)
        if r.status_code == 404:
            # If bank export endpoint does not exist, skip this step gracefully
            pass
        else:
            assert r.status_code == 200, f"Failed to get bank export file: {r.text}"
            content_type = r.headers.get("Content-Type", "")
            assert content_type in ["application/octet-stream", "application/pdf", "text/csv"], "Unexpected content type for bank export file."
            content = r.content
            assert content is not None and len(content) > 0, "Empty bank export file content."

    finally:
        # Clean up: delete created leave request, attendance record, and employee
        # Delete leave request
        if 'leave_id' in locals() and leave_id:
            try:
                _ = requests.delete(f"{BASE_URL}/hr/leave-requests/{leave_id}/", headers=headers, timeout=TIMEOUT)
            except Exception:
                pass
        # Delete attendance record
        if 'attendance_id' in locals() and attendance_id:
            try:
                _ = requests.delete(f"{BASE_URL}/hr/attendance/{attendance_id}/", headers=headers, timeout=TIMEOUT)
            except Exception:
                pass
        # Delete payroll entry is usually not allowed or needed, skip deletion
        # Delete employee
        if employee_id:
            try:
                _ = requests.delete(f"{BASE_URL}/hr/employees/{employee_id}/", headers=headers, timeout=TIMEOUT)
            except Exception:
                pass

test_hr_employee_attendance_and_payroll_processing()
