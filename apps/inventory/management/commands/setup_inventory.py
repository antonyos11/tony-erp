"""
أمر إعداد بيانات المخزون الأساسية
python manage.py setup_inventory
"""
from django.core.management.base import BaseCommand
from apps.inventory.models import UnitOfMeasure, Category


class Command(BaseCommand):
    help = 'إعداد وحدات القياس والتصنيفات الأساسية للمخزون'

    def handle(self, *args, **options):
        self.stdout.write('بدء إعداد بيانات المخزون الأساسية...')

        self._create_units()
        self._create_categories()

        self.stdout.write(self.style.SUCCESS('تم إعداد بيانات المخزون بنجاح ✓'))

    def _create_units(self):
        """إنشاء وحدات القياس الأساسية"""
        units = [
            {'name': 'قطعة', 'symbol': 'قطعة'},
            {'name': 'متر', 'symbol': 'م'},
            {'name': 'كيلوجرام', 'symbol': 'كجم'},
            {'name': 'رول', 'symbol': 'رول'},
            {'name': 'لتر', 'symbol': 'لتر'},
            {'name': 'علبة', 'symbol': 'علبة'},
            {'name': 'كرتونة', 'symbol': 'كرتونة'},
            {'name': 'زوج', 'symbol': 'زوج'},
        ]

        created_count = 0
        for unit_data in units:
            obj, created = UnitOfMeasure.objects.get_or_create(
                name=unit_data['name'],
                defaults={'symbol': unit_data['symbol']},
            )
            if created:
                created_count += 1
                self.stdout.write(f'  ✓ وحدة: {obj.name}')

        self.stdout.write(f'وحدات القياس: {created_count} جديدة من أصل {len(units)}')

    def _create_categories(self):
        """إنشاء شجرة التصنيفات"""

        # التصنيفات الرئيسية
        raw_parent, _ = Category.objects.get_or_create(name='خامات')
        finished_parent, _ = Category.objects.get_or_create(name='منتجات نهائية')
        semi_parent, _ = Category.objects.get_or_create(name='منتجات نصف مصنعة')

        raw_children = [
            'الإسفنج',
            'الحديد والسوست',
            'اللباد والقطن',
            'الأقمشة',
            'الفايبر',
            'الفازلين',
            'الغراء',
            'التغليف',
            'التيب',
            'الإكسسوارات',
            'مستلزمات الإنتاج',
        ]

        finished_children = [
            'مراتب سوست متصلة',
            'مراتب سوست منفصلة',
            'مراتب طبية (بدون سوست)',
            'لحاف فايبر',
            'مخدات فايبر',
            'مخدات ريش',
            'خداديات',
            'ملايات',
            'كفرات مراتب',
            'كفرات لحاف',
            'سراير',
            'مفروشات أخرى',
        ]

        semi_children = [
            'سوست مجمعة',
            'أقمشة مكبتنة',
            'إسفنج مقطع',
        ]

        created_count = 0

        for name in raw_children:
            obj, created = Category.objects.get_or_create(name=name, defaults={'parent': raw_parent})
            if created:
                created_count += 1
                self.stdout.write(f'  ✓ تصنيف: خامات > {name}')

        for name in finished_children:
            obj, created = Category.objects.get_or_create(name=name, defaults={'parent': finished_parent})
            if created:
                created_count += 1
                self.stdout.write(f'  ✓ تصنيف: منتجات نهائية > {name}')

        for name in semi_children:
            obj, created = Category.objects.get_or_create(name=name, defaults={'parent': semi_parent})
            if created:
                created_count += 1
                self.stdout.write(f'  ✓ تصنيف: نصف مصنع > {name}')

        total = 3 + len(raw_children) + len(finished_children) + len(semi_children)
        self.stdout.write(f'التصنيفات: {created_count} جديدة من أصل {total}')
