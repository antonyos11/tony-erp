from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import random

from crm.models import (
    CustomerType, CustomerSource, Customer, ContactPerson,
    OpportunityStage, Opportunity, ActivityType, Activity,
    TicketCategory, SupportTicket
)


class Command(BaseCommand):
    help = 'إنشاء بيانات تجريبية لنظام CRM'

    def handle(self, *args, **options):
        self.stdout.write('بدء إنشاء البيانات التجريبية...')

        # إنشاء أنواع العملاء
        customer_types = [
            {'name': 'عميل عادي', 'description': 'عملاء عاديون'},
            {'name': 'عميل VIP', 'description': 'عملاء مهمون'},
            {'name': 'عميل تجاري', 'description': 'شركات تجارية'},
            {'name': 'عميل حكومي', 'description': 'جهات حكومية'},
        ]
        for ct_data in customer_types:
            CustomerType.objects.get_or_create(
                name=ct_data['name'],
                defaults={'description': ct_data['description']}
            )
        self.stdout.write('تم إنشاء أنواع العملاء')

        # إنشاء مصادر العملاء
        customer_sources = [
            {'name': 'موقع إلكتروني', 'description': 'من الموقع الإلكتروني'},
            {'name': 'شبكات التواصل', 'description': 'فيسبوك، تويتر، إنستجرام'},
            {'name': 'إحالة عميل', 'description': 'من عميل حالي'},
            {'name': 'معرض تجاري', 'description': 'من المعارض التجارية'},
            {'name': 'إعلانات', 'description': 'من الحملات الإعلانية'},
        ]
        for cs_data in customer_sources:
            CustomerSource.objects.get_or_create(
                name=cs_data['name'],
                defaults={'description': cs_data['description']}
            )
        self.stdout.write('تم إنشاء مصادر العملاء')

        # إنشاء مراحل الفرص
        opportunity_stages = [
            {'name': 'عميل محتمل', 'order': 1, 'probability': 10.00},
            {'name': 'اتصال أولي', 'order': 2, 'probability': 25.00},
            {'name': 'اجتماع مجدول', 'order': 3, 'probability': 40.00},
            {'name': 'عرض سعر مرسل', 'order': 4, 'probability': 60.00},
            {'name': 'تفاوض', 'order': 5, 'probability': 80.00},
            {'name': 'فرصة ناجحة', 'order': 6, 'probability': 100.00, 'is_won': True},
            {'name': 'فرصة مفقودة', 'order': 7, 'probability': 0.00, 'is_lost': True},
        ]
        for os_data in opportunity_stages:
            OpportunityStage.objects.get_or_create(
                name=os_data['name'],
                defaults={
                    'order': os_data['order'],
                    'probability': os_data['probability'],
                    'is_won': os_data.get('is_won', False),
                    'is_lost': os_data.get('is_lost', False),
                }
            )
        self.stdout.write('تم إنشاء مراحل الفرص')

        # إنشاء أنواع الأنشطة
        activity_types = [
            {'name': 'مكالمة هاتفية', 'icon': 'fas fa-phone', 'color': '#007bff'},
            {'name': 'اجتماع', 'icon': 'fas fa-handshake', 'color': '#28a745'},
            {'name': 'بريد إلكتروني', 'icon': 'fas fa-envelope', 'color': '#17a2b8'},
            {'name': 'زيارة عميل', 'icon': 'fas fa-map-marker-alt', 'color': '#ffc107'},
            {'name': 'عرض تقديمي', 'icon': 'fas fa-presentation', 'color': '#fd7e14'},
            {'name': 'متابعة', 'icon': 'fas fa-clock', 'color': '#6c757d'},
        ]
        for at_data in activity_types:
            ActivityType.objects.get_or_create(
                name=at_data['name'],
                defaults={
                    'icon': at_data['icon'],
                    'color': at_data['color'],
                }
            )
        self.stdout.write('تم إنشاء أنواع الأنشطة')

        # إنشاء فئات التذاكر
        ticket_categories = [
            {'name': 'مشكلة تقنية', 'color': '#dc3545'},
            {'name': 'استفسار عام', 'color': '#17a2b8'},
            {'name': 'طلب دعم', 'color': '#28a745'},
            {'name': 'شكوى', 'color': '#ffc107'},
            {'name': 'اقتراح', 'color': '#6f42c1'},
        ]
        for tc_data in ticket_categories:
            TicketCategory.objects.get_or_create(
                name=tc_data['name'],
                defaults={'color': tc_data['color']}
            )
        self.stdout.write('تم إنشاء فئات التذاكر')

        # الحصول على المستخدمين الموجودين أو إنشاء مستخدم افتراضي
        users = list(User.objects.all())
        if not users:
            admin_user = User.objects.create_user(
                username='admin',
                email='admin@company.com',
                password='admin123',
                first_name='مدير',
                last_name='النظام'
            )
            users = [admin_user]

        # إنشاء عملاء تجريبيين
        customer_data = [
            {
                'first_name': 'أحمد', 'last_name': 'محمد',
                'company_name': 'شركة النجاح للتجارة',
                'phone': '02-12345678', 'mobile': '01012345678',
                'email': 'ahmed@alnajah.com'
            },
            {
                'first_name': 'فاطمة', 'last_name': 'علي',
                'company_name': 'مؤسسة الأمل التجارية',
                'phone': '02-87654321', 'mobile': '01087654321',
                'email': 'fatma@alamal.com'
            },
            {
                'first_name': 'محمد', 'last_name': 'حسن',
                'company_name': '',
                'phone': '02-11111111', 'mobile': '01011111111',
                'email': 'mohamed@email.com'
            },
            {
                'first_name': 'نورا', 'last_name': 'سامي',
                'company_name': 'شركة المستقبل للتطوير',
                'phone': '02-22222222', 'mobile': '01022222222',
                'email': 'nora@future.com'
            },
            {
                'first_name': 'خالد', 'last_name': 'أحمد',
                'company_name': 'مجموعة الرائد التجارية',
                'phone': '02-33333333', 'mobile': '01033333333',
                'email': 'khaled@raed.com'
            },
        ]

        customer_types_list = list(CustomerType.objects.all())
        customer_sources_list = list(CustomerSource.objects.all())

        created_customers = []
        for i, cd in enumerate(customer_data, 1):
            customer, created = Customer.objects.get_or_create(
                customer_code=f'CUS{i:05d}',
                defaults={
                    'first_name': cd['first_name'],
                    'last_name': cd['last_name'],
                    'company_name': cd['company_name'],
                    'phone': cd['phone'],
                    'mobile': cd['mobile'],
                    'email': cd['email'],
                    'address_line1': f'شارع {i} - المنطقة التجارية',
                    'city': 'القاهرة',
                    'state': 'القاهرة',
                    'postal_code': f'1111{i}',
                    'customer_type': random.choice(customer_types_list),
                    'source': random.choice(customer_sources_list),
                    'assigned_to': random.choice(users),
                    'credit_limit': random.uniform(10000, 100000),
                    'payment_terms': '30 يوم',
                    'status': 'active',
                }
            )
            created_customers.append(customer)
        self.stdout.write('تم إنشاء العملاء التجريبيين')

        # إنشاء جهات اتصال
        for customer in created_customers:
            if customer.company_name:  # فقط للشركات
                ContactPerson.objects.get_or_create(
                    customer=customer,
                    name=f'مدير المشتريات - {customer.company_name}',
                    defaults={
                        'position': 'مدير المشتريات',
                        'phone': customer.phone,
                        'mobile': customer.mobile,
                        'email': f'manager@{customer.company_name.split()[0].lower()}.com',
                        'is_primary': True,
                    }
                )
        self.stdout.write('تم إنشاء جهات الاتصال')

        # إنشاء فرص تجارية
        opportunity_stages_list = list(OpportunityStage.objects.exclude(is_lost=True))
        opportunity_names = [
            'توريد أجهزة كمبيوتر',
            'تطوير نظام إدارة',
            'خدمات استشارية',
            'توريد مواد خام',
            'مشروع تطوير موقع',
            'نظام نقاط البيع',
            'خدمات الصيانة',
            'برنامج محاسبي',
            'حلول الأمان',
            'نظام إدارة المخازن',
        ]
        for customer in created_customers:
            num_opportunities = random.randint(1, 3)
            for _ in range(num_opportunities):
                opportunity_name = f'{random.choice(opportunity_names)} - {customer.company_name or customer.full_name}'
                days_ahead = random.randint(7, 90)
                expected_date = timezone.now().date() + timedelta(days=days_ahead)
                stage = random.choice(opportunity_stages_list)
                Opportunity.objects.get_or_create(
                    name=opportunity_name,
                    customer=customer,
                    defaults={
                        'estimated_value': random.uniform(50000, 500000),
                        'probability': stage.probability,
                        'expected_close_date': expected_date,
                        'stage': stage,
                        'priority': random.choice(['low', 'medium', 'high', 'urgent']),
                        'assigned_to': random.choice(users),
                        'description': f'وصف تفصيلي للفرصة التجارية مع {customer.full_name}',
                        'notes': 'ملاحظات إضافية حول الفرصة',
                    }
                )
        self.stdout.write('تم إنشاء الفرص التجارية')

        # إنشاء أنشطة
        activity_types_list = list(ActivityType.objects.all())
        opportunities_list = list(Opportunity.objects.all())
        for opportunity in opportunities_list:
            num_activities = random.randint(1, 2)
            for _ in range(num_activities):
                days_from_now = random.randint(-7, 14)
                activity_date = timezone.now() + timedelta(days=days_from_now)
                activity_type = random.choice(activity_types_list)
                Activity.objects.get_or_create(
                    title=f'{activity_type.name} مع {opportunity.customer.full_name}',
                    customer=opportunity.customer,
                    opportunity=opportunity,
                    scheduled_date=activity_date,
                    defaults={
                        'activity_type': activity_type,
                        'description': f'نشاط {activity_type.name} متعلق بالفرصة: {opportunity.name}',
                        'duration_minutes': random.choice([30, 60, 90, 120]),
                        'status': random.choice(['planned', 'completed']) if days_from_now < 0 else 'planned',
                        'priority': random.choice(['low', 'medium', 'high']),
                        'assigned_to': opportunity.assigned_to,
                    }
                )
        self.stdout.write('تم إنشاء الأنشطة')

        # إنشاء تذاكر دعم
        ticket_categories_list = list(TicketCategory.objects.all())
        for i, customer in enumerate(created_customers[:3]):
            ticket_number = f'TKT{timezone.now().year}{i+1:04d}'
            SupportTicket.objects.get_or_create(
                ticket_number=ticket_number,
                defaults={
                    'title': f'طلب دعم من {customer.full_name}',
                    'description': 'وصف تفصيلي لمشكلة أو طلب الدعم المقدم من العميل.',
                    'customer': customer,
                    'category': random.choice(ticket_categories_list),
                    'status': random.choice(['open', 'in_progress', 'resolved']),
                    'priority': random.choice(['low', 'medium', 'high']),
                    'assigned_to': random.choice(users),
                    'created_by': random.choice(users),
                }
            )
        self.stdout.write('تم إنشاء تذاكر الدعم')

        # إحصائيات نهائية
        stats = {
            'customer_types': CustomerType.objects.count(),
            'customer_sources': CustomerSource.objects.count(),
            'customers': Customer.objects.count(),
            'contact_persons': ContactPerson.objects.count(),
            'opportunity_stages': OpportunityStage.objects.count(),
            'opportunities': Opportunity.objects.count(),
            'activity_types': ActivityType.objects.count(),
            'activities': Activity.objects.count(),
            'ticket_categories': TicketCategory.objects.count(),
            'support_tickets': SupportTicket.objects.count(),
        }
        self.stdout.write(
            self.style.SUCCESS(
                '\nتم إنشاء البيانات التجريبية بنجاح\n\n'
                'إحصائيات البيانات المُنشأة:\n'
                f'- أنواع العملاء: {stats["customer_types"]}\n'
                f'- مصادر العملاء: {stats["customer_sources"]}\n'
                f'- العملاء: {stats["customers"]}\n'
                f'- جهات الاتصال: {stats["contact_persons"]}\n'
                f'- مراحل الفرص: {stats["opportunity_stages"]}\n'
                f'- الفرص التجارية: {stats["opportunities"]}\n'
                f'- أنواع الأنشطة: {stats["activity_types"]}\n'
                f'- الأنشطة: {stats["activities"]}\n'
                f'- فئات التذاكر: {stats["ticket_categories"]}\n'
                f'- تذاكر الدعم: {stats["support_tickets"]}\n'
            )
        )