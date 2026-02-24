import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost:8000"
AUTH = HTTPBasicAuth("boss", "Mm02022006")
TIMEOUT = 30

def test_automatic_daily_backup_execution():
    url = f"{BASE_URL}/api/backups/automatic-daily-execution-status"
    try:
        response = requests.get(url, auth=AUTH, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()
        # Expected data keys and values assumed: {"last_backup_status": "success", "last_backup_time": "ISO8601 timestamp"}
        assert "last_backup_status" in data, "Response missing last_backup_status"
        assert "last_backup_time" in data, "Response missing last_backup_time"
        assert data["last_backup_status"].lower() == "success", f"Backup status expected 'success' but got '{data['last_backup_status']}'"
    except requests.RequestException as e:
        assert False, f"HTTP request failed: {e}"

test_automatic_daily_backup_execution()