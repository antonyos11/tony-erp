import requests
from bs4 import BeautifulSoup
import time

BASE_URL = "http://127.0.0.1:8000"
LOGIN_URL = f"{BASE_URL}/accounts/login/"
LOGOUT_URL = f"{BASE_URL}/accounts/logout/"
USERNAME = "superadmin"
PASSWORD = "admin123"
HEADERS = {"User-Agent": "test-agent"}
TIMEOUT = 30

def test_get_accounts_logout_logout_and_redirect():
    with requests.Session() as session:
        # Step 1: GET /accounts/login/ to fetch CSRF token and cookies
        resp = session.get(LOGIN_URL, headers=HEADERS, timeout=TIMEOUT)
        assert resp.status_code == 200, f"Login page did not return 200 OK, got {resp.status_code}"
        # Parse CSRF token from cookies or page
        csrf_token = None
        # Try to get csrfmiddlewaretoken from cookies
        if 'csrftoken' in session.cookies:
            csrf_token = session.cookies['csrftoken']
        else:
            # fallback: parse from HTML form input field named csrfmiddlewaretoken
            soup = BeautifulSoup(resp.text, "html.parser")
            csrf_input = soup.find("input", attrs={"name": "csrfmiddlewaretoken"})
            if csrf_input and csrf_input.get("value"):
                csrf_token = csrf_input["value"]
        assert csrf_token, "CSRF token not found on login page"

        # Prepare login payload
        login_data = {
            "username": USERNAME,
            "password": PASSWORD,
            "csrfmiddlewaretoken": csrf_token,
        }

        # Important: set Referer header usually required by Django for POST forms
        login_headers = HEADERS.copy()
        login_headers.update({
            "Referer": LOGIN_URL
        })

        # Step 2: POST /accounts/login/ to login and create a session
        login_resp = session.post(LOGIN_URL, data=login_data, headers=login_headers, timeout=TIMEOUT, allow_redirects=False)
        # Django generally returns a 302 Found redirect on successful login
        assert login_resp.status_code in (302, 303), f"Login POST did not redirect, got status {login_resp.status_code}"
        assert 'sessionid' in session.cookies, "Session cookie not set after login"

        # Delay to respect rate limits
        time.sleep(1)

        # Step 3: GET /accounts/logout/ to logout - should redirect to login page (302)
        logout_resp = session.get(LOGOUT_URL, headers=HEADERS, timeout=TIMEOUT, allow_redirects=False)
        assert logout_resp.status_code == 302, f"Logout did not redirect, got {logout_resp.status_code}"

        # Check that redirect location is the login page or contains '/accounts/login'
        location = logout_resp.headers.get("Location", "")
        assert location, "Logout response missing Location header for redirect"
        assert "/accounts/login" in location, f"Logout redirect location incorrect: {location}"

        # Step 4: Verify session is cleared by attempting to access a url needing auth (like /accounts/logout/) again and expect redirect to login
        second_logout_resp = session.get(LOGOUT_URL, headers=HEADERS, timeout=TIMEOUT, allow_redirects=False)
        # After logout session is invalid, accessing logout should redirect to login (302)
        assert second_logout_resp.status_code == 302, f"Second logout attempt did not redirect, got {second_logout_resp.status_code}"
        second_location = second_logout_resp.headers.get("Location", "")
        assert "/accounts/login" in second_location, f"Second logout redirect location incorrect: {second_location}"

test_get_accounts_logout_logout_and_redirect()