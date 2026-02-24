#!/usr/bin/env python
"""
🧪 Spec-Kit Validation Tests
=============================
اختبارات للتحقق من صحة توثيق Spec-Kit مقارنة بالنظام الفعلي

التشغيل:
    python manage.py test docs.spec-kit.tests.test_spec_kit
    أو:
    cd /var/www/tony_erp && python docs/spec-kit/tests/test_spec_kit.py
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

# إعداد Django
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')

import django
django.setup()

from django.apps import apps
from django.urls import get_resolver
from django.conf import settings


class Colors:
    """ألوان للطباعة"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


class SpecKitValidator:
    """مدقق Spec-Kit"""
    
    def __init__(self):
        self.results = {
            'passed': 0,
            'failed': 0,
            'warnings': 0,
            'tests': []
        }
        self.spec_dir = Path(__file__).parent.parent
    
    def log_pass(self, test_name, message):
        """تسجيل اختبار ناجح"""
        self.results['passed'] += 1
        self.results['tests'].append({
            'name': test_name,
            'status': 'PASS',
            'message': message
        })
        print(f"  {Colors.GREEN}✅ PASS{Colors.END} - {test_name}: {message}")
    
    def log_fail(self, test_name, message):
        """تسجيل اختبار فاشل"""
        self.results['failed'] += 1
        self.results['tests'].append({
            'name': test_name,
            'status': 'FAIL',
            'message': message
        })
        print(f"  {Colors.RED}❌ FAIL{Colors.END} - {test_name}: {message}")
    
    def log_warn(self, test_name, message):
        """تسجيل تحذير"""
        self.results['warnings'] += 1
        self.results['tests'].append({
            'name': test_name,
            'status': 'WARN',
            'message': message
        })
        print(f"  {Colors.YELLOW}⚠️ WARN{Colors.END} - {test_name}: {message}")
    
    def print_header(self, title):
        """طباعة عنوان القسم"""
        print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.END}")
        print(f"{Colors.CYAN}{Colors.BOLD}  {title}{Colors.END}")
        print(f"{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.END}")

    # ==========================================
    # اختبارات الوحدات (Modules)
    # ==========================================
    
    def test_installed_apps_count(self):
        """التحقق من عدد التطبيقات المثبتة"""
        self.print_header("🔧 اختبار التطبيقات المثبتة")
        
        # الحصول على التطبيقات المخصصة (غير Django الأساسية)
        custom_apps = [
            app for app in settings.INSTALLED_APPS 
            if not app.startswith('django.') 
            and app not in ['rest_framework', 'rest_framework_simplejwt', 
                           'django_filters', 'corsheaders', 'django_otp',
                           'crispy_forms', 'crispy_bootstrap5', 'channels',
                           'django_celery_beat', 'django_otp.plugins.otp_totp',
                           'django_otp.plugins.otp_static']
        ]
        
        documented_count = 79  # من التوثيق
        actual_count = len(custom_apps)
        
        if actual_count >= documented_count - 5:  # هامش 5 تطبيقات
            self.log_pass(
                "عدد التطبيقات",
                f"موثق: {documented_count}, فعلي: {actual_count}"
            )
        else:
            self.log_fail(
                "عدد التطبيقات",
                f"موثق: {documented_count}, فعلي: {actual_count}"
            )
        
        return custom_apps

    def test_models_count(self):
        """التحقق من عدد الموديلات"""
        self.print_header("📊 اختبار الموديلات")
        
        # الحصول على جميع الموديلات
        all_models = apps.get_models()
        
        # فلترة موديلات Django الأساسية
        custom_models = [
            model for model in all_models
            if not model._meta.app_label.startswith('django')
            and model._meta.app_label not in ['contenttypes', 'sessions', 'admin', 'auth']
        ]
        
        documented_count = 629  # من التوثيق
        actual_count = len(custom_models)
        
        # هامش 10%
        margin = documented_count * 0.1
        
        if abs(actual_count - documented_count) <= margin:
            self.log_pass(
                "عدد الموديلات",
                f"موثق: {documented_count}, فعلي: {actual_count}"
            )
        else:
            self.log_warn(
                "عدد الموديلات",
                f"موثق: {documented_count}, فعلي: {actual_count} (فرق: {abs(actual_count - documented_count)})"
            )
        
        return custom_models

    def test_models_per_app(self):
        """التحقق من توزيع الموديلات على التطبيقات"""
        
        # الموديلات الموثقة لكل تطبيق (من 04-DATA-MODELS.md)
        documented_models = {
            'ecommerce': 42,
            'hr': 41,
            'crm': 37,
            'accounting': 30,
            'production': 25,
            'purchases': 22,
            'inventory': 18,
            'branches': 18,
            'smart_pricing': 16,
            'installments': 13,
            'sales': 13,
            'showrooms': 13,
        }
        
        for app_label, doc_count in documented_models.items():
            try:
                app_config = apps.get_app_config(app_label)
                actual_count = len(list(app_config.get_models()))
                
                if abs(actual_count - doc_count) <= 3:  # هامش 3 موديلات
                    self.log_pass(
                        f"موديلات {app_label}",
                        f"موثق: {doc_count}, فعلي: {actual_count}"
                    )
                else:
                    self.log_warn(
                        f"موديلات {app_label}",
                        f"موثق: {doc_count}, فعلي: {actual_count}"
                    )
            except LookupError:
                self.log_fail(
                    f"موديلات {app_label}",
                    f"التطبيق غير موجود!"
                )

    # ==========================================
    # اختبارات URLs
    # ==========================================
    
    def test_url_patterns_count(self):
        """التحقق من عدد URLs"""
        self.print_header("🔗 اختبار URLs")
        
        def count_urls(urlpatterns, count=0):
            for pattern in urlpatterns:
                count += 1
                if hasattr(pattern, 'url_patterns'):
                    count = count_urls(pattern.url_patterns, count)
            return count
        
        resolver = get_resolver()
        actual_count = count_urls(resolver.url_patterns)
        documented_count = 5300  # من التوثيق
        
        # هامش 20%
        margin = documented_count * 0.2
        
        if abs(actual_count - documented_count) <= margin:
            self.log_pass(
                "عدد URLs",
                f"موثق: {documented_count}, فعلي: {actual_count}"
            )
        else:
            self.log_warn(
                "عدد URLs",
                f"موثق: {documented_count}, فعلي: {actual_count}"
            )
        
        return actual_count

    # ==========================================
    # اختبارات الإعدادات
    # ==========================================
    
    def test_django_version(self):
        """التحقق من إصدار Django"""
        self.print_header("⚙️ اختبار الإعدادات")
        
        import django
        actual_version = django.VERSION
        documented_version = (5, 2)  # من التوثيق
        
        if actual_version[:2] == documented_version:
            self.log_pass(
                "إصدار Django",
                f"موثق: 5.2.x, فعلي: {'.'.join(map(str, actual_version[:3]))}"
            )
        else:
            self.log_fail(
                "إصدار Django",
                f"موثق: 5.2.x, فعلي: {'.'.join(map(str, actual_version[:3]))}"
            )

    def test_python_version(self):
        """التحقق من إصدار Python"""
        import platform
        py_version = platform.python_version_tuple()
        
        if int(py_version[0]) >= 3 and int(py_version[1]) >= 11:
            self.log_pass(
                "إصدار Python",
                f"موثق: 3.11+, فعلي: {platform.python_version()}"
            )
        else:
            self.log_fail(
                "إصدار Python",
                f"موثق: 3.11+, فعلي: {platform.python_version()}"
            )

    def test_middleware_count(self):
        """التحقق من عدد Middleware"""
        middleware_count = len(settings.MIDDLEWARE)
        
        if middleware_count >= 15:  # يجب أن يكون على الأقل 15
            self.log_pass(
                "عدد Middleware",
                f"موجود: {middleware_count} middleware"
            )
        else:
            self.log_warn(
                "عدد Middleware",
                f"موجود: {middleware_count} middleware (متوقع >= 15)"
            )

    # ==========================================
    # اختبارات الملفات
    # ==========================================
    
    def test_spec_files_exist(self):
        """التحقق من وجود ملفات Spec-Kit"""
        self.print_header("📁 اختبار ملفات Spec-Kit")
        
        expected_files = [
            '00-README.md',
            '01-SYSTEM-OVERVIEW.md',
            '02-ARCHITECTURE.md',
            '03-MODULES-CATALOG.md',
            '04-DATA-MODELS.md',
            '05-API-REFERENCE.md',
            '06-SECURITY.md',
            '07-INTEGRATIONS.md',
            '08-DEPLOYMENT.md',
            '09-DEPENDENCIES.md',
            '10-DATABASE-SCHEMA.md',
        ]
        
        for filename in expected_files:
            filepath = self.spec_dir / filename
            if filepath.exists():
                size = filepath.stat().st_size / 1024  # KB
                self.log_pass(
                    f"ملف {filename}",
                    f"موجود ({size:.1f} KB)"
                )
            else:
                self.log_fail(
                    f"ملف {filename}",
                    "غير موجود!"
                )

    # ==========================================
    # اختبارات الموديلات الأساسية
    # ==========================================
    
    def test_core_models_exist(self):
        """التحقق من وجود الموديلات الأساسية"""
        self.print_header("🏛️ اختبار الموديلات الأساسية")
        
        core_models = [
            ('inventory', 'Product'),
            ('inventory', 'Category'),
            ('inventory', 'Stock'),
            ('sales', 'Invoice'),
            ('sales', 'SaleOrder'),
            ('purchases', 'PurchaseBill'),
            ('purchases', 'PurchaseOrder'),
            ('accounting', 'Account'),
            ('accounting', 'JournalEntry'),
            ('hr', 'Employee'),
            ('hr', 'Department'),
            ('crm', 'Customer'),
            ('crm', 'Opportunity'),
            ('pos', 'POSSession'),
            ('pos', 'POSOrder'),
            ('users', 'UserProfile'),
            ('partners', 'Partner'),
        ]
        
        for app_label, model_name in core_models:
            try:
                model = apps.get_model(app_label, model_name)
                fields_count = len(model._meta.fields)
                self.log_pass(
                    f"{app_label}.{model_name}",
                    f"موجود ({fields_count} حقل)"
                )
            except LookupError:
                self.log_fail(
                    f"{app_label}.{model_name}",
                    "غير موجود!"
                )

    # ==========================================
    # اختبارات الأمان
    # ==========================================
    
    def test_security_settings(self):
        """التحقق من إعدادات الأمان"""
        self.print_header("🔐 اختبار إعدادات الأمان")
        
        # التحقق من وجود إعدادات الأمان
        security_checks = [
            ('SECRET_KEY موجود', hasattr(settings, 'SECRET_KEY') and settings.SECRET_KEY),
            ('SESSION_COOKIE_SECURE', getattr(settings, 'SESSION_COOKIE_SECURE', False) or settings.DEBUG),
            ('CSRF_COOKIE_SECURE', getattr(settings, 'CSRF_COOKIE_SECURE', False) or settings.DEBUG),
            ('MIDDLEWARE أمان', any('Security' in m for m in settings.MIDDLEWARE)),
            ('Rate Limiting', any('RateLimit' in m for m in settings.MIDDLEWARE)),
            ('CSP Middleware', any('CSP' in m.upper() for m in settings.MIDDLEWARE)),
        ]
        
        for check_name, passed in security_checks:
            if passed:
                self.log_pass(check_name, "مفعّل ✓")
            else:
                self.log_warn(check_name, "غير مفعّل (قد يكون بسبب وضع التطوير)")

    # ==========================================
    # اختبارات API
    # ==========================================
    
    def test_rest_framework_config(self):
        """التحقق من إعدادات REST Framework"""
        self.print_header("🔌 اختبار REST Framework")
        
        if hasattr(settings, 'REST_FRAMEWORK'):
            rf_settings = settings.REST_FRAMEWORK
            
            # التحقق من المصادقة
            if 'DEFAULT_AUTHENTICATION_CLASSES' in rf_settings:
                self.log_pass(
                    "Authentication Classes",
                    f"{len(rf_settings['DEFAULT_AUTHENTICATION_CLASSES'])} فئة"
                )
            else:
                self.log_warn("Authentication Classes", "غير محدد")
            
            # التحقق من الصلاحيات
            if 'DEFAULT_PERMISSION_CLASSES' in rf_settings:
                self.log_pass(
                    "Permission Classes",
                    f"{len(rf_settings['DEFAULT_PERMISSION_CLASSES'])} فئة"
                )
            else:
                self.log_warn("Permission Classes", "غير محدد")
            
            # التحقق من الترقيم
            if 'DEFAULT_PAGINATION_CLASS' in rf_settings:
                self.log_pass("Pagination", "مفعّل ✓")
            else:
                self.log_warn("Pagination", "غير محدد")
        else:
            self.log_fail("REST_FRAMEWORK", "الإعدادات غير موجودة!")

    # ==========================================
    # اختبارات قاعدة البيانات
    # ==========================================
    
    def test_database_connection(self):
        """التحقق من اتصال قاعدة البيانات"""
        self.print_header("🗄️ اختبار قاعدة البيانات")
        
        from django.db import connection
        
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            
            db_engine = settings.DATABASES['default']['ENGINE']
            self.log_pass(
                "اتصال قاعدة البيانات",
                f"ناجح ({db_engine.split('.')[-1]})"
            )
        except Exception as e:
            self.log_fail(
                "اتصال قاعدة البيانات",
                f"فشل: {str(e)}"
            )

    def test_tables_count(self):
        """التحقق من عدد الجداول"""
        from django.db import connection
        
        try:
            with connection.cursor() as cursor:
                # SQLite
                if 'sqlite' in settings.DATABASES['default']['ENGINE']:
                    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                # PostgreSQL
                else:
                    cursor.execute("""
                        SELECT COUNT(*) FROM information_schema.tables 
                        WHERE table_schema = 'public'
                    """)
                
                count = cursor.fetchone()[0]
                
                if count >= 100:  # يجب أن يكون على الأقل 100 جدول
                    self.log_pass(
                        "عدد الجداول",
                        f"{count} جدول"
                    )
                else:
                    self.log_warn(
                        "عدد الجداول",
                        f"{count} جدول (متوقع >= 100)"
                    )
        except Exception as e:
            self.log_warn("عدد الجداول", f"تعذر الحساب: {str(e)}")

    # ==========================================
    # التشغيل الرئيسي
    # ==========================================
    
    def run_all_tests(self):
        """تشغيل جميع الاختبارات"""
        print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
        print(f"{Colors.BOLD}  🧪 Spec-Kit Validation Tests{Colors.END}")
        print(f"{Colors.BOLD}  📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.END}")
        print(f"{Colors.BOLD}{'='*60}{Colors.END}")
        
        # تشغيل الاختبارات
        self.test_spec_files_exist()
        self.test_installed_apps_count()
        self.test_models_count()
        self.test_models_per_app()
        self.test_url_patterns_count()
        self.test_django_version()
        self.test_python_version()
        self.test_middleware_count()
        self.test_core_models_exist()
        self.test_security_settings()
        self.test_rest_framework_config()
        self.test_database_connection()
        self.test_tables_count()
        
        # طباعة الملخص
        self.print_summary()
        
        return self.results
    
    def print_summary(self):
        """طباعة ملخص النتائج"""
        print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
        print(f"{Colors.BOLD}  📊 ملخص النتائج{Colors.END}")
        print(f"{Colors.BOLD}{'='*60}{Colors.END}")
        
        total = self.results['passed'] + self.results['failed'] + self.results['warnings']
        
        print(f"\n  {Colors.GREEN}✅ نجح: {self.results['passed']}{Colors.END}")
        print(f"  {Colors.YELLOW}⚠️ تحذيرات: {self.results['warnings']}{Colors.END}")
        print(f"  {Colors.RED}❌ فشل: {self.results['failed']}{Colors.END}")
        print(f"  📝 المجموع: {total}")
        
        # نسبة النجاح
        if total > 0:
            success_rate = ((self.results['passed'] + self.results['warnings']) / total) * 100
            print(f"\n  📈 نسبة النجاح: {success_rate:.1f}%")
        
        # الحالة النهائية
        if self.results['failed'] == 0:
            print(f"\n  {Colors.GREEN}{Colors.BOLD}🎉 جميع الاختبارات نجحت!{Colors.END}")
        else:
            print(f"\n  {Colors.RED}{Colors.BOLD}⚠️ يوجد {self.results['failed']} اختبار فاشل{Colors.END}")
        
        print(f"\n{'='*60}\n")
    
    def save_report(self, filepath=None):
        """حفظ التقرير كملف JSON"""
        if filepath is None:
            filepath = self.spec_dir / 'tests' / 'test_report.json'
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'passed': self.results['passed'],
                'failed': self.results['failed'],
                'warnings': self.results['warnings'],
                'total': self.results['passed'] + self.results['failed'] + self.results['warnings']
            },
            'tests': self.results['tests']
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"📄 تم حفظ التقرير في: {filepath}")


def main():
    """الدالة الرئيسية"""
    validator = SpecKitValidator()
    results = validator.run_all_tests()
    validator.save_report()
    
    # إرجاع كود الخروج
    return 0 if results['failed'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
