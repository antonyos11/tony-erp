from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from crm.models import (
    Customer, CustomerType, CustomerSource, ContactPerson,
    Opportunity, OpportunityStage, Activity, ActivityType,
    Quotation, QuotationItem, SupportTicket, TicketCategory,
    Campaign, CampaignResponse
)
from inventory.models import Product
import random

class Command(BaseCommand):
    help = 'إنشاء بيانات تجريبية لنظام CRM'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('بدء إنشاء البيانات التجريبية لنظام CRM...'))
        
        # تحقق من وجود بيانات
        if Customer.objects.exists():
            self.stdout.write(self.style.WARNING('يوجد عملاء بالفعل في النظام. سيتم تخطي إنشاء البيانات التجريبية.'))
            self.stdout.write(self.style.SUCCESS(f'الإحصائيات الحالية:'))
            self.stdout.write(f'- العملاء: {Customer.objects.count()}')
            self.stdout.write(f'- جهات الاتصال: {ContactPerson.objects.count()}')
            self.stdout.write(f'- الفرص: {Opportunity.objects.count()}')
            self.stdout.write(f'- الأنشطة: {Activity.objects.count()}')
            self.stdout.write(f'- تذاكر الدعم: {SupportTicket.objects.count()}')
            self.stdout.write(f'- الحملات: {Campaign.objects.count()}')
            return
        
        # الحصول على المستخدمين
        users = User.objects.all()
        if not users.exists():
            self.stdout.write(self.style.ERROR('لا يوجد مستخدمين في النظام. يرجى إنشاء مستخدم أولاً.'))
            return
        
        # الحصول على الأنواع والمصادر
        customer_types = CustomerType.objects.all()
        customer_sources = CustomerSource.objects.all()
        opportunity_stages = OpportunityStage.objects.all().order_by('order')
        activity_types = ActivityType.objects.all()
        ticket_categories = TicketCategory.objects.all()
        
        # إنشاء عملاء تجريبيين
        sample_customers = [
            {
                'first_name': 'أحمد', 'last_name': 'محمد', 'company_name': 'شركة النجاح للتجارة',
                'phone': '01012345678', 'email': 'ahmed@najah.com', 'city': 'القاهرة'
            },
            {
                'first_name': 'فاطمة', 'last_name': 'عبدالله', 'company_name': 'مؤسسة الأمل',
                'phone': '01198765432', 'email': 'fatma@amal.com', 'city': 'الإسكندرية'
            },
            {
                'first_name': 'محمد', 'last_name': 'حسن', 'company_name': 'شركة التميز للاستيراد والتصدير',
                'phone': '01067890123', 'email': 'mohamed@tamayoz.com', 'city': 'الجيزة'
            },
            {
                'first_name': 'سارة', 'last_name': 'علي', 'company_name': 'مجموعة الإبداع التجارية',
                'phone': '01145678901', 'email': 'sara@ibdaa.com', 'city': 'القاهرة'
            },
            {
                'first_name': 'علي', 'last_name': 'أحمد', 'company_name': 'شركة الرائد للتكنولوجيا',
                'phone': '01234567890', 'email': 'ali@raed-tech.com', 'city': 'المنصورة'
            },
        ]
        
        created_customers = []
        for i, customer_data in enumerate(sample_customers):
            customer = Customer.objects.create(
                customer_code=f'C{i+1:06d}',
                first_name=customer_data['first_name'],
                last_name=customer_data['last_name'],
                company_name=customer_data['company_name'],
                phone=customer_data['phone'],
                email=customer_data['email'],
                city=customer_data['city'],
                customer_type=random.choice(customer_types) if customer_types.exists() else None,
                source=random.choice(customer_sources) if customer_sources.exists() else None,
                assigned_to=random.choice(users),
                credit_limit=Decimal(random.randint(10000, 100000))
            )
            created_customers.append(customer)
            self.stdout.write(f'تم إنشاء العميل: {customer.full_name}')
        
        # إنشاء جهات اتصال
        for customer in created_customers:
            contact = ContactPerson.objects.create(
                customer=customer,
                name=f'مدير المبيعات - {customer.company_name}',
                position='مدير المبيعات',
                phone=customer.phone.replace('01', '02'),
                email=f'sales@{customer.email.split("@")[1] if customer.email else "example.com"}',
                is_primary=True
            )
        
        # إنشاء فرص تجارية
        opportunity_names = [
            'توريد أجهزة كمبيوتر',
            'نظام إدارة المخزون',
            'خدمات التسويق الرقمي',
            'تطوير موقع إلكتروني',
            'استشارات تقنية',
            'أنظمة الأمان',
            'حلول المحاسبة',
            'خدمات التدريب'
        ]
        
        for customer in created_customers:
            for _ in range(random.randint(1, 3)):
                stage = random.choice(opportunity_stages)
                opportunity = Opportunity.objects.create(
                    name=random.choice(opportunity_names),
                    customer=customer,
                    estimated_value=Decimal(random.randint(50000, 500000)),
                    expected_close_date=timezone.now().date() + timedelta(days=random.randint(10, 90)),
                    stage=stage,
                    probability=stage.probability,  # تعيين الاحتمالية مباشرة
                    priority=random.choice(['low', 'medium', 'high']),
                    assigned_to=random.choice(users),
                    description=f'فرصة تجارية مع {customer.company_name} لتوريد الخدمات والحلول التقنية'
                )
                self.stdout.write(f'تم إنشاء فرصة: {opportunity.name} - {customer.full_name}')
        
        # إنشاء أنشطة
        activity_titles = [
            'اجتماع مع العميل',
            'مكالمة متابعة',
            'إرسال عرض سعر',
            'زيارة ميدانية',
            'عرض تقديمي',
            'متابعة عرض السعر'
        ]
        
        for customer in created_customers:
            for _ in range(random.randint(2, 5)):
                activity = Activity.objects.create(
                    title=random.choice(activity_titles),
                    customer=customer,
                    activity_type=random.choice(activity_types) if activity_types.exists() else None,
                    scheduled_date=timezone.now() + timedelta(days=random.randint(-30, 30)),
                    duration_minutes=random.choice([30, 60, 90, 120]),
                    status=random.choice(['planned', 'completed', 'in_progress']),
                    priority=random.choice(['low', 'medium', 'high']),
                    assigned_to=random.choice(users),
                    description=f'نشاط متعلق بالعميل {customer.full_name}'
                )
        
        # إنشاء تذاكر دعم
        ticket_titles = [
            'مشكلة في النظام',
            'طلب دعم فني',
            'استفسار عن الخدمة',
            'تحديث البيانات',
            'مشكلة في الفوترة'
        ]
        
        for customer in created_customers[:3]:  # فقط لبعض العملاء
            ticket = SupportTicket.objects.create(
                title=random.choice(ticket_titles),
                customer=customer,
                category=random.choice(ticket_categories) if ticket_categories.exists() else None,
                description=f'طلب دعم من العميل {customer.full_name}',
                status=random.choice(['open', 'in_progress', 'resolved']),
                priority=random.choice(['low', 'medium', 'high']),
                assigned_to=random.choice(users),
                created_by=random.choice(users),
                ticket_number=f'T{random.randint(100000, 999999)}'
            )
        
        # إنشاء حملة تسويقية
        campaign = Campaign.objects.create(
            name='حملة العروض الصيفية',
            campaign_type='email',
            description='حملة تسويقية لعروض الصيف الخاصة',
            message_content='استفد من عروضنا الصيفية المميزة!',
            budget=Decimal('25000'),
            status='active',
            start_date=timezone.now() - timedelta(days=7),
            end_date=timezone.now() + timedelta(days=30),
            created_by=random.choice(users)
        )
        
        # إضافة عملاء للحملة
        campaign.target_customers.set(created_customers[:3])
        
        # إنشاء استجابات للحملة
        for customer in created_customers[:3]:
            CampaignResponse.objects.create(
                campaign=campaign,
                customer=customer,
                response_type=random.choice(['interested', 'not_interested', 'meeting_scheduled']),
                notes='استجابة تجريبية للحملة'
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'تم إنشاء البيانات التجريبية بنجاح!\n'
                f'- العملاء: {len(created_customers)}\n'
                f'- جهات الاتصال: {ContactPerson.objects.count()}\n'
                f'- الفرص: {Opportunity.objects.count()}\n'
                f'- الأنشطة: {Activity.objects.count()}\n'
                f'- تذاكر الدعم: {SupportTicket.objects.count()}\n'
                f'- الحملات: {Campaign.objects.count()}'
            )
        )