from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum, Avg, Case, When, IntegerField
from django.db.models.functions import TruncMonth
from django.http import JsonResponse, HttpResponse
import csv
from io import StringIO
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string
from django.contrib.auth.models import User
from datetime import datetime, timedelta
import json

from .models import (
    Customer, CustomerType, CustomerSource, ContactPerson,
    Opportunity, OpportunityStage, Activity, ActivityType,
    Quotation, QuotationItem, SupportTicket, TicketCategory, TicketComment,
    Campaign, CampaignResponse, CommissionAccrual
)
from .forms import (
    CustomerForm, ContactPersonForm, OpportunityForm,
    ActivityForm, QuotationForm, QuotationItemFormSet,
    SupportTicketForm, CampaignForm
)

# Dashboard Views
@login_required
def dashboard(request):
    """لوحة التحكم الرئيسية"""
    # الإحصائيات الأساسية
    stats = {
        'total_customers': Customer.objects.count(),
        'active_customers': Customer.objects.filter(status='active').count(),
        'open_opportunities': Opportunity.objects.filter(
            stage__is_won=False, stage__is_lost=False
        ).count(),
        'open_tickets': SupportTicket.objects.filter(status__in=['open', 'in_progress']).count(),
    }
    
    # الفرص المتأخرة
    overdue_opportunities = Opportunity.objects.filter(
        expected_close_date__lt=timezone.now().date(),
        stage__is_won=False,
        stage__is_lost=False
    )[:10]
    
    # الأنشطة القادمة
    upcoming_activities = Activity.objects.filter(
        scheduled_date__gte=timezone.now(),
        scheduled_date__lte=timezone.now() + timedelta(days=7),
        status='planned'
    ).select_related('customer', 'activity_type')[:10]
    
    # الفرص حسب المرحلة
    opportunities_by_stage = list(
        OpportunityStage.objects.annotate(
            count=Count('opportunity')
        ).values('name', 'count')
    )
    
    # إحصائيات حقيقية
    total_opportunities = Opportunity.objects.count()
    won_opportunities = Opportunity.objects.filter(stage__is_won=True).count()
    conversion_rate = round((won_opportunities / total_opportunities * 100), 1) if total_opportunities > 0 else 0
    
    # متوسط وقت الرد على التذاكر (بالساعات)
    from django.db.models import F, ExpressionWrapper, DurationField
    avg_response = 0
    resolved_tickets = SupportTicket.objects.filter(status='resolved', resolved_at__isnull=False)
    if resolved_tickets.exists():
        total_hours = 0
        count = 0
        for ticket in resolved_tickets[:100]:
            if ticket.resolved_at and ticket.created_at:
                delta = ticket.resolved_at - ticket.created_at
                total_hours += delta.total_seconds() / 3600
                count += 1
        avg_response = round(total_hours / count, 1) if count > 0 else 0
    
    # معدل الرضا (بناءً على التذاكر المحلولة vs الكلية)
    total_tickets = SupportTicket.objects.count()
    resolved_count = SupportTicket.objects.filter(status='resolved').count()
    satisfaction_rate = round((resolved_count / total_tickets * 100), 1) if total_tickets > 0 else 0
    
    # عدد المراحل الفعلية التي فيها فرص
    active_stages = OpportunityStage.objects.annotate(
        opp_count=Count('opportunity')
    ).filter(opp_count__gt=0).count()
    
    context = {
        'stats': stats,
        'overdue_opportunities': overdue_opportunities,
        'upcoming_activities': upcoming_activities,
        'opportunities_by_stage': json.dumps(opportunities_by_stage),
        'active_stages': active_stages,
        'satisfaction_rate': satisfaction_rate,
        'avg_response': avg_response,
        'conversion_rate': conversion_rate,
        'total_opportunities': total_opportunities,
    }
    
    return render(request, 'crm/dashboard.html', context)

# Customer Views
@login_required
def customer_list(request):
    """قائمة العملاء - محسّن للأداء"""
    # تحسين الأداء باستخدام select_related و prefetch_related
    customers = Customer.objects.select_related(
        'customer_type',
        'source',
        'assigned_to'
    ).prefetch_related(
        'contacts'
    )

    # فلتر البحث
    search = request.GET.get('search')
    search_type = request.GET.get('search_type', 'all').lower()
    if search:
        terms = [t.strip() for t in search.split() if t.strip()]
        if search_type == 'code':
            customers = customers.filter(customer_code__icontains=search)
        elif search_type == 'mobile':
            customers = customers.filter(mobile__icontains=search)
        elif search_type == 'phone':
            customers = customers.filter(phone__icontains=search)
        elif search_type == 'name':
            q_obj = Q(first_name__icontains=search) | Q(last_name__icontains=search) | Q(company_name__icontains=search)
            if len(terms) > 1:
                for term in terms:
                    q_obj |= Q(first_name__icontains=term) | Q(last_name__icontains=term) | Q(company_name__icontains=term)
            customers = customers.filter(q_obj)
        else:  # all
            q_obj = (
                Q(customer_code__icontains=search) |
                Q(phone__icontains=search) |
                Q(mobile__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(company_name__icontains=search)
            )
            if len(terms) > 1:
                for term in terms:
                    q_obj |= Q(first_name__icontains=term) | Q(last_name__icontains=term) | Q(company_name__icontains=term)
            customers = customers.filter(q_obj)
    
    # فلتر النوع
    customer_type = request.GET.get('customer_type')
    if customer_type:
        customers = customers.filter(customer_type_id=customer_type)
    
    # فلتر الحالة
    status = request.GET.get('status')
    if status:
        customers = customers.filter(status=status)

    # فلتر مصدر العميل
    source = request.GET.get('source')
    if source:
        customers = customers.filter(source_id=source)
    
    # تقسيم الصفحات
    paginator = Paginator(customers, 12)
    page = request.GET.get('page')
    customers = paginator.get_page(page)
    
    context = {
        'customers': customers,
        'customer_types': CustomerType.objects.all(),
    'customer_sources': CustomerSource.objects.filter(is_active=True),
        'search': search,
    'selected_search_type': search_type,
        'selected_customer_type': customer_type,
    'selected_status': status,
    'selected_source': source,
    }
    
    return render(request, 'crm/customer_list.html', context)

@login_required
def customer_detail(request, pk):
    """تفاصيل العميل"""
    customer = get_object_or_404(Customer, pk=pk)
    
    # جهات الاتصال
    contacts = ContactPerson.objects.filter(customer=customer)
    
    # الفرص
    opportunities_qs = Opportunity.objects.filter(customer=customer).select_related('stage')
    opportunities = opportunities_qs[:10]
    
    # الأنشطة
    activities_qs = Activity.objects.filter(customer=customer).select_related('activity_type')
    activities = activities_qs[:10]
    
    # عروض الأسعار
    quotations_qs = Quotation.objects.filter(customer=customer)
    quotations = quotations_qs[:10]
    
    # تذاكر الدعم
    tickets_qs = SupportTicket.objects.filter(customer=customer).select_related('category')
    tickets = tickets_qs[:10]
    
    # إحصائيات العميل
    customer_stats = {
        'total_opportunities': opportunities_qs.count(),
        'won_opportunities': opportunities_qs.filter(stage__is_won=True).count(),
        'activities_count': activities_qs.count(),
        'quotations_count': quotations_qs.count(),
        'tickets_count': tickets_qs.count(),
        'total_value': opportunities_qs.aggregate(total=Sum('estimated_value'))['total'] or 0,
    }
    
    context = {
        'customer': customer,
        'contacts': contacts,
        'opportunities': opportunities,
        'activities': activities,
        'quotations': quotations,
        'tickets': tickets,
        'customer_stats': customer_stats,
    }
    
    return render(request, 'crm/customer_detail.html', context)

@login_required
def customer_create(request):
    """إضافة عميل جديد"""
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save(commit=False)
            # الكود يُولّد الآن تلقائياً في نموذج Customer.save()
            customer.save()
            
            messages.success(request, f'تم إضافة العميل {customer.full_name} بنجاح')
            
            if 'save_and_add_another' in request.POST:
                return redirect('crm:customer_create')
            else:
                return redirect('crm:customer_detail', pk=customer.pk)
    else:
        form = CustomerForm()
    
    return render(request, 'crm/customer_form.html', {'form': form})

@login_required
def customer_edit(request, pk):
    """تعديل بيانات العميل"""
    customer = get_object_or_404(Customer, pk=pk)
    
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, f'تم تحديث بيانات العميل {customer.full_name} بنجاح')
            return redirect('crm:customer_detail', pk=customer.pk)
    else:
        form = CustomerForm(instance=customer)
    
    return render(request, 'crm/customer_form.html', {
        'form': form,
        'object': customer
    })

@login_required
def customer_delete(request, pk):
    """حذف عميل"""
    customer = get_object_or_404(Customer, pk=pk)
    
    if request.method == 'POST':
        customer_name = customer.full_name
        customer.delete()
        messages.success(request, f'تم حذف العميل {customer_name} بنجاح')
        return redirect('crm:customer_list')
    
    return render(request, 'crm/customer_confirm_delete.html', {'customer': customer})

# Contact Person Views
@login_required
def contact_create(request):
    """إضافة جهة اتصال جديدة - صفحة شاملة"""
    customers = Customer.objects.filter(owner=request.user).order_by('company_name') if hasattr(Customer, 'owner') else Customer.objects.all().order_by('company_name')
    
    if request.method == 'POST':
        customer_pk = request.POST.get('customer')
        if customer_pk:
            customer = get_object_or_404(Customer, pk=customer_pk)
            form = ContactPersonForm(request.POST)
            if form.is_valid():
                contact = form.save(commit=False)
                contact.customer = customer
                contact.save()
                messages.success(request, 'تم إضافة جهة الاتصال بنجاح')
                return redirect('crm:contact_list')
        else:
            messages.error(request, 'يرجى اختيار عميل')
            form = ContactPersonForm(request.POST)
    else:
        form = ContactPersonForm()
    
    context = {
        'form': form,
        'customers': customers,
        'title': 'إضافة جهة اتصال جديدة'
    }
    
    return render(request, 'crm/contact_create.html', context)

@login_required
def contact_person_create(request, customer_pk):
    """إضافة جهة اتصال جديدة"""
    customer = get_object_or_404(Customer, pk=customer_pk)
    
    if request.method == 'POST':
        form = ContactPersonForm(request.POST)
        if form.is_valid():
            contact = form.save(commit=False)
            contact.customer = customer
            contact.save()
            
            messages.success(request, 'تم إضافة جهة الاتصال بنجاح')
            return redirect('crm:customer_detail', pk=customer.pk)
    else:
        form = ContactPersonForm()
    
    context = {
        'form': form,
        'customer': customer,
        'title': 'إضافة جهة اتصال جديدة'
    }
    
    return render(request, 'crm/contact_person_form.html', context)

@login_required
def contact_person_edit(request, pk):
    """تعديل جهة اتصال"""
    contact = get_object_or_404(ContactPerson, pk=pk)
    
    if request.method == 'POST':
        form = ContactPersonForm(request.POST, instance=contact)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث جهة الاتصال بنجاح')
            return redirect('crm:customer_detail', pk=contact.customer.pk)
    else:
        form = ContactPersonForm(instance=contact)
    
    context = {
        'form': form,
        'contact': contact,
        'customer': contact.customer,
        'title': 'تعديل جهة الاتصال'
    }
    
    return render(request, 'crm/contact_person_form.html', context)

@login_required
def contact_person_delete(request, pk):
    """حذف جهة اتصال"""
    contact = get_object_or_404(ContactPerson, pk=pk)
    customer = contact.customer
    
    if request.method == 'POST':
        contact.delete()
        messages.success(request, 'تم حذف جهة الاتصال بنجاح')
        return redirect('crm:customer_detail', pk=customer.pk)
    
    return render(request, 'crm/contact_person_confirm_delete.html', {
        'contact': contact,
        'customer': customer
    })

# Opportunity Views
@login_required
def opportunity_list(request):
    """قائمة الفرص التجارية - محسّن للأداء"""
    # تحسين الأداء باستخدام select_related و prefetch_related
    opportunities = Opportunity.objects.select_related(
        'customer',
        'stage',
        'assigned_to',
        'contact_person',
        'closed_by'
    ).prefetch_related(
        'activity_set'
    )
    
    # الفلاتر
    search = request.GET.get('search')
    if search:
        opportunities = opportunities.filter(
            Q(name__icontains=search) |
            Q(customer__first_name__icontains=search) |
            Q(customer__last_name__icontains=search) |
            Q(customer__company_name__icontains=search)
        )
    
    stage = request.GET.get('stage')
    if stage:
        opportunities = opportunities.filter(stage_id=stage)
    
    overdue = request.GET.get('overdue')
    if overdue:
        opportunities = opportunities.filter(
            expected_close_date__lt=timezone.now().date(),
            stage__is_won=False,
            stage__is_lost=False
        )

    # فلتر المكلف (مسؤول المبيعات)
    assigned_to = request.GET.get('assigned_to')
    if assigned_to:
        opportunities = opportunities.filter(assigned_to_id=assigned_to)

    # فلتر المندوب الذي أغلق الصفقة
    closed_by = request.GET.get('closed_by')
    if closed_by:
        opportunities = opportunities.filter(closed_by_id=closed_by)
    
    # تقسيم الصفحات
    paginator = Paginator(opportunities, 20)
    page = request.GET.get('page')
    opportunities = paginator.get_page(page)
    
    context = {
        'opportunities': opportunities,
        'stages': OpportunityStage.objects.all(),
        'sales_users': User.objects.filter(is_active=True),
        'sales_employees': __import__('hr.models', fromlist=['Employee']).Employee.objects.filter(status='active'),
        'search': search,
        'selected_stage': stage,
    'selected_assigned': assigned_to,
        'selected_closed_by': closed_by,
    }
    
    return render(request, 'crm/opportunity_list.html', context)

@login_required
def opportunity_kanban(request):
    """عرض كانبان للفرص"""
    stages = OpportunityStage.objects.prefetch_related(
        'opportunity_set__customer'
    ).order_by('order')
    
    return render(request, 'crm/opportunity_kanban.html', {
        'stages': stages
    })

@login_required
def opportunity_create(request):
    """إضافة فرصة تجارية جديدة"""
    if request.method == 'POST':
        form = OpportunityForm(request.POST)
        if form.is_valid():
            opportunity = form.save(commit=False)
            # تعيين احتمالية النجاح من المرحلة
            opportunity.probability = opportunity.stage.probability
            opportunity.save()
            
            messages.success(request, f'تم إضافة الفرصة التجارية "{opportunity.name}" بنجاح')
            return redirect('crm:opportunity_detail', pk=opportunity.pk)
    else:
        form = OpportunityForm()
        # تعيين المستخدم الحالي كافتراضي
        form.fields['assigned_to'].initial = request.user
    
    context = {
        'form': form,
        'title': 'إضافة فرصة تجارية جديدة'
    }
    return render(request, 'crm/opportunity_form.html', context)

@login_required
def opportunity_detail(request, pk):
    """تفاصيل الفرصة التجارية"""
    opportunity = get_object_or_404(Opportunity, pk=pk)
    
    # الأنشطة المرتبطة بهذه الفرصة
    activities = Activity.objects.filter(opportunity=opportunity).select_related(
        'activity_type', 'assigned_to'
    ).order_by('-scheduled_date')[:10]
    
    # عروض الأسعار المرتبطة
    quotations = Quotation.objects.filter(opportunity=opportunity)[:5]
    
    # إحصائيات الفرصة
    opportunity_stats = {
        'activities_count': activities.count(),
        'quotations_count': quotations.count(),
        'days_since_created': (timezone.now().date() - opportunity.created_at.date()).days,
        'days_until_close': (opportunity.expected_close_date - timezone.now().date()).days if opportunity.expected_close_date >= timezone.now().date() else None,
    }
    
    context = {
        'opportunity': opportunity,
        'activities': activities,
        'quotations': quotations,
        'opportunity_stats': opportunity_stats,
        'all_stages': OpportunityStage.objects.all().order_by('order'),
    }
    
    return render(request, 'crm/opportunity_detail.html', context)

