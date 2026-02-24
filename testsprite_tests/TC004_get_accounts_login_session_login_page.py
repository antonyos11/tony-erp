import requests

def test_get_accounts_login_page():
    base_url = "http://127.0.0.1:8000"
    session = requests.Session()
    timeout = 30

    try:
        # GET /accounts/login/ without authentication should serve login page
        login_url = f"{base_url}/accounts/login/"
        response = session.get(login_url, timeout=timeout)
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
        content_type = response.headers.get("Content-Type", "")
        assert "text/html" in content_type, "Response content is not HTML"

        # Check if login form and csrfmiddlewaretoken likely exist in HTML by string checks
        html = response.text
        assert '<form' in html, "No form element found in login page HTML"
        assert 'name="csrfmiddlewaretoken"' in html, "CSRF token input not found in login page HTML"
        # Rough check that form method is POST
        assert 'method="post"' in html.lower(), "Login form method is not POST"
    except Exception as e:
        raise AssertionError(f"Test failed: {e}")

test_get_accounts_login_page()
