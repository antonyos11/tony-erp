"""
Load Testing for Tony ERP using Locust
اختبار الأداء تحت الحمل لنظام Tony ERP
"""

from locust import HttpUser, task, between, SequentialTaskSet
import random
import json


class AuthenticatedUser(HttpUser):
    """مستخدم مصادق يقوم بعمليات مختلفة في النظام"""
    
    wait_time = between(1, 3)  # انتظار من 1 إلى 3 ثواني بين المهام
    
    def on_start(self):
        """تسجيل الدخول عند بدء المستخدم"""
        login_response = self.client.post("/accounts/login/", {
            "username": "admin",
            "password": "admin123"
        })
        
        if login_response.status_code == 200:
            # استخراج CSRF token للطلبات اللاحقة
            self.csrf_token = self.client.cookies.get('csrftoken')
        else:
            print(f"Login failed: {login_response.status_code}")
    
    @task(5)
    def view_dashboard(self):
        """عرض لوحة التحكم - المهمة الأكثر شيوعاً"""
        self.client.get("/dashboard/")
    
    @task(3)
    def view_sales_list(self):
        """عرض قائمة المبيعات"""
        self.client.get("/sales/")
    
    @task(3)
    def view_inventory_list(self):
        """عرض قائمة المخزون"""
        self.client.get("/inventory/products/")
    
    @task(2)
    def view_reports(self):
        """عرض التقارير"""
        self.client.get("/reports/")
    
    @task(2)
    def view_customers(self):
        """عرض قائمة العملاء"""
        self.client.get("/crm/customers/")
    
    @task(1)
    def view_accounting(self):
        """عرض المحاسبة"""
        self.client.get("/accounting/")
    
    @task(1)
    def view_purchases(self):
        """عرض المشتريات"""
        self.client.get("/purchases/")


class APIUser(HttpUser):
    """مستخدم يستخدم API بشكل رئيسي"""
    
    wait_time = between(0.5, 2)
    
    def on_start(self):
        """الحصول على JWT token"""
        response = self.client.post("/api/token/", json={
            "username": "admin",
            "password": "admin123"
        })
        
        if response.status_code == 200:
            data = response.json()
            self.token = data.get('access')
            self.headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            }
        else:
            self.headers = {}
    
    @task(5)
    def api_dashboard_stats(self):
        """استعلام إحصائيات لوحة التحكم"""
        self.client.get("/api/reports/overview/", headers=self.headers)
    
    @task(3)
    def api_sales_list(self):
        """قائمة المبيعات عبر API"""
        self.client.get("/api/sales/", headers=self.headers)
    
    @task(3)
    def api_inventory_list(self):
        """قائمة المخزون عبر API"""
        self.client.get("/api/inventory/products/", headers=self.headers)
    
    @task(2)
    def api_customers_list(self):
        """قائمة العملاء عبر API"""
        self.client.get("/api/crm/customers/", headers=self.headers)
    
    @task(1)
    def api_reports_sales(self):
        """تقرير المبيعات عبر API"""
        self.client.get("/api/reports/sales/", headers=self.headers)


class HeavyOperationsUser(HttpUser):
    """مستخدم يقوم بعمليات ثقيلة (تقارير، تصدير)"""
    
    wait_time = between(5, 10)
    
    def on_start(self):
        """تسجيل الدخول"""
        self.client.post("/accounts/login/", {
            "username": "admin",
            "password": "admin123"
        })
    
    @task(3)
    def generate_sales_report(self):
        """إنشاء تقرير مبيعات"""
        self.client.get("/reports/sales/detailed/")
    
    @task(3)
    def generate_inventory_report(self):
        """إنشاء تقرير مخزون"""
        self.client.get("/reports/inventory/valuation/")
    
    @task(2)
    def export_sales_excel(self):
        """تصدير المبيعات إلى Excel"""
        self.client.get("/sales/export/excel/")
    
    @task(2)
    def generate_financial_statement(self):
        """إنشاء قائمة مالية"""
        self.client.get("/accounting/statements/income/")
    
    @task(1)
    def generate_cash_flow(self):
        """إنشاء قائمة التدفقات النقدية"""
        self.client.get("/accounting/statements/cash-flow/")


class QuickActionsSequence(SequentialTaskSet):
    """سلسلة متتابعة من الإجراءات السريعة"""
    
    @task
    def view_dashboard(self):
        self.client.get("/dashboard/")
    
    @task
    def view_product_list(self):
        self.client.get("/inventory/products/")
    
    @task
    def view_product_detail(self):
        # افتراض وجود منتج برقم 1
        self.client.get("/inventory/products/1/")
    
    @task
    def back_to_dashboard(self):
        self.client.get("/dashboard/")


class SequentialUser(HttpUser):
    """مستخدم ينفذ مهام متسلسلة"""
    
    wait_time = between(2, 5)
    tasks = [QuickActionsSequence]
    
    def on_start(self):
        self.client.post("/accounts/login/", {
            "username": "admin",
            "password": "admin123"
        })


# تكوين نسب المستخدمين
# يمكن استخدامها عند التشغيل بـ:
# locust -f locustfile.py --users 100 --spawn-rate 10

"""
مثال على التشغيل:

# اختبار بسيط مع 10 مستخدمين
locust -f load_tests/locustfile.py --host=http://localhost:8000 --users 10 --spawn-rate 2

# اختبار متوسط مع 50 مستخدم
locust -f load_tests/locustfile.py --host=http://localhost:8000 --users 50 --spawn-rate 5

# اختبار ثقيل مع 200 مستخدم
locust -f load_tests/locustfile.py --host=http://localhost:8000 --users 200 --spawn-rate 10 --run-time 10m

# اختبار headless (بدون واجهة)
locust -f load_tests/locustfile.py --host=http://localhost:8000 --users 100 --spawn-rate 10 --run-time 5m --headless --html=report.html
"""
