"""
عروض الخدمات المنزلية - Views
طلبات الصيانة والنظافة
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone
from django.http import JsonResponse
from datetime import timedelta

from .models import (
    ServiceType, MaintenanceCategory, CleaningPackage,
    ServiceRequest, RequestImage, ServiceArea, ServiceWorker,
    HomeServicesSettings
)
from .forms import (
    MaintenanceRequestForm, CleaningRequestForm, ServiceRequestAdminForm,
    ServiceTypeForm, MaintenanceCategoryForm, CleaningPackageForm,
    RequestImageForm, HomeServicesSettingsForm
)


# ==================== الواجهات العامة (للعملاء) ====================

def services_home(request):
    """الصفحة الرئيسية للخدمات المنزلية"""
    settings = HomeServicesSettings.get_settings()
    maintenance_categories = MaintenanceCategory.objects.filter(is_active=True)
    cleaning_packages = CleaningPackage.objects.filter(is_active=True)
    featured_packages = cleaning_packages.filter(is_featured=True)
    
    context = {
        'settings': settings,
        'maintenance_categories': maintenance_categories,
        'cleaning_packages': cleaning_packages,
        'featured_packages': featured_packages,
    }
    return render(request, 'home_services/public/home.html', context)


def maintenance_request_create(request):
    """إنشاء طلب صيانة جديد"""
    settings = HomeServicesSettings.get_settings()
    
    if not settings.enable_maintenance:
        messages.warning(request, _('خدمة الصيانة غير متاحة حالياً'))
        return redirect('home_services:services_home')
    
    categories = MaintenanceCategory.objects.filter(is_active=True)
    
    if request.method == 'POST':
        form = MaintenanceRequestForm(request.POST)
        if form.is_valid():
            service_request = form.save(commit=False)
            service_request.request_type = 'maintenance'
            if request.user.is_authenticated:
                service_request.user = request.user
            service_request.save()
            
            # رفع الصور إن وجدت
            images = request.FILES.getlist('images')
            for image in images:
                RequestImage.objects.create(request=service_request, image=image)
            
            messages.success(request, settings.confirmation_message or _('تم إرسال طلبك بنجاح! سنتواصل معك قريباً.'))
            return redirect('home_services:request_success', pk=service_request.pk)
    else:
        initial = {}
        if request.user.is_authenticated:
            initial['customer_name'] = request.user.get_full_name()
            initial['customer_email'] = request.user.email
        form = MaintenanceRequestForm(initial=initial)
    
    context = {
        'form': form,
        'categories': categories,
        'settings': settings,
    }
    return render(request, 'home_services/public/maintenance_request.html', context)


def cleaning_request_create(request):
    """إنشاء طلب نظافة جديد"""
    settings = HomeServicesSettings.get_settings()
    
    if not settings.enable_cleaning:
        messages.warning(request, _('خدمة النظافة غير متاحة حالياً'))
        return redirect('home_services:services_home')
    
    packages = CleaningPackage.objects.filter(is_active=True)
    
    if request.method == 'POST':
        form = CleaningRequestForm(request.POST)
        if form.is_valid():
            service_request = form.save(commit=False)
            service_request.request_type = 'cleaning'
            if request.user.is_authenticated:
                service_request.user = request.user
            
            # حساب السعر التقديري من الباقة
            if service_request.cleaning_package:
                service_request.estimated_price = service_request.cleaning_package.effective_price
            
            service_request.save()
            
            # رفع الصور إن وجدت
            images = request.FILES.getlist('images')
            for image in images:
                RequestImage.objects.create(request=service_request, image=image)
            
            messages.success(request, settings.confirmation_message or _('تم إرسال طلبك بنجاح! سنتواصل معك قريباً.'))
            return redirect('home_services:request_success', pk=service_request.pk)
    else:
        initial = {}
        if request.user.is_authenticated:
            initial['customer_name'] = request.user.get_full_name()
            initial['customer_email'] = request.user.email
        form = CleaningRequestForm(initial=initial)
    
    context = {
        'form': form,
        'packages': packages,
        'settings': settings,
    }
    return render(request, 'home_services/public/cleaning_request.html', context)


def request_success(request, pk):
    """صفحة نجاح الطلب"""
    service_request = get_object_or_404(ServiceRequest, pk=pk)
    settings = HomeServicesSettings.get_settings()
    
    context = {
        'service_request': service_request,
        'settings': settings,
    }
    return render(request, 'home_services/public/request_success.html', context)


def track_request(request):
    """تتبع الطلب"""
    service_request = None
    error = None
    
    if request.method == 'POST' or request.GET.get('request_number'):
        request_number = request.POST.get('request_number') or request.GET.get('request_number')
        phone = request.POST.get('phone') or request.GET.get('phone')
        
        if request_number:
            try:
                service_request = ServiceRequest.objects.get(
                    request_number__iexact=request_number.strip()
                )
                # التحقق من رقم الهاتف للأمان
                if phone and service_request.customer_phone != phone.strip():
                    service_request = None
                    error = _('رقم الطلب أو الهاتف غير صحيح')
            except ServiceRequest.DoesNotExist:
                error = _('لم يتم العثور على الطلب')
    
    context = {
        'service_request': service_request,
        'error': error,
    }
    return render(request, 'home_services/public/track_request.html', context)


def cleaning_packages_list(request):
    """عرض باقات النظافة"""
    packages = CleaningPackage.objects.filter(is_active=True).order_by('sort_order')
    settings = HomeServicesSettings.get_settings()
    
    context = {
        'packages': packages,
        'settings': settings,
    }
    return render(request, 'home_services/public/cleaning_packages.html', context)


# ==================== لوحة التحكم الإدارية ====================

@login_required
def dashboard(request):
    """لوحة تحكم الخدمات المنزلية"""
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # إحصائيات الطلبات
    total_requests = ServiceRequest.objects.count()
    pending_requests = ServiceRequest.objects.filter(status='pending').count()
    today_requests = ServiceRequest.objects.filter(created_at__date=today).count()
    
    # طلبات الأسبوع
    week_requests = ServiceRequest.objects.filter(created_at__date__gte=week_ago)
    week_stats = week_requests.aggregate(
        count=Count('id'),
        revenue=Sum('final_price')
    )
    
    # إحصائيات حسب النوع
    maintenance_count = ServiceRequest.objects.filter(request_type='maintenance').count()
    cleaning_count = ServiceRequest.objects.filter(request_type='cleaning').count()
    
    # أحدث الطلبات
    recent_requests = ServiceRequest.objects.order_by('-created_at')[:10]
    
    # طلبات تحتاج اهتمام
    urgent_requests = ServiceRequest.objects.filter(
        status='pending',
        urgency__in=['urgent', 'emergency']
    ).order_by('-created_at')[:5]
    
    context = {
        'total_requests': total_requests,
        'pending_requests': pending_requests,
        'today_requests': today_requests,
        'week_stats': week_stats,
        'maintenance_count': maintenance_count,
        'cleaning_count': cleaning_count,
        'recent_requests': recent_requests,
        'urgent_requests': urgent_requests,
    }
    return render(request, 'home_services/admin/dashboard.html', context)


@login_required
def request_list(request):
    """قائمة طلبات الخدمة"""
    requests_qs = ServiceRequest.objects.all().order_by('-created_at')
    
    # الفلترة
    request_type = request.GET.get('type')
    status = request.GET.get('status')
    search = request.GET.get('search')
    
    if request_type:
        requests_qs = requests_qs.filter(request_type=request_type)
    if status:
        requests_qs = requests_qs.filter(status=status)
    if search:
        requests_qs = requests_qs.filter(
            Q(request_number__icontains=search) |
            Q(customer_name__icontains=search) |
            Q(customer_phone__icontains=search) |
            Q(title__icontains=search)
        )
    
    paginator = Paginator(requests_qs, 20)
    page = request.GET.get('page')
    requests_list = paginator.get_page(page)
    
    context = {
        'requests': requests_list,
        'request_type': request_type,
        'status': status,
        'search': search,
    }
    return render(request, 'home_services/admin/request_list.html', context)


@login_required
def request_detail(request, pk):
    """تفاصيل طلب الخدمة"""
    service_request = get_object_or_404(ServiceRequest, pk=pk)
    
    if request.method == 'POST':
        form = ServiceRequestAdminForm(request.POST, instance=service_request)
        if form.is_valid():
            form.save()
            messages.success(request, _('تم تحديث الطلب بنجاح'))
            return redirect('home_services:request_detail', pk=pk)
    else:
        form = ServiceRequestAdminForm(instance=service_request)
    
    context = {
        'service_request': service_request,
        'form': form,
    }
    return render(request, 'home_services/admin/request_detail.html', context)


@login_required
def request_update_status(request, pk):
    """تحديث حالة الطلب"""
    service_request = get_object_or_404(ServiceRequest, pk=pk)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(ServiceRequest.STATUS_CHOICES):
            service_request.status = new_status
            
            # تحديث التواريخ تلقائياً
            if new_status == 'in_progress' and not service_request.started_at:
                service_request.started_at = timezone.now()
            elif new_status == 'completed' and not service_request.completed_at:
                service_request.completed_at = timezone.now()
            
            service_request.save()
            messages.success(request, _('تم تحديث الحالة'))
    
    return redirect('home_services:request_detail', pk=pk)


# ==================== إدارة فئات الصيانة ====================

@login_required
def maintenance_category_list(request):
    """قائمة فئات الصيانة"""
    categories = MaintenanceCategory.objects.annotate(
        requests_count=Count('servicerequest')
    ).order_by('sort_order')
    return render(request, 'home_services/admin/category_list.html', {'categories': categories})


@login_required
def maintenance_category_create(request):
    """إضافة فئة صيانة"""
    if request.method == 'POST':
        form = MaintenanceCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _('تم إضافة الفئة بنجاح'))
            return redirect('home_services:maintenance_category_list')
    else:
        form = MaintenanceCategoryForm()
    
    return render(request, 'home_services/admin/category_form.html', {'form': form})


@login_required
def maintenance_category_edit(request, pk):
    """تعديل فئة صيانة"""
    category = get_object_or_404(MaintenanceCategory, pk=pk)
    
    if request.method == 'POST':
        form = MaintenanceCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, _('تم تحديث الفئة بنجاح'))
            return redirect('home_services:maintenance_category_list')
    else:
        form = MaintenanceCategoryForm(instance=category)
    
    return render(request, 'home_services/admin/category_form.html', {'form': form, 'category': category})


# ==================== إدارة باقات النظافة ====================

@login_required
def cleaning_package_list(request):
    """قائمة باقات النظافة"""
    packages = CleaningPackage.objects.annotate(
        requests_count=Count('servicerequest')
    ).order_by('sort_order')
    return render(request, 'home_services/admin/package_list.html', {'packages': packages})


@login_required
def cleaning_package_create(request):
    """إضافة باقة نظافة"""
    if request.method == 'POST':
        form = CleaningPackageForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _('تم إضافة الباقة بنجاح'))
            return redirect('home_services:cleaning_package_list')
    else:
        form = CleaningPackageForm()
    
    return render(request, 'home_services/admin/package_form.html', {'form': form})


@login_required
def cleaning_package_edit(request, pk):
    """تعديل باقة نظافة"""
    package = get_object_or_404(CleaningPackage, pk=pk)
    
    if request.method == 'POST':
        form = CleaningPackageForm(request.POST, instance=package)
        if form.is_valid():
            form.save()
            messages.success(request, _('تم تحديث الباقة بنجاح'))
            return redirect('home_services:cleaning_package_list')
    else:
        form = CleaningPackageForm(instance=package)
    
    return render(request, 'home_services/admin/package_form.html', {'form': form, 'package': package})


# ==================== الإعدادات ====================

@login_required
def settings_view(request):
    """إعدادات الخدمات المنزلية"""
    settings = HomeServicesSettings.get_settings()
    
    if request.method == 'POST':
        form = HomeServicesSettingsForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, _('تم حفظ الإعدادات بنجاح'))
            return redirect('home_services:settings')
    else:
        form = HomeServicesSettingsForm(instance=settings)
    
    return render(request, 'home_services/admin/settings.html', {'form': form, 'settings': settings})


# ==================== التقارير ====================

@login_required
def reports_dashboard(request):
    """لوحة التقارير"""
    today = timezone.now().date()
    month_start = today.replace(day=1)
    
    # إحصائيات الشهر
    month_requests = ServiceRequest.objects.filter(created_at__date__gte=month_start)
    month_stats = month_requests.aggregate(
        total=Count('id'),
        completed=Count('id', filter=Q(status='completed')),
        revenue=Sum('final_price', filter=Q(payment_status='paid')),
        avg_rating=Avg('rating', filter=Q(rating__isnull=False))
    )
    
    # حسب النوع
    by_type = month_requests.values('request_type').annotate(count=Count('id'))
    
    # حسب الحالة
    by_status = month_requests.values('status').annotate(count=Count('id'))
    
    context = {
        'month_stats': month_stats,
        'by_type': by_type,
        'by_status': by_status,
    }
    return render(request, 'home_services/admin/reports.html', context)
