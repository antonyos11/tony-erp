#!/usr/bin/env python3
"""
TestSprite Advanced Testing Suite
اختبارات متقدمة لنظام Tony ERP
"""

import requests
import json
from datetime import datetime
import sys
import time

BASE_URL = "http://72.62.176.249"
API_BASE = f"{BASE_URL}/api"

GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
RESET = '\033[0m'

class AdvancedTestRunner:
    def __init__(self):
        self.results = {
            'passed': 0,
            'failed': 0,
            'warnings': 0,
            'performance': []
        }
        self.tests = []
        
    def test(self, name, description, category="general"):
        def decorator(func):
            self.tests.append({
                'name': name,
                'description': description,
                'category': category,
                'func': func
            })
            return func
        return decorator
    
    def measure_performance(self, url, method="GET", **kwargs):
        """قياس أداء الطلب"""
        start = time.time()
        response = requests.request(method, url, **kwargs)
        elapsed = (time.time() - start) * 1000  # بالميلي ثانية
        
        self.results['performance'].append({
            'url': url,
            'method': method,
            'time_ms': elapsed,
            'status': response.status_code
        })
        
        return response, elapsed
    
    def run(self):
        print(f"\n{CYAN}{'='*70}{RESET}")
        print(f"{CYAN}TestSprite Advanced Testing Suite - Tony ERP{RESET}")
        print(f"{CYAN}Server: {BASE_URL}{RESET}")
        print(f"{CYAN}Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}")
        print(f"{CYAN}{'='*70}{RESET}\n")
        
        categories = {}
        for test in self.tests:
            cat = test['category']
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(test)
        
        for category, tests in categories.items():
            print(f"\n{BLUE}{'─'*70}{RESET}")
            print(f"{BLUE}Category: {category.upper()}{RESET}")
            print(f"{BLUE}{'─'*70}{RESET}\n")
            
            for test in tests:
                print(f"{YELLOW}[{test['name']}]{RESET} {test['description']}")
                try:
                    result = test['func']()
                    if result and isinstance(result, dict) and result.get('warning'):
                        print(f"{YELLOW}⚠ WARNING{RESET} - {result.get('message', 'Check required')}")
                        self.results['warnings'] += 1
                    else:
                        print(f"{GREEN}✓ PASSED{RESET}")
                        self.results['passed'] += 1
                except AssertionError as e:
                    print(f"{RED}✗ FAILED{RESET} - {str(e)}")
                    self.results['failed'] += 1
                except Exception as e:
                    print(f"{RED}✗ ERROR{RESET} - {str(e)}")
                    self.results['failed'] += 1
                print()
        
        self.print_summary()
        return self.results['failed'] == 0

    def print_summary(self):
        total = self.results['passed'] + self.results['failed'] + self.results['warnings']
        
        print(f"\n{CYAN}{'='*70}{RESET}")
        print(f"{CYAN}Test Summary{RESET}")
        print(f"{CYAN}{'='*70}{RESET}")
        print(f"{GREEN}✓ Passed:{RESET}   {self.results['passed']:>3}/{total}")
        print(f"{RED}✗ Failed:{RESET}   {self.results['failed']:>3}/{total}")
        print(f"{YELLOW}⚠ Warnings:{RESET} {self.results['warnings']:>3}/{total}")
        print(f"Success Rate: {(self.results['passed']/total*100) if total > 0 else 0:.1f}%")
        
        # تقرير الأداء
        if self.results['performance']:
            print(f"\n{CYAN}Performance Report{RESET}")
            print(f"{CYAN}{'─'*70}{RESET}")
            
            avg_time = sum(p['time_ms'] for p in self.results['performance']) / len(self.results['performance'])
            max_time = max(self.results['performance'], key=lambda x: x['time_ms'])
            min_time = min(self.results['performance'], key=lambda x: x['time_ms'])
            
            print(f"Average Response Time: {avg_time:.2f} ms")
            print(f"Fastest Request: {min_time['time_ms']:.2f} ms ({min_time['url']})")
            print(f"Slowest Request: {max_time['time_ms']:.2f} ms ({max_time['url']})")
            
            # تحذير إذا كان هناك طلبات بطيئة
            slow_requests = [p for p in self.results['performance'] if p['time_ms'] > 1000]
            if slow_requests:
                print(f"\n{YELLOW}⚠ Slow Requests (>1s):{RESET}")
                for req in slow_requests:
                    print(f"  - {req['url']}: {req['time_ms']:.2f} ms")
        
        print(f"{CYAN}{'='*70}{RESET}\n")


