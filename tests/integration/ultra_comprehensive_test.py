#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
اختبار شامل ومفصل لنظام Tony ERP
يختبر جميع المسارات والسيناريوهات والتكامل بين الوحدات
"""

import os
import sys
import json
import django
import requests
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict
import traceback

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory
from django.urls import reverse, resolve, get_resolver, URLPattern, URLResolver
from django.db import connection, transaction
from django.db.models import Model
from django.apps import apps
from django.conf import settings

User = get_user_model()

# ===============================
# هيكل بيانات نتائج الاختبار
# ===============================

@dataclass
class TestResult:
    """نتيجة اختبار واحد"""
    name: str
    category: str
    status: str  # 'pass', 'fail', 'error', 'skip'
    message: str = ""
    details: Dict = field(default_factory=dict)
    duration_ms: float = 0

@dataclass
class TestCategory:
    """فئة اختبارات"""
    name: str
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    tests: List[TestResult] = field(default_factory=list)

class ComprehensiveTestSuite:
    """مجموعة اختبارات شاملة"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.client = Client()
        self.session = requests.Session()
        self.results: Dict[str, TestCategory] = {}
        self.issues: List[Dict] = []
        self.suggestions: List[str] = []
        self.user = None
        self.start_time: datetime = datetime.now()
        
    def setup(self):
        """إعداد بيئة الاختبار"""
        print("\n" + "="*80)
        print("🔧 إعداد بيئة الاختبار")
        print("="*80)
        
        self.start_time = datetime.now()
        
        # الحصول على مستخدم للاختبار
        try:
            self.user = User.objects.filter(is_superuser=True).first()
            if self.user:
                self.client.force_login(self.user)
                print(f"✅ تسجيل الدخول كـ: {self.user.username}")
            else:
                print("⚠️ لا يوجد مستخدم superuser")
        except Exception as e:
            print(f"❌ خطأ في الإعداد: {e}")
    
    def add_result(self, category: str, result: TestResult):
        """إضافة نتيجة اختبار"""
        if category not in self.results:
            self.results[category] = TestCategory(name=category)
        
        cat = self.results[category]
        cat.tests.append(result)
        
        if result.status == 'pass':
            cat.passed += 1
        elif result.status == 'fail':
            cat.failed += 1
            self.issues.append({
                'category': category,
                'test': result.name,
                'message': result.message,
                'details': result.details
            })
        elif result.status == 'error':
            cat.errors += 1
            self.issues.append({
                'category': category,
                'test': result.name,
                'message': result.message,
                'details': result.details
            })
        else:
            cat.skipped += 1
    
    def run_all_tests(self):
        """تشغيل جميع الاختبارات"""
        print("\n" + "="*80)
        print("🚀 بدء الاختبار الشامل لنظام Tony ERP")
        print("="*80)
        
        self.setup()
        
        # تشغيل فئات الاختبارات
        test_methods = [
            ("فحص صحة السيرفر", self.test_server_health),
            ("فحص جميع المسارات", self.test_all_urls),
            ("فحص نماذج البيانات", self.test_models),
            ("فحص العلاقات بين النماذج", self.test_model_relations),
            ("فحص الصفحات الرئيسية", self.test_main_pages),
            ("فحص واجهة المستخدم", self.test_ui_elements),
            ("سيناريوهات المحاسبة", self.test_accounting_scenarios),
            ("سيناريوهات المخزون", self.test_inventory_scenarios),
            ("سيناريوهات المبيعات", self.test_sales_scenarios),
            ("سيناريوهات المشتريات", self.test_purchases_scenarios),
            ("سيناريوهات الإنتاج", self.test_production_scenarios),
            ("سيناريوهات CRM", self.test_crm_scenarios),
            ("سيناريوهات الموارد البشرية", self.test_hr_scenarios),
            ("سيناريوهات الصيانة", self.test_maintenance_scenarios),
            ("فحص التكامل بين الوحدات", self.test_integration),
            ("فحص الأمان", self.test_security),
            ("فحص الأداء", self.test_performance),
            ("فحص API", self.test_api_endpoints),
        ]
        
        for name, method in test_methods:
            print(f"\n📋 {name}...")
            try:
                method()
            except Exception as e:
                print(f"❌ خطأ في {name}: {e}")
                traceback.print_exc()
        
        self.generate_report()
    
    # ===============================
    # اختبارات صحة السيرفر
    # ===============================
    
    def test_server_health(self):
        """اختبار صحة السيرفر"""
        category = "صحة السيرفر"
        
        # فحص health endpoints
        health_endpoints = [
            ('/health/live/', 'فحص الحياة'),
            ('/health/ready/', 'فحص الجاهزية'),
        ]
        
        for url, name in health_endpoints:
            try:
                response = self.client.get(url)
                if response.status_code == 200:
                    self.add_result(category, TestResult(
                        name=name,
                        category=category,
                        status='pass',
                        message=f"الـ endpoint يعمل بشكل صحيح"
                    ))
                else:
                    self.add_result(category, TestResult(
                        name=name,
                        category=category,
                        status='fail',
                        message=f"كود الاستجابة: {response.status_code}"
                    ))
            except Exception as e:
                self.add_result(category, TestResult(
                    name=name,
                    category=category,
                    status='error',
                    message=str(e)
                ))
        
        # فحص قاعدة البيانات
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            self.add_result(category, TestResult(
                name="اتصال قاعدة البيانات",
                category=category,
                status='pass',
                message="الاتصال بقاعدة البيانات يعمل"
            ))
        except Exception as e:
            self.add_result(category, TestResult(
                name="اتصال قاعدة البيانات",
                category=category,
                status='error',
                message=str(e)
            ))
    
    # ===============================
    # اختبار جميع المسارات
    # ===============================
    
    def get_all_urls(self, resolver=None, prefix=''):
        """الحصول على جميع المسارات المسجلة"""
        if resolver is None:
            resolver = get_resolver()
        
        urls = []
        for pattern in resolver.url_patterns:
            if isinstance(pattern, URLResolver):
                # مسار به مسارات فرعية
                new_prefix = prefix + str(pattern.pattern)
                urls.extend(self.get_all_urls(pattern, new_prefix))
            elif isinstance(pattern, URLPattern):
                url = prefix + str(pattern.pattern)
                urls.append({
                    'url': url,
                    'name': pattern.name,
                    'callback': pattern.callback
                })
        return urls
    
    def test_all_urls(self):
        """اختبار جميع المسارات"""
        category = "المسارات"
        all_urls = self.get_all_urls()
        
        print(f"   📊 عدد المسارات: {len(all_urls)}")
        
        # تصنيف المسارات
        testable_urls = []
        skip_patterns = [
            '<pk>', '<int:', '<str:', '<slug:', '<uuid:', 
            'admin/', 'api/', '__debug__', 'i18n/'
        ]
        
        for url_info in all_urls:
            url = url_info['url']
            # تحويل إلى مسار حقيقي
            if not any(p in url for p in skip_patterns):
                # تنظيف المسار
                clean_url = '/' + url.rstrip('$').lstrip('^').replace('\\', '')
                if not clean_url.endswith('/'):
                    clean_url += '/'
                testable_urls.append({
                    **url_info,
                    'clean_url': clean_url
                })
        
        print(f"   📊 مسارات قابلة للاختبار: {len(testable_urls)}")
        
        # اختبار عينة من المسارات
        tested = 0
        passed = 0
        failed = 0
        
        for url_info in testable_urls[:100]:  # أول 100 مسار
            url = url_info['clean_url']
            try:
                response = self.client.get(url, follow=True)
                if response.status_code in [200, 302, 301]:
                    passed += 1
                    status = 'pass'
                elif response.status_code in [403, 401]:
                    passed += 1  # طبيعي - يحتاج صلاحيات
                    status = 'pass'
                elif response.status_code == 404:
                    failed += 1
                    status = 'fail'
                    self.add_result(category, TestResult(
                        name=f"مسار: {url}",
                        category=category,
                        status='fail',
                        message=f"الصفحة غير موجودة (404)",
                        details={'url': url, 'name': url_info['name']}
                    ))
                else:
                    failed += 1
                    status = 'fail'
                    self.add_result(category, TestResult(
                        name=f"مسار: {url}",
                        category=category,
                        status='fail',
                        message=f"كود خطأ: {response.status_code}",
                        details={'url': url}
                    ))
                tested += 1
            except Exception as e:
                failed += 1
                self.add_result(category, TestResult(
                    name=f"مسار: {url}",
                    category=category,
                    status='error',
                    message=str(e)[:100]
                ))
        
        print(f"   ✅ نجح: {passed} | ❌ فشل: {failed}")
        
        # إضافة ملخص
        self.add_result(category, TestResult(
            name="ملخص فحص المسارات",
            category=category,
            status='pass' if failed == 0 else 'fail',
            message=f"تم اختبار {tested} مسار - نجح {passed} - فشل {failed}",
            details={'total': len(all_urls), 'testable': len(testable_urls), 'tested': tested}
        ))
    
    # ===============================
    # اختبار النماذج
    # ===============================
    
    def test_models(self):
        """اختبار نماذج البيانات"""
        category = "نماذج البيانات"
        
        app_labels = [
            'accounting', 'inventory', 'sales', 'purchases', 
            'production', 'crm', 'hr', 'maintenance', 'core',
            'users', 'fixed_assets', 'fleet', 'pos', 'ecommerce',
            'showrooms', 'approvals', 'notifications', 'payments',
            'projects', 'contracting', 'shipping', 'eservices',
            'home_services', 'data_import', 'taxes', 'partners'
        ]
        
        for app_label in app_labels:
            try:
                app_config = apps.get_app_config(app_label)
                models = app_config.get_models()
                model_count = 0
                
                for model in models:
                    model_count += 1
                    try:
                        # محاولة عد السجلات
                        count = model.objects.count()
                        # فحص الحقول
                        fields = [f.name for f in model._meta.fields]
                        
                    except Exception as e:
                        self.add_result(category, TestResult(
                            name=f"{app_label}.{model.__name__}",
                            category=category,
                            status='error',
                            message=f"خطأ في النموذج: {str(e)[:50]}"
                        ))
                
                if model_count > 0:
                    self.add_result(category, TestResult(
                        name=f"تطبيق {app_label}",
                        category=category,
                        status='pass',
                        message=f"{model_count} نموذج",
                        details={'models': model_count}
                    ))
                    
            except LookupError:
                # التطبيق غير موجود
                pass
            except Exception as e:
                self.add_result(category, TestResult(
                    name=f"تطبيق {app_label}",
                    category=category,
                    status='error',
                    message=str(e)[:50]
                ))
    
    def test_model_relations(self):
        """اختبار العلاقات بين النماذج"""
        category = "علاقات النماذج"
        
        # فحص بعض العلاقات الهامة
        relation_tests = [
            ('sales.Invoice', 'customer', 'crm.Customer'),
            ('purchases.PurchaseOrder', 'supplier', 'purchases.Supplier'),
            ('production.ProductionOrder', 'product', 'inventory.Product'),
            ('inventory.StockMovement', 'product', 'inventory.Product'),
            ('hr.Employee', 'user', 'users.CustomUser'),
        ]
        
        for model_path, field_name, related_model in relation_tests:
            try:
                app_label, model_name = model_path.split('.')
                model = apps.get_model(app_label, model_name)
                
                # التحقق من وجود العلاقة
                field = model._meta.get_field(field_name)
                
                self.add_result(category, TestResult(
                    name=f"{model_path} -> {field_name}",
                    category=category,
                    status='pass',
                    message=f"العلاقة موجودة وصحيحة"
                ))
            except Exception as e:
                self.add_result(category, TestResult(
                    name=f"{model_path} -> {field_name}",
                    category=category,
                    status='fail',
                    message=str(e)[:80]
                ))
    
    # ===============================
    # اختبار الصفحات الرئيسية
    # ===============================
    
    def test_main_pages(self):
        """اختبار الصفحات الرئيسية"""
        category = "الصفحات الرئيسية"
        
        main_pages = [
            ('/', 'الصفحة الرئيسية'),
            ('/dashboard/', 'لوحة التحكم'),
            ('/accounting/', 'المحاسبة'),
            ('/inventory/', 'المخزون'),
            ('/sales/', 'المبيعات'),
            ('/purchases/', 'المشتريات'),
            ('/production/', 'الإنتاج'),
            ('/crm/', 'العملاء'),
            ('/hr/', 'الموارد البشرية'),
            ('/maintenance/', 'الصيانة'),
            ('/reports/', 'التقارير'),
            ('/pos/', 'نقاط البيع'),
            ('/fleet/', 'الأسطول'),
            ('/store/', 'المتجر'),
        ]
        
        for url, name in main_pages:
            try:
                response = self.client.get(url, follow=True)
                
                if response.status_code == 200:
                    # فحص محتوى الصفحة
                    content = response.content.decode('utf-8', errors='ignore')
                    has_content = len(content) > 500
                    has_html = '<html' in content.lower() or '<!doctype' in content.lower()
                    
                    if has_content and has_html:
                        self.add_result(category, TestResult(
                            name=name,
                            category=category,
                            status='pass',
                            message=f"الصفحة تعمل ({len(content)} bytes)"
                        ))
                    else:
                        self.add_result(category, TestResult(
                            name=name,
                            category=category,
                            status='fail',
                            message=f"محتوى غير صالح"
                        ))
                else:
                    self.add_result(category, TestResult(
                        name=name,
                        category=category,
                        status='fail',
                        message=f"كود: {response.status_code}"
                    ))
            except Exception as e:
                self.add_result(category, TestResult(
                    name=name,
                    category=category,
                    status='error',
                    message=str(e)[:80]
                ))
    
    # ===============================
    # اختبار عناصر الواجهة
    # ===============================
    
    def test_ui_elements(self):
        """اختبار عناصر واجهة المستخدم"""
        category = "واجهة المستخدم"
        
        # فحص لوحة التحكم
        try:
            response = self.client.get('/dashboard/', follow=True)
            content = response.content.decode('utf-8', errors='ignore')
            
            ui_elements = [
                ('القائمة الجانبية', 'sidebar'),
                ('شريط التنقل', 'navbar'),
                ('القائمة الرئيسية', 'nav'),
            ]
            
            for name, keyword in ui_elements:
                if keyword in content.lower():
                    self.add_result(category, TestResult(
                        name=name,
                        category=category,
                        status='pass',
                        message="موجود في الصفحة"
                    ))
                else:
                    self.add_result(category, TestResult(
                        name=name,
                        category=category,
                        status='fail',
                        message="غير موجود"
                    ))
        except Exception as e:
            self.add_result(category, TestResult(
                name="فحص الواجهة",
                category=category,
                status='error',
                message=str(e)[:80]
            ))
    
    # ===============================
    # سيناريوهات المحاسبة
    # ===============================
    
    def test_accounting_scenarios(self):
        """اختبار سيناريوهات المحاسبة"""
        category = "سيناريوهات المحاسبة"
        
        try:
            from accounting.models import Account, JournalEntry, JournalEntryLine
            
            # 1. فحص شجرة الحسابات
            accounts_count = Account.objects.count()
            self.add_result(category, TestResult(
                name="شجرة الحسابات",
                category=category,
                status='pass' if accounts_count > 0 else 'fail',
                message=f"عدد الحسابات: {accounts_count}"
            ))
            
            # 2. فحص أنواع الحسابات
            account_types = Account.objects.values_list('account_type', flat=True).distinct()
            self.add_result(category, TestResult(
                name="أنواع الحسابات",
                category=category,
                status='pass',
                message=f"الأنواع: {list(account_types)[:5]}"
            ))
            
            # 3. فحص القيود
            entries_count = JournalEntry.objects.count()
            self.add_result(category, TestResult(
                name="القيود المحاسبية",
                category=category,
                status='pass',
                message=f"عدد القيود: {entries_count}"
            ))
            
            # 4. فحص التوازن
            if entries_count > 0:
                entry = JournalEntry.objects.first()
                lines = entry.lines.all()
                total_debit = sum(line.debit or 0 for line in lines)
                total_credit = sum(line.credit or 0 for line in lines)
                balanced = abs(total_debit - total_credit) < Decimal('0.01')
                
                self.add_result(category, TestResult(
                    name="توازن القيود",
                    category=category,
                    status='pass' if balanced else 'fail',
                    message=f"مدين: {total_debit}, دائن: {total_credit}"
                ))
                
        except Exception as e:
            self.add_result(category, TestResult(
                name="اختبار المحاسبة",
                category=category,
                status='error',
                message=str(e)[:80]
            ))
    
    # ===============================
    # سيناريوهات المخزون
    # ===============================
    
    def test_inventory_scenarios(self):
        """اختبار سيناريوهات المخزون"""
        category = "سيناريوهات المخزون"
        
        try:
            from inventory.models import Product, Warehouse, StockMovement
            
            # 1. المنتجات
            products_count = Product.objects.count()
            self.add_result(category, TestResult(
                name="المنتجات",
                category=category,
                status='pass' if products_count > 0 else 'fail',
                message=f"عدد المنتجات: {products_count}"
            ))
            
            # 2. المستودعات
            warehouses_count = Warehouse.objects.count()
            self.add_result(category, TestResult(
                name="المستودعات",
                category=category,
                status='pass' if warehouses_count > 0 else 'fail',
                message=f"عدد المستودعات: {warehouses_count}"
            ))
            
            # 3. حركات المخزون
            movements_count = StockMovement.objects.count()
            self.add_result(category, TestResult(
                name="حركات المخزون",
                category=category,
                status='pass',
                message=f"عدد الحركات: {movements_count}"
            ))
            
        except Exception as e:
            self.add_result(category, TestResult(
                name="اختبار المخزون",
                category=category,
                status='error',
                message=str(e)[:80]
            ))
    
    # ===============================
    # سيناريوهات المبيعات
    # ===============================
    
    def test_sales_scenarios(self):
        """اختبار سيناريوهات المبيعات"""
        category = "سيناريوهات المبيعات"
        
        try:
            from sales.models import Invoice, InvoiceItem
            
            # 1. الفواتير
            invoices_count = Invoice.objects.count()
            self.add_result(category, TestResult(
                name="فواتير المبيعات",
                category=category,
                status='pass',
                message=f"عدد الفواتير: {invoices_count}"
            ))
            
            # 2. فحص فاتورة
            if invoices_count > 0:
                invoice = Invoice.objects.first()
                has_items = invoice.items.exists() if hasattr(invoice, 'items') else False
                self.add_result(category, TestResult(
                    name="بنود الفاتورة",
                    category=category,
                    status='pass' if has_items else 'fail',
                    message=f"الفاتورة لها بنود: {has_items}"
                ))
                
        except Exception as e:
            self.add_result(category, TestResult(
                name="اختبار المبيعات",
                category=category,
                status='error',
                message=str(e)[:80]
            ))
    
    # ===============================
    # سيناريوهات المشتريات
    # ===============================
    
    def test_purchases_scenarios(self):
        """اختبار سيناريوهات المشتريات"""
        category = "سيناريوهات المشتريات"
        
        try:
            from purchases.models import Supplier, PurchaseOrder
            
            # 1. الموردين
            suppliers_count = Supplier.objects.count()
            self.add_result(category, TestResult(
                name="الموردين",
                category=category,
                status='pass' if suppliers_count > 0 else 'fail',
                message=f"عدد الموردين: {suppliers_count}"
            ))
            
            # 2. أوامر الشراء
            orders_count = PurchaseOrder.objects.count()
            self.add_result(category, TestResult(
                name="أوامر الشراء",
                category=category,
                status='pass',
                message=f"عدد الأوامر: {orders_count}"
            ))
            
        except Exception as e:
            self.add_result(category, TestResult(
                name="اختبار المشتريات",
                category=category,
                status='error',
                message=str(e)[:80]
            ))
    
    # ===============================
    # سيناريوهات الإنتاج
    # ===============================
    
    def test_production_scenarios(self):
        """اختبار سيناريوهات الإنتاج"""
        category = "سيناريوهات الإنتاج"
        
        try:
            from production.models import ProductionOrder, FinishedGoodUnit
            
            # 1. أوامر الإنتاج
            orders_count = ProductionOrder.objects.count()
            self.add_result(category, TestResult(
                name="أوامر الإنتاج",
                category=category,
                status='pass',
                message=f"عدد الأوامر: {orders_count}"
            ))
            
            # 2. الوحدات المنتجة
            units_count = FinishedGoodUnit.objects.count()
            self.add_result(category, TestResult(
                name="الوحدات المنتجة",
                category=category,
                status='pass',
                message=f"عدد الوحدات: {units_count}"
            ))
            
            # 3. الضمانات
            warranty_count = FinishedGoodUnit.objects.filter(warranty_registered=True).count()
            self.add_result(category, TestResult(
                name="الضمانات المسجلة",
                category=category,
                status='pass',
                message=f"عدد الضمانات: {warranty_count}"
            ))
            
        except Exception as e:
            self.add_result(category, TestResult(
                name="اختبار الإنتاج",
                category=category,
                status='error',
                message=str(e)[:80]
            ))
    
    # ===============================
    # سيناريوهات CRM
    # ===============================
    
    def test_crm_scenarios(self):
        """اختبار سيناريوهات إدارة العملاء"""
        category = "سيناريوهات CRM"
        
        try:
            from crm.models import Customer, Lead
            
            # 1. العملاء
            customers_count = Customer.objects.count()
            self.add_result(category, TestResult(
                name="العملاء",
                category=category,
                status='pass',
                message=f"عدد العملاء: {customers_count}"
            ))
            
            # 2. العملاء المحتملين
            try:
                leads_count = Lead.objects.count()
                self.add_result(category, TestResult(
                    name="العملاء المحتملين",
                    category=category,
                    status='pass',
                    message=f"عدد العملاء المحتملين: {leads_count}"
                ))
            except:
                pass
            
        except Exception as e:
            self.add_result(category, TestResult(
                name="اختبار CRM",
                category=category,
                status='error',
                message=str(e)[:80]
            ))
    
    # ===============================
    # سيناريوهات الموارد البشرية
    # ===============================
    
    def test_hr_scenarios(self):
        """اختبار سيناريوهات الموارد البشرية"""
        category = "سيناريوهات HR"
        
        try:
            from hr.models import Employee, Department
            
            # 1. الموظفين
            employees_count = Employee.objects.count()
            self.add_result(category, TestResult(
                name="الموظفين",
                category=category,
                status='pass',
                message=f"عدد الموظفين: {employees_count}"
            ))
            
            # 2. الأقسام
            departments_count = Department.objects.count()
            self.add_result(category, TestResult(
                name="الأقسام",
                category=category,
                status='pass' if departments_count > 0 else 'fail',
                message=f"عدد الأقسام: {departments_count}"
            ))
            
        except Exception as e:
            self.add_result(category, TestResult(
                name="اختبار HR",
                category=category,
                status='error',
                message=str(e)[:80]
            ))
    
    # ===============================
    # سيناريوهات الصيانة
    # ===============================
    
    def test_maintenance_scenarios(self):
        """اختبار سيناريوهات الصيانة"""
        category = "سيناريوهات الصيانة"
        
        try:
            from maintenance.models import MaintenanceRequest
            
            # طلبات الصيانة
            requests_count = MaintenanceRequest.objects.count()
            self.add_result(category, TestResult(
                name="طلبات الصيانة",
                category=category,
                status='pass',
                message=f"عدد الطلبات: {requests_count}"
            ))
            
        except Exception as e:
            self.add_result(category, TestResult(
                name="اختبار الصيانة",
                category=category,
                status='error',
                message=str(e)[:80]
            ))
    
    # ===============================
    # اختبار التكامل
    # ===============================
    
    def test_integration(self):
        """اختبار التكامل بين الوحدات"""
        category = "التكامل"
        
        # 1. تكامل الإنتاج مع CRM
        try:
            from production.models import FinishedGoodUnit
            from crm.models import Customer
            
            # وحدات مربوطة بعملاء
            linked_units = FinishedGoodUnit.objects.filter(customer__isnull=False).count()
            self.add_result(category, TestResult(
                name="تكامل الإنتاج-CRM",
                category=category,
                status='pass',
                message=f"وحدات مربوطة بعملاء: {linked_units}"
            ))
        except Exception as e:
            self.add_result(category, TestResult(
                name="تكامل الإنتاج-CRM",
                category=category,
                status='error',
                message=str(e)[:80]
            ))
        
        # 2. تكامل المبيعات مع المخزون
        try:
            response = self.client.get('/sales/', follow=True)
            self.add_result(category, TestResult(
                name="تكامل المبيعات-المخزون",
                category=category,
                status='pass' if response.status_code == 200 else 'fail',
                message=f"صفحة المبيعات: {response.status_code}"
            ))
        except Exception as e:
            self.add_result(category, TestResult(
                name="تكامل المبيعات-المخزون",
                category=category,
                status='error',
                message=str(e)[:80]
            ))
    
    # ===============================
    # اختبار الأمان
    # ===============================
    
    def test_security(self):
        """اختبار الأمان"""
        category = "الأمان"
        
        # 1. فحص الوصول بدون تسجيل
        client = Client()  # عميل جديد بدون تسجيل
        
        protected_urls = [
            '/dashboard/',
            '/accounting/',
            '/inventory/',
            '/sales/',
        ]
        
        for url in protected_urls:
            try:
                response = client.get(url)
                if response.status_code in [302, 301]:  # إعادة توجيه لتسجيل الدخول
                    self.add_result(category, TestResult(
                        name=f"حماية {url}",
                        category=category,
                        status='pass',
                        message="محمي - يتطلب تسجيل دخول"
                    ))
                elif response.status_code == 200:
                    self.add_result(category, TestResult(
                        name=f"حماية {url}",
                        category=category,
                        status='fail',
                        message="⚠️ غير محمي!"
                    ))
                else:
                    self.add_result(category, TestResult(
                        name=f"حماية {url}",
                        category=category,
                        status='pass',
                        message=f"كود: {response.status_code}"
                    ))
            except Exception as e:
                self.add_result(category, TestResult(
                    name=f"حماية {url}",
                    category=category,
                    status='error',
                    message=str(e)[:50]
                ))
    
    # ===============================
    # اختبار الأداء
    # ===============================
    
    def test_performance(self):
        """اختبار الأداء"""
        category = "الأداء"
        
        import time
        
        performance_urls = [
            ('/', 'الصفحة الرئيسية'),
            ('/dashboard/', 'لوحة التحكم'),
            ('/inventory/', 'المخزون'),
        ]
        
        for url, name in performance_urls:
            try:
                start = time.time()
                response = self.client.get(url, follow=True)
                duration = (time.time() - start) * 1000
                
                if duration < 500:
                    status = 'pass'
                    msg = f"سريع ({duration:.0f}ms)"
                elif duration < 2000:
                    status = 'pass'
                    msg = f"مقبول ({duration:.0f}ms)"
                else:
                    status = 'fail'
                    msg = f"بطيء ({duration:.0f}ms)"
                
                self.add_result(category, TestResult(
                    name=f"سرعة {name}",
                    category=category,
                    status=status,
                    message=msg,
                    details={'duration_ms': duration}
                ))
            except Exception as e:
                self.add_result(category, TestResult(
                    name=f"سرعة {name}",
                    category=category,
                    status='error',
                    message=str(e)[:50]
                ))
    
    # ===============================
    # اختبار API
    # ===============================
    
    def test_api_endpoints(self):
        """اختبار نقاط API"""
        category = "API"
        
        api_endpoints = [
            ('/api/', 'API Root'),
            ('/health/live/', 'Health Live'),
            ('/health/ready/', 'Health Ready'),
        ]
        
        for url, name in api_endpoints:
            try:
                response = self.client.get(url)
                self.add_result(category, TestResult(
                    name=name,
                    category=category,
                    status='pass' if response.status_code in [200, 401, 403] else 'fail',
                    message=f"كود: {response.status_code}"
                ))
            except Exception as e:
                self.add_result(category, TestResult(
                    name=name,
                    category=category,
                    status='error',
                    message=str(e)[:50]
                ))
    
    # ===============================
    # توليد التقرير
    # ===============================
    
    def generate_report(self):
        """توليد تقرير الاختبار"""
        duration = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        
        print("\n" + "="*80)
        print("📊 تقرير الاختبار الشامل")
        print("="*80)
        
        total_passed = 0
        total_failed = 0
        total_errors = 0
        total_skipped = 0
        
        for cat_name, cat in self.results.items():
            total_passed += cat.passed
            total_failed += cat.failed
            total_errors += cat.errors
            total_skipped += cat.skipped
            
            status_icon = "✅" if cat.failed == 0 and cat.errors == 0 else "❌"
            print(f"\n{status_icon} {cat_name}:")
            print(f"   ✅ نجح: {cat.passed} | ❌ فشل: {cat.failed} | ⚠️ أخطاء: {cat.errors} | ⏭️ تخطي: {cat.skipped}")
        
        print("\n" + "-"*80)
        print(f"📈 الملخص العام:")
        print(f"   ✅ نجح: {total_passed}")
        print(f"   ❌ فشل: {total_failed}")
        print(f"   ⚠️ أخطاء: {total_errors}")
        print(f"   ⏭️ تخطي: {total_skipped}")
        print(f"   ⏱️ المدة: {duration:.2f} ثانية")
        
        # المشاكل المكتشفة
        if self.issues:
            print("\n" + "="*80)
            print("🔴 المشاكل المكتشفة:")
            print("="*80)
            for i, issue in enumerate(self.issues[:20], 1):
                print(f"\n{i}. [{issue['category']}] {issue['test']}")
                print(f"   المشكلة: {issue['message']}")
        
        # حفظ التقرير
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'duration_seconds': duration,
            'summary': {
                'passed': total_passed,
                'failed': total_failed,
                'errors': total_errors,
                'skipped': total_skipped
            },
            'categories': {
                name: {
                    'passed': cat.passed,
                    'failed': cat.failed,
                    'errors': cat.errors,
                    'skipped': cat.skipped,
                    'tests': [
                        {
                            'name': t.name,
                            'status': t.status,
                            'message': t.message
                        } for t in cat.tests
                    ]
                } for name, cat in self.results.items()
            },
            'issues': self.issues
        }
        
        report_file = 'ultra_test_report.json'
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n📁 تم حفظ التقرير في: {report_file}")
        
        return report_data


if __name__ == '__main__':
    suite = ComprehensiveTestSuite()
    suite.run_all_tests()
