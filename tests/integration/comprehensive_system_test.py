#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
اختبار شامل متكامل لنظام Tony ERP
Comprehensive system test for Tony ERP
"""

import os
import sys
import django
from pathlib import Path

# Setup Django environment
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from django.core.management import call_command
from django.db import connection
from decimal import Decimal
import json

class TonyERPComprehensiveTest:
    """فئة لاختبار شامل للنظام"""
    
    def __init__(self):
        self.client = Client()
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.test_results = []
        self.test_user = None
        
    def log(self, category, test_name, status, details=""):
        """تسجيل نتيجة الاختبار"""
        symbol = "✅" if status == "pass" else ("⚠️" if status == "warn" else "❌")
        msg = f"{symbol} [{category}] {test_name}"
        if details:
            msg += f": {details}"
        print(msg)
        
        self.test_results.append({
            'category': category,
            'test': test_name,
            'status': status,
            'details': details
        })
        
        if status == "pass":
            self.passed += 1
        elif status == "warn":
            self.warnings += 1
        else:
            self.failed += 1
    
    def test_1_system_health(self):
        """اختبار صحة النظام الأساسية"""
        print("\n" + "="*80)
        print("المجموعة 1: فحص صحة النظام الأساسية")
        print("="*80)
        
        # 1.1 Django Check
        try:
            call_command('check', verbosity=0)
            self.log("SYSTEM", "Django System Check", "pass", "لا توجد أخطاء")
        except Exception as e:
            self.log("SYSTEM", "Django System Check", "fail", str(e))
        
        # 1.2 Database Connection
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            self.log("SYSTEM", "Database Connection", "pass")
        except Exception as e:
            self.log("SYSTEM", "Database Connection", "fail", str(e))
        
        # 1.3 Migrations
        try:
            from django.db.migrations.loader import MigrationLoader
            loader = MigrationLoader(connection)
            if loader.applied_migrations:
                self.log("SYSTEM", "Migrations Status", "pass", f"{len(loader.applied_migrations)} مطبق")
            else:
                self.log("SYSTEM", "Migrations Status", "warn", "لا توجد هجرات مطبقة")
        except Exception as e:
            self.log("SYSTEM", "Migrations Status", "fail", str(e))
    
    def test_2_authentication(self):
        """اختبار نظام المصادقة"""
        print("\n" + "="*80)
        print("المجموعة 2: نظام المصادقة والمستخدمين")
        print("="*80)
        
        # 2.1 Superuser Exists
        try:
            superuser = User.objects.filter(is_superuser=True).first()
            if superuser:
                self.test_user = superuser
                self.log("AUTH", "Superuser Exists", "pass", f"المستخدم: {superuser.username}")
            else:
                self.log("AUTH", "Superuser Exists", "fail", "لا يوجد مستخدم إداري")
        except Exception as e:
            self.log("AUTH", "Superuser Exists", "fail", str(e))
        
        # 2.2 Login Test
        if self.test_user:
            try:
                self.client.force_login(self.test_user)
                self.log("AUTH", "User Login", "pass")
            except Exception as e:
                self.log("AUTH", "User Login", "fail", str(e))
        else:
            self.log("AUTH", "User Login", "fail", "لا يوجد مستخدم للاختبار")
    
    def test_3_core_pages(self):
        """اختبار الصفحات الأساسية"""
        print("\n" + "="*80)
        print("المجموعة 3: الصفحات الأساسية")
        print("="*80)
        
        pages = {
            'الصفحة الرئيسية': '/',
            'لوحة التحكم Admin': '/admin/',
            'المستخدمين': '/users/',
            'المخزون': '/inventory/',
            'المبيعات': '/sales/',
            'المشتريات': '/purchases/',
            'المحاسبة': '/accounting/',
        }
        
        for name, url in pages.items():
            try:
                response = self.client.get(url, follow=True)
                if response.status_code == 200:
                    self.log("PAGES", f"صفحة {name}", "pass", f"Status: {response.status_code}")
                elif response.status_code == 302:
                    self.log("PAGES", f"صفحة {name}", "warn", f"تحويل إلى: {response.url}")
                else:
                    self.log("PAGES", f"صفحة {name}", "fail", f"Status: {response.status_code}")
            except Exception as e:
                self.log("PAGES", f"صفحة {name}", "fail", str(e))
    
    def test_4_models(self):
        """اختبار النماذج الأساسية"""
        print("\n" + "="*80)
        print("المجموعة 4: النماذج الأساسية (Models)")
        print("="*80)
        
        models_to_test = [
            ('المستخدمين', 'django.contrib.auth.models', 'User'),
            ('الحسابات', 'accounting.models', 'Account'),
            ('المنتجات', 'inventory.models', 'Product'),
            ('المخازن', 'inventory.models', 'Warehouse'),
            ('العملاء', 'sales.models', 'Customer'),
            ('الفواتير', 'sales.models', 'Invoice'),
            ('الموردين', 'purchases.models', 'Supplier'),
            ('المشتريات', 'purchases.models', 'Purchase'),
        ]
        
        for name, module, model_name in models_to_test:
            try:
                import importlib
                mod = importlib.import_module(module)
                model = getattr(mod, model_name)
                count = model.objects.count()
                self.log("MODELS", f"نموذج {name}", "pass", f"{count} سجل")
            except ImportError:
                self.log("MODELS", f"نموذج {name}", "fail", f"لا يمكن استيراد {module}.{model_name}")
            except AttributeError:
                self.log("MODELS", f"نموذج {name}", "fail", f"{model_name} غير موجود في {module}")
            except Exception as e:
                self.log("MODELS", f"نموذج {name}", "fail", str(e))
    
    def test_5_permissions(self):
        """اختبار نظام الصلاحيات"""
        print("\n" + "="*80)
        print("المجموعة 5: نظام الصلاحيات")
        print("="*80)
        
        # 5.1 PermissionService exists
        try:
            from core.security import PermissionService
            self.log("PERMISSIONS", "PermissionService", "pass", "الخدمة متوفرة")
        except ImportError:
            self.log("PERMISSIONS", "PermissionService", "fail", "لا يمكن استيراد PermissionService")
            return
        
        # 5.2 Test basic permission check
        if self.test_user:
            try:
                can_view = PermissionService.can_view(self.test_user, 'accounting')
                self.log("PERMISSIONS", "فحص الصلاحيات", "pass", f"can_view accounting: {can_view}")
            except Exception as e:
                self.log("PERMISSIONS", "فحص الصلاحيات", "fail", str(e))
    
    def test_6_templates(self):
        """اختبار القوالب"""
        print("\n" + "="*80)
        print("المجموعة 6: القوالب (Templates)")
        print("="*80)
        
        from django.template.loader import get_template
        
        templates_to_test = [
            'base.html',
            'core/tony_erb_dashboard.html',
            'components/main_menu.html',
        ]
        
        for template_name in templates_to_test:
            try:
                get_template(template_name)
                self.log("TEMPLATES", f"قالب {template_name}", "pass")
            except Exception as e:
                self.log("TEMPLATES", f"قالب {template_name}", "fail", str(e))
    
    def test_7_static_files(self):
        """اختبار الملفات الثابتة"""
        print("\n" + "="*80)
        print("المجموعة 7: الملفات الثابتة (Static Files)")
        print("="*80)
        
        from django.conf import settings
        from django.contrib.staticfiles.finders import find
        
        static_files = [
            'css/ui_v2.css',
            'css/tony-erb-modern.css',
            'js/global_ui.js',
        ]
        
        for static_file in static_files:
            found = find(static_file)
            if found:
                self.log("STATIC", f"ملف {static_file}", "pass")
            else:
                self.log("STATIC", f"ملف {static_file}", "warn", "غير موجود")
    
    def test_8_database_integrity(self):
        """اختبار سلامة قاعدة البيانات"""
        print("\n" + "="*80)
        print("المجموعة 8: سلامة قاعدة البيانات")
        print("="*80)
        
        # 8.1 Check for standard fields
        try:
            from inventory.models import Product
            product = Product.objects.first()
            if product:
                has_created_at = hasattr(product, 'created_at')
                has_updated_at = hasattr(product, 'updated_at')
                if has_created_at and has_updated_at:
                    self.log("DB_INTEGRITY", "الحقول القياسية", "pass", "created_at & updated_at موجودة")
                else:
                    self.log("DB_INTEGRITY", "الحقول القياسية", "warn", "بعض الحقول القياسية مفقودة")
            else:
                self.log("DB_INTEGRITY", "الحقول القياسية", "warn", "لا توجد منتجات للاختبار")
        except Exception as e:
            self.log("DB_INTEGRITY", "الحقول القياسية", "fail", str(e))
    
    def run_all_tests(self):
        """تشغيل جميع الاختبارات"""
        print("\n" + "="*80)
        print("🚀 بدء الاختبار الشامل لنظام Tony ERP")
        print("="*80)
        
        self.test_1_system_health()
        self.test_2_authentication()
        self.test_3_core_pages()
        self.test_4_models()
        self.test_5_permissions()
        self.test_6_templates()
        self.test_7_static_files()
        self.test_8_database_integrity()
        
        self.print_summary()
    
    def print_summary(self):
        """طباعة ملخص النتائج"""
        print("\n" + "="*80)
        print("📊 ملخص نتائج الاختبار")
        print("="*80)
        
        total = self.passed + self.failed + self.warnings
        print(f"\nإجمالي الاختبارات: {total}")
        print(f"✅ نجح: {self.passed}")
        print(f"⚠️  تحذيرات: {self.warnings}")
        print(f"❌ فشل: {self.failed}")
        
        percentage = (self.passed / total * 100) if total > 0 else 0
        print(f"\nنسبة النجاح: {percentage:.1f}%")
        
        if self.failed == 0:
            print("\n🎉 ممتاز! النظام يعمل بشكل ممتاز!")
        elif self.failed < 5:
            print("\n👍 جيد! توجد بعض المشاكل البسيطة")
        else:
            print("\n⚠️  انتبه! توجد مشاكل تحتاج للمعالجة")
        
        print("="*80 + "\n")
        
        return self.failed == 0 and self.warnings < 3


if __name__ == '__main__':
    tester = TonyERPComprehensiveTest()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)