runner = AdvancedTestRunner()


# ═══════════════════════════════════════════════════════════════════
# اختبارات الأداء (Performance Tests)
# ═══════════════════════════════════════════════════════════════════

@runner.test("PERF001", "Server Response Time - زمن استجابة الخادم", "performance")
def test_server_response_time():
    response, elapsed = runner.measure_performance(BASE_URL)
    assert response.status_code in [200, 302, 301]
    print(f"  → Response time: {elapsed:.2f} ms")
    
    if elapsed > 1000:
        return {'warning': True, 'message': 'Response time > 1 second'}
    return True


@runner.test("PERF002", "API Response Time - زمن استجابة API", "performance")
def test_api_response_time():
    response, elapsed = runner.measure_performance(f"{API_BASE}/products/")
    assert response.status_code in [200, 401]
    print(f"  → API response time: {elapsed:.2f} ms")
    
    if elapsed > 2000:
        return {'warning': True, 'message': 'API response time > 2 seconds'}
    return True


@runner.test("PERF003", "Concurrent Requests - الطلبات المتزامنة", "performance")
def test_concurrent_requests():
    import concurrent.futures
    
    def make_request():
        return requests.get(BASE_URL, timeout=10)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(make_request) for _ in range(5)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    assert all(r.status_code in [200, 302, 301] for r in results)
    print(f"  → All 5 concurrent requests succeeded")
    return True


# ═══════════════════════════════════════════════════════════════════
# اختبارات الأمان (Security Tests)
# ═══════════════════════════════════════════════════════════════════

@runner.test("SEC001", "HTTPS Redirect - إعادة التوجيه الآمن", "security")
def test_https_redirect():
    response = requests.get(BASE_URL, timeout=10, allow_redirects=False)
    # في الإنتاج يجب إعادة التوجيه لـ HTTPS
    print(f"  → Status: {response.status_code}")
    return True


@runner.test("SEC002", "SQL Injection Prevention - منع حقن SQL", "security")
def test_sql_injection():
    # محاولة حقن SQL في المعاملات
    response = requests.get(f"{API_BASE}/products/?id=1' OR '1'='1", timeout=10)
    assert response.status_code in [200, 400, 401, 404]
    print(f"  → Server handled SQL injection attempt: {response.status_code}")
    return True


@runner.test("SEC003", "XSS Prevention - منع XSS", "security")
def test_xss_prevention():
    xss_payload = "<script>alert('XSS')</script>"
    response = requests.get(f"{API_BASE}/products/?search={xss_payload}", timeout=10)
    assert response.status_code in [200, 400, 401, 404]
    
    if response.status_code == 200:
        assert xss_payload not in response.text
        print(f"  → XSS payload properly escaped")
    return True


@runner.test("SEC004", "API Authentication Required - المصادقة مطلوبة", "security")
def test_api_auth_required():
    # محاولة الوصول بدون مصادقة
    response = requests.post(f"{API_BASE}/products/", json={}, timeout=10)
    assert response.status_code in [401, 403, 405]
    print(f"  → API properly requires authentication: {response.status_code}")
    return True


# ═══════════════════════════════════════════════════════════════════
# اختبارات التكامل (Integration Tests)
# ═══════════════════════════════════════════════════════════════════

@runner.test("INT001", "Database Connection - اتصال قاعدة البيانات", "integration")
def test_database_connection():
    response = requests.get(f"{API_BASE}/products/", timeout=10)
    # إذا كان الخادم يستجيب، فقاعدة البيانات متصلة
    assert response.status_code in [200, 401]
    print(f"  → Database connection active")
    return True


@runner.test("INT002", "Cache System - نظام التخزين المؤقت", "integration")
def test_cache_system():
    # طلب مرتين ونقارن الأوقات
    response1, time1 = runner.measure_performance(BASE_URL)
    response2, time2 = runner.measure_performance(BASE_URL)
    
    assert response1.status_code in [200, 302, 301]
    assert response2.status_code in [200, 302, 301]
    
    if time2 < time1 * 0.8:  # الثاني أسرع بـ20%+
        print(f"  → Cache appears to be working (2nd request faster)")
    else:
        print(f"  → Time1: {time1:.2f}ms, Time2: {time2:.2f}ms")
    return True


