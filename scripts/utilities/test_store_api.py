#!/usr/bin/env python3
"""
اختبار شامل لـ APIs المتجر الإلكتروني
Comprehensive E-commerce API Testing
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://72.62.176.249"
STORE_URL = f"{BASE_URL}/store"

class StoreAPITester:
    def __init__(self):
        self.session = requests.Session()
        self.results = {
            'passed': 0,
            'failed': 0,
            'total': 0
        }
    
    def print_header(self, text):
        print("\n" + "=" * 60)
        print(f"  {text}")
        print("=" * 60)
    
    def print_test(self, test_name, passed, details=""):
        self.results['total'] += 1
        if passed:
            self.results['passed'] += 1
            print(f"✅ {test_name}")
        else:
            self.results['failed'] += 1
            print(f"❌ {test_name}")
        if details:
            print(f"   {details}")
    
    def test_store_home(self):
        """اختبار الصفحة الرئيسية"""
        self.print_header("اختبار الصفحة الرئيسية")
        try:
            response = self.session.get(f"{STORE_URL}/")
            passed = response.status_code == 200
            self.print_test(
                "الصفحة الرئيسية",
                passed,
                f"Status: {response.status_code}"
            )
            return passed
        except Exception as e:
            self.print_test("الصفحة الرئيسية", False, str(e))
            return False
    
    def test_products_list(self):
        """اختبار صفحة المنتجات"""
        self.print_header("اختبار صفحة المنتجات")
        try:
            response = self.session.get(f"{STORE_URL}/products/")
            passed = response.status_code == 200
            self.print_test(
                "صفحة المنتجات",
                passed,
                f"Status: {response.status_code}"
            )
            return passed
        except Exception as e:
            self.print_test("صفحة المنتجات", False, str(e))
            return False
    
    def test_product_detail(self):
        """اختبار صفحة تفاصيل المنتج"""
        self.print_header("اختبار تفاصيل المنتج")
        try:
            # جلب أول منتج نشط
            import requests
            response = requests.get(f"{STORE_URL}/api/products/")
            if response.status_code == 200:
                data = response.json()
                if data.get('results') and len(data['results']) > 0:
                    product_id = data['results'][0]['id']
                else:
                    product_id = 36  # fallback
            else:
                product_id = 36  # fallback
            
            response = self.session.get(f"{STORE_URL}/product/{product_id}/")
            passed = response.status_code == 200
            self.print_test(
                "صفحة تفاصيل المنتج",
                passed,
                f"Status: {response.status_code} (Product ID: {product_id})"
            )
            return passed
        except Exception as e:
            self.print_test("صفحة تفاصيل المنتج", False, str(e))
            return False
    
    def test_categories_list(self):
        """اختبار صفحة الفئات"""
        self.print_header("اختبار صفحة الفئات")
        try:
            response = self.session.get(f"{STORE_URL}/categories/")
            passed = response.status_code == 200
            self.print_test(
                "صفحة الفئات",
                passed,
                f"Status: {response.status_code}"
            )
            return passed
        except Exception as e:
            self.print_test("صفحة الفئات", False, str(e))
            return False
    
    def test_cart_view(self):
        """اختبار سلة التسوق"""
        self.print_header("اختبار سلة التسوق")
        try:
            response = self.session.get(f"{STORE_URL}/cart/")
            passed = response.status_code == 200
            self.print_test(
                "صفحة السلة",
                passed,
                f"Status: {response.status_code}"
            )
            return passed
        except Exception as e:
            self.print_test("صفحة السلة", False, str(e))
            return False
    
    def test_cart_count_api(self):
        """اختبار API عدد عناصر السلة"""
        self.print_header("اختبار API عدد العناصر")
        try:
            response = self.session.get(f"{STORE_URL}/cart/count/")
            passed = response.status_code == 200
            if passed:
                data = response.json()
                details = f"عدد العناصر: {data.get('count', 0)}"
            else:
                details = f"Status: {response.status_code}"
            self.print_test("API عدد العناصر", passed, details)
            return passed
        except Exception as e:
            self.print_test("API عدد العناصر", False, str(e))
            return False
    
    def test_search(self):
        """اختبار البحث"""
        self.print_header("اختبار البحث")
        try:
            response = self.session.get(f"{STORE_URL}/search/?q=مرتبة")
            passed = response.status_code == 200
            self.print_test(
                "البحث عن منتجات",
                passed,
                f"Status: {response.status_code}"
            )
            return passed
        except Exception as e:
            self.print_test("البحث عن منتجات", False, str(e))
            return False
    
    def test_static_pages(self):
        """اختبار الصفحات الثابتة"""
        self.print_header("اختبار الصفحات الثابتة")
        
        pages = [
            ('about', 'من نحن'),
            ('contact', 'اتصل بنا'),
            ('privacy', 'سياسة الخصوصية'),
            ('terms', 'الشروط والأحكام'),
            ('shipping', 'الشحن والتوصيل'),
        ]
        
        for page_url, page_name in pages:
            try:
                response = self.session.get(f"{STORE_URL}/{page_url}/")
                passed = response.status_code == 200
                self.print_test(
                    f"صفحة {page_name}",
                    passed,
                    f"Status: {response.status_code}"
                )
            except Exception as e:
                self.print_test(f"صفحة {page_name}", False, str(e))
    
    def test_authentication_pages(self):
        """اختبار صفحات تسجيل الدخول"""
        self.print_header("اختبار صفحات المصادقة")
        
        auth_pages = [
            ('login', 'تسجيل الدخول'),
            ('register', 'التسجيل'),
        ]
        
        for page_url, page_name in auth_pages:
            try:
                response = self.session.get(f"{STORE_URL}/{page_url}/")
                passed = response.status_code == 200
                self.print_test(
                    f"صفحة {page_name}",
                    passed,
                    f"Status: {response.status_code}"
                )
            except Exception as e:
                self.print_test(f"صفحة {page_name}", False, str(e))
    
    def print_summary(self):
        """طباعة ملخص النتائج"""
        self.print_header("ملخص نتائج الاختبار")
        print(f"\n📊 إجمالي الاختبارات: {self.results['total']}")
        print(f"✅ نجح: {self.results['passed']}")
        print(f"❌ فشل: {self.results['failed']}")
        
        if self.results['total'] > 0:
            success_rate = (self.results['passed'] / self.results['total']) * 100
            print(f"📈 معدل النجاح: {success_rate:.1f}%")
        
        print("\n" + "=" * 60)
        
        if self.results['failed'] == 0:
            print("🎉 جميع الاختبارات نجحت!")
        else:
            print(f"⚠️ يوجد {self.results['failed']} اختبار فاشل")
        
        print("=" * 60)
    
    def run_all_tests(self):
        """تشغيل جميع الاختبارات"""
        print("\n" + "🚀 " * 30)
        print("  بدء اختبار المتجر الإلكتروني - Tony Store")
        print(f"  التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("🚀 " * 30)
        
        # الاختبارات الأساسية
        self.test_store_home()
        self.test_products_list()
        self.test_product_detail()
        self.test_categories_list()
        self.test_cart_view()
        self.test_cart_count_api()
        self.test_search()
        
        # الصفحات الثابتة
        self.test_static_pages()
        
        # صفحات المصادقة
        self.test_authentication_pages()
        
        # ملخص النتائج
        self.print_summary()

if __name__ == "__main__":
    tester = StoreAPITester()
    tester.run_all_tests()
