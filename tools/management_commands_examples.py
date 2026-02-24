"""
Custom Django Management Commands للأوامر المخصصة
يتم وضع هذه الأوامر في core/management/commands/
"""

# للاستخدام، أنشئ الملفات في: core/management/commands/

# مثال 1: clear_old_logs.py
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import os

class Command(BaseCommand):
    help = 'حذف السجلات القديمة'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='عدد الأيام للاحتفاظ بالسجلات'
        )

    def handle(self, *args, **options):
        days = options['days']
        cutoff_date = timezone.now() - timedelta(days=days)
        
        logs_dir = 'logs'
        deleted_count = 0
        
        for filename in os.listdir(logs_dir):
            filepath = os.path.join(logs_dir, filename)
            if os.path.isfile(filepath):
                file_time = timezone.datetime.fromtimestamp(
                    os.path.getmtime(filepath)
                )
                if file_time < cutoff_date:
                    os.remove(filepath)
                    deleted_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'تم حذف {deleted_count} ملف سجل')
        )
"""

# مثال 2: generate_test_data.py
"""
from django.core.management.base import BaseCommand
from inventory.models import Product
from sales.models import Customer
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'إنشاء بيانات تجريبية للاختبار'

    def add_arguments(self, parser):
        parser.add_argument(
            '--products',
            type=int,
            default=10,
            help='عدد المنتجات'
        )
        parser.add_argument(
            '--customers',
            type=int,
            default=20,
            help='عدد العملاء'
        )

    def handle(self, *args, **options):
        products_count = options['products']
        customers_count = options['customers']
        
        # إنشاء منتجات
        for i in range(products_count):
            Product.objects.get_or_create(
                name=f'منتج تجريبي {i+1}',
                defaults={'price': 100 + i}
            )
        
        # إنشاء عملاء
        for i in range(customers_count):
            Customer.objects.get_or_create(
                name=f'عميل تجريبي {i+1}',
                defaults={'phone': f'05{i:08d}'}
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'تم إنشاء {products_count} منتج و {customers_count} عميل'
            )
        )
"""

# مثال 3: check_system_health.py
"""
from django.core.management.base import BaseCommand
from django.db import connection
from django.core.cache import cache
import requests

class Command(BaseCommand):
    help = 'فحص صحة النظام'

    def handle(self, *args, **options):
        checks = []
        
        # فحص قاعدة البيانات
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            checks.append(('Database', True))
        except Exception as e:
            checks.append(('Database', False, str(e)))
        
        # فحص Cache
        try:
            cache.set('health_check', 'ok', 10)
            result = cache.get('health_check')
            checks.append(('Cache', result == 'ok'))
        except Exception as e:
            checks.append(('Cache', False, str(e)))
        
        # فحص Disk Space
        import shutil
        try:
            total, used, free = shutil.disk_usage('/')
            free_gb = free // (2**30)
            checks.append(('Disk Space', free_gb > 1, f'{free_gb}GB free'))
        except Exception as e:
            checks.append(('Disk Space', False, str(e)))
        
        # عرض النتائج
        self.stdout.write('\n=== System Health Check ===\n')
        for check in checks:
            name = check[0]
            status = check[1]
            message = check[2] if len(check) > 2 else ''
            
            if status:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ {name}: OK {message}')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'✗ {name}: FAIL {message}')
                )
"""

# مثال 4: export_data.py
"""
from django.core.management.base import BaseCommand
from django.core import serializers
from inventory.models import Product
from sales.models import Customer
import json

class Command(BaseCommand):
    help = 'تصدير البيانات إلى JSON'

    def add_arguments(self, parser):
        parser.add_argument(
            '--model',
            type=str,
            choices=['products', 'customers', 'all'],
            default='all',
            help='البيانات المراد تصديرها'
        )
        parser.add_argument(
            '--output',
            type=str,
            default='export.json',
            help='ملف الإخراج'
        )

    def handle(self, *args, **options):
        model_choice = options['model']
        output_file = options['output']
        
        data = []
        
        if model_choice in ['products', 'all']:
            products = Product.objects.all()
            data.extend(json.loads(serializers.serialize('json', products)))
        
        if model_choice in ['customers', 'all']:
            customers = Customer.objects.all()
            data.extend(json.loads(serializers.serialize('json', customers)))
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        self.stdout.write(
            self.style.SUCCESS(f'تم تصدير {len(data)} سجل إلى {output_file}')
        )
"""

print("""
لإنشاء هذه الأوامر:

1. أنشئ المجلد: core/management/commands/
2. ضع ملف __init__.py في كل مجلد
3. أنشئ ملفات الأوامر (مثل clear_old_logs.py)
4. استخدمها: python manage.py <command_name>

الأوامر المقترحة:
- clear_old_logs - حذف السجلات القديمة
- generate_test_data - إنشاء بيانات تجريبية
- check_system_health - فحص صحة النظام
- export_data - تصدير البيانات
- optimize_database - تحسين قاعدة البيانات
- send_reports - إرسال التقارير الدورية
""")