@login_required
def opportunity_edit(request, pk):
    """تعديل الفرصة التجارية"""
    opportunity = get_object_or_404(Opportunity, pk=pk)
    
    if request.method == 'POST':
        form = OpportunityForm(request.POST, instance=opportunity)
        if form.is_valid():
            updated_opportunity = form.save(commit=False)
            # تحديث احتمالية النجاح من المرحلة
            updated_opportunity.probability = updated_opportunity.stage.probability
            # إذا تم تحديث المرحلة إلى مرحلة ربح أو خسارة، تحديث تاريخ الإغلاق
            if updated_opportunity.stage.is_won or updated_opportunity.stage.is_lost:
                if not updated_opportunity.closed_at:
                    updated_opportunity.closed_at = timezone.now()
                # تعيين الموظف الذي أغلق الفرصة إذا كانت ربح
                if updated_opportunity.stage.is_won and not updated_opportunity.closed_by:
                    # محاولة إيجاد ملف الموظف المرتبط بالمستخدم الحالي
                    employee = getattr(request.user, 'employee_profile', None)
                    if employee:
                        updated_opportunity.closed_by = employee
            updated_opportunity.save()
            
            messages.success(request, f'تم تحديث الفرصة التجارية "{opportunity.name}" بنجاح')
            return redirect('crm:opportunity_detail', pk=opportunity.pk)
    else:
        form = OpportunityForm(instance=opportunity)
    
    context = {
        'form': form,
        'opportunity': opportunity,
        'title': 'تعديل الفرصة التجارية'
    }
    return render(request, 'crm/opportunity_form.html', context)

@login_required
def opportunity_delete(request, pk):
    """حذف فرصة تجارية"""
    opportunity = get_object_or_404(Opportunity, pk=pk)
    
    if request.method == 'POST':
        opportunity_name = opportunity.name
        opportunity.delete()
        messages.success(request, f'تم حذف الفرصة التجارية "{opportunity_name}" بنجاح')
        return redirect('crm:opportunity_list')
    
    return render(request, 'crm/opportunity_confirm_delete.html', {'opportunity': opportunity})

