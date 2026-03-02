"""
محرك CRM — إدارة العملاء والعملاء المحتملين
"""
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, Count, Avg, Q
from apps.crm.models import Lead, Interaction, Complaint, CustomerRating, Task
from apps.sales.models import Customer, SalesInvoice, SalesReturn


class CRMEngine:

    # ════════════════════════════════
    # Leads
    # ════════════════════════════════

    @classmethod
    @transaction.atomic
    def create_lead(cls, name, phone, source, branch, assigned_to=None,
                     email='', company='', address='', governorate='',
                     interested_products=None, estimated_value=0,
                     priority='medium', notes='', user=None):
        """إنشاء عميل محتمل"""
        lead = Lead.objects.create(
            name=name, phone=phone, email=email, company=company,
            address=address, governorate=governorate, source=source,
            status='new', priority=priority, branch=branch,
            assigned_to=assigned_to, estimated_value=estimated_value,
            notes=notes, created_by=user, updated_by=user,
        )
        if interested_products:
            lead.interested_products.set(interested_products)
        return lead

    @classmethod
    @transaction.atomic
    def convert_lead_to_customer(cls, lead, customer_type='retail', user=None):
        """تحويل Lead إلى عميل حقيقي"""
        if lead.status == 'won' and lead.converted_to_customer:
            raise ValueError("هذا الـ Lead تم تحويله بالفعل!")

        last = Customer.objects.order_by('-code').first()
        new_num = int(last.code[1:]) + 1 if last and last.code.startswith('C') else 1

        customer = Customer.objects.create(
            code=f'C{new_num:04d}',
            name=lead.name,
            customer_type=customer_type,
            phone=lead.phone,
            phone2=lead.phone2,
            address=lead.address,
            governorate=lead.governorate,
            branch=lead.branch,
            is_active=True,
            created_by=user,
            updated_by=user,
        )

        lead.converted_to_customer = customer
        lead.conversion_date = timezone.now()
        lead.status = 'won'
        lead.save()

        return customer

    @classmethod
    def get_lead_pipeline(cls, branch=None, assigned_to=None):
        """Pipeline عرض الـ Leads حسب المراحل"""
        filters = Q(status__in=['new', 'contacted', 'interested', 'qualified', 'negotiation'])
        if branch:
            filters &= Q(branch=branch)
        if assigned_to:
            filters &= Q(assigned_to=assigned_to)

        leads = Lead.objects.filter(filters)

        return {
            'new': leads.filter(status='new').count(),
            'contacted': leads.filter(status='contacted').count(),
            'interested': leads.filter(status='interested').count(),
            'qualified': leads.filter(status='qualified').count(),
            'negotiation': leads.filter(status='negotiation').count(),
            'total_value': leads.aggregate(total=Sum('estimated_value'))['total'] or 0,
            'total_leads': leads.count(),
        }

    # ════════════════════════════════
    # Interactions
    # ════════════════════════════════

    @classmethod
    def log_interaction(cls, interaction_type, subject, details,
                         customer=None, lead=None, handled_by=None,
                         branch=None, result='', follow_up_date=None,
                         quotation=None, invoice=None,
                         satisfaction_rating=None, user=None):
        """تسجيل تفاعل مع عميل أو Lead"""
        interaction = Interaction.objects.create(
            customer=customer, lead=lead,
            date=timezone.now(),
            interaction_type=interaction_type,
            result=result,
            subject=subject, details=details,
            handled_by=handled_by or user,
            branch=branch,
            follow_up_required=bool(follow_up_date),
            follow_up_date=follow_up_date,
            quotation=quotation, invoice=invoice,
            satisfaction_rating=satisfaction_rating,
            created_by=user, updated_by=user,
        )

        # تحديث آخر تواصل
        if lead:
            lead.last_contact_date = timezone.now().date()
            if follow_up_date:
                lead.next_follow_up = follow_up_date
            lead.save()

        return interaction

    # ════════════════════════════════
    # Complaints
    # ════════════════════════════════

    @classmethod
    def create_complaint(cls, customer, complaint_type, subject, description,
                          branch, severity='medium', product=None, invoice=None,
                          assigned_to=None, images=None, user=None):
        """إنشاء شكوى"""
        today = timezone.now()
        count = Complaint.objects.filter(
            date__year=today.year, date__month=today.month
        ).count() + 1

        complaint = Complaint.objects.create(
            complaint_number=f"CMP-{today.strftime('%Y%m')}-{count:04d}",
            date=today, customer=customer,
            complaint_type=complaint_type, severity=severity,
            subject=subject, description=description,
            product=product, invoice=invoice,
            branch=branch, assigned_to=assigned_to,
            created_by=user, updated_by=user,
        )

        # تحديث تقييم العميل
        cls.update_customer_rating(customer)

        return complaint

    @classmethod
    @transaction.atomic
    def resolve_complaint(cls, complaint, resolution, resolution_type,
                            resolution_cost=0, user=None):
        """حل شكوى"""
        complaint.resolution = resolution
        complaint.resolution_type = resolution_type
        complaint.resolution_cost = resolution_cost
        complaint.resolution_date = timezone.now()
        complaint.status = 'resolved'
        complaint.updated_by = user
        complaint.save()

        cls.update_customer_rating(complaint.customer)
        return complaint

    # ════════════════════════════════
    # Customer Rating
    # ════════════════════════════════

    @classmethod
    def update_customer_rating(cls, customer):
        """تحديث تقييم العميل تلقائياً"""
        rating, created = CustomerRating.objects.get_or_create(customer=customer)

        invoices = SalesInvoice.objects.filter(
            customer=customer,
            status__in=['confirmed', 'paid', 'partial_paid', 'delivered'],
        )

        rating.total_purchases = invoices.aggregate(total=Sum('total'))['total'] or Decimal('0')
        rating.total_invoices = invoices.count()

        returns = SalesReturn.objects.filter(customer=customer, status='completed')
        rating.total_returns = returns.aggregate(total=Sum('total'))['total'] or Decimal('0')

        if rating.total_purchases > 0:
            rating.return_rate = (rating.total_returns / rating.total_purchases * 100).quantize(Decimal('0.01'))

        rating.total_complaints = Complaint.objects.filter(customer=customer).count()

        last_invoice = invoices.order_by('-date').first()
        if last_invoice:
            rating.last_purchase_date = last_invoice.date.date()
            rating.days_since_last_purchase = (timezone.now().date() - last_invoice.date.date()).days

        # حساب النقاط
        score = 0
        if rating.total_purchases >= 100000: score += 30
        elif rating.total_purchases >= 50000: score += 20
        elif rating.total_purchases >= 10000: score += 10
        if rating.total_invoices >= 20: score += 20
        elif rating.total_invoices >= 10: score += 15
        elif rating.total_invoices >= 5: score += 10
        if rating.return_rate <= 2: score += 15
        elif rating.return_rate <= 5: score += 10
        elif rating.return_rate <= 10: score += 5
        else: score -= 10
        if rating.total_complaints == 0: score += 15
        elif rating.total_complaints <= 2: score += 10
        else: score -= 5
        if rating.days_since_last_purchase <= 30: score += 20
        elif rating.days_since_last_purchase <= 90: score += 10
        elif rating.days_since_last_purchase > 180: score -= 10

        rating.score = max(0, min(100, score))

        if score >= 80: rating.grade = 'A+'
        elif score >= 65: rating.grade = 'A'
        elif score >= 50: rating.grade = 'B'
        elif score >= 35: rating.grade = 'C'
        elif score >= 20: rating.grade = 'D'
        else: rating.grade = 'F'

        rating.save()
        return rating

    @classmethod
    def update_all_ratings(cls):
        """تحديث تقييم كل العملاء"""
        for customer in Customer.objects.filter(is_active=True):
            cls.update_customer_rating(customer)

    # ════════════════════════════════
    # Reports
    # ════════════════════════════════

    @classmethod
    def get_crm_dashboard(cls, branch=None):
        """بيانات لوحة CRM"""
        filters = {}
        if branch:
            filters['branch'] = branch

        today = timezone.now().date()

        return {
            'pipeline': cls.get_lead_pipeline(branch=branch),
            'total_customers': Customer.objects.filter(is_active=True, **filters).count(),
            'new_leads_this_month': Lead.objects.filter(
                created_at__month=today.month, created_at__year=today.year, **filters
            ).count(),
            'conversion_rate': cls._calculate_conversion_rate(branch),
            'open_complaints': Complaint.objects.filter(
                status__in=['open', 'in_progress'], **filters
            ).count(),
            'follow_ups_today': Interaction.objects.filter(
                follow_up_date=today, is_follow_up_done=False,
            ).count(),
            'overdue_follow_ups': Interaction.objects.filter(
                follow_up_date__lt=today, is_follow_up_done=False,
            ).count(),
            'top_customers': CustomerRating.objects.filter(
                grade__in=['A+', 'A']
            ).select_related('customer')[:10],
            'at_risk_customers': CustomerRating.objects.filter(
                days_since_last_purchase__gte=90
            ).select_related('customer')[:10],
        }

    @classmethod
    def _calculate_conversion_rate(cls, branch=None):
        filters = {}
        if branch:
            filters['branch'] = branch
        total = Lead.objects.filter(**filters).count()
        won = Lead.objects.filter(status='won', **filters).count()
        return round(won / total * 100, 1) if total > 0 else 0
