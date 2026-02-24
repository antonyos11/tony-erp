import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost:8000"
AUTH = HTTPBasicAuth("boss", "Mm02022006")
TIMEOUT = 30

def test_generate_accurate_financial_reports():
    try:
        # Trigger generation of the financial report
        # Assuming the endpoint to generate or fetch report is /financial-reports with GET method
        url = f"{BASE_URL}/api/reports/profit-loss/"
        headers = {
            "Accept": "application/json"
        }
        response = requests.get(url, auth=AUTH, headers=headers, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()

        # Validate response structure and content for accuracy and absence of errors
        assert isinstance(data, dict), "Response should be a JSON object"
        assert "report" in data, "'report' key missing in response"
        report = data["report"]
        assert isinstance(report, dict), "'report' should be a dictionary"
        # Check required fields in the report
        required_fields = ["total_revenue", "total_expenses", "net_profit", "errors"]
        for field in required_fields:
            assert field in report, f"'{field}' missing in report data"
        # Validate financial values are non-negative numbers
        assert isinstance(report["total_revenue"], (int, float)) and report["total_revenue"] >= 0, "Invalid total_revenue value"
        assert isinstance(report["total_expenses"], (int, float)) and report["total_expenses"] >= 0, "Invalid total_expenses value"
        assert isinstance(report["net_profit"], (int, float)), "Invalid net_profit value"
        # net_profit should be total_revenue - total_expenses (allowing small rounding differences)
        assert abs(report["net_profit"] - (report["total_revenue"] - report["total_expenses"])) < 0.01, "net_profit does not match revenue - expenses"

        # Ensure no errors in report
        assert isinstance(report["errors"], list), "'errors' should be a list"
        assert len(report["errors"]) == 0, f"Report contains errors: {report['errors']}"

    except requests.HTTPError as http_err:
        assert False, f"HTTP error occurred: {http_err}"
    except requests.RequestException as req_err:
        assert False, f"Request exception occurred: {req_err}"
    except ValueError as json_err:
        assert False, f"JSON decode error: {json_err}"

test_generate_accurate_financial_reports()