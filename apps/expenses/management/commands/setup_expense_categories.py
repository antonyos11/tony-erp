"""
أمر إنشاء تصنيفات المصروفات الافتراضية
يُشغَّل مرة واحدة عند إعداد النظام
python manage.py setup_expense_categories
"""
from django.core.management.base import BaseCommand
from apps.accounts.models import Account
from apps.expenses.models import ExpenseCategory


CATEGORIES = [
    # (name, account_code, parent_name, budget_monthly)
    # -- إدارية وعمومية --
    ('إدارية وعمومية', '61', None, 0),
    ('رواتب وأجور إدارية', '611', 'إدارية وعمومية', 0),
    ('إيجارات', '612', 'إدارية وعمومية', 0),
    ('كهرباء ومياه', '613', 'إدارية وعمومية', 0),
    ('اتصالات وإنترنت', '614', 'إدارية وعمومية', 0),
    ('صيانة وإصلاحات', '615', 'إدارية وعمومية', 0),
    ('نقل وانتقالات', '616', 'إدارية وعمومية', 0),
    ('أدوات مكتبية', '617', 'إدارية وعمومية', 0),
    ('مصروفات متنوعة', '619', 'إدارية وعمومية', 0),
    # -- بيع وتسويق --
    ('بيع وتسويق', '62', None, 0),
    ('مصروفات توصيل', '621', 'بيع وتسويق', 0),
    ('عمولات بائعين', '622', 'بيع وتسويق', 0),
    ('تسويق وإعلان', '623', 'بيع وتسويق', 0),
    # -- تمويلية --
    ('تمويلية', '63', None, 0),
    ('فوائد بنكية', '631', 'تمويلية', 0),
    ('عمولات بنكية', '632', 'تمويلية', 0),
]


class Command(BaseCommand):
    help = 'إنشاء تصنيفات المصروفات الافتراضية'

    def handle(self, *args, **options):
        self.stdout.write('🚀 بدء إنشاء تصنيفات المصروفات...')
        created_count = 0
        parents = {}

        for name, account_code, parent_name, budget in CATEGORIES:
            try:
                account = Account.objects.get(code=account_code)
            except Account.DoesNotExist:
                self.stdout.write(self.style.WARNING(
                    f'⚠️  الحساب {account_code} غير موجود — تخطي تصنيف "{name}"'
                ))
                continue

            parent = parents.get(parent_name) if parent_name else None

            category, created = ExpenseCategory.objects.get_or_create(
                name=name,
                defaults={
                    'account': account,
                    'parent': parent,
                    'budget_monthly': budget,
                    'is_active': True,
                }
            )

            if created:
                created_count += 1
                self.stdout.write(f'  ✅ {name}')
            else:
                self.stdout.write(f'  ⏭️  موجود بالفعل: {name}')

            parents[name] = category

        self.stdout.write(self.style.SUCCESS(
            f'✅ تم إنشاء {created_count} تصنيف مصروفات'
        ))
