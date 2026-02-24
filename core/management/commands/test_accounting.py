#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
إختبار نظام الحسابات ومراكز التكلفة - Django Management Command
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from accounting.models import Account, CostCenter
from datetime import datetime
import json

User = get_user_model()

class Command(BaseCommand):
    help = 'اختبار شامل لنظام الحسابات ومراكز التكلفة'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = Client()
        self.test_results = []
        self.admin_user = None
        
    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='عرض تفاصيل إضافية',
        )
    
    def log_result(self, test_name, success, details):
        """تسجيل نتيجة الاختبار"""
        result = {
            'test': test_name,
            'success': success,
            'details': details,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        self.test_results.append(result)
        status = "✅ نجح" if success else "❌ فشل"
        self.stdout.write(f"{status} {test_name}: {details}")
        
    def setup_test_environment(self):
        """إعداد بيئة الاختبار"""
        try:
            # التأكد من وجود مستخدم admin
            admin_user = User.objects.filter(username='superadmin').first()
            if not admin_user:
                admin_user = User.objects.create_superuser(
                    username='superadmin',
                    email='admin@example.com',
                    password='admin123'
                )
            self.admin_user = admin_user
            
            # لا نحتاج لتسجيل الدخول للاختبارات المباشرة على النماذج
            self.log_result(
                "إعداد بيئة الاختبار",
                True,
                f"تم إنشاء/العثور على المستخدم الإداري: {admin_user.username}"
            )
            return True
            
        except Exception as e:
            self.log_result("إعداد بيئة الاختبار", False, f"خطأ: {str(e)}")
            return False
    
    def test_create_account(self):
        """اختبار إنشاء حساب جديد"""
        try:
            # بيانات الحساب الجديد
            account_data = {
                'name': 'حساب اختبار - صندوق',
                'account_type': 'asset',
                'code': 'TEST001',  # استخدام 'code' بدلاً من 'account_code'
                'description': 'حساب تجريبي لاختبار النظام',
                'is_active': True
            }
            
            # إنشاء الحساب باستخدام ORM
            account = Account.objects.create(**account_data)
            
            # التحقق من الحفظ
            saved_account = Account.objects.get(pk=account.pk)
            
            # التحقق من جميع الحقول
            all_fields_correct = (
                saved_account.name == account_data['name'] and
                saved_account.account_type == account_data['account_type'] and
                saved_account.code == account_data['code'] and
                saved_account.description == account_data['description'] and
                saved_account.is_active == account_data['is_active']
            )
            
            self.created_account_id = account.pk
            
            self.log_result(
                "إنشاء حساب جديد",
                all_fields_correct,
                f"تم إنشاء الحساب بالمعرف {account.pk} - جميع الحقول صحيحة: {all_fields_correct}"
            )
            
            return account.pk if all_fields_correct else None
            
        except Exception as e:
            self.log_result("إنشاء حساب جديد", False, f"خطأ: {str(e)}")
            return None
    
    def test_update_account(self, account_id):
        """اختبار تحديث الحساب"""
        try:
            if not account_id:
                self.log_result("تحديث الحساب", False, "لا يوجد معرف حساب للتحديث")
                return False
            
            # الحصول على الحساب
            account = Account.objects.get(pk=account_id)
            
            # تحديث البيانات
            new_name = "حساب اختبار محدث - الخزينة الرئيسية"
            new_description = "تم تحديث الوصف - اختبار التحديث"
            
            account.name = new_name
            account.description = new_description
            account.save()
            
            # التحقق من التحديث
            updated_account = Account.objects.get(pk=account_id)
            
            update_success = (
                updated_account.name == new_name and
                updated_account.description == new_description
            )
            
            self.log_result(
                "تحديث الحساب",
                update_success,
                f"تم تحديث الحساب {account_id} - التحديث انعكس بنجاح: {update_success}"
            )
            
            return update_success
            
        except Exception as e:
            self.log_result("تحديث الحساب", False, f"خطأ: {str(e)}")
            return False
    
    def test_create_cost_center(self, account_id):
        """اختبار إنشاء مركز تكلفة"""
        try:
            if not account_id:
                self.log_result("إنشاء مركز التكلفة", False, "لا يوجد معرف حساب للربط")
                return None
            
            # الحصول على الحساب
            account = Account.objects.get(pk=account_id)
            
            # بيانات مركز التكلفة (بدون account field مباشرة)
            cost_center_data = {
                'name': 'مركز تكلفة اختبار - الإدارة العامة',
                'code': 'CC001',
                'description': 'مركز تكلفة تجريبي',
                'is_active': True,
                # 'account': account  # إزالة هذا السطر لأنه غير موجود في النموذج
            }
            
            # إنشاء مركز التكلفة
            cost_center = CostCenter.objects.create(**cost_center_data)
            
            # التحقق من الحفظ
            saved_cost_center = CostCenter.objects.get(pk=cost_center.pk)
            
            creation_success = (
                saved_cost_center.name == cost_center_data['name'] and
                saved_cost_center.code == cost_center_data['code']
            )
            
            self.created_cost_center_id = cost_center.pk
            
            self.log_result(
                "إنشاء مركز التكلفة",
                creation_success,
                f"تم إنشاء مركز التكلفة {cost_center.pk} - الإنشاء ناجح: {creation_success}"
            )
            
            return cost_center.pk if creation_success else None
            
        except Exception as e:
            self.log_result("إنشاء مركز التكلفة", False, f"خطأ: {str(e)}")
            return None
    
    def test_url_endpoints(self):
        """اختبار مسارات API"""
        endpoints = [
            ('/accounting/accounts/', 'GET', 'قائمة الحسابات'),
            ('/accounting/accounts/create/', 'GET', 'صفحة إنشاء حساب'),
            ('/accounting/cost-centers/', 'GET', 'قائمة مراكز التكلفة'),
        ]
        
        # إضافة مسار تفاصيل الحساب إذا كان متوفراً
        if hasattr(self, 'created_account_id') and self.created_account_id:
            endpoints.append((f'/accounting/accounts/{self.created_account_id}/details/', 'GET', 'تفاصيل الحساب'))
        
        url_results = []
        
        for endpoint, method, description in endpoints:
            try:
                # محاولة الوصول بدون تسجيل دخول أولاً
                response = self.client.get(endpoint)
                status_code = response.status_code
                
                # إذا كان 302 (إعادة توجيه) أو 403، نسجل دخول ونجرب مرة أخرى
                if status_code in [302, 403]:
                    self.client.login(username='superadmin', password='admin123')
                    response = self.client.get(endpoint)
                    status_code = response.status_code
                
                success = status_code in [200, 201]
                
                url_results.append({
                    'url': endpoint,
                    'method': method,
                    'status_code': status_code,
                    'success': success,
                    'description': description
                })
                
                status_text = "نجح" if success else "فشل"
                self.log_result(
                    f"اختبار المسار {endpoint}",
                    success,
                    f"{description} - Status Code: {status_code} - {status_text}"
                )
                
            except Exception as e:
                url_results.append({
                    'url': endpoint,
                    'method': method,
                    'status_code': 'ERROR',
                    'success': False,
                    'description': description,
                    'error': str(e)
                })
                
                self.log_result(
                    f"اختبار المسار {endpoint}",
                    False,
                    f"{description} - خطأ: {str(e)}"
                )
        
        return url_results
    
    def generate_final_report(self):
        """إنتاج التقرير النهائي"""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("📊 التقرير النهائي لاختبار نظام الحسابات ومراكز التكلفة")
        self.stdout.write("=" * 60)
        
        total_tests = len(self.test_results)
        successful_tests = len([r for r in self.test_results if r['success']])
        failed_tests = total_tests - successful_tests
        
        self.stdout.write(f"إجمالي الاختبارات: {total_tests}")
        self.stdout.write(f"الاختبارات الناجحة: {successful_tests} ✅")
        self.stdout.write(f"الاختبارات الفاشلة: {failed_tests} ❌")
        self.stdout.write(f"معدل النجاح: {(successful_tests/total_tests)*100:.1f}%")
        
        self.stdout.write("\n📝 تفاصيل النتائج:")
        self.stdout.write("-" * 60)
        
        for result in self.test_results:
            status = "✅ نجح" if result['success'] else "❌ فشل"
            self.stdout.write(f"{status} {result['test']}")
            self.stdout.write(f"   التفاصيل: {result['details']}")
            self.stdout.write(f"   الوقت: {result['timestamp']}")
            self.stdout.write("-" * 40)
        
        # ملخص الوضع النهائي
        self.stdout.write("\n🎯 الملخص:")
        if failed_tests == 0:
            self.stdout.write(self.style.SUCCESS("✅ جميع الاختبارات نجحت! النظام يعمل بشكل مثالي."))
        elif failed_tests <= 2:
            self.stdout.write(self.style.WARNING("⚠️ معظم الاختبارات نجحت مع بعض المشاكل الطفيفة."))
        else:
            self.stdout.write(self.style.ERROR("❌ يوجد مشاكل في النظام تحتاج لمعالجة."))
    
    def handle(self, *args, **options):
        """المعالج الرئيسي للأمر"""
        self.stdout.write("🚀 بدء اختبار نظام الحسابات ومراكز التكلفة في Tony ERP")
        self.stdout.write("=" * 60)
        
        # إعداد البيئة
        if not self.setup_test_environment():
            self.stdout.write(self.style.ERROR("❌ فشل في إعداد بيئة الاختبار"))
            return
        
        # اختبار إنشاء الحساب
        account_id = self.test_create_account()
        
        # اختبار تحديث الحساب
        self.test_update_account(account_id)
        
        # اختبار إنشاء مركز التكلفة
        cost_center_id = self.test_create_cost_center(account_id)
        
        # اختبار المسارات
        url_results = self.test_url_endpoints()
        
        # تقرير النتائج النهائي
        self.generate_final_report()