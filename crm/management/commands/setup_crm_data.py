from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from crm.models import (
    CustomerType, CustomerSource, OpportunityStage, ActivityType, TicketCategory
)

class Command(BaseCommand):
    help = 'إنشاء البيانات الأساسية لنظام CRM'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('بدء إنشاء البيانات الأساسية لنظام CRM...'))

        # إنشاء أنواع العملاء
        customer_types = [
            {'name': 'عميل عادي', 'description': 'عميل عادي بدون خصومات خاصة', 'discount_percentage': 0},
            {'name': 'عميل مميز', 'description': 'عميل مميز يحصل على خصم 5%', 'discount_percentage': 5},
            {'name': 'عميل VIP', 'description': 'عميل VIP يحصل على خصم 10%', 'discount_percentage': 10},
            {'name': 'شركة', 'description': 'شركات وكيانات تجارية', 'discount_percentage': 15},
        ]

        for ct_data in customer_types:
            customer_type, created = CustomerType.objects.get_or_create(
                name=ct_data['name'],
                defaults=ct_data
            )
            if created:
                self.stdout.write(f'تم إنشاء نوع العميل: {customer_type.name}')

        # إنشاء مصادر العملاء
        customer_sources = [
            {'name': 'موقع الويب', 'description': 'عملاء جاؤوا من موقع الشركة الإلكتروني'},
            {'name': 'وسائل التواصل الاجتماعي', 'description': 'فيسبوك، إنستجرام، تويتر'},
            {'name': 'إعلانات جوجل', 'description': 'إعلانات البحث والعرض على جوجل'},
            {'name': 'ترشيح من عميل', 'description': 'عميل حالي رشح عميل جديد'},
            {'name': 'مكالمة هاتفية', 'description': 'عميل اتصل بالشركة مباشرة'},
            {'name': 'زيارة مباشرة', 'description': 'عميل زار المكتب مباشرة'},
            {'name': 'معرض أو فعالية', 'description': 'التقى بالعميل في معرض أو فعالية'},
        ]

        for cs_data in customer_sources:
            source, created = CustomerSource.objects.get_or_create(
                name=cs_data['name'],
                defaults=cs_data
            )
            if created:
                self.stdout.write(f'تم إنشاء مصدر العميل: {source.name}')

        # إنشاء مراحل الفرص التجارية
        opportunity_stages = [
            {'name': 'مؤهل للمبيعات', 'order': 1, 'probability': 20, 'is_won': False, 'is_lost': False},
            {'name': 'تحديد الاحتياجات', 'order': 2, 'probability': 30, 'is_won': False, 'is_lost': False},
            {'name': 'عرض الحل', 'order': 3, 'probability': 50, 'is_won': False, 'is_lost': False},
            {'name': 'مفاوضات', 'order': 4, 'probability': 70, 'is_won': False, 'is_lost': False},
            {'name': 'تجربة المنتج', 'order': 5, 'probability': 85, 'is_won': False, 'is_lost': False},
            {'name': 'إغلاق ناجح', 'order': 6, 'probability': 100, 'is_won': True, 'is_lost': False},
            {'name': 'خسارة الصفقة', 'order': 7, 'probability': 0, 'is_won': False, 'is_lost': True},
        ]

        for os_data in opportunity_stages:
            stage, created = OpportunityStage.objects.get_or_create(
                name=os_data['name'],
                defaults=os_data
            )
            if created:
                self.stdout.write(f'تم إنشاء مرحلة الفرصة: {stage.name}')

        # إنشاء أنواع الأنشطة
        activity_types = [
            {'name': 'مكالمة هاتفية', 'icon': 'fas fa-phone', 'color': '#007bff'},
            {'name': 'اجتماع', 'icon': 'fas fa-users', 'color': '#28a745'},
            {'name': 'بريد إلكتروني', 'icon': 'fas fa-envelope', 'color': '#17a2b8'},
            {'name': 'عرض تقديمي', 'icon': 'fas fa-presentation', 'color': '#fd7e14'},
            {'name': 'زيارة العميل', 'icon': 'fas fa-map-marker-alt', 'color': '#6f42c1'},
            {'name': 'متابعة', 'icon': 'fas fa-redo', 'color': '#20c997'},
            {'name': 'مهمة', 'icon': 'fas fa-tasks', 'color': '#ffc107'},
        ]

        for at_data in activity_types:
            activity_type, created = ActivityType.objects.get_or_create(
                name=at_data['name'],
                defaults=at_data
            )
            if created:
                self.stdout.write(f'تم إنشاء نوع النشاط: {activity_type.name}')

        # إنشاء فئات تذاكر الدعم
        ticket_categories = [
            {'name': 'استفسار عام', 'description': 'أسئلة عامة حول المنتجات أو الخدمات', 'color': '#007bff'},
            {'name': 'مشكلة تقنية', 'description': 'مشاكل في استخدام المنتج أو الخدمة', 'color': '#dc3545'},
            {'name': 'طلب تغيير', 'description': 'طلبات تعديل أو تحسين', 'color': '#fd7e14'},
            {'name': 'شكوى', 'description': 'شكاوى من الخدمة أو المنتج', 'color': '#e83e8c'},
            {'name': 'طلب إضافي', 'description': 'طلب خدمات أو منتجات إضافية', 'color': '#28a745'},
            {'name': 'إلغاء الخدمة', 'description': 'طلب إلغاء أو إيقاف الخدمة', 'color': '#6c757d'},
        ]

        for tc_data in ticket_categories:
            category, created = TicketCategory.objects.get_or_create(
                name=tc_data['name'],
                defaults=tc_data
            )
            if created:
                self.stdout.write(f'تم إنشاء فئة التذكرة: {category.name}')

        self.stdout.write(
            self.style.SUCCESS('تم إنشاء جميع البيانات الأساسية لنظام CRM بنجاح!')
        )
        self.stdout.write(
            self.style.WARNING('يمكنك الآن البدء في استخدام نظام CRM بكامل ميزاته.')
        )