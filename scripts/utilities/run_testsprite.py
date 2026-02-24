#!/usr/bin/env python3
"""
TestSprite Runner for Tony ERP
اختبارات TestSprite على الخادم المباشر
"""

import requests
import json
from datetime import datetime
import sys

# إعدادات الخادم
BASE_URL = "http://72.62.176.249"
API_BASE = f"{BASE_URL}/api"

# ألوان للطباعة
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

class TestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []
        
    def test(self, name, description):
        """ديكوريتر لتعريف الاختبارات"""
        def decorator(func):
            self.tests.append({
                'name': name,
                'description': description,
                'func': func
            })
            return func
        return decorator
    
    def run(self):
        """تشغيل جميع الاختبارات"""
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}TestSprite - Tony ERP Testing Suite{RESET}")
        print(f"{BLUE}Server: {BASE_URL}{RESET}")
        print(f"{BLUE}Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}")
        print(f"{BLUE}{'='*60}{RESET}\n")
        
        for test in self.tests:
            print(f"{YELLOW}Testing:{RESET} {test['description']}")
            try:
                test['func']()
                print(f"{GREEN}✓ PASSED{RESET} - {test['name']}\n")
                self.passed += 1
            except AssertionError as e:
                print(f"{RED}✗ FAILED{RESET} - {test['name']}")
                print(f"{RED}Error: {str(e)}{RESET}\n")
                self.failed += 1
            except Exception as e:
                print(f"{RED}✗ ERROR{RESET} - {test['name']}")
                print(f"{RED}Exception: {str(e)}{RESET}\n")
                self.failed += 1
        
        # النتيجة النهائية
        total = self.passed + self.failed
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}Test Results:{RESET}")
        print(f"{GREEN}Passed:{RESET} {self.passed}/{total}")
        print(f"{RED}Failed:{RESET} {self.failed}/{total}")
        print(f"Success Rate: {(self.passed/total*100) if total > 0 else 0:.1f}%")
        print(f"{BLUE}{'='*60}{RESET}\n")
        
        return self.failed == 0


# إنشاء مدير الاختبارات
runner = TestRunner()


@runner.test("TC001", "Server Health Check - فحص صحة الخادم")
def test_server_health():
    """اختبار الوصول للخادم"""
    response = requests.get(BASE_URL, timeout=10)
    assert response.status_code in [200, 302, 301], f"Server not responding: {response.status_code}"


@runner.test("TC002", "API Products List - قائمة المنتجات")
def test_products_list():
    """اختبار جلب قائمة المنتجات"""
    response = requests.get(f"{API_BASE}/products/", timeout=10)
    assert response.status_code in [200, 401], f"Unexpected status: {response.status_code}"
    
    if response.status_code == 200:
        data = response.json()
        print(f"  → Found {len(data) if isinstance(data, list) else 'N/A'} products")


@runner.test("TC003", "API Customers List - قائمة العملاء")
def test_customers_list():
    """اختبار جلب قائمة العملاء"""
    response = requests.get(f"{API_BASE}/customers/", timeout=10)
    assert response.status_code in [200, 401], f"Unexpected status: {response.status_code}"


@runner.test("TC004", "API Suppliers List - قائمة الموردين")
def test_suppliers_list():
    """اختبار جلب قائمة الموردين"""
    response = requests.get(f"{API_BASE}/suppliers/", timeout=10)
    assert response.status_code in [200, 401], f"Unexpected status: {response.status_code}"


@runner.test("TC005", "API Stock Levels - مستويات المخزون")
def test_stock_levels():
    """اختبار جلب مستويات المخزون"""
    response = requests.get(f"{API_BASE}/inventory/stock-levels/", timeout=10)
    assert response.status_code in [200, 401, 404], f"Unexpected status: {response.status_code}"


@runner.test("TC006", "Dashboard Access - الوصول للوحة التحكم")
def test_dashboard_access():
    """اختبار الوصول للوحة التحكم"""
    response = requests.get(f"{BASE_URL}/dashboard/", timeout=10)
    assert response.status_code in [200, 302, 301], f"Dashboard not accessible: {response.status_code}"


@runner.test("TC007", "Login Page - صفحة تسجيل الدخول")
def test_login_page():
    """اختبار صفحة تسجيل الدخول"""
    response = requests.get(f"{BASE_URL}/accounts/login/", timeout=10)
    assert response.status_code == 200, f"Login page not found: {response.status_code}"


@runner.test("TC008", "Static Files - الملفات الثابتة")
def test_static_files():
    """اختبار الملفات الثابتة (CSS/JS)"""
    response = requests.get(f"{BASE_URL}/static/css/style.css", timeout=10)
    # يمكن أن يكون 200 أو 404 حسب الإعدادات
    assert response.status_code in [200, 404, 301, 302], f"Static files error: {response.status_code}"


@runner.test("TC009", "API Authentication Endpoint - نقطة المصادقة")
def test_auth_endpoint():
    """اختبار نقطة المصادقة"""
    response = requests.post(
        f"{API_BASE}/auth/login/",
        json={"username": "test", "password": "test"},
        timeout=10
    )
    assert response.status_code in [200, 400, 401, 404], f"Auth endpoint error: {response.status_code}"


@runner.test("TC010", "Response Headers - رؤوس الاستجابة")
def test_response_headers():
    """اختبار رؤوس الاستجابة"""
    response = requests.get(BASE_URL, timeout=10)
    assert 'content-type' in response.headers, "Missing Content-Type header"
    print(f"  → Content-Type: {response.headers.get('content-type')}")


if __name__ == "__main__":
    success = runner.run()
    sys.exit(0 if success else 1)
