"""
أمر Django لإنشاء الأدوار والصلاحيات المحاسبية

الاستخدام:
python manage.py create_accounting_roles
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounting.permissions import (
    create_accounting_roles,
    assign_user_to_role,
    AccountingRoles
)


class Command(BaseCommand):
    help = 'إنشاء الأدوار والصلاحيات المحاسبية الثلاثة (كاشير، محاسب، مدير مالي)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--assign-superusers',
            action='store_true',
            help='تعيين جميع المستخدمين المديرين (superusers) كـ مدير مالي تلقائياً',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 بدء إنشاء الأدوار المحاسبية...\n'))
        
        # إنشاء الأدوار
        results = create_accounting_roles()
        
        # عرض النتائج
        self.stdout.write(self.style.SUCCESS('\n📊 ملخص العملية:'))
        self.stdout.write(f"  ✅ أدوار تم إنشاؤها: {len(results['created'])}")
        self.stdout.write(f"  🔄 أدوار تم تحديثها: {len(results['updated'])}")
        self.stdout.write(f"  ❌ أخطاء: {len(results['errors'])}")
        
        if results['errors']:
            self.stdout.write(self.style.WARNING('\n⚠️ الأخطاء:'))
            for error in results['errors']:
                self.stdout.write(f"  • {error}")
        
        # تعيين المديرين كـ مدير مالي
        if options['assign_superusers']:
            self.stdout.write(self.style.SUCCESS('\n👔 تعيين المستخدمين المديرين كـ مدير مالي...'))
            superusers = User.objects.filter(is_superuser=True, is_active=True)
            
            assigned_count = 0
            for user in superusers:
                if assign_user_to_role(user, AccountingRoles.CFO):
                    assigned_count += 1
            
            self.stdout.write(self.style.SUCCESS(f'  ✅ تم تعيين {assigned_count} مستخدم'))
        
        # رسالة النجاح النهائية
        self.stdout.write(self.style.SUCCESS('\n✨ تم إنشاء الأدوار المحاسبية بنجاح!\n'))
        
        # تعليمات ما بعد التثبيت
        self.stdout.write(self.style.WARNING('📝 الخطوات التالية:'))
        self.stdout.write('  1. قم بتعيين المستخدمين للأدوار المناسبة')
        self.stdout.write('  2. استخدم الكود التالي لتعيين مستخدم:\n')
        self.stdout.write('     from accounting.permissions import assign_user_to_role, AccountingRoles')
        self.stdout.write('     user = User.objects.get(username="اسم_المستخدم")')
        self.stdout.write('     assign_user_to_role(user, AccountingRoles.ACCOUNTANT)\n')

