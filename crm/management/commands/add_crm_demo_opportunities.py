from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from crm.models import (
    Customer, Opportunity, OpportunityStage, Activity, ActivityType,
    SupportTicket, TicketCategory, Campaign, CampaignResponse
)
import random

class Command(BaseCommand):
    help = 'إضافة فرص وأنشطة تجريبية لنظام CRM'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('بدء إضافة البيانات التجريبية...'))
        
        # الحصول على البيانات الموجودة
        customers = Customer.objects.all()
        users = User.objects.all()
        opportunity_stages = OpportunityStage.objects.all().order_by('order')
        activity_types = ActivityType.objects.all()
        ticket_categories = TicketCategory.objects.all()
        
        if not customers.exists():
            self.stdout.write(self.style.ERROR('لا يوجد عملاء في النظام'))
            return
            
        if not users.exists():
            self.stdout.write(self.style.ERROR('لا يوجد مستخدمين في النظام'))
            return
        
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
        
        for customer in customers:
            for _ in range(random.randint(1, 3)):
                stage = random.choice(opportunity_stages)
                opportunity = Opportunity.objects.create(
                    name=random.choice(opportunity_names),
                    customer=customer,
                    estimated_value=Decimal(random.randint(50000, 500000)),
                    expected_close_date=timezone.now().date() + timedelta(days=random.randint(10, 90)),
                    stage=stage,
                    probability=stage.probability,
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
        
        for customer in customers:
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
        
        for customer in customers[:3]:  # فقط لبعض العملاء
            ticket = SupportTicket.objects.create(
                title=random.choice(ticket_titles),
                customer=customer,
                category=random.choice(ticket_categories) if ticket_categories.exists() else None,
                description=f'طلب دعم من العميل {customer.full_name}',
                status=random.choice(['open', 'in_progress', 'resolved']),
                priority=random.choice(['low', 'medium', 'high']),
                assigned_to=random.choice(users),
                created_by=random.choice(users)
            )
            # تعيين رقم التذكرة يدوياً لتجنب مشاكل الرقم التلقائي
            ticket.ticket_number = f'T{ticket.id:06d}'
            ticket.save()
        
        # إنشاء حملة تسويقية
        if not Campaign.objects.exists():
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
            campaign.target_customers.set(customers[:3])
            
            # إنشاء استجابات للحملة
            for customer in customers[:3]:
                CampaignResponse.objects.create(
                    campaign=campaign,
                    customer=customer,
                    response_type=random.choice(['interested', 'not_interested', 'meeting_scheduled']),
                    notes='استجابة تجريبية للحملة'
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'تم إنشاء البيانات التجريبية بنجاح!\n'
                f'- العملاء: {Customer.objects.count()}\n'
                f'- الفرص: {Opportunity.objects.count()}\n'
                f'- الأنشطة: {Activity.objects.count()}\n'
                f'- تذاكر الدعم: {SupportTicket.objects.count()}\n'
                f'- الحملات: {Campaign.objects.count()}'
            )
        )