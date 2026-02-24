"""
أمر إعداد البيانات الأولية للخدمات المنزلية
"""

from django.core.management.base import BaseCommand
from home_services.models import (
    MaintenanceCategory, CleaningPackage, ServiceType, HomeServicesSettings
)
from decimal import Decimal


class Command(BaseCommand):
    help = 'إعداد البيانات الأولية لخدمات الصيانة والنظافة'

    def handle(self, *args, **options):
        self.stdout.write('جاري إعداد بيانات الخدمات المنزلية...\n')
        
        # إنشاء فئات الصيانة
        maintenance_categories = [
            {'name': 'كهرباء', 'code': 'ELEC', 'icon': 'bi-lightning-charge', 'sort_order': 1},
            {'name': 'سباكة', 'code': 'PLUMB', 'icon': 'bi-droplet', 'sort_order': 2},
            {'name': 'تكييف', 'code': 'AC', 'icon': 'bi-snow', 'sort_order': 3},
            {'name': 'أجهزة منزلية', 'code': 'APPL', 'icon': 'bi-tv', 'sort_order': 4},
            {'name': 'نجارة', 'code': 'CARP', 'icon': 'bi-hammer', 'sort_order': 5},
            {'name': 'دهان', 'code': 'PAINT', 'icon': 'bi-brush', 'sort_order': 6},
            {'name': 'ألومنيوم وزجاج', 'code': 'ALUM', 'icon': 'bi-window', 'sort_order': 7},
            {'name': 'صيانة عامة', 'code': 'GEN', 'icon': 'bi-tools', 'sort_order': 8},
        ]
        
        created_cats = 0
        for cat_data in maintenance_categories:
            cat, created = MaintenanceCategory.objects.get_or_create(
                code=cat_data['code'],
                defaults=cat_data
            )
            if created:
                created_cats += 1
        
        self.stdout.write(f'✓ تم إنشاء {created_cats} فئة صيانة\n')
        
        # إنشاء باقات النظافة
        cleaning_packages = [
            {
                'name': 'تنظيف شقة صغيرة',
                'code': 'CLN-SM',
                'description': 'تنظيف شامل لشقة صغيرة (غرفة أو غرفتين)',
                'includes': 'تنظيف الأرضيات\nتنظيف الحمامات\nتنظيف المطبخ\nمسح الأتربة\nترتيب عام',
                'excludes': 'غسيل السجاد\nتنظيف الزجاج الخارجي',
                'price': Decimal('150'),
                'duration_hours': Decimal('3'),
                'workers_count': 1,
                'sort_order': 1,
            },
            {
                'name': 'تنظيف شقة متوسطة',
                'code': 'CLN-MD',
                'description': 'تنظيف شامل لشقة متوسطة (3-4 غرف)',
                'includes': 'تنظيف الأرضيات\nتنظيف الحمامات\nتنظيف المطبخ\nمسح الأتربة\nتنظيف النوافذ الداخلية\nترتيب عام',
                'excludes': 'غسيل السجاد\nتنظيف الزجاج الخارجي',
                'price': Decimal('250'),
                'duration_hours': Decimal('4'),
                'workers_count': 2,
                'sort_order': 2,
                'is_featured': True,
            },
            {
                'name': 'تنظيف فيلا',
                'code': 'CLN-VL',
                'description': 'تنظيف شامل للفيلا',
                'includes': 'تنظيف جميع الطوابق\nتنظيف الحمامات\nتنظيف المطبخ\nمسح الأتربة\nتنظيف النوافذ\nتنظيف الحديقة',
                'excludes': 'غسيل السجاد الكبير',
                'price': Decimal('500'),
                'duration_hours': Decimal('6'),
                'workers_count': 3,
                'sort_order': 3,
            },
            {
                'name': 'تنظيف عميق',
                'code': 'CLN-DP',
                'description': 'تنظيف عميق شامل مع التعقيم',
                'includes': 'تنظيف عميق لجميع الأسطح\nتعقيم الحمامات والمطبخ\nتنظيف خلف الأثاث\nتنظيف المكيفات\nغسيل السجاد',
                'excludes': '',
                'price': Decimal('400'),
                'discount_price': Decimal('350'),
                'duration_hours': Decimal('5'),
                'workers_count': 2,
                'sort_order': 4,
                'is_featured': True,
            },
            {
                'name': 'تنظيف مكتب',
                'code': 'CLN-OF',
                'description': 'تنظيف المكاتب والشركات',
                'includes': 'تنظيف الأرضيات\nمسح المكاتب\nتنظيف الحمامات\nتفريغ سلات المهملات',
                'excludes': 'تنظيف السجاد',
                'price': Decimal('200'),
                'duration_hours': Decimal('3'),
                'workers_count': 2,
                'sort_order': 5,
            },
            {
                'name': 'تنظيف بعد البناء',
                'code': 'CLN-CON',
                'description': 'تنظيف شامل بعد أعمال البناء والترميم',
                'includes': 'إزالة مخلفات البناء\nتنظيف الأتربة\nتلميع الأرضيات\nتنظيف النوافذ\nتنظيف الجدران',
                'excludes': '',
                'price': Decimal('600'),
                'duration_hours': Decimal('8'),
                'workers_count': 3,
                'sort_order': 6,
            },
        ]
        
        created_pkgs = 0
        for pkg_data in cleaning_packages:
            pkg, created = CleaningPackage.objects.get_or_create(
                code=pkg_data['code'],
                defaults=pkg_data
            )
            if created:
                created_pkgs += 1
        
        self.stdout.write(f'✓ تم إنشاء {created_pkgs} باقة نظافة\n')
        
        # إنشاء الإعدادات الافتراضية
        settings, created = HomeServicesSettings.objects.get_or_create(
            pk=1,
            defaults={
                'enable_maintenance': True,
                'enable_cleaning': True,
                'confirmation_message': 'شكراً لك! تم استلام طلبك بنجاح وسيتم التواصل معك قريباً لتأكيد الموعد.',
            }
        )
        if created:
            self.stdout.write('✓ تم إنشاء الإعدادات الافتراضية\n')
        
        self.stdout.write(self.style.SUCCESS('\n✅ تم إعداد بيانات الخدمات المنزلية بنجاح!'))
        self.stdout.write('\nالروابط:')
        self.stdout.write('  - الصفحة الرئيسية: /home-services/')
        self.stdout.write('  - طلب صيانة: /home-services/maintenance/request/')
        self.stdout.write('  - طلب نظافة: /home-services/cleaning/request/')
        self.stdout.write('  - لوحة التحكم: /home-services/admin/dashboard/')
