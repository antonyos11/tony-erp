#!/usr/bin/env python3
"""
Manual TestSprite Backend Tests
Replicates the intended tests from the TestSprite plan targeting core functionality.
"""
import requests
import unittest
import sys

BASE_URL = "http://localhost:8000"

class TestSpriteBackendTests(unittest.TestCase):

    def setUp(self):
        self.session = requests.Session()

    def test_products_list(self):
        """Test retrieving the list of products"""
        url = f"{BASE_URL}/api/products/"
        print(f"Testing {url}...")
        response = self.session.get(url, timeout=10)
        
        # Depending on auth settings, this might be 200 or 401
        if response.status_code == 401:
            print("  -> Auth required (Expected behavior for secured API)")
        elif response.status_code == 200:
            data = response.json()
            print(f"  -> Found {len(data) if isinstance(data, list) else 'N/A'} products")
            self.assertIsInstance(data, list, "Response should be a list")
            if len(data) > 0:
                self.assertIn('name', data[0], "Product should have a name")
        else:
            self.fail(f"Unexpected status code: {response.status_code}")

    def test_customers_list(self):
        """Test retrieving the list of customers"""
        url = f"{BASE_URL}/api/customers/"
        print(f"Testing {url}...")
        response = self.session.get(url, timeout=10)
        
        if response.status_code == 401:
            print("  -> Auth required (Expected behavior for secured API)")
        elif response.status_code == 200:
            data = response.json()
            print(f"  -> Found {len(data) if isinstance(data, list) else 'N/A'} customers")
            self.assertIsInstance(data, list, "Response should be a list")
        else:
            self.fail(f"Unexpected status code: {response.status_code}")

    def test_auth_login_invalid(self):
        """Test login with invalid credentials"""
        url = f"{BASE_URL}/api/token/"
        print(f"Testing {url} (Invalid Creds)...")
        data = {"username": "invalid_user", "password": "wrong_password"}
        response = self.session.post(url, json=data, timeout=10)
        
        # Should be 400 or 401
        self.assertIn(response.status_code, [400, 401, 403], f"Should fail auth, got {response.status_code}")
        print("  -> Login failed as expected")

    def test_server_health_root(self):
        """Test root endpoint health"""
        print(f"Testing {BASE_URL}...")
        response = self.session.get(BASE_URL, timeout=10)
        self.assertIn(response.status_code, [200, 301, 302], f"Server root failed: {response.status_code}")
        print("  -> Server is reachable")

if __name__ == "__main__":
    unittest.main()
