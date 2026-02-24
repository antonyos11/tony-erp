"""
أمر إدارة Django لإعداد نظام نقاط البيع (POS)
===============================================
الاستخدام:
    python manage.py setup_pos
    python manage.py setup_pos --verbose
    python manage.py setup_pos --quiet
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from payments.models import PaymentMethod
from inventory.models import Location, Product
from accounting.models import Account
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'إعداد نظام نقاط البيع (POS) - إنشاء طرق الدفع والمواقع المطلوبة'

    def add_arguments(self, parser):
        parser.add_argument(
            '--quiet',
            action='store_true',
            help='إخفاء رسائل التفاصيل',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='إعادة إنشاء البيانات حتى لو موجودة',
        )

    def handle(self, *args, **options):
        quiet = options.get('quiet', False)
        force = options.get('force', False)
        
        if not quiet:
            self.stdout.write("\n" + "=" * 60)
            self.stdout.write(self.style.SUCCESS("🏪  إعداد نظام نقاط البيع (POS)"))
            self.stdout.write("=" * 60 + "\n")
        
        try:
            with transaction.atomic():
                # 1. إنشاء طرق الدفع
                if not quiet:
                    self.stdout.write("📋 1. إعداد طرق الدفع...")
                created, updated = self._create_payment_methods(quiet, force)
                if not quiet:
                    self.stdout.write(f"   → تم إنشاء {created} طريقة جديدة، تحديث {updated} موجودة\n")
                
                # 2. إنشاء موقع POS
                if not quiet:
                    self.stdout.write("📍 2. إعداد موقع نقطة البيع...")
                self._create_pos_location(quiet, force)
                if not quiet:
                    self.stdout.write("")
                
                # 3. ربط حساب الصندوق
                if not quiet:
                    self.stdout.write("💰 3. ربط الحسابات المحاسبية...")
                self._verify_cash_account(quiet)
                if not quiet:
                    self.stdout.write("")
                
                # 4. التحقق من المتطلبات
                if not quiet:
                    self.stdout.write("✅ 4. التحقق من المتطلبات...")
                issues = self._verify_requirements(quiet)
                
                if issues and not quiet:
                    self.stdout.write(self.style.WARNING("\n⚠️  تحذيرات:"))
                    for issue in issues:
                        self.stdout.write(f"   - {issue}")
                
                if not quiet:
                    self.stdout.write("\n" + "=" * 60)
                    self.stdout.write(self.style.SUCCESS("🎉  تم إعداد نظام POS بنجاح!"))
                    self.stdout.write("=" * 60)
                    
                    # إحصائيات نهائية
                    self.stdout.write("\n📊 الإحصائيات:")
                    self.stdout.write(f"   - طرق الدفع: {PaymentMethod.objects.count()}")
                    self.stdout.write(f"   - مواقع POS: {Location.objects.filter(type='store').count()}")
                    
                    self.stdout.write("\n💡 الخطوات التالية:")
                    self.stdout.write("   1. افتح نظام POS من: /pos/")
                    self.stdout.write("   2. ابدأ جلسة جديدة لنقطة البيع")
                    self.stdout.write("   3. أضف منتجات للسلة وأتم عملية البيع")
                    self.stdout.write("")
                    
        except Exception as e:
            raise CommandError(f"خطأ أثناء إعداد POS: {str(e)}")

    def _create_payment_methods(self, quiet=False, force=False):
        """إنشاء طرق الدفع الأساسية"""
        
        payment_methods_data = [
            {'name': 'نقدي', 'type': 'cash', 'display_order': 1, 'is_active': True},
            {'name': 'فيزا', 'type': 'credit_card', 'display_order': 2, 'is_active': True},
            {'name': 'ماستر كارد', 'type': 'credit_card', 'display_order': 3, 'is_active': True},
            {'name': 'حوالة بنكية', 'type': 'bank_transfer', 'display_order': 4, 'is_active': True},
            {'name': 'فودافون كاش', 'type': 'vodafone_cash', 'display_order': 5, 'is_active': True},
            {'name': 'إنستا باي', 'type': 'instapay', 'display_order': 6, 'is_active': True},
            {'name': 'شيك', 'type': 'check', 'display_order': 7, 'is_active': True},
        ]
        
        created_count = 0
        updated_count = 0
        
        for method_data in payment_methods_data:
            method, created = PaymentMethod.objects.get_or_create(
                name=method_data['name'],
                defaults=method_data
            )
            if created:
                created_count += 1
                if not quiet:
                    self.stdout.write(self.style.SUCCESS(f"  ✅ تم إنشاء: {method.name}"))
            else:
                if force:
                    for key, value in method_data.items():
                        setattr(method, key, value)
                    method.save()
                updated_count += 1
                if not quiet:
                    self.stdout.write(f"  ✔️ موجود: {method.name}")
        
        return created_count, updated_count

    def _create_pos_location(self, quiet=False, force=False):
        """إنشاء موقع/معرض افتراضي للـ POS"""
        
        pos_location, created = Location.objects.get_or_create(
            code='POS-MAIN',
            defaults={
                'name': 'المعرض الرئيسي - نقطة البيع',
                'type': 'store',
                'address': 'المتجر الرئيسي',
                'is_active': True,
                'is_default': True,
            }
        )
        
        if created:
            if not quiet:
                self.stdout.write(self.style.SUCCESS(f"  ✅ تم إنشاء موقع POS: {pos_location.name}"))
        else:
            if not quiet:
                self.stdout.write(f"  ✔️ موقع POS موجود: {pos_location.name}")

    def _verify_cash_account(self, quiet=False):
        """ربط حساب الصندوق بطريقة الدفع النقدي"""
        
        cash_account = Account.objects.filter(name__icontains='صندوق').first()
        if not cash_account:
            cash_account = Account.objects.filter(account_type='asset').first()
        
        if cash_account:
            cash_method = PaymentMethod.objects.filter(type='cash').first()
            if cash_method and not cash_method.account:
                cash_method.account = cash_account
                cash_method.save()
                if not quiet:
                    self.stdout.write(self.style.SUCCESS(
                        f"  ✅ تم ربط '{cash_account.name}' بالدفع النقدي"))
            elif not quiet:
                self.stdout.write("  ✔️ حساب الصندوق مرتبط مسبقاً")
        elif not quiet:
            self.stdout.write(self.style.WARNING(
                "  ⚠️ لم يتم العثور على حساب صندوق"))

    def _verify_requirements(self, quiet=False):
        """التحقق من المتطلبات الأخرى"""
        
        issues = []
        
        if not User.objects.filter(is_active=True).exists():
            issues.append("لا يوجد مستخدمين نشطين")
        
        # Product لا يحتوي على is_active، استخدم count() فقط
        product_count = Product.objects.count()
        if product_count == 0:
            issues.append("لا توجد منتجات - يجب إضافة منتجات للبيع")
        elif not quiet:
            self.stdout.write(f"  ✅ يوجد {product_count} منتج")
        
        return issues