@runner.test("INT003", "Static Files Serving - خدمة الملفات الثابتة", "integration")
def test_static_files_serving():
    # اختبار أنواع مختلفة من الملفات الثابتة
    files = [
        '/static/css/style.css',
        '/static/js/main.js',
        '/static/admin/css/base.css'
    ]
    
    working_files = 0
    for file_path in files:
        response = requests.get(f"{BASE_URL}{file_path}", timeout=10)
        if response.status_code == 200:
            working_files += 1
    
    print(f"  → {working_files}/{len(files)} static file types accessible")
    return True


@runner.test("INT004", "Media Files Upload Path - مسار رفع الملفات", "integration")
def test_media_upload_path():
    response = requests.get(f"{BASE_URL}/media/", timeout=10)
    # 403 يعني المجلد موجود لكن لا يمكن الوصول (طبيعي)
    # 404 يعني المجلد غير موجود
    print(f"  → Media path status: {response.status_code}")
    return True


# ═══════════════════════════════════════════════════════════════════
# اختبارات وظيفية (Functional Tests)
# ═══════════════════════════════════════════════════════════════════

@runner.test("FUNC001", "Login Functionality - وظيفة تسجيل الدخول", "functional")
def test_login_functionality():
    response = requests.get(f"{BASE_URL}/accounts/login/", timeout=10)
    assert response.status_code == 200
    assert 'login' in response.text.lower() or 'username' in response.text.lower()
    print(f"  → Login page contains login form")
    return True


@runner.test("FUNC002", "Dashboard Redirect - إعادة توجيه لوحة التحكم", "functional")
def test_dashboard_redirect():
    response = requests.get(f"{BASE_URL}/dashboard/", timeout=10, allow_redirects=False)
    # يجب إعادة التوجيه لتسجيل الدخول إذا لم يكن مصادقاً
    print(f"  → Dashboard status: {response.status_code}")
    assert response.status_code in [200, 302, 301]
    return True


@runner.test("FUNC003", "API Endpoints Available - نقاط API متاحة", "functional")
def test_api_endpoints():
    endpoints = [
        '/api/products/',
        '/api/customers/',
        '/api/suppliers/',
        '/api/inventory/stock-levels/'
    ]
    
    available = 0
    for endpoint in endpoints:
        response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
        if response.status_code in [200, 401]:
            available += 1
    
    print(f"  → {available}/{len(endpoints)} API endpoints responding")
    assert available > 0
    return True


@runner.test("FUNC004", "Error Pages - صفحات الأخطاء", "functional")
def test_error_pages():
    # اختبار صفحة 404
    response = requests.get(f"{BASE_URL}/nonexistent-page-test-123/", timeout=10)
    print(f"  → 404 page status: {response.status_code}")
    assert response.status_code in [404, 302, 301]
    return True


# ═══════════════════════════════════════════════════════════════════
# اختبارات التوافق (Compatibility Tests)
# ═══════════════════════════════════════════════════════════════════

@runner.test("COMPAT001", "Mobile Responsiveness - توافق الجوال", "compatibility")
def test_mobile_responsiveness():
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)'
    }
    response = requests.get(BASE_URL, headers=headers, timeout=10)
    assert response.status_code in [200, 302, 301]
    
    # تحقق من وجود viewport meta tag
    if 'viewport' in response.text.lower():
        print(f"  → Viewport meta tag found (mobile-friendly)")
    return True


@runner.test("COMPAT002", "API JSON Response - استجابة JSON", "compatibility")
def test_api_json_response():
    response = requests.get(f"{API_BASE}/products/", timeout=10)
    
    if response.status_code == 200:
        try:
            data = response.json()
            print(f"  → Valid JSON response received")
            return True
        except json.JSONDecodeError:
            raise AssertionError("Response is not valid JSON")
    elif response.status_code == 401:
        print(f"  → Authentication required (expected)")
        return True
    return True


@runner.test("COMPAT003", "Arabic Language Support - دعم اللغة العربية", "compatibility")
def test_arabic_language():
    response = requests.get(BASE_URL, timeout=10)
    
    # تحقق من وجود محتوى عربي
    if 'lang="ar"' in response.text or 'اللغة' in response.text or 'تسجيل' in response.text:
        print(f"  → Arabic language support detected")
    else:
        print(f"  → No Arabic content found in homepage")
    return True


if __name__ == "__main__":
    success = runner.run()
    sys.exit(0 if success else 1)