@login_required
@require_POST
def opportunity_move_stage(request, pk):
    """نقل الفرصة إلى مرحلة أخرى (AJAX)"""
    try:
        opportunity = get_object_or_404(Opportunity, pk=pk)
        stage_id = request.POST.get('stage_id')
        
        if not stage_id:
            return JsonResponse({'success': False, 'message': 'معرف المرحلة مطلوب'})
        
        stage = get_object_or_404(OpportunityStage, pk=stage_id)
        opportunity.stage = stage
        opportunity.probability = stage.probability
        
        # إذا كانت مرحلة ربح أو خسارة، تحديث تاريخ الإغلاق
        if stage.is_won or stage.is_lost:
            if not opportunity.closed_at:
                opportunity.closed_at = timezone.now()
            if stage.is_won and not opportunity.closed_by:
                employee = getattr(request.user, 'employee_profile', None)
                if employee:
                    opportunity.closed_by = employee
        else:
            opportunity.closed_at = None
            opportunity.closed_by = None
            
        opportunity.save()
        
        return JsonResponse({
            'success': True,
            'message': f'تم نقل الفرصة إلى مرحلة "{stage.name}" بنجاح',
            'stage_name': stage.name
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
def opportunity_convert(request, pk):
    """تحويل الفرصة إلى عرض سعر أو فاتورة"""
    opportunity = get_object_or_404(Opportunity, pk=pk)
    
    if request.method == 'POST':
        convert_to = request.POST.get('convert_to')
        
        if convert_to == 'quotation':
            # إنشاء عرض سعر جديد
            quotation = Quotation.objects.create(
                customer=opportunity.customer,
                opportunity=opportunity,
                contact_person=opportunity.contact_person,
                quotation_date=timezone.now().date(),
                valid_until=timezone.now().date() + timedelta(days=30),
                prepared_by=request.user,
                quotation_number=f"QUO{Quotation.objects.count() + 1:05d}"
            )
            messages.success(request, f'تم إنشاء عرض السعر رقم {quotation.quotation_number} بنجاح')
            return redirect('crm:quotation_detail', pk=quotation.pk)
        
        # يمكن إضافة تحويل إلى فاتورة لاحقاً
    
    context = {
        'opportunity': opportunity,
        'title': 'تحويل الفرصة التجارية'
    }
    return render(request, 'crm/opportunity_convert.html', context)

# Activity Views
@login_required
def activity_list(request):
    """قائمة الأنشطة"""
    activities = Activity.objects.select_related(
        'customer', 'opportunity', 'activity_type', 'assigned_to'
    )
    
    # فلاتر البحث
    search = request.GET.get('search')
    if search:
        activities = activities.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(customer__first_name__icontains=search) |
            Q(customer__last_name__icontains=search)
        )
    
    # فلتر الحالة
    status = request.GET.get('status')
    if status:
        activities = activities.filter(status=status)
    
    # فلتر نوع النشاط
    activity_type = request.GET.get('activity_type')
    if activity_type:
        activities = activities.filter(activity_type_id=activity_type)
    
    # فلتر الأنشطة المتأخرة
    overdue = request.GET.get('overdue')
    if overdue:
        activities = activities.filter(
            scheduled_date__lt=timezone.now(),
            status__in=['planned', 'in_progress']
        )
    
    # فلتر المكلف
    assigned_to = request.GET.get('assigned_to')
    if assigned_to:
        activities = activities.filter(assigned_to_id=assigned_to)
    
    # ترتيب حسب الموعد المحدد
    activities = activities.order_by('scheduled_date')
    
    # تقسيم الصفحات
    paginator = Paginator(activities, 20)
    page = request.GET.get('page')
    activities = paginator.get_page(page)
    
    context = {
        'activities': activities,
        'activity_types': ActivityType.objects.all(),
        'users': User.objects.filter(is_active=True),
        'search': search,
        'selected_status': status,
        'selected_activity_type': activity_type,
        'selected_assigned_to': assigned_to,
    }
    
    return render(request, 'crm/activity_list.html', context)

@login_required
def activity_calendar(request):
    """تقويم الأنشطة"""
    # الحصول على الأنشطة للشهر الحالي
    current_month = timezone.now().month
    current_year = timezone.now().year
    
    month = request.GET.get('month', current_month)
    year = request.GET.get('year', current_year)
    
    activities = Activity.objects.filter(
        scheduled_date__month=month,
        scheduled_date__year=year
    ).select_related('customer', 'activity_type', 'assigned_to')
    
    # تحويل الأنشطة إلى تنسيق JSON للتقويم
    calendar_events = []
    for activity in activities:
        calendar_events.append({
            'id': activity.id,
            'title': activity.title,
            'start': activity.scheduled_date.isoformat(),
            'end': (activity.scheduled_date + timedelta(minutes=activity.duration_minutes)).isoformat(),
            'backgroundColor': activity.activity_type.color if hasattr(activity.activity_type, 'color') else '#007bff',
            'url': f'/crm/activities/{activity.id}/',
            'customer': activity.customer.full_name if activity.customer else '',
            'status': activity.get_status_display(),
        })
    
    context = {
        'calendar_events': json.dumps(calendar_events),
        'current_month': int(month),
        'current_year': int(year),
    }
    
    return render(request, 'crm/activity_calendar.html', context)

@login_required
def activity_create(request):
    """إنشاء نشاط جديد"""
    if request.method == 'POST':
        form = ActivityForm(request.POST)
        if form.is_valid():
            activity = form.save(commit=False)
            # تعيين المستخدم الحالي إذا لم يتم تعيين أحد
            if not activity.assigned_to:
                activity.assigned_to = request.user
            activity.save()
            
            messages.success(request, f'تم إضافة النشاط "{activity.title}" بنجاح')
            return redirect('crm:activity_detail', pk=activity.pk)
    else:
        form = ActivityForm()
        # إعدادات افتراضية
        form.fields['assigned_to'].initial = request.user
        form.fields['scheduled_date'].initial = timezone.now()
        
        # إذا تم تمرير customer_id أو opportunity_id في URL
        customer_id = request.GET.get('customer_id')
        if customer_id:
            form.fields['customer'].initial = customer_id
            
        opportunity_id = request.GET.get('opportunity_id')
        if opportunity_id:
            form.fields['opportunity'].initial = opportunity_id
    
    context = {
        'form': form,
        'title': 'إنشاء نشاط جديد'
    }
    return render(request, 'crm/activity_form.html', context)

@login_required
def activity_detail(request, pk):
    """تفاصيل النشاط"""
    activity = get_object_or_404(Activity, pk=pk)
    
    context = {
        'activity': activity,
    }
    
    return render(request, 'crm/activity_detail.html', context)

@login_required
def activity_edit(request, pk):
    """تعديل النشاط"""
    activity = get_object_or_404(Activity, pk=pk)
    
    if request.method == 'POST':
        form = ActivityForm(request.POST, instance=activity)
        if form.is_valid():
            form.save()
            messages.success(request, f'تم تحديث النشاط "{activity.title}" بنجاح')
            return redirect('crm:activity_detail', pk=activity.pk)
    else:
        form = ActivityForm(instance=activity)
    
    context = {
        'form': form,
        'activity': activity,
        'title': 'تعديل النشاط'
    }
    return render(request, 'crm/activity_form.html', context)

@login_required
def activity_delete(request, pk):
    """حذف نشاط"""
    activity = get_object_or_404(Activity, pk=pk)
    
    if request.method == 'POST':
        activity_title = activity.title
        activity.delete()
        messages.success(request, f'تم حذف النشاط "{activity_title}" بنجاح')
        return redirect('crm:activity_list')
    
    return render(request, 'crm/activity_confirm_delete.html', {'activity': activity})

@login_required
@require_POST
def activity_complete(request, pk):
    """إكمال النشاط"""
    activity = get_object_or_404(Activity, pk=pk)
    
    outcome = request.POST.get('outcome', '')
    follow_up_required = request.POST.get('follow_up_required') == 'on'
    follow_up_date = request.POST.get('follow_up_date')
    
    activity.status = 'completed'
    activity.completed_at = timezone.now()
    activity.outcome = outcome
    activity.follow_up_required = follow_up_required
    
    if follow_up_date:
        try:
            activity.follow_up_date = datetime.strptime(follow_up_date, '%Y-%m-%dT%H:%M')
        except ValueError:
            pass
    
    activity.save()
    
    # تحديث تاريخ آخر تواصل مع العميل
    if activity.customer:
        activity.customer.last_contact_date = timezone.now()
        activity.customer.save()
    
    messages.success(request, f'تم إكمال النشاط "{activity.title}" بنجاح')
    
    # إذا كان طلب AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': 'تم إكمال النشاط بنجاح'})
    
    return redirect('crm:activity_detail', pk=activity.pk)

# Quotation Views
@login_required
def quotation_list(request):
    """قائمة عروض الأسعار"""
    quotations = Quotation.objects.select_related('customer', 'opportunity', 'prepared_by')
    
    # فلاتر البحث
    search = request.GET.get('search')
    if search:
        quotations = quotations.filter(
            Q(quotation_number__icontains=search) |
            Q(customer__first_name__icontains=search) |
            Q(customer__last_name__icontains=search) |
            Q(customer__company_name__icontains=search)
        )
    
    # فلتر الحالة
    status = request.GET.get('status')
    if status:
        quotations = quotations.filter(status=status)
    
    # فلتر العميل
    customer = request.GET.get('customer')
    if customer:
        quotations = quotations.filter(customer_id=customer)
    
    # فلتر المعد
    prepared_by = request.GET.get('prepared_by')
    if prepared_by:
        quotations = quotations.filter(prepared_by_id=prepared_by)
    
    # فلتر منتهية الصلاحية
    expired = request.GET.get('expired')
    if expired:
        quotations = quotations.filter(
            valid_until__lt=timezone.now().date(),
            status__in=['draft', 'sent']
        )
    
    # ترتيب حسب تاريخ الإنشاء
    quotations = quotations.order_by('-created_at')
    
    # تقسيم الصفحات
    paginator = Paginator(quotations, 15)
    page = request.GET.get('page')
    quotations = paginator.get_page(page)
    
    context = {
        'quotations': quotations,
        'customers': Customer.objects.filter(status='active'),
        'users': User.objects.filter(is_active=True),
        'search': search,
        'selected_status': status,
        'selected_customer': customer,
        'selected_prepared_by': prepared_by,
    }
    
    return render(request, 'crm/quotation_list.html', context)

@login_required
def quotation_create(request):
    """إنشاء عرض سعر جديد"""
    if request.method == 'POST':
        form = QuotationForm(request.POST)
        formset = QuotationItemFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            quotation = form.save(commit=False)
            # إنشاء رقم عرض السعر تلقائياً
            last_quotation = Quotation.objects.order_by('-id').first()
            if last_quotation:
                last_number = int(last_quotation.quotation_number[3:]) if last_quotation.quotation_number[3:].isdigit() else 0
                quotation.quotation_number = f"QUO{last_number + 1:05d}"
            else:
                quotation.quotation_number = "QUO00001"
            
            quotation.prepared_by = request.user
            quotation.save()
            
            # حفظ الأصناف
            formset.instance = quotation
            items = formset.save()
            
            # حساب المجاميع
            quotation.calculate_totals()

            # تحذير غير معيق: إذا كان هناك خصم/ضريبة على مستوى الأصناف سيتم تجاهل الحقول العامة
            try:
                if getattr(formset, 'has_line_discount', False) and float(quotation.discount_percentage) > 0:
                    messages.warning(request, 'تم استخدام خصومات الأصناف، لذا تم تجاهل نسبة الخصم العامة في الحسابات.')
                if getattr(formset, 'has_line_tax', False) and float(quotation.tax_percentage) > 0:
                    messages.warning(request, 'تم استخدام ضرائب الأصناف، لذا تم تجاهل نسبة الضريبة العامة في الحسابات.')
            except Exception:
                pass
            
            messages.success(request, f'تم إنشاء عرض السعر رقم {quotation.quotation_number} بنجاح')
            return redirect('crm:quotation_detail', pk=quotation.pk)
    else:
        form = QuotationForm()
        formset = QuotationItemFormSet()
        
        # إعدادات افتراضية
        form.fields['quotation_date'].initial = timezone.now().date()
        form.fields['valid_until'].initial = timezone.now().date() + timedelta(days=30)
        form.fields['tax_percentage'].initial = 14.00  # القيمة المضافة في مصر
        
        # إذا تم تمرير customer_id أو opportunity_id في URL
        customer_id = request.GET.get('customer_id')
        if customer_id:
            form.fields['customer'].initial = customer_id
            
        opportunity_id = request.GET.get('opportunity_id')
        if opportunity_id:
            try:
                opportunity = Opportunity.objects.get(pk=opportunity_id)
                # نسخ البيانات من الفرصة التجارية
                form.fields['opportunity'].initial = opportunity_id
                form.fields['customer'].initial = opportunity.customer.id
                form.fields['contact_person'].initial = opportunity.contact_person.id if opportunity.contact_person else None
                # نسخ القيمة المقدرة كإجمالي
                form.initial['subtotal'] = opportunity.estimated_value
                # نسخ تاريخ الإغلاق المتوقع كصلاحية
                form.fields['valid_until'].initial = opportunity.expected_close_date
                # نسخ الوصف
                form.initial['notes'] = opportunity.description
            except Opportunity.DoesNotExist:
                pass
    
    context = {
        'form': form,
        'formset': formset,
        'title': 'إنشاء عرض سعر جديد'
    }
    return render(request, 'crm/quotation_form.html', context)

@login_required
def quotation_detail(request, pk):
    """تفاصيل عرض السعر"""
    from core.models import Company
    
    quotation = get_object_or_404(Quotation, pk=pk)
    
    # العناصر المرتبطة بعرض السعر
    quotation_items = QuotationItem.objects.filter(quotation=quotation).select_related('product')
    
    # جلب بيانات الشركة
    company = Company.objects.first()
    
    context = {
        'quotation': quotation,
        'quotation_items': quotation_items,
        'company': company,
    }
    
    return render(request, 'crm/quotation_detail.html', context)

@login_required
def quotation_print(request, pk):
    """عرض HTML قابل للطباعة لعرض السعر (يمكن لاحقاً تحويله PDF)."""
    from core.models import Company
    
    quotation = get_object_or_404(Quotation, pk=pk)
    quotation_items = quotation.items.select_related('product')
    company = Company.objects.first()
    auto_print = request.GET.get('auto_print', '0') == '1'
    
    # جلب بيانات الفرع
    branch_name = ''
    branch_phone = ''
    branch_address = ''
    
    if hasattr(quotation, 'showroom') and quotation.showroom:
        branch_name = quotation.showroom.name_ar or quotation.showroom.name
        branch_phone = quotation.showroom.contact_phone or ''
        branch_address = quotation.showroom.address or ''
    elif hasattr(request, 'active_showroom') and request.active_showroom:
        branch_name = request.active_showroom.name_ar or request.active_showroom.name
        branch_phone = request.active_showroom.contact_phone or ''
        branch_address = request.active_showroom.address or ''
    
    # جلب جميع الفروع
    all_branches = []
    try:
        from showrooms.models import Showroom
        for branch in Showroom.objects.filter(is_active=True).order_by('id'):
            all_branches.append({
                'name': branch.name_ar or branch.name,
                'country': branch.country or '',
                'governorate': branch.governorate or '',
                'city': branch.city or '',
                'address': branch.address or '',
                'phone': branch.contact_phone or '',
            })
    except:
        pass
    
    return render(request, 'crm/quotation_print.html', {
        'quotation': quotation,
        'items': quotation_items,
        'company': company,
        'branch_name': branch_name,
        'branch_phone': branch_phone,
        'branch_address': branch_address,
        'all_branches': all_branches,
        'auto_print': auto_print,
        'print_mode': True,
    })

@login_required
def quotation_edit(request, pk):
    """تعديل عرض السعر"""
    quotation = get_object_or_404(Quotation, pk=pk)
    
    if request.method == 'POST':
        form = QuotationForm(request.POST, instance=quotation)
        formset = QuotationItemFormSet(request.POST, instance=quotation)
        
        if form.is_valid() and formset.is_valid():
            updated_quotation = form.save()
            formset.save()
            
            # إعادة حساب المجاميع
            updated_quotation.calculate_totals()

            # تحذير غير معيق بنفس المنطق
            try:
                if getattr(formset, 'has_line_discount', False) and float(updated_quotation.discount_percentage) > 0:
                    messages.warning(request, 'تم استخدام خصومات الأصناف، لذا تم تجاهل نسبة الخصم العامة في الحسابات.')
                if getattr(formset, 'has_line_tax', False) and float(updated_quotation.tax_percentage) > 0:
                    messages.warning(request, 'تم استخدام ضرائب الأصناف، لذا تم تجاهل نسبة الضريبة العامة في الحسابات.')
            except Exception:
                pass
            
            messages.success(request, f'تم تحديث عرض السعر رقم {quotation.quotation_number} بنجاح')
            return redirect('crm:quotation_detail', pk=quotation.pk)
    else:
        form = QuotationForm(instance=quotation)
        formset = QuotationItemFormSet(instance=quotation)
    
    context = {
        'form': form,
        'formset': formset,
        'quotation': quotation,
        'title': 'تعديل عرض السعر'
    }
    return render(request, 'crm/quotation_form.html', context)

@login_required
def quotation_delete(request, pk):
    """حذف عرض السعر"""
    quotation = get_object_or_404(Quotation, pk=pk)
    
    if request.method == 'POST':
        quotation_number = quotation.quotation_number
        quotation.delete()
        messages.success(request, f'تم حذف عرض السعر رقم {quotation_number} بنجاح')
        return redirect('crm:quotation_list')
    
    return render(request, 'crm/quotation_confirm_delete.html', {'quotation': quotation})

@login_required
def quotation_duplicate(request, pk):
    """نسخ عرض السعر"""
    original_quotation = get_object_or_404(Quotation, pk=pk)
    
    # إنشاء نسخة جديدة
    new_quotation = Quotation.objects.create(
        customer=original_quotation.customer,
        opportunity=original_quotation.opportunity,
        contact_person=original_quotation.contact_person,
        quotation_date=timezone.now().date(),
        valid_until=timezone.now().date() + timedelta(days=30),
        discount_percentage=original_quotation.discount_percentage,
        tax_percentage=original_quotation.tax_percentage,
        terms_and_conditions=original_quotation.terms_and_conditions,
        notes=original_quotation.notes,
        prepared_by=request.user,
        quotation_number=f"QUO{Quotation.objects.count() + 1:05d}",
        status='draft'
    )
    
    # نسخ الأصناف
    for item in original_quotation.items.all():
        QuotationItem.objects.create(
            quotation=new_quotation,
            product=item.product,
            description=item.description,
            quantity=item.quantity,
            unit_price=item.unit_price,
            discount_percentage=getattr(item, 'discount_percentage', 0) or 0,
            tax_percentage=getattr(item, 'tax_percentage', 0) or 0,
        )
    
    # حساب المجاميع
    new_quotation.calculate_totals()
    
    messages.success(request, f'تم إنشاء نسخة جديدة برقم {new_quotation.quotation_number} بنجاح')
    return redirect('crm:quotation_detail', pk=new_quotation.pk)

@login_required
@require_POST
def quotation_send(request, pk):
    """إرسال عرض السعر"""
    quotation = get_object_or_404(Quotation, pk=pk)
    
    quotation.status = 'sent'
    quotation.sent_at = timezone.now()
    quotation.save()
    
    messages.success(request, f'تم إرسال عرض السعر رقم {quotation.quotation_number} بنجاح')
    
    # إذا كان طلب AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': 'تم إرسال عرض السعر بنجاح'})
    
    return redirect('crm:quotation_detail', pk=quotation.pk)

@login_required
@require_POST
def quotation_accept(request, pk):
    """قبول عرض السعر"""
    quotation = get_object_or_404(Quotation, pk=pk)
    
    quotation.status = 'accepted'
    quotation.responded_at = timezone.now()
    quotation.save()
    
    # إذا كانت مرتبطة بفرصة تجارية، تحديث حالة الفرصة
    if quotation.opportunity:
        won_stage = OpportunityStage.objects.filter(is_won=True).first()
        if won_stage:
            quotation.opportunity.stage = won_stage
            quotation.opportunity.probability = won_stage.probability
            quotation.opportunity.closed_at = timezone.now()
            # تعيين الموظف الذي أغلق الصفقة (إن وجد)
            employee = getattr(request.user, 'employee_profile', None)
            if employee:
                quotation.opportunity.closed_by = employee
            quotation.opportunity.save()

    # إنشاء استحقاق عمولة لمندوب المبيعات الذي أغلق الصفقة
    employee = getattr(request.user, 'employee_profile', None)
    if employee:
        try:
            CommissionAccrual.create_for_quotation(quotation, employee, created_by=request.user)
        except Exception:
            pass  # لا نفشل العملية بسبب العمولة
    
    messages.success(request, f'تم قبول عرض السعر رقم {quotation.quotation_number} بنجاح')
    
    # إذا كان طلب AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': 'تم قبول عرض السعر بنجاح'})
    
    return redirect('crm:quotation_detail', pk=quotation.pk)

@login_required
@require_POST
def quotation_reject(request, pk):
    """رفض عرض السعر"""
    quotation = get_object_or_404(Quotation, pk=pk)
    
    quotation.status = 'rejected'
    quotation.responded_at = timezone.now()
    quotation.save()
    
    # إذا كانت مرتبطة بفرصة تجارية، تحديث حالة الفرصة
    if quotation.opportunity:
        lost_stage = OpportunityStage.objects.filter(is_lost=True).first()
        if lost_stage:
            quotation.opportunity.stage = lost_stage
            quotation.opportunity.probability = lost_stage.probability
            quotation.opportunity.closed_at = timezone.now()
            quotation.opportunity.save()
    
    messages.success(request, f'تم رفض عرض السعر رقم {quotation.quotation_number}')
    
    # إذا كان طلب AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': 'تم رفض عرض السعر'})
    
    return redirect('crm:quotation_detail', pk=quotation.pk)

@login_required
def quotation_pdf(request, pk):
    """تصدير عرض السعر كـ PDF"""
    quotation = get_object_or_404(Quotation, pk=pk)
    
    # هنا يمكن استخدام مكتبة مثل reportlab أو weasyprint
    # للمثال سنعيد template بسيط
    context = {
        'quotation': quotation,
        'quotation_items': quotation.items.all(),
    }
    
    response = HttpResponse(content_type='text/html')
    response['Content-Disposition'] = f'inline; filename="quotation_{quotation.quotation_number}.html"'
    
    # تمرير request لضمان تفعيل context processors وتحديد BASE_TEMPLATE
    html_content = render_to_string('crm/quotation_pdf.html', context, request=request)
    response.write(html_content)
    
    return response


@login_required
@require_POST
def quotation_send_email(request, pk):
    """إرسال عرض السعر بالإيميل"""
    import json
    from django.core.mail import EmailMultiAlternatives
    from django.template.loader import render_to_string
    from core.models import Company
    
    quotation = get_object_or_404(Quotation, pk=pk)
    
    try:
        data = json.loads(request.body)
        email_to = data.get('email', '')
        subject = data.get('subject', f'عرض سعر رقم {quotation.quotation_number}')
        body = data.get('body', '')
        
        if not email_to:
            return JsonResponse({'success': False, 'error': 'البريد الإلكتروني مطلوب'})
        
        # جلب بيانات الشركة
        company = Company.objects.first()
        
        # إنشاء HTML للإيميل
        html_content = render_to_string('crm/quotation_email.html', {
            'quotation': quotation,
            'items': quotation.items.all(),
            'company': company,
            'body': body,
        })
        
        # إنشاء الإيميل
        email = EmailMultiAlternatives(
            subject=subject,
            body=body,
            from_email=None,  # سيستخدم DEFAULT_FROM_EMAIL
            to=[email_to],
        )
        email.attach_alternative(html_content, "text/html")
        
        # إرسال الإيميل
        email.send(fail_silently=False)
        
        return JsonResponse({
            'success': True,
            'message': f'تم إرسال الإيميل بنجاح إلى {email_to}'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
def quotation_convert_to_invoice(request, pk):
    """تحويل عرض السعر إلى فاتورة"""
    from sales.models import Invoice, InvoiceItem
    from inventory.models import Location
    from django.db import transaction
    
    quotation = get_object_or_404(Quotation, pk=pk)
    
    if quotation.status != 'accepted':
        messages.error(request, 'يجب قبول عرض السعر أولاً قبل تحويله إلى فاتورة')
        return redirect('crm:quotation_detail', pk=quotation.pk)
    
    if quotation.status == 'converted':
        messages.warning(request, 'تم تحويل هذا العرض مسبقاً إلى فاتورة')
        return redirect('crm:quotation_detail', pk=quotation.pk)
    
    try:
        with transaction.atomic():
            # Get default location (or first available)
            default_location = Location.objects.first()
            if not default_location:
                messages.error(request, 'لا توجد مواقع مخزنية متاحة. يجب إنشاء موقع مخزني أولاً')
                return redirect('crm:quotation_detail', pk=quotation.pk)
            
            # Create Invoice from Quotation
            invoice = Invoice.objects.create(
                customer=quotation.customer,
                date=timezone.now().date(),
                due_date=quotation.valid_until,
                discount=quotation.discount_amount,
                is_tax_inclusive=True if quotation.tax_amount > 0 else False,
                cached_total=quotation.total_amount,
            )
            
            # Copy items from Quotation to Invoice
            quotation_items = quotation.items.all()
            for q_item in quotation_items:
                InvoiceItem.objects.create(
                    invoice=invoice,
                    product=q_item.product,
                    location=default_location,
                    quantity=int(q_item.quantity),
                    price=q_item.unit_price,
                )
            
            # Update quotation status
            quotation.status = 'converted'
            quotation.save(update_fields=['status'])
            
            # Update opportunity if linked
            if quotation.opportunity:
                opportunity = quotation.opportunity
                # Move opportunity to won stage if exists
                won_stage = OpportunityStage.objects.filter(is_won=True).first()
                if won_stage:
                    opportunity.stage = won_stage
                    opportunity.probability = 100
                    opportunity.closed_at = timezone.now()
                    opportunity.save(update_fields=['stage', 'probability', 'closed_at'])
            
            messages.success(request, f'تم تحويل عرض السعر رقم {quotation.quotation_number} إلى فاتورة رقم {invoice.number} بنجاح')
            return redirect('sales:invoice_detail', pk=invoice.pk)
            
    except Exception as e:
        messages.error(request, f'حدث خطأ أثناء تحويل عرض السعر: {str(e)}')
        return redirect('crm:quotation_detail', pk=quotation.pk)

# Support Ticket Views
@login_required
def ticket_list(request):
    """قائمة تذاكر الدعم الفني"""
    tickets = SupportTicket.objects.select_related('customer', 'category', 'assigned_to', 'created_by')
    
    # فلاتر البحث
    search = request.GET.get('search')
    if search:
        tickets = tickets.filter(
            Q(ticket_number__icontains=search) |
            Q(title__icontains=search) |
            Q(customer__first_name__icontains=search) |
            Q(customer__last_name__icontains=search)
        )
    
    # فلتر الحالة
    status = request.GET.get('status')
    if status:
        tickets = tickets.filter(status=status)
    
    # فلتر الفئة
    category = request.GET.get('category')
    if category:
        tickets = tickets.filter(category_id=category)
    
    # فلتر الأولوية
    priority = request.GET.get('priority')
    if priority:
        tickets = tickets.filter(priority=priority)
    
    # فلتر المكلف
    assigned_to = request.GET.get('assigned_to')
    if assigned_to:
        tickets = tickets.filter(assigned_to_id=assigned_to)
    
    # ترتيب حسب تاريخ الإنشاء
    tickets = tickets.order_by('-created_at')
    
    # تقسيم الصفحات
    paginator = Paginator(tickets, 20)
    page = request.GET.get('page')
    tickets = paginator.get_page(page)
    
    context = {
        'tickets': tickets,
        'categories': TicketCategory.objects.all(),
        'users': User.objects.filter(is_active=True),
        'search': search,
        'selected_status': status,
        'selected_category': category,
        'selected_priority': priority,
        'selected_assigned_to': assigned_to,
    }
    
    return render(request, 'crm/tickets/ticket_list.html', context)

@login_required
def ticket_create(request):
    """إنشاء تذكرة دعم جديدة"""
    if request.method == 'POST':
        form = SupportTicketForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            
            # إنشاء رقم التذكرة تلقائياً
            last_ticket = SupportTicket.objects.order_by('-id').first()
            if last_ticket:
                last_number = int(last_ticket.ticket_number[3:]) if last_ticket.ticket_number[3:].isdigit() else 0
                ticket.ticket_number = f"TIC{last_number + 1:05d}"
            else:
                ticket.ticket_number = "TIC00001"
            
            ticket.created_by = request.user
            ticket.save()
            
            messages.success(request, f'تم إنشاء تذكرة الدعم رقم {ticket.ticket_number} بنجاح')
            return redirect('crm:ticket_detail', pk=ticket.pk)
    else:
        form = SupportTicketForm()
        
        # إذا تم تمرير customer_id في URL
        customer_id = request.GET.get('customer_id')
        if customer_id:
            form.fields['customer'].initial = customer_id
    
    context = {
        'form': form,
        'title': 'إنشاء تذكرة دعم جديدة'
    }
    return render(request, 'crm/tickets/ticket_form.html', context)

@login_required
def ticket_detail(request, pk):
    """تفاصيل تذكرة الدعم"""
    ticket = get_object_or_404(SupportTicket, pk=pk)
    
    # التعليقات
    comments = TicketComment.objects.filter(ticket=ticket).select_related('created_by').order_by('created_at')
    
    # إحصائيات التذكرة
    ticket_stats = {
        'comments_count': comments.count(),
        'days_open': (timezone.now().date() - ticket.created_at.date()).days,
        'response_time': (comments.first().created_at - ticket.created_at).days if comments.exists() else None,
    }
    
    context = {
        'ticket': ticket,
        'comments': comments,
        'ticket_stats': ticket_stats,
    }
    
    return render(request, 'crm/tickets/ticket_detail.html', context)

@login_required
def ticket_edit(request, pk):
    """تعديل تذكرة الدعم"""
    ticket = get_object_or_404(SupportTicket, pk=pk)
    
    if request.method == 'POST':
        form = SupportTicketForm(request.POST, instance=ticket)
        if form.is_valid():
            form.save()
            messages.success(request, f'تم تحديث تذكرة الدعم رقم {ticket.ticket_number} بنجاح')
            return redirect('crm:ticket_detail', pk=ticket.pk)
    else:
        form = SupportTicketForm(instance=ticket)
    
    context = {
        'form': form,
        'ticket': ticket,
        'title': 'تعديل تذكرة الدعم'
    }
    return render(request, 'crm/tickets/ticket_form.html', context)

@login_required
def ticket_delete(request, pk):
    """حذف تذكرة الدعم"""
    ticket = get_object_or_404(SupportTicket, pk=pk)
    
    if request.method == 'POST':
        ticket_number = ticket.ticket_number
        ticket.delete()
        messages.success(request, f'تم حذف تذكرة الدعم رقم {ticket_number} بنجاح')
        return redirect('crm:ticket_list')
    
    return render(request, 'crm/tickets/ticket_confirm_delete.html', {'ticket': ticket})

@login_required
@require_POST
def ticket_close(request, pk):
    """إغلاق تذكرة الدعم"""
    ticket = get_object_or_404(SupportTicket, pk=pk)
    
    ticket.status = 'closed'
    ticket.closed_at = timezone.now()
    ticket.save()
    
    messages.success(request, f'تم إغلاق تذكرة الدعم رقم {ticket.ticket_number} بنجاح')
    
    # إذا كان طلب AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': 'تم إغلاق التذكرة بنجاح'})
    
    return redirect('crm:ticket_detail', pk=ticket.pk)

@login_required
@require_POST
def ticket_add_comment(request, pk):
    """إضافة تعليق للتذكرة"""
    ticket = get_object_or_404(SupportTicket, pk=pk)
    
    comment_text = request.POST.get('comment')
    is_internal = request.POST.get('is_internal') == 'on'
    
    if comment_text:
        TicketComment.objects.create(
            ticket=ticket,
            comment=comment_text,
            is_internal=is_internal,
            created_by=request.user
        )
        
        messages.success(request, 'تم إضافة التعليق بنجاح')
    else:
        messages.error(request, 'نص التعليق مطلوب')
    
    # إذا كان طلب AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': bool(comment_text), 'message': 'تم إضافة التعليق بنجاح' if comment_text else 'نص التعليق مطلوب'})
    
    return redirect('crm:ticket_detail', pk=ticket.pk)

@login_required
@require_POST
def ticket_assign(request, pk):
    """تعيين تذكرة الدعم لمستخدم"""
    ticket = get_object_or_404(SupportTicket, pk=pk)
    
    user_id = request.POST.get('assigned_to')
    if user_id:
        try:
            user = User.objects.get(pk=user_id)
            ticket.assigned_to = user
            ticket.save()
            
            messages.success(request, f'تم تعيين التذكرة للمستخدم {user.get_full_name() or user.username} بنجاح')
        except User.DoesNotExist:
            messages.error(request, 'المستخدم غير موجود')
    else:
        ticket.assigned_to = None
        ticket.save()
        messages.success(request, 'تم إلغاء تعيين التذكرة')
    
    # إذا كان طلب AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': 'تم تعيين التذكرة بنجاح'})
    
    return redirect('crm:ticket_detail', pk=ticket.pk)

# AJAX Views (مكتملة)
@login_required
def ajax_customer_search(request):
    """البحث في العملاء عبر AJAX (بالكود أو الاسم أو الهاتف/الموبايل) مع ترتيب النتائج"""
    query = request.GET.get('q', '').strip()
    search_type = request.GET.get('type', 'all').lower()
    qs = Customer.objects.all()
    results = []
    if query:
        terms = [t.strip() for t in query.split() if t.strip()]
        if search_type == 'code':
            qs = qs.filter(customer_code__icontains=query)
        elif search_type == 'mobile':
            qs = qs.filter(mobile__icontains=query)
        elif search_type == 'phone':
            qs = qs.filter(phone__icontains=query)
        elif search_type == 'name':
            q_obj = Q(first_name__icontains=query) | Q(last_name__icontains=query) | Q(company_name__icontains=query)
            if len(terms) > 1:
                for term in terms:
                    q_obj |= Q(first_name__icontains=term) | Q(last_name__icontains=term) | Q(company_name__icontains=term)
            qs = qs.filter(q_obj)
        else:
            q_obj = (
                Q(customer_code__icontains=query) |
                Q(phone__icontains=query) |
                Q(mobile__icontains=query) |
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(company_name__icontains=query)
            )
            if len(terms) > 1:
                for term in terms:
                    q_obj |= Q(first_name__icontains=term) | Q(last_name__icontains=term) | Q(company_name__icontains=term)
            qs = qs.filter(q_obj)

        # نجلب مجموعة أكبر قليلاً للترتيب
        candidates = list(qs[:50])
        q_lower = query.lower()
        def rank(c: Customer):
            code = (c.customer_code or '').lower()
            full_name = f"{c.first_name} {c.last_name}".strip().lower()
            company = (c.company_name or '').lower()
            # ترتيب: تطابق كامل للكود، ثم يبدأ بالكود/الاسم/الشركة، ثم يحتوي
            if code == q_lower:
                return 0
            if code.startswith(q_lower):
                return 1
            if full_name.startswith(q_lower) or company.startswith(q_lower):
                return 2
            # وجود في أي مكان
            if q_lower in code:
                return 3
            if q_lower in full_name or q_lower in company:
                return 4
            # fallback
            return 5
        candidates.sort(key=rank)
        results = candidates[:10]

    data = [
        {
            'id': c.id,
            'text': f"{c.customer_code} - {c.full_name}",
            'company': c.company_name or ''
        } for c in results
    ]
    return JsonResponse({'results': data})

@login_required
def ajax_get_contacts(request, customer_id):
    """الحصول على جهات اتصال العميل"""
    contacts = ContactPerson.objects.filter(customer_id=customer_id)
    
    data = [{
        'id': contact.id,
        'name': contact.name,
        'position': contact.position,
        'phone': contact.phone,
        'email': contact.email,
        'is_primary': contact.is_primary
    } for contact in contacts]
    
    return JsonResponse({'contacts': data})

@login_required
@require_POST
def ajax_create_customer(request):
    """إنشاء عميل CRM سريع عبر AJAX.
    المدخلات المتوقعة: name, phone?, email?
    المخرجات: {success, id, name}
    """
    try:
        name = (request.POST.get('name') or '').strip()
        phone = (request.POST.get('phone') or '').strip()
        email = (request.POST.get('email') or '').strip()
        
        if not name:
            return JsonResponse({'success': False, 'message': 'الاسم مطلوب'}, status=400)
        
        # كشف تكرار بسيط (نفس الاسم أو الهاتف)
        from django.db.models import Q
        duplicate_qs = Customer.objects.filter(
            Q(first_name__iexact=name) | 
            (Q(phone__iexact=phone) if phone else Q()) |
            (Q(mobile__iexact=phone) if phone else Q())
        )
        if duplicate_qs.exists():
            existing = duplicate_qs.first()
            # أرجع العميل الموجود بدلاً من خطأ
            return JsonResponse({
                'success': True, 
                'id': existing.id, 
                'name': str(existing),
                'existing': True
            })
        
        # إنشاء كود فريد للعميل
        import random
        import string
        from datetime import datetime
        customer_code = f"CUS{datetime.now().strftime('%Y%m%d')}{random.randint(1000,9999)}"
        
        # تقسيم الاسم
        name_parts = name.split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        customer = Customer.objects.create(
            customer_code=customer_code,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            email=email,
            status='active'
        )
        
        return JsonResponse({
            'success': True, 
            'id': customer.id, 
            'name': str(customer)
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)

@login_required
@require_POST
def ajax_create_contact(request):
    """إنشاء جهة اتصال عبر AJAX وإرجاع JSON.
    المدخلات المتوقعة: customer_id, name, position?, phone?, mobile?, email?, is_primary? (on/true/1)
    المخرجات: {success, id, name, position}
    أخطاء: 400 للمدخلات غير الصالحة.
    """
    try:
        customer_id = request.POST.get('customer_id')
        name = (request.POST.get('name') or '').strip()
        if not customer_id or not name:
            return JsonResponse({'success': False, 'message': 'العميل والاسم مطلوبان'}, status=400)
        customer = get_object_or_404(Customer, pk=customer_id)
        # كشف تكرار بسيط بالاسم لنفس العميل
        if ContactPerson.objects.filter(customer=customer, name__iexact=name).exists():
            existing = ContactPerson.objects.filter(customer=customer, name__iexact=name).first()
            return JsonResponse({'success': True, 'id': existing.id, 'name': existing.name, 'position': existing.position or ''})
        position = (request.POST.get('position') or '').strip()
        phone = (request.POST.get('phone') or '').strip()
        mobile = (request.POST.get('mobile') or '').strip()
        email = (request.POST.get('email') or '').strip()
        is_primary = str(request.POST.get('is_primary') or '').lower() in ['1', 'true', 'on', 'yes']
        contact = ContactPerson.objects.create(
            customer=customer,
            name=name,
            position=position,
            phone=phone,
            mobile=mobile,
            email=email,
            is_primary=is_primary,
        )
        return JsonResponse({'success': True, 'id': contact.id, 'name': contact.name, 'position': contact.position or ''})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)

@login_required
def ajax_opportunities_by_stage(request, stage_id):
    """الفرص حسب المرحلة"""
    opportunities = Opportunity.objects.filter(stage_id=stage_id)
    
    data = [{
        'id': opp.id,
        'name': opp.name,
        'customer': opp.customer.full_name,
        'value': float(opp.estimated_value),
        'probability': float(opp.probability),
        'expected_close_date': opp.expected_close_date.isoformat()
    } for opp in opportunities]
    
    return JsonResponse({'opportunities': data})

@login_required
def ajax_dashboard_stats(request):
    """إحصائيات لوحة التحكم"""
    stats = {
        'customers': Customer.objects.count(),
        'opportunities': Opportunity.objects.count(),
        'activities': Activity.objects.count(),
        'tickets': SupportTicket.objects.count(),
    }
    
    return JsonResponse(stats)

# Placeholder Views (سيتم تطويرها لاحقاً)
@login_required
def campaign_list(request):
    return render(request, 'crm/coming_soon.html', {'feature': 'قائمة الحملات التسويقية'})

@login_required
def campaign_create(request):
    return render(request, 'crm/coming_soon.html', {'feature': 'إنشاء حملة جديدة'})

@login_required
def campaign_detail(request, pk):
    return render(request, 'crm/coming_soon.html', {'feature': 'تفاصيل الحملة'})

@login_required
def campaign_edit(request, pk):
    return render(request, 'crm/coming_soon.html', {'feature': 'تعديل الحملة'})

@login_required
def campaign_delete(request, pk):
    return render(request, 'crm/coming_soon.html', {'feature': 'حذف الحملة'})

@login_required
def campaign_launch(request, pk):
    return render(request, 'crm/coming_soon.html', {'feature': 'إطلاق الحملة'})

@login_required
def campaign_pause(request, pk):
    return render(request, 'crm/coming_soon.html', {'feature': 'إيقاف الحملة'})

@login_required
def campaign_report(request, pk):
    return render(request, 'crm/coming_soon.html', {'feature': 'تقرير الحملة'})

@login_required
def reports_dashboard(request):
    reports = [
        { 'name': 'تقرير التحويلات حسب المصدر', 'url': 'crm:source_conversions_report', 'icon': 'bi-diagram-3' },
        { 'name': 'تقرير العمولات', 'url': 'crm:commissions_report', 'icon': 'bi-cash-coin' },
        { 'name': 'اتجاه العمولات (شهري)', 'url': 'crm:commissions_trend', 'icon': 'bi-graph-up-arrow' },
        { 'name': 'اتجاه قبول العروض (شهري)', 'url': 'crm:acceptance_trend', 'icon': 'bi-graph-up' },
    ]
    return render(request, 'crm/reports_dashboard.html', { 'reports': reports })

@login_required
def sales_report(request):
    return render(request, 'crm/coming_soon.html', {'feature': 'تقرير المبيعات'})

@login_required
def customer_report(request):
    return render(request, 'crm/coming_soon.html', {'feature': 'تقرير العملاء'})

@login_required
def opportunity_report(request):
    return render(request, 'crm/coming_soon.html', {'feature': 'تقرير الفرص'})

@login_required
def activity_report(request):
    return render(request, 'crm/coming_soon.html', {'feature': 'تقرير الأنشطة'})

@login_required
def pipeline_report(request):
    return render(request, 'crm/coming_soon.html', {'feature': 'تقرير الأنبوب'})

@login_required
def crm_settings(request):
    """صفحة إعدادات CRM الرئيسية"""
    context = {
        'customer_types_count': CustomerType.objects.count(),
        'customer_sources_count': CustomerSource.objects.count(),
        'opportunity_stages_count': OpportunityStage.objects.count(),
        'activity_types_count': ActivityType.objects.count(),
    }
    return render(request, 'crm/settings.html', context)

@login_required
def customer_types(request):
    """إدارة أنواع العملاء"""
    if request.method == 'POST':
        action = request.POST.get('action', 'add')
        
        if action == 'add':
            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()
            discount = request.POST.get('discount_percentage', '0')
            
            if name:
                try:
                    discount_val = Decimal(discount) if discount else Decimal('0')
                except:
                    discount_val = Decimal('0')
                    
                CustomerType.objects.create(
                    name=name,
                    description=description,
                    discount_percentage=discount_val
                )
                messages.success(request, f'تم إضافة نوع العميل "{name}" بنجاح')
            else:
                messages.error(request, 'يرجى إدخال اسم النوع')
                
        elif action == 'edit':
            type_id = request.POST.get('type_id')
            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()
            discount = request.POST.get('discount_percentage', '0')
            
            try:
                customer_type = CustomerType.objects.get(pk=type_id)
                if name:
                    customer_type.name = name
                    customer_type.description = description
                    try:
                        customer_type.discount_percentage = Decimal(discount) if discount else Decimal('0')
                    except:
                        pass
                    customer_type.save()
                    messages.success(request, f'تم تعديل نوع العميل "{name}" بنجاح')
                else:
                    messages.error(request, 'يرجى إدخال اسم النوع')
            except CustomerType.DoesNotExist:
                messages.error(request, 'نوع العميل غير موجود')
                
        elif action == 'delete':
            type_id = request.POST.get('type_id')
            try:
                customer_type = CustomerType.objects.get(pk=type_id)
                name = customer_type.name
                # التحقق من عدم وجود عملاء مرتبطين
                if Customer.objects.filter(customer_type=customer_type).exists():
                    messages.warning(request, f'لا يمكن حذف نوع العميل "{name}" لأنه مرتبط بعملاء')
                else:
                    customer_type.delete()
                    messages.success(request, f'تم حذف نوع العميل "{name}" بنجاح')
            except CustomerType.DoesNotExist:
                messages.error(request, 'نوع العميل غير موجود')
        
        return redirect('crm:customer_types')
    
    # GET request - عرض القائمة
    from django.db.models import Count
    customer_types_list = CustomerType.objects.annotate(
        customer_count=Count('customer')
    ).order_by('name')
    
    context = {
        'customer_types': customer_types_list,
    }
    return render(request, 'crm/settings/customer_types.html', context)

@login_required
def customer_sources(request):
    """إدارة مصادر العملاء"""
    if request.method == 'POST':
        action = request.POST.get('action', 'add')
        
        if action == 'add':
            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()
            is_active = request.POST.get('is_active') == 'on'
            
            if name:
                CustomerSource.objects.create(
                    name=name,
                    description=description,
                    is_active=is_active
                )
                messages.success(request, f'تم إضافة مصدر العميل "{name}" بنجاح')
            else:
                messages.error(request, 'يرجى إدخال اسم المصدر')
                
        elif action == 'edit':
            source_id = request.POST.get('source_id')
            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()
            is_active = request.POST.get('is_active') == 'on'
            
            try:
                source = CustomerSource.objects.get(pk=source_id)
                if name:
                    source.name = name
                    source.description = description
                    source.is_active = is_active
                    source.save()
                    messages.success(request, f'تم تعديل مصدر العميل "{name}" بنجاح')
                else:
                    messages.error(request, 'يرجى إدخال اسم المصدر')
            except CustomerSource.DoesNotExist:
                messages.error(request, 'مصدر العميل غير موجود')
                
        elif action == 'delete':
            source_id = request.POST.get('source_id')
            try:
                source = CustomerSource.objects.get(pk=source_id)
                name = source.name
                if Customer.objects.filter(source=source).exists():
                    messages.warning(request, f'لا يمكن حذف مصدر العميل "{name}" لأنه مرتبط بعملاء')
                else:
                    source.delete()
                    messages.success(request, f'تم حذف مصدر العميل "{name}" بنجاح')
            except CustomerSource.DoesNotExist:
                messages.error(request, 'مصدر العميل غير موجود')
        
        return redirect('crm:customer_sources')
    
    from django.db.models import Count
    sources = CustomerSource.objects.annotate(
        customer_count=Count('customer')
    ).order_by('name')
    
    context = {
        'sources': sources,
    }
    return render(request, 'crm/settings/customer_sources.html', context)

@login_required
def opportunity_stages(request):
    """إدارة مراحل الفرص"""
    if request.method == 'POST':
        action = request.POST.get('action', 'add')
        
        if action == 'add':
            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()
            color = request.POST.get('color', '#6c757d').strip()
            order = request.POST.get('order', '0')
            probability = request.POST.get('probability', '0')
            
            if name:
                try:
                    order_val = int(order) if order else 0
                    prob_val = int(probability) if probability else 0
                except:
                    order_val = 0
                    prob_val = 0
                    
                OpportunityStage.objects.create(
                    name=name,
                    description=description,
                    color=color,
                    order=order_val,
                    probability=prob_val
                )
                messages.success(request, f'تم إضافة مرحلة الفرصة "{name}" بنجاح')
            else:
                messages.error(request, 'يرجى إدخال اسم المرحلة')
                
        elif action == 'edit':
            stage_id = request.POST.get('stage_id')
            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()
            color = request.POST.get('color', '#6c757d').strip()
            order = request.POST.get('order', '0')
            probability = request.POST.get('probability', '0')
            
            try:
                stage = OpportunityStage.objects.get(pk=stage_id)
                if name:
                    stage.name = name
                    stage.description = description
                    stage.color = color
                    try:
                        stage.order = int(order) if order else 0
                        stage.probability = int(probability) if probability else 0
                    except:
                        pass
                    stage.save()
                    messages.success(request, f'تم تعديل مرحلة الفرصة "{name}" بنجاح')
                else:
                    messages.error(request, 'يرجى إدخال اسم المرحلة')
            except OpportunityStage.DoesNotExist:
                messages.error(request, 'مرحلة الفرصة غير موجودة')
                
        elif action == 'delete':
            stage_id = request.POST.get('stage_id')
            try:
                stage = OpportunityStage.objects.get(pk=stage_id)
                name = stage.name
                if Opportunity.objects.filter(stage=stage).exists():
                    messages.warning(request, f'لا يمكن حذف مرحلة الفرصة "{name}" لأنها مرتبطة بفرص')
                else:
                    stage.delete()
                    messages.success(request, f'تم حذف مرحلة الفرصة "{name}" بنجاح')
            except OpportunityStage.DoesNotExist:
                messages.error(request, 'مرحلة الفرصة غير موجودة')
        
        return redirect('crm:opportunity_stages')
    
    from django.db.models import Count
    stages = OpportunityStage.objects.annotate(
        opportunity_count=Count('opportunity')
    ).order_by('order', 'name')
    
    context = {
        'stages': stages,
    }
    return render(request, 'crm/settings/opportunity_stages.html', context)

@login_required
def activity_types(request):
    """إدارة أنواع الأنشطة"""
    if request.method == 'POST':
        action = request.POST.get('action', 'add')
        
        if action == 'add':
            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()
            icon = request.POST.get('icon', 'fas fa-tasks').strip()
            color = request.POST.get('color', '#6c757d').strip()
            
            if name:
                ActivityType.objects.create(
                    name=name,
                    description=description,
                    icon=icon,
                    color=color
                )
                messages.success(request, f'تم إضافة نوع النشاط "{name}" بنجاح')
            else:
                messages.error(request, 'يرجى إدخال اسم النوع')
                
        elif action == 'edit':
            type_id = request.POST.get('type_id')
            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()
            icon = request.POST.get('icon', 'fas fa-tasks').strip()
            color = request.POST.get('color', '#6c757d').strip()
            
            try:
                activity_type = ActivityType.objects.get(pk=type_id)
                if name:
                    activity_type.name = name
                    activity_type.description = description
                    activity_type.icon = icon
                    activity_type.color = color
                    activity_type.save()
                    messages.success(request, f'تم تعديل نوع النشاط "{name}" بنجاح')
                else:
                    messages.error(request, 'يرجى إدخال اسم النوع')
            except ActivityType.DoesNotExist:
                messages.error(request, 'نوع النشاط غير موجود')
                
        elif action == 'delete':
            type_id = request.POST.get('type_id')
            try:
                activity_type = ActivityType.objects.get(pk=type_id)
                name = activity_type.name
                if Activity.objects.filter(activity_type=activity_type).exists():
                    messages.warning(request, f'لا يمكن حذف نوع النشاط "{name}" لأنه مرتبط بأنشطة')
                else:
                    activity_type.delete()
                    messages.success(request, f'تم حذف نوع النشاط "{name}" بنجاح')
            except ActivityType.DoesNotExist:
                messages.error(request, 'نوع النشاط غير موجود')
        
        return redirect('crm:activity_types')
    
    from django.db.models import Count
    activity_types_list = ActivityType.objects.annotate(
        activity_count=Count('activity')
    ).order_by('name')
    
    context = {
        'activity_types': activity_types_list,
    }
    return render(request, 'crm/settings/activity_types.html', context)

@login_required
def ticket_categories(request):
    """إدارة فئات تذاكر الدعم"""
    if request.method == 'POST':
        action = request.POST.get('action', 'add')
        
        if action == 'add':
            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()
            
            if name:
                TicketCategory.objects.create(
                    name=name,
                    description=description
                )
                messages.success(request, f'تم إضافة فئة التذكرة "{name}" بنجاح')
            else:
                messages.error(request, 'يرجى إدخال اسم الفئة')
                
        elif action == 'edit':
            cat_id = request.POST.get('category_id')
            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()
            
            try:
                category = TicketCategory.objects.get(pk=cat_id)
                if name:
                    category.name = name
                    category.description = description
                    category.save()
                    messages.success(request, f'تم تعديل فئة التذكرة "{name}" بنجاح')
                else:
                    messages.error(request, 'يرجى إدخال اسم الفئة')
            except TicketCategory.DoesNotExist:
                messages.error(request, 'فئة التذكرة غير موجودة')
                
        elif action == 'delete':
            cat_id = request.POST.get('category_id')
            try:
                category = TicketCategory.objects.get(pk=cat_id)
                name = category.name
                if Ticket.objects.filter(category=category).exists():
                    messages.warning(request, f'لا يمكن حذف فئة التذكرة "{name}" لأنها مرتبطة بتذاكر')
                else:
                    category.delete()
                    messages.success(request, f'تم حذف فئة التذكرة "{name}" بنجاح')
            except TicketCategory.DoesNotExist:
                messages.error(request, 'فئة التذكرة غير موجودة')
        
        return redirect('crm:ticket_categories')
    
    from django.db.models import Count
    categories = TicketCategory.objects.annotate(
        ticket_count=Count('supportticket')
    ).order_by('name')
    
    context = {
        'categories': categories,
    }
    return render(request, 'crm/settings/ticket_categories.html', context)

@login_required
def quick_add_customer(request):
    return render(request, 'crm/coming_soon.html', {'feature': 'إضافة سريعة للعميل'})

@login_required
def quick_add_opportunity(request):
    return render(request, 'crm/coming_soon.html', {'feature': 'إضافة سريعة للفرصة'})

@login_required
def quick_add_activity(request):
    return render(request, 'crm/coming_soon.html', {'feature': 'إضافة سريعة للنشاط'})

@login_required
def bulk_delete_customers(request):
    return render(request, 'crm/coming_soon.html', {'feature': 'حذف مجمع للعملاء'})

@login_required
def bulk_move_opportunities(request):
    return render(request, 'crm/coming_soon.html', {'feature': 'نقل مجمع للفرص'})

@login_required
def bulk_complete_activities(request):
    return render(request, 'crm/coming_soon.html', {'feature': 'إكمال مجمع للأنشطة'})

@login_required
def customer_export(request):
    return render(request, 'crm/coming_soon.html', {'feature': 'تصدير العملاء'})

@login_required
def commissions_report(request):
    """تقرير مبسط لعمولات المبيعات حسب الموظف والفترة."""
    from django.utils.dateparse import parse_date
    start = request.GET.get('start')
    end = request.GET.get('end')
    status = request.GET.get('status') or 'all'

    qs = CommissionAccrual.objects.select_related('employee').all()
    if status and status != 'all':
        qs = qs.filter(status=status)
    if start:
        qs = qs.filter(accrued_at__date__gte=parse_date(start))
    if end:
        qs = qs.filter(accrued_at__date__lte=parse_date(end))

    by_employee = (
        qs.values('employee__id', 'employee__arabic_name')
          .annotate(total=Sum('amount'), count=Count('id'))
          .order_by('-total')
    )

    # CSV export
    if request.GET.get('export') == 'csv':
        output = StringIO()
        # UTF-8 BOM for better Excel compatibility on Windows
        output.write('\ufeff')
        writer = csv.writer(output)
        writer.writerow(['الموظف', 'عدد العمولات', 'إجمالي العمولة'])
        for r in by_employee:
            writer.writerow([
                r.get('employee__arabic_name') or '',
                r.get('count') or 0,
                r.get('total') or 0,
            ])
        filename_parts = ["commissions"]
        if start: filename_parts.append(f"from-{start}")
        if end: filename_parts.append(f"to-{end}")
        if status and status != 'all': filename_parts.append(status)
        fname = "_".join(filename_parts) + ".csv"
        resp = HttpResponse(output.getvalue(), content_type='text/csv; charset=utf-8')
        resp['Content-Disposition'] = f'attachment; filename="{fname}"'
        return resp

    context = {
        'rows': by_employee,
        'start': start,
        'end': end,
        'status': status,
    }
    return render(request, 'crm/commissions_report.html', context)

@login_required
def source_conversions_report(request):
    """
    تقرير تحويلات حسب مصدر العميل: عملاء جدد، فرص (إجمالي/ربح/خسارة/مفتوحة)،
    عروض (إجمالي/مقبولة) ونِسَب التحويل لكل مصدر خلال فترة محددة.
    """
    from django.utils.dateparse import parse_date
    from django.db.models import Count, Sum, Case, When, IntegerField

    start = request.GET.get('start')
    end = request.GET.get('end')

    # مصادر فعّالة لعرض صف حتى إن كانت الأرقام صفراً
    sources = CustomerSource.objects.filter(is_active=True).order_by('name')

    cust_qs = Customer.objects.filter(source__isnull=False)
    if start:
        cust_qs = cust_qs.filter(created_at__date__gte=parse_date(start))
    if end:
        cust_qs = cust_qs.filter(created_at__date__lte=parse_date(end))

    opp_qs = Opportunity.objects.select_related('stage', 'customer__source').filter(
        customer__source__isnull=False
    )
    if start:
        opp_qs = opp_qs.filter(created_at__date__gte=parse_date(start))
    if end:
        opp_qs = opp_qs.filter(created_at__date__lte=parse_date(end))

    quo_qs = Quotation.objects.select_related('customer__source').filter(
        customer__source__isnull=False
    )
    if start:
        quo_qs = quo_qs.filter(quotation_date__gte=parse_date(start))
    if end:
        quo_qs = quo_qs.filter(quotation_date__lte=parse_date(end))

    # تجميعات حسب المصدر
    cust_by_source = {
        (row.get('source_id') or row.get('customer__source_id')): row.get('customers', 0)
        for row in (
            cust_qs.values('source_id').annotate(customers=Count('id'))
        )
    }

    opp_by_source = {
        (row['customer__source_id']): {
            'total': row['total'],
            'won': row['won'],
            'lost': row['lost'],
        }
        for row in (
            opp_qs.values('customer__source_id')
                .annotate(
                    total=Count('id'),
                    won=Sum(Case(When(stage__is_won=True, then=1), default=0, output_field=IntegerField())),
                    lost=Sum(Case(When(stage__is_lost=True, then=1), default=0, output_field=IntegerField())),
                )
        )
    }

    quo_by_source = {
        row['customer__source_id']: {
            'quotations': row['quotations'],
            'accepted': row['accepted'],
        }
        for row in (
            quo_qs.values('customer__source_id')
                 .annotate(
                     quotations=Count('id'),
                     accepted=Sum(Case(When(status='accepted', then=1), default=0, output_field=IntegerField())),
                 )
        )
    }

    rows = []
    totals = {
        'customers': 0,
        'opp_total': 0,
        'opp_won': 0,
        'opp_lost': 0,
        'opp_open': 0,
        'quo_total': 0,
        'quo_accepted': 0,
    }

    chart_labels = []
    chart_win_rates = []

    for src in sources:
        customers_count = cust_by_source.get(src.id, 0) or 0
        opp_stats = opp_by_source.get(src.id, {'total': 0, 'won': 0, 'lost': 0})
        opp_total = opp_stats['total'] or 0
        opp_won = opp_stats['won'] or 0
        opp_lost = opp_stats['lost'] or 0
        opp_open = max(opp_total - opp_won - opp_lost, 0)

        quo_stats = quo_by_source.get(src.id, {'quotations': 0, 'accepted': 0})
        quo_total = quo_stats['quotations'] or 0
        quo_accepted = quo_stats['accepted'] or 0

        win_rate = round((opp_won / opp_total) * 100, 2) if opp_total else 0.0
        acceptance_rate = round((quo_accepted / quo_total) * 100, 2) if quo_total else 0.0

        rows.append({
            'source': src,
            'customers': customers_count,
            'opp_total': opp_total,
            'opp_won': opp_won,
            'opp_lost': opp_lost,
            'opp_open': opp_open,
            'quo_total': quo_total,
            'quo_accepted': quo_accepted,
            'win_rate': win_rate,
            'acceptance_rate': acceptance_rate,
        })

        totals['customers'] += customers_count
        totals['opp_total'] += opp_total
        totals['opp_won'] += opp_won
        totals['opp_lost'] += opp_lost
        totals['opp_open'] += opp_open
        totals['quo_total'] += quo_total
        totals['quo_accepted'] += quo_accepted

        chart_labels.append(src.name)
        chart_win_rates.append(win_rate)

    # CSV export
    if request.GET.get('export') == 'csv':
        output = StringIO()
        # UTF-8 BOM for better Excel compatibility on Windows
        output.write('\ufeff')
        writer = csv.writer(output)
        writer.writerow([
            'المصدر', 'العملاء', 'الفرص (إجمالي)', 'الفرص (ربح)', 'الفرص (خسارة)', 'الفرص (مفتوحة)',
            'عروض (إجمالي)', 'عروض (مقبولة)', 'نسبة ربح %', 'نسبة قبول %'
        ])
        for row in rows:
            writer.writerow([
                getattr(row['source'], 'name', ''),
                row['customers'],
                row['opp_total'],
                row['opp_won'],
                row['opp_lost'],
                row['opp_open'],
                row['quo_total'],
                row['quo_accepted'],
                row['win_rate'],
                row['acceptance_rate'],
            ])
        fname = f"source_conversions_{(start or 'all')}_{(end or 'all')}.csv"
        resp = HttpResponse(output.getvalue(), content_type='text/csv; charset=utf-8')
        resp['Content-Disposition'] = f'attachment; filename="{fname}"'
        return resp

    context = {
        'rows': rows,
        'totals': totals,
        'start': start,
        'end': end,
        'chart_labels': chart_labels,
        'chart_win_rates': chart_win_rates,
    'totals_win_rate': round((totals['opp_won'] / totals['opp_total']) * 100, 2) if totals['opp_total'] else 0,
    'totals_acceptance_rate': round((totals['quo_accepted'] / totals['quo_total']) * 100, 2) if totals['quo_total'] else 0,
    }

    return render(request, 'crm/source_conversions_report.html', context)


# ==========================
# Trend Reports
# ==========================
@login_required
def commissions_trend(request):
    """اتجاه العمولات شهرياً (مجمعة وموزعة حسب الموظف)."""
    from django.utils.dateparse import parse_date
    # الافتراضي: آخر 6 أشهر
    end_default = timezone.now().date()
    start_default = (end_default.replace(day=1) - timezone.timedelta(days=150)).replace(day=1)
    start = parse_date(request.GET.get('start')) if request.GET.get('start') else start_default
    end = parse_date(request.GET.get('end')) if request.GET.get('end') else end_default

    qs = CommissionAccrual.objects.filter(accrued_at__date__gte=start, accrued_at__date__lte=end)

    # إجمالي شهري
    monthly_totals = (
        qs.annotate(month=TruncMonth('accrued_at'))
          .values('month')
          .annotate(total=Sum('amount'))
          .order_by('month')
    )

    # شهري حسب الموظف
    monthly_by_emp = (
        qs.annotate(month=TruncMonth('accrued_at'))
          .values('month', 'employee__arabic_name')
          .annotate(total=Sum('amount'))
          .order_by('month', 'employee__arabic_name')
    )

    # بناء المحاور
    labels = [m['month'].strftime('%Y-%m') for m in monthly_totals]
    employees = sorted({row['employee__arabic_name'] or 'غير محدد' for row in monthly_by_emp})
    # خرائط لمساعدة الملء
    index_by_label = {label: i for i, label in enumerate(labels)}
    data_by_emp = {emp: [0] * len(labels) for emp in employees}

    for row in monthly_by_emp:
        label = row['month'].strftime('%Y-%m')
        emp = row['employee__arabic_name'] or 'غير محدد'
        data_by_emp[emp][index_by_label[label]] = float(row['total'])

    datasets = []
    base_colors = [
        '#0d6efd', '#198754', '#fd7e14', '#6f42c1', '#20c997', '#d63384', '#0dcaf0', '#ffc107', '#6610f2', '#dc3545'
    ]
    for idx, emp in enumerate(employees):
        datasets.append({
            'label': emp,
            'data': data_by_emp[emp],
            'backgroundColor': base_colors[idx % len(base_colors)],
            'stack': 'commissions',
        })

    # CSV export (tall format: month, employee, amount)
    if request.GET.get('export') == 'csv':
        output = StringIO()
        output.write('\ufeff')  # BOM for Excel
        writer = csv.writer(output)
        writer.writerow(['الشهر', 'الموظف', 'قيمة العمولة'])
        for row in monthly_by_emp:
            writer.writerow([
                row['month'].strftime('%Y-%m'),
                row['employee__arabic_name'] or 'غير محدد',
                row['total'] or 0,
            ])
        fname = f"commissions_trend_{start}_{end}.csv"
        resp = HttpResponse(output.getvalue(), content_type='text/csv; charset=utf-8')
        resp['Content-Disposition'] = f'attachment; filename="{fname}"'
        return resp

    context = {
        'start': start,
        'end': end,
        'labels': labels,
        'datasets': datasets,
        'total_per_month': [float(row['total']) for row in monthly_totals],
    }
    return render(request, 'crm/commissions_trend.html', context)


@login_required
def acceptance_trend(request):
    """اتجاه معدل قبول عروض الأسعار شهرياً، مع فلتر اختياري بالمصدر."""
    from django.utils.dateparse import parse_date

    end_default = timezone.now().date()
    start_default = (end_default.replace(day=1) - timezone.timedelta(days=150)).replace(day=1)
    start = parse_date(request.GET.get('start')) if request.GET.get('start') else start_default
    end = parse_date(request.GET.get('end')) if request.GET.get('end') else end_default
    source_id = request.GET.get('source')

    qs = Quotation.objects.select_related('customer__source').filter(
        quotation_date__gte=start, quotation_date__lte=end
    )
    selected_source = None
    if source_id:
        qs = qs.filter(customer__source_id=source_id)
        selected_source = CustomerSource.objects.filter(id=source_id).first()

    monthly = (
        qs.annotate(month=TruncMonth('quotation_date'))
          .values('month')
          .annotate(
              total=Count('id'),
              accepted=Sum(Case(When(status='accepted', then=1), default=0, output_field=IntegerField()))
          )
          .order_by('month')
    )

    labels = []
    rates = []
    total_series = []
    accepted_series = []
    for row in monthly:
        labels.append(row['month'].strftime('%Y-%m'))
        tot = int(row['total'] or 0)
        acc = int(row['accepted'] or 0)
        rate = round((acc / tot) * 100, 2) if tot else 0.0
        rates.append(rate)
        total_series.append(tot)
        accepted_series.append(acc)

    # CSV export: month, total quotations, accepted, acceptance rate, optional source
    if request.GET.get('export') == 'csv':
        output = StringIO()
        output.write('\ufeff')  # BOM for Excel
        writer = csv.writer(output)
        header = ['الشهر', 'إجمالي العروض', 'العروض المقبولة', 'معدل القبول %']
        if selected_source:
            header.append('المصدر')
        writer.writerow(header)
        for i, label in enumerate(labels):
            row = [label, total_series[i], accepted_series[i], rates[i]]
            if selected_source:
                row.append(selected_source.name)
            writer.writerow(row)
        src_part = f"_source-{selected_source.id}" if selected_source else ""
        fname = f"acceptance_trend_{start}_{end}{src_part}.csv"
        resp = HttpResponse(output.getvalue(), content_type='text/csv; charset=utf-8')
        resp['Content-Disposition'] = f'attachment; filename="{fname}"'
        return resp

    context = {
        'start': start,
        'end': end,
        'sources': CustomerSource.objects.filter(is_active=True).order_by('name'),
        'selected_source': int(source_id) if source_id else None,
        'labels': labels,
        'rates': rates,
        'total_series': total_series,
        'accepted_series': accepted_series,
        'title_suffix': f" - {selected_source.name}" if selected_source else '',
    }
    return render(request, 'crm/acceptance_trend.html', context)

@login_required
def ajax_product_price(request, product_id):
    """إرجاع السعر الأساسي والسعر الفعلي (بعد العروض) لمنتج."""
    from inventory.models import Product
    product = get_object_or_404(Product, pk=product_id)
    return JsonResponse({
        'id': product.id,
        'price': str(product.price),
        'effective_price': str(product.effective_price),
    'current_stock': product.current_stock,
    'is_low_stock': product.is_low_stock,
    })


# ============================================
# CRM Options Page - خيارات CRM
# ============================================
@login_required
def crm_options(request):
    """خيارات CRM"""
    return render(request, 'crm/options.html')


# ============================================
# Follow-ups Views - المتابعات
# ============================================
@login_required
def followup_list(request):
    """قائمة كل المتابعات"""
    from .models import FollowUp
    followups = FollowUp.objects.select_related('customer', 'assigned_to').order_by('-due_date')
    
    search = request.GET.get('search', '')
    if search:
        followups = followups.filter(
            Q(customer__first_name__icontains=search) |
            Q(customer__last_name__icontains=search) |
            Q(customer__company_name__icontains=search) |
            Q(notes__icontains=search)
        )
    
    status = request.GET.get('status', '')
    if status:
        followups = followups.filter(status=status)
    
    priority = request.GET.get('priority', '')
    if priority:
        followups = followups.filter(priority=priority)
    
    paginator = Paginator(followups, 15)
    page = request.GET.get('page')
    followups = paginator.get_page(page)
    
    context = {
        'followups': followups,
        'search': search,
        'selected_status': status,
        'selected_priority': priority,
    }
    return render(request, 'crm/followup_list.html', context)


@login_required
def my_followups(request):
    """متابعاتي - المتابعات المخصصة للمستخدم الحالي"""
    from .models import FollowUp
    followups = FollowUp.objects.filter(assigned_to=request.user).select_related('customer').order_by('-due_date')
    
    status = request.GET.get('status', '')
    if status:
        followups = followups.filter(status=status)
    
    paginator = Paginator(followups, 15)
    page = request.GET.get('page')
    followups = paginator.get_page(page)
    
    context = {
        'followups': followups,
        'selected_status': status,
    }
    return render(request, 'crm/my_followups.html', context)


@login_required
def followup_create(request):
    """إنشاء متابعة جديدة"""
    from .models import FollowUp
    if request.method == 'POST':
        customer_id = request.POST.get('customer')
        customer = get_object_or_404(Customer, pk=customer_id)
        
        followup = FollowUp.objects.create(
            customer=customer,
            assigned_to_id=request.POST.get('assigned_to') or request.user.id,
            follow_up_type=request.POST.get('followup_type', 'call'),
            due_date=request.POST.get('due_date'),
            priority=request.POST.get('priority', 'medium'),
            description=request.POST.get('notes', ''),
            subject=request.POST.get('subject', 'متابعة'),
            created_by=request.user
        )
        messages.success(request, 'تم إنشاء المتابعة بنجاح')
        return redirect('crm:followup_list')
    
    customers = Customer.objects.filter(status='active')[:100]
    users = User.objects.filter(is_active=True)
    
    context = {
        'customers': customers,
        'users': users,
    }
    return render(request, 'crm/followup_form.html', context)


@login_required
def followup_detail(request, pk):
    """تفاصيل المتابعة"""
    from .models import FollowUp
    followup = get_object_or_404(FollowUp, pk=pk)
    return render(request, 'crm/followup_detail.html', {'followup': followup})


@login_required
def followup_edit(request, pk):
    """تعديل متابعة"""
    from .models import FollowUp
    followup = get_object_or_404(FollowUp, pk=pk)
    
    if request.method == 'POST':
        followup.follow_up_type = request.POST.get('followup_type', followup.follow_up_type)
        followup.due_date = request.POST.get('due_date', followup.due_date)
        followup.priority = request.POST.get('priority', followup.priority)
        followup.status = request.POST.get('status', followup.status)
        followup.description = request.POST.get('notes', followup.description)
        followup.result = request.POST.get('result', followup.result)
        followup.save()
        messages.success(request, 'تم تعديل المتابعة بنجاح')
        return redirect('crm:followup_list')
    
    customers = Customer.objects.filter(status='active')[:100]
    users = User.objects.filter(is_active=True)
    
    context = {
        'followup': followup,
        'customers': customers,
        'users': users,
    }
    return render(request, 'crm/followup_form.html', context)


@login_required
def followup_delete(request, pk):
    """حذف متابعة"""
    from .models import FollowUp
    followup = get_object_or_404(FollowUp, pk=pk)
    if request.method == 'POST':
        followup.delete()
        messages.success(request, 'تم حذف المتابعة بنجاح')
    return redirect('crm:followup_list')


@login_required
def followup_complete(request, pk):
    """إتمام متابعة"""
    from .models import FollowUp
    followup = get_object_or_404(FollowUp, pk=pk)
    followup.status = 'completed'
    followup.result = request.POST.get('result', '')
    followup.save()
    messages.success(request, 'تم إتمام المتابعة بنجاح')
    return redirect('crm:followup_list')


# ============================================
# Tasks Views - المهام
# ============================================
@login_required
def task_list(request):
    """قائمة المهام"""
    from .models import Task
    tasks = Task.objects.select_related('customer', 'assigned_to').order_by('-due_date')
    
    search = request.GET.get('search', '')
    if search:
        tasks = tasks.filter(Q(title__icontains=search) | Q(description__icontains=search))
    
    status = request.GET.get('status', '')
    if status:
        tasks = tasks.filter(status=status)
    
    priority = request.GET.get('priority', '')
    if priority:
        tasks = tasks.filter(priority=priority)
    
    paginator = Paginator(tasks, 15)
    page = request.GET.get('page')
    tasks = paginator.get_page(page)
    
    context = {
        'tasks': tasks,
        'search': search,
        'selected_status': status,
        'selected_priority': priority,
    }
    return render(request, 'crm/task_list.html', context)


@login_required
def task_create(request):
    """إنشاء مهمة جديدة"""
    from .models import Task
    if request.method == 'POST':
        task = Task.objects.create(
            title=request.POST.get('title'),
            description=request.POST.get('description', ''),
            customer_id=request.POST.get('customer') or None,
            assigned_to_id=request.POST.get('assigned_to') or request.user.id,
            due_date=request.POST.get('due_date'),
            priority=request.POST.get('priority', 'medium'),
            created_by=request.user
        )
        messages.success(request, 'تم إنشاء المهمة بنجاح')
        return redirect('crm:task_list')
    
    customers = Customer.objects.filter(status='active')[:100]
    users = User.objects.filter(is_active=True)
    
    context = {
        'customers': customers,
        'users': users,
    }
    return render(request, 'crm/task_form.html', context)


@login_required
def task_detail(request, pk):
    """تفاصيل المهمة"""
    from .models import Task
    task = get_object_or_404(Task, pk=pk)
    return render(request, 'crm/task_detail.html', {'task': task})


@login_required
def task_edit(request, pk):
    """تعديل مهمة"""
    from .models import Task
    task = get_object_or_404(Task, pk=pk)
    
    if request.method == 'POST':
        task.title = request.POST.get('title', task.title)
        task.description = request.POST.get('description', task.description)
        task.due_date = request.POST.get('due_date', task.due_date)
        task.priority = request.POST.get('priority', task.priority)
        task.status = request.POST.get('status', task.status)
        task.save()
        messages.success(request, 'تم تعديل المهمة بنجاح')
        return redirect('crm:task_list')
    
    customers = Customer.objects.filter(status='active')[:100]
    users = User.objects.filter(is_active=True)
    
    context = {
        'task': task,
        'customers': customers,
        'users': users,
    }
    return render(request, 'crm/task_form.html', context)


@login_required
def task_delete(request, pk):
    """حذف مهمة"""
    from .models import Task
    task = get_object_or_404(Task, pk=pk)
    if request.method == 'POST':
        task.delete()
        messages.success(request, 'تم حذف المهمة بنجاح')
    return redirect('crm:task_list')


@login_required
def task_complete(request, pk):
    """إتمام مهمة"""
    from .models import Task
    task = get_object_or_404(Task, pk=pk)
    task.status = 'completed'
    task.save()
    messages.success(request, 'تم إتمام المهمة بنجاح')
    return redirect('crm:task_list')


# ============================================
# Appointments Views - المواعيد
# ============================================
@login_required
def appointment_list(request):
    """قائمة المواعيد"""
    from .models import Appointment
    appointments = Appointment.objects.select_related('customer', 'assigned_to').order_by('-appointment_date')
    
    status = request.GET.get('status', '')
    if status:
        appointments = appointments.filter(status=status)
    
    paginator = Paginator(appointments, 15)
    page = request.GET.get('page')
    appointments = paginator.get_page(page)
    
    context = {
        'appointments': appointments,
        'selected_status': status,
    }
    return render(request, 'crm/appointment_list.html', context)


@login_required
def appointment_calendar(request):
    """تقويم المواعيد"""
    from .models import Appointment
    appointments = Appointment.objects.select_related('customer').all()
    
    events = []
    for apt in appointments:
        events.append({
            'id': apt.id,
            'title': apt.title,
            'start': apt.appointment_date.isoformat(),
            'end': apt.appointment_end.isoformat() if apt.appointment_end else None,
            'className': f'status-{apt.status}',
        })
    
    context = {
        'events': json.dumps(events),
    }
    return render(request, 'crm/appointment_calendar.html', context)


@login_required
def appointment_create(request):
    """إنشاء موعد جديد"""
    from .models import Appointment
    if request.method == 'POST':
        appointment = Appointment.objects.create(
            title=request.POST.get('title'),
            customer_id=request.POST.get('customer') or None,
            assigned_to_id=request.POST.get('assigned_to') or request.user.id,
            appointment_date=request.POST.get('appointment_date'),
            appointment_end=request.POST.get('appointment_end') or None,
            location=request.POST.get('location', ''),
            notes=request.POST.get('notes', ''),
            created_by=request.user
        )
        messages.success(request, 'تم إنشاء الموعد بنجاح')
        return redirect('crm:appointment_list')
    
    customers = Customer.objects.filter(status='active')[:100]
    users = User.objects.filter(is_active=True)
    
    context = {
        'customers': customers,
        'users': users,
    }
    return render(request, 'crm/appointment_form.html', context)


@login_required
def appointment_detail(request, pk):
    """تفاصيل الموعد"""
    from .models import Appointment
    appointment = get_object_or_404(Appointment, pk=pk)
    return render(request, 'crm/appointment_detail.html', {'appointment': appointment})


@login_required
def appointment_edit(request, pk):
    """تعديل موعد"""
    from .models import Appointment
    appointment = get_object_or_404(Appointment, pk=pk)
    
    if request.method == 'POST':
        appointment.title = request.POST.get('title', appointment.title)
        appointment.appointment_date = request.POST.get('appointment_date', appointment.appointment_date)
        appointment.appointment_end = request.POST.get('appointment_end') or None
        appointment.location = request.POST.get('location', appointment.location)
        appointment.status = request.POST.get('status', appointment.status)
        appointment.notes = request.POST.get('notes', appointment.notes)
        appointment.save()
        messages.success(request, 'تم تعديل الموعد بنجاح')
        return redirect('crm:appointment_list')
    
    customers = Customer.objects.filter(status='active')[:100]
    users = User.objects.filter(is_active=True)
    
    context = {
        'appointment': appointment,
        'customers': customers,
        'users': users,
    }
    return render(request, 'crm/appointment_form.html', context)


@login_required
def appointment_delete(request, pk):
    """حذف موعد"""
    from .models import Appointment
    appointment = get_object_or_404(Appointment, pk=pk)
    if request.method == 'POST':
        appointment.delete()
        messages.success(request, 'تم حذف الموعد بنجاح')
    return redirect('crm:appointment_list')


# ============================================
# Kanban & Calendar - لوحة كانبان والتقويم
# ============================================
@login_required
def kanban_board(request):
    """لوحة كانبان"""
    from .models import Task, FollowUp, Appointment
    
    # المهام حسب الحالة
    tasks_pending = Task.objects.filter(status='pending').select_related('customer', 'assigned_to')[:20]
    tasks_in_progress = Task.objects.filter(status='in_progress').select_related('customer', 'assigned_to')[:20]
    tasks_completed = Task.objects.filter(status='completed').select_related('customer', 'assigned_to')[:20]
    
    # الفرص حسب المرحلة
    stages = OpportunityStage.objects.all().order_by('order')
    opportunities_by_stage = {}
    for stage in stages:
        opportunities_by_stage[stage.id] = Opportunity.objects.filter(stage=stage).select_related('customer')[:10]
    
    context = {
        'tasks_pending': tasks_pending,
        'tasks_in_progress': tasks_in_progress,
        'tasks_completed': tasks_completed,
        'stages': stages,
        'opportunities_by_stage': opportunities_by_stage,
    }
    return render(request, 'crm/kanban_board.html', context)


@login_required
def crm_calendar(request):
    """التقويم الشامل"""
    from .models import Task, Appointment, FollowUp
    
    events = []
    
    # المهام
    tasks = Task.objects.filter(due_date__isnull=False).select_related('customer')
    for task in tasks:
        events.append({
            'id': f'task_{task.id}',
            'title': f'📋 {task.title}',
            'start': task.due_date.isoformat(),
            'className': f'task-{task.status}',
            'type': 'task',
        })
    
    # المواعيد
    appointments = Appointment.objects.all().select_related('customer')
    for apt in appointments:
        events.append({
            'id': f'apt_{apt.id}',
            'title': f'📅 {apt.title}',
            'start': apt.appointment_date.isoformat(),
            'end': apt.appointment_end.isoformat() if apt.appointment_end else None,
            'className': f'appointment-{apt.status}',
            'type': 'appointment',
        })
    
    # المتابعات
    followups = FollowUp.objects.filter(due_date__isnull=False).select_related('customer')
    for fu in followups:
        events.append({
            'id': f'followup_{fu.id}',
            'title': f'📞 {fu.customer}',
            'start': fu.due_date.isoformat(),
            'className': f'followup-{fu.status}',
            'type': 'followup',
        })
    
    context = {
        'events': json.dumps(events, default=str),
    }
    return render(request, 'crm/crm_calendar.html', context)


# ============================================
# Email Views - البريد الإلكتروني
# ============================================
@login_required
def email_dashboard(request):
    """لوحة البريد الإلكتروني"""
    from .models import EmailLog, EmailTemplate, EmailSettings
    
    stats = {
        'total_sent': EmailLog.objects.filter(status='sent').count(),
        'total_failed': EmailLog.objects.filter(status='failed').count(),
        'total_templates': EmailTemplate.objects.filter(is_active=True).count(),
    }
    
    recent_logs = EmailLog.objects.select_related('customer').order_by('-sent_at')[:10]
    
    context = {
        'stats': stats,
        'recent_logs': recent_logs,
    }
    return render(request, 'crm/email/dashboard.html', context)


@login_required
def email_send(request):
    """إرسال بريد إلكتروني"""
    from .models import EmailTemplate, EmailLog
    
    if request.method == 'POST':
        customer_id = request.POST.get('customer')
        subject = request.POST.get('subject')
        body = request.POST.get('body')
        to_email = request.POST.get('to_email')
        
        # إنشاء سجل البريد
        log = EmailLog.objects.create(
            customer_id=customer_id if customer_id else None,
            to_email=to_email,
            subject=subject,
            body=body,
            sent_by=request.user,
            status='pending'
        )
        
        # محاولة الإرسال
        try:
            from django.core.mail import send_mail
            send_mail(subject, body, None, [to_email])
            log.status = 'sent'
            log.sent_at = timezone.now()
            log.save()
            messages.success(request, 'تم إرسال البريد بنجاح')
        except Exception as e:
            log.status = 'failed'
            log.error_message = str(e)
            log.save()
            messages.error(request, f'فشل إرسال البريد: {e}')
        
        return redirect('crm:email_log')
    
    customers = Customer.objects.filter(email__isnull=False).exclude(email='')[:100]
    templates = EmailTemplate.objects.filter(is_active=True)
    
    context = {
        'customers': customers,
        'templates': templates,
    }
    return render(request, 'crm/email/send.html', context)


@login_required
def email_templates(request):
    """قوالب البريد الإلكتروني"""
    from .models import EmailTemplate
    templates = EmailTemplate.objects.all().order_by('-created_at')
    
    paginator = Paginator(templates, 15)
    page = request.GET.get('page')
    templates = paginator.get_page(page)
    
    return render(request, 'crm/email/templates.html', {'templates': templates})


@login_required
def email_template_create(request):
    """إنشاء قالب بريد"""
    from .models import EmailTemplate
    if request.method == 'POST':
        template = EmailTemplate.objects.create(
            name=request.POST.get('name'),
            subject=request.POST.get('subject'),
            body=request.POST.get('body'),
            is_active=request.POST.get('is_active') == 'on',
            created_by=request.user
        )
        messages.success(request, 'تم إنشاء القالب بنجاح')
        return redirect('crm:email_templates')
    
    return render(request, 'crm/email/template_form.html', {})


@login_required
def email_template_edit(request, pk):
    """تعديل قالب بريد"""
    from .models import EmailTemplate
    template = get_object_or_404(EmailTemplate, pk=pk)
    
    if request.method == 'POST':
        template.name = request.POST.get('name', template.name)
        template.subject = request.POST.get('subject', template.subject)
        template.body = request.POST.get('body', template.body)
        template.is_active = request.POST.get('is_active') == 'on'
        template.save()
        messages.success(request, 'تم تعديل القالب بنجاح')
        return redirect('crm:email_templates')
    
    return render(request, 'crm/email/template_form.html', {'template': template})


@login_required
def email_template_delete(request, pk):
    """حذف قالب بريد"""
    from .models import EmailTemplate
    template = get_object_or_404(EmailTemplate, pk=pk)
    if request.method == 'POST':
        template.delete()
        messages.success(request, 'تم حذف القالب بنجاح')
    return redirect('crm:email_templates')


@login_required
def email_log(request):
    """سجل البريد الإلكتروني"""
    from .models import EmailLog
    logs = EmailLog.objects.select_related('customer', 'sent_by').order_by('-sent_at')
    
    status = request.GET.get('status', '')
    if status:
        logs = logs.filter(status=status)
    
    paginator = Paginator(logs, 20)
    page = request.GET.get('page')
    logs = paginator.get_page(page)
    
    return render(request, 'crm/email/log.html', {'logs': logs, 'selected_status': status})


@login_required
def email_settings(request):
    """إعدادات البريد الإلكتروني"""
    from .models import EmailSettings
    settings_obj, created = EmailSettings.objects.get_or_create(pk=1)
    
    if request.method == 'POST':
        settings_obj.smtp_host = request.POST.get('smtp_host', '')
        settings_obj.smtp_port = request.POST.get('smtp_port', 587)
        settings_obj.smtp_username = request.POST.get('smtp_username', '')
        if request.POST.get('smtp_password'):
            settings_obj.smtp_password = request.POST.get('smtp_password')
        settings_obj.from_email = request.POST.get('from_email', '')
        settings_obj.from_name = request.POST.get('from_name', '')
        settings_obj.use_tls = request.POST.get('use_tls') == 'on'
        settings_obj.save()
        messages.success(request, 'تم حفظ الإعدادات بنجاح')
        return redirect('crm:email_settings')
    
    return render(request, 'crm/email/settings.html', {'settings': settings_obj})


# ============================================
# WhatsApp Views - الواتساب
# ============================================
@login_required
def whatsapp_dashboard(request):
    """لوحة الواتساب"""
    from .models import WhatsAppConversation, WhatsAppMessage, WhatsAppTemplate
    
    stats = {
        'total_conversations': WhatsAppConversation.objects.count(),
        'total_messages': WhatsAppMessage.objects.count(),
        'total_templates': WhatsAppTemplate.objects.filter(is_active=True).count(),
    }
    
    recent_conversations = WhatsAppConversation.objects.select_related('customer').order_by('-last_message_at')[:10]
    
    context = {
        'stats': stats,
        'recent_conversations': recent_conversations,
    }
    return render(request, 'crm/whatsapp/dashboard.html', context)


@login_required
def whatsapp_conversations(request):
    """محادثات الواتساب"""
    from .models import WhatsAppConversation
    conversations = WhatsAppConversation.objects.select_related('customer').order_by('-last_message_at')
    
    paginator = Paginator(conversations, 20)
    page = request.GET.get('page')
    conversations = paginator.get_page(page)
    
    return render(request, 'crm/whatsapp/conversations.html', {'conversations': conversations})


@login_required
def whatsapp_conversation_detail(request, pk):
    """تفاصيل المحادثة"""
    from .models import WhatsAppConversation, WhatsAppMessage
    conversation = get_object_or_404(WhatsAppConversation, pk=pk)
    messages_list = WhatsAppMessage.objects.filter(conversation=conversation).order_by('sent_at')
    
    if request.method == 'POST':
        # إرسال رسالة جديدة
        message_text = request.POST.get('message')
        if message_text:
            WhatsAppMessage.objects.create(
                conversation=conversation,
                direction='outgoing',
                message_type='text',
                content=message_text,
                sent_by=request.user,
                status='pending'
            )
            conversation.last_message_at = timezone.now()
            conversation.save()
            messages.success(request, 'تم إرسال الرسالة')
            return redirect('crm:whatsapp_conversation_detail', pk=pk)
    
    context = {
        'conversation': conversation,
        'messages_list': messages_list,
    }
    return render(request, 'crm/whatsapp/conversation_detail.html', context)


@login_required
def whatsapp_bulk(request):
    """رسائل الواتساب الجماعية"""
    from .models import WhatsAppBulkMessage
    bulk_messages = WhatsAppBulkMessage.objects.all().order_by('-created_at')
    
    paginator = Paginator(bulk_messages, 15)
    page = request.GET.get('page')
    bulk_messages = paginator.get_page(page)
    
    return render(request, 'crm/whatsapp/bulk.html', {'bulk_messages': bulk_messages})


@login_required
def whatsapp_bulk_create(request):
    """إنشاء رسالة جماعية"""
    from .models import WhatsAppBulkMessage, WhatsAppTemplate
    
    if request.method == 'POST':
        template_id = request.POST.get('template')
        template = get_object_or_404(WhatsAppTemplate, pk=template_id) if template_id else None
        
        bulk = WhatsAppBulkMessage.objects.create(
            name=request.POST.get('name'),
            template=template,
            message_content=request.POST.get('message_content', ''),
            created_by=request.user
        )
        
        # إضافة المستلمين
        customer_ids = request.POST.getlist('customers')
        for cid in customer_ids:
            bulk.recipients.add(cid)
        
        messages.success(request, 'تم إنشاء الرسالة الجماعية بنجاح')
        return redirect('crm:whatsapp_bulk')
    
    customers = Customer.objects.filter(mobile__isnull=False).exclude(mobile='')[:100]
    templates = WhatsAppTemplate.objects.filter(is_active=True)
    
    context = {
        'customers': customers,
        'templates': templates,
    }
    return render(request, 'crm/whatsapp/bulk_form.html', context)


@login_required
def whatsapp_templates(request):
    """قوالب الواتساب"""
    from .models import WhatsAppTemplate
    templates = WhatsAppTemplate.objects.all().order_by('-created_at')
    
    paginator = Paginator(templates, 15)
    page = request.GET.get('page')
    templates = paginator.get_page(page)
    
    return render(request, 'crm/whatsapp/templates.html', {'templates': templates})


@login_required
def whatsapp_template_create(request):
    """إنشاء قالب واتساب"""
    from .models import WhatsAppTemplate
    if request.method == 'POST':
        template = WhatsAppTemplate.objects.create(
            name=request.POST.get('name'),
            template_type=request.POST.get('template_type', 'text'),
            content=request.POST.get('content'),
            is_active=request.POST.get('is_active') == 'on',
            created_by=request.user
        )
        messages.success(request, 'تم إنشاء القالب بنجاح')
        return redirect('crm:whatsapp_templates')
    
    return render(request, 'crm/whatsapp/template_form.html', {})


@login_required
def whatsapp_template_edit(request, pk):
    """تعديل قالب واتساب"""
    from .models import WhatsAppTemplate
    template = get_object_or_404(WhatsAppTemplate, pk=pk)
    
    if request.method == 'POST':
        template.name = request.POST.get('name', template.name)
        template.template_type = request.POST.get('template_type', template.template_type)
        template.content = request.POST.get('content', template.content)
        template.is_active = request.POST.get('is_active') == 'on'
        template.save()
        messages.success(request, 'تم تعديل القالب بنجاح')
        return redirect('crm:whatsapp_templates')
    
    return render(request, 'crm/whatsapp/template_form.html', {'template': template})


@login_required
def whatsapp_log(request):
    """سجل رسائل الواتساب"""
    from .models import WhatsAppMessage
    messages_list = WhatsAppMessage.objects.select_related('conversation', 'sent_by').order_by('-sent_at')
    
    paginator = Paginator(messages_list, 20)
    page = request.GET.get('page')
    messages_list = paginator.get_page(page)
    
    return render(request, 'crm/whatsapp/log.html', {'messages_list': messages_list})


@login_required
def whatsapp_settings(request):
    """إعدادات الواتساب"""
    from .models import WhatsAppSettings
    settings_obj, created = WhatsAppSettings.objects.get_or_create(pk=1)
    
    if request.method == 'POST':
        settings_obj.api_provider = request.POST.get('api_provider', 'twilio')
        settings_obj.api_key = request.POST.get('api_key', '')
        settings_obj.api_secret = request.POST.get('api_secret', '')
        settings_obj.phone_number = request.POST.get('phone_number', '')
        settings_obj.webhook_url = request.POST.get('webhook_url', '')
        settings_obj.is_active = request.POST.get('is_active') == 'on'
        settings_obj.save()
        messages.success(request, 'تم حفظ الإعدادات بنجاح')
        return redirect('crm:whatsapp_settings')
    
    return render(request, 'crm/whatsapp/settings.html', {'settings': settings_obj})


# ============================================
# Communication Analytics - تحليلات التواصل
# ============================================
@login_required
def communication_analytics(request):
    """تحليلات التواصل"""
    from .models import EmailLog, WhatsAppMessage, FollowUp
    
    # إحصائيات البريد
    email_stats = {
        'total': EmailLog.objects.count(),
        'sent': EmailLog.objects.filter(status='sent').count(),
        'failed': EmailLog.objects.filter(status='failed').count(),
    }
    
    # إحصائيات الواتساب
    whatsapp_stats = {
        'total': WhatsAppMessage.objects.count(),
        'sent': WhatsAppMessage.objects.filter(status='sent').count(),
        'delivered': WhatsAppMessage.objects.filter(status='delivered').count(),
    }
    
    # إحصائيات المتابعات
    followup_stats = {
        'total': FollowUp.objects.count(),
        'completed': FollowUp.objects.filter(status='completed').count(),
        'pending': FollowUp.objects.filter(status='pending').count(),
    }
    
    context = {
        'email_stats': email_stats,
        'whatsapp_stats': whatsapp_stats,
        'followup_stats': followup_stats,
    }
    return render(request, 'crm/communication_analytics.html', context)


# ============================================
# Contracts Views - العقود
# ============================================
@login_required
def contract_list(request):
    """قائمة العقود"""
    from .models import Contract
    contracts = Contract.objects.select_related('customer', 'contract_type').order_by('-created_at')
    
    search = request.GET.get('search', '')
    if search:
        contracts = contracts.filter(
            Q(contract_number__icontains=search) |
            Q(customer__first_name__icontains=search) |
            Q(customer__company_name__icontains=search)
        )
    
    status = request.GET.get('status', '')
    if status:
        contracts = contracts.filter(status=status)
    
    paginator = Paginator(contracts, 15)
    page = request.GET.get('page')
    contracts = paginator.get_page(page)
    
    context = {
        'contracts': contracts,
        'search': search,
        'selected_status': status,
    }
    return render(request, 'crm/contract_list.html', context)


@login_required
def contract_create(request):
    """إنشاء عقد جديد"""
    from .models import Contract, ContractType
    
    if request.method == 'POST':
        contract = Contract.objects.create(
            customer_id=request.POST.get('customer'),
            contract_type_id=request.POST.get('contract_type'),
            contract_number=request.POST.get('contract_number'),
            start_date=request.POST.get('start_date'),
            end_date=request.POST.get('end_date'),
            value=request.POST.get('value') or 0,
            terms=request.POST.get('terms', ''),
            notes=request.POST.get('notes', ''),
            created_by=request.user
        )
        messages.success(request, 'تم إنشاء العقد بنجاح')
        return redirect('crm:contract_list')
    
    customers = Customer.objects.filter(status='active')[:100]
    contract_types = ContractType.objects.filter(is_active=True)
    
    context = {
        'customers': customers,
        'contract_types': contract_types,
    }
    return render(request, 'crm/contract_form.html', context)


@login_required
def contract_detail(request, pk):
    """تفاصيل العقد"""
    from .models import Contract, ContractRenewal
    contract = get_object_or_404(Contract, pk=pk)
    renewals = ContractRenewal.objects.filter(contract=contract).order_by('-renewal_date')
    
    context = {
        'contract': contract,
        'renewals': renewals,
    }
    return render(request, 'crm/contract_detail.html', context)


@login_required
def contract_edit(request, pk):
    """تعديل عقد"""
    from .models import Contract, ContractType
    contract = get_object_or_404(Contract, pk=pk)
    
    if request.method == 'POST':
        contract.contract_type_id = request.POST.get('contract_type', contract.contract_type_id)
        contract.start_date = request.POST.get('start_date', contract.start_date)
        contract.end_date = request.POST.get('end_date', contract.end_date)
        contract.value = request.POST.get('value', contract.value)
        contract.status = request.POST.get('status', contract.status)
        contract.terms = request.POST.get('terms', contract.terms)
        contract.notes = request.POST.get('notes', contract.notes)
        contract.save()
        messages.success(request, 'تم تعديل العقد بنجاح')
        return redirect('crm:contract_detail', pk=pk)
    
    customers = Customer.objects.filter(status='active')[:100]
    contract_types = ContractType.objects.filter(is_active=True)
    
    context = {
        'contract': contract,
        'customers': customers,
        'contract_types': contract_types,
    }
    return render(request, 'crm/contract_form.html', context)


@login_required
def contract_delete(request, pk):
    """حذف عقد"""
    from .models import Contract
    contract = get_object_or_404(Contract, pk=pk)
    if request.method == 'POST':
        contract.delete()
        messages.success(request, 'تم حذف العقد بنجاح')
    return redirect('crm:contract_list')


@login_required
def contract_renew(request, pk):
    """تجديد عقد"""
    from .models import Contract, ContractRenewal
    contract = get_object_or_404(Contract, pk=pk)
    
    if request.method == 'POST':
        renewal = ContractRenewal.objects.create(
            contract=contract,
            old_end_date=contract.end_date,
            new_end_date=request.POST.get('new_end_date'),
            new_value=request.POST.get('new_value') or contract.value,
            notes=request.POST.get('notes', ''),
            renewed_by=request.user
        )
        
        # تحديث العقد
        contract.end_date = renewal.new_end_date
        contract.value = renewal.new_value
        contract.status = 'active'
        contract.save()
        
        messages.success(request, 'تم تجديد العقد بنجاح')
        return redirect('crm:contract_detail', pk=pk)
    
    return render(request, 'crm/contract_renew.html', {'contract': contract})


@login_required
def contract_renewals(request):
    """قائمة تجديدات العقود"""
    from .models import ContractRenewal
    renewals = ContractRenewal.objects.select_related('original_contract', 'original_contract__customer', 'new_contract', 'created_by').order_by('-renewal_date')
    
    paginator = Paginator(renewals, 15)
    page = request.GET.get('page')
    renewals = paginator.get_page(page)
    
    return render(request, 'crm/contract_renewals.html', {'renewals': renewals})


@login_required
def contract_settings(request):
    """إعدادات العقود"""
    from .models import ContractType
    contract_types = ContractType.objects.all().order_by('name')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create':
            ContractType.objects.create(
                name=request.POST.get('name'),
                description=request.POST.get('description', ''),
                default_duration=request.POST.get('default_duration') or 12,
                is_active=request.POST.get('is_active') == 'on'
            )
            messages.success(request, 'تم إنشاء نوع العقد بنجاح')
        elif action == 'delete':
            type_id = request.POST.get('type_id')
            ContractType.objects.filter(pk=type_id).delete()
            messages.success(request, 'تم حذف نوع العقد')
        
        return redirect('crm:contract_settings')
    
    return render(request, 'crm/contract_settings.html', {'contract_types': contract_types})


@login_required
def maintenance_contracts(request):
    """تتبع عقود الصيانة"""
    from .models import Contract
    contracts = Contract.objects.filter(
        contract_type__name__icontains='صيانة'
    ).select_related('customer', 'contract_type').order_by('-end_date')
    
    # العقود التي ستنتهي قريباً
    thirty_days = timezone.now().date() + timedelta(days=30)
    expiring_soon = contracts.filter(end_date__lte=thirty_days, status='active')
    
    paginator = Paginator(contracts, 15)
    page = request.GET.get('page')
    contracts = paginator.get_page(page)
    
    context = {
        'contracts': contracts,
        'expiring_soon': expiring_soon,
    }
    return render(request, 'crm/maintenance_contracts.html', context)


# ============================================
# Service Plans Views - الخطط والباقات
# ============================================
@login_required
def plan_list(request):
    """قائمة الخطط والباقات"""
    from .models import ServicePlan
    plans = ServicePlan.objects.all().order_by('name')
    
    return render(request, 'crm/plan_list.html', {'plans': plans})


@login_required
def plan_create(request):
    """إنشاء خطة جديدة"""
    from .models import ServicePlan
    
    if request.method == 'POST':
        plan = ServicePlan.objects.create(
            name=request.POST.get('name'),
            description=request.POST.get('description', ''),
            price=request.POST.get('price') or 0,
            duration_months=request.POST.get('duration_months') or 1,
            features=request.POST.get('features', ''),
            is_active=request.POST.get('is_active') == 'on'
        )
        messages.success(request, 'تم إنشاء الخطة بنجاح')
        return redirect('crm:plan_list')
    
    return render(request, 'crm/plan_form.html', {})


@login_required
def plan_edit(request, pk):
    """تعديل خطة"""
    from .models import ServicePlan
    plan = get_object_or_404(ServicePlan, pk=pk)
    
    if request.method == 'POST':
        plan.name = request.POST.get('name', plan.name)
        plan.description = request.POST.get('description', plan.description)
        plan.price = request.POST.get('price', plan.price)
        plan.duration_months = request.POST.get('duration_months', plan.duration_months)
        plan.features = request.POST.get('features', plan.features)
        plan.is_active = request.POST.get('is_active') == 'on'
        plan.save()
        messages.success(request, 'تم تعديل الخطة بنجاح')
        return redirect('crm:plan_list')
    
    return render(request, 'crm/plan_form.html', {'plan': plan})


@login_required
def plan_delete(request, pk):
    """حذف خطة"""
    from .models import ServicePlan
    plan = get_object_or_404(ServicePlan, pk=pk)
    if request.method == 'POST':
        plan.delete()
        messages.success(request, 'تم حذف الخطة بنجاح')
    return redirect('crm:plan_list')


@login_required
def subscription_list(request):
    """قائمة اشتراكات العملاء"""
    from .models import CustomerSubscription
    subscriptions = CustomerSubscription.objects.select_related('customer', 'plan').order_by('-end_date')
    
    status = request.GET.get('status', '')
    if status:
        subscriptions = subscriptions.filter(status=status)
    
    paginator = Paginator(subscriptions, 15)
    page = request.GET.get('page')
    subscriptions = paginator.get_page(page)
    
    return render(request, 'crm/subscription_list.html', {'subscriptions': subscriptions, 'selected_status': status})


@login_required
def quotation_settings(request):
    """إعدادات عروض الأسعار"""
    return render(request, 'crm/quotation_settings.html')


# ============================================
# Settings Views - الإعدادات
# ============================================
@login_required
def business_activities(request):
    """الأنشطة التجارية"""
    from .models import BusinessActivity
    activities = BusinessActivity.objects.all().order_by('name')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create':
            BusinessActivity.objects.create(
                name=request.POST.get('name'),
                description=request.POST.get('description', ''),
                is_active=request.POST.get('is_active') == 'on'
            )
            messages.success(request, 'تم إنشاء النشاط التجاري بنجاح')
        elif action == 'delete':
            activity_id = request.POST.get('activity_id')
            BusinessActivity.objects.filter(pk=activity_id).delete()
            messages.success(request, 'تم حذف النشاط التجاري')
        
        return redirect('crm:business_activities')
    
    return render(request, 'crm/settings/business_activities.html', {'activities': activities})


@login_required
def regions(request):
    """المحافظات والمناطق"""
    from .models import Region
    regions_list = Region.objects.all().order_by('name')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create':
            Region.objects.create(
                name=request.POST.get('name'),
                parent_id=request.POST.get('parent') or None,
                is_active=request.POST.get('is_active') == 'on'
            )
            messages.success(request, 'تم إنشاء المنطقة بنجاح')
        elif action == 'delete':
            region_id = request.POST.get('region_id')
            Region.objects.filter(pk=region_id).delete()
            messages.success(request, 'تم حذف المنطقة')
        
        return redirect('crm:regions')
    
    return render(request, 'crm/settings/regions.html', {'regions': regions_list})


@login_required
def rejection_reasons(request):
    """أسباب الرفض"""
    from .models import RejectionReason
    reasons = RejectionReason.objects.all().order_by('name')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create':
            RejectionReason.objects.create(
                name=request.POST.get('name'),
                description=request.POST.get('description', ''),
                is_active=request.POST.get('is_active') == 'on'
            )
            messages.success(request, 'تم إنشاء سبب الرفض بنجاح')
        elif action == 'delete':
            reason_id = request.POST.get('reason_id')
            RejectionReason.objects.filter(pk=reason_id).delete()
            messages.success(request, 'تم حذف سبب الرفض')
        
        return redirect('crm:rejection_reasons')
    
    return render(request, 'crm/settings/rejection_reasons.html', {'reasons': reasons})


@login_required
def contract_types(request):
    """أنواع العقود"""
    return redirect('crm:contract_settings')


@login_required
def general_settings(request):
    """إعدادات النظام العامة"""
    from .models import CRMSettings
    settings_obj, created = CRMSettings.objects.get_or_create(pk=1)
    
    if request.method == 'POST':
        settings_obj.company_name = request.POST.get('company_name', '')
        settings_obj.default_currency = request.POST.get('default_currency', 'EGP')
        settings_obj.auto_followup_days = request.POST.get('auto_followup_days', 7)
        settings_obj.quote_validity_days = request.POST.get('quote_validity_days', 30)
        settings_obj.contract_reminder_days = request.POST.get('contract_reminder_days', 30)
        settings_obj.save()
        messages.success(request, 'تم حفظ الإعدادات بنجاح')
        return redirect('crm:general_settings')
    
    return render(request, 'crm/settings/general.html', {'settings': settings_obj})


# ============================================
# Admin Views - النظام المتقدم
# ============================================
@login_required
def admin_roles(request):
    """إدارة الأدوار"""
    from django.contrib.auth.models import Group
    roles = Group.objects.all().order_by('name')
    return render(request, 'crm/admin/roles.html', {'roles': roles})


@login_required
def admin_teams(request):
    """إدارة الفرق"""
    return render(request, 'crm/admin/teams.html')


@login_required
def admin_user_assignments(request):
    """تعيينات المستخدمين"""
    users = User.objects.filter(is_active=True).order_by('username')
    return render(request, 'crm/admin/user_assignments.html', {'users': users})


@login_required
def admin_modules(request):
    """مديولات النظام"""
    return render(request, 'crm/admin/modules.html')


@login_required
def admin_approvals(request):
    """إدارة الموافقات"""
    return render(request, 'crm/admin/approvals.html')


@login_required
def admin_system(request):
    """إعدادات النظام العامة"""
    return redirect('crm:general_settings')


# ============================================
# Currency Views - إدارة العملات
# ============================================
@login_required
def currency_list(request):
    """قائمة العملات"""
    from core.models import Currency
    currencies = Currency.objects.all().order_by('code')
    return render(request, 'crm/currency_list.html', {'currencies': currencies})


# ============================================
# Additional Reports - تقارير إضافية
# ============================================
@login_required
def support_report(request):
    """تقرير الدعم الفني"""
    tickets = SupportTicket.objects.select_related('customer', 'category').all()
    
    stats = {
        'total': tickets.count(),
        'open': tickets.filter(status='open').count(),
        'in_progress': tickets.filter(status='in_progress').count(),
        'closed': tickets.filter(status='closed').count(),
    }
    
    context = {
        'stats': stats,
        'tickets': tickets[:50],
    }
    return render(request, 'crm/reports/support_report.html', context)


@login_required
def performance_report(request):
    """تقرير الأداء"""
    users = User.objects.filter(is_active=True)
    
    performance_data = []
    for user in users:
        data = {
            'user': user,
            'opportunities': Opportunity.objects.filter(assigned_to=user).count(),
            'won_opportunities': Opportunity.objects.filter(assigned_to=user, stage__is_won=True).count(),
            'activities': Activity.objects.filter(assigned_to=user).count(),
            'tickets': SupportTicket.objects.filter(assigned_to=user).count(),
        }
        performance_data.append(data)
    
    return render(request, 'crm/reports/performance_report.html', {'performance_data': performance_data})


# ============================================
# Contact List View - جهات الاتصال
# ============================================
@login_required
def contact_list(request):
    """قائمة جهات الاتصال"""
    contacts = ContactPerson.objects.select_related('customer').order_by('-created_at')
    
    search = request.GET.get('search', '')
    if search:
        contacts = contacts.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search) |
            Q(mobile__icontains=search)
        )
    
    paginator = Paginator(contacts, 15)
    page = request.GET.get('page')
    contacts = paginator.get_page(page)
    
    return render(request, 'crm/contact_list.html', {'contacts': contacts, 'search': search})