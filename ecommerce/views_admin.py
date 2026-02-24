"""
views لوحة تحكم المتجر الإلكتروني
إدارة الإعدادات، بوابات الدفع، شركات الشحن، التواصل الاجتماعي
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import permission_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from .models import (
    EcommerceSettings, OnlineProduct, ProductCategory, Order, OrderItem,
    PaymentGateway, ShippingCompany, SocialMediaIntegration,
    StorePageContent, StoreBanner, Coupon, ProductReview,
    Customer, SocialAccount, SocialAuthProvider, Brand
)
from .forms import (
    EcommerceSettingsForm, PaymentGatewayForm, ShippingCompanyForm,
    SocialMediaIntegrationForm, StorePageContentForm, StoreBannerForm,
    CouponForm, ProductCategoryForm, OnlineProductForm, SocialAuthProviderForm
)
from .decorators import admin_login_required


@admin_login_required
@permission_required('ecommerce.view_ecommercesettings', raise_exception=True)
def store_dashboard(request):
    """لوحة تحكم المتجر الرئيسية"""
    today = timezone.now().date()
    last_30_days = today - timedelta(days=30)
    last_7_days = today - timedelta(days=7)
    
    # إحصائيات عامة
    total_products = OnlineProduct.objects.filter(is_active=True).count()
    total_orders = Order.objects.count()
    total_revenue = Order.objects.filter(
        payment_status='paid'
    ).aggregate(total=Sum('total'))['total'] or Decimal('0')
    
    # طلبات اليوم
    today_orders = Order.objects.filter(created_at__date=today).count()
    today_revenue = Order.objects.filter(
        created_at__date=today, payment_status='paid'
    ).aggregate(total=Sum('total'))['total'] or Decimal('0')
    
    # طلبات آخر 7 أيام
    week_orders = Order.objects.filter(created_at__date__gte=last_7_days).count()
    week_revenue = Order.objects.filter(
        created_at__date__gte=last_7_days, payment_status='paid'
    ).aggregate(total=Sum('total'))['total'] or Decimal('0')
    
    # طلبات آخر 30 يوم
    month_orders = Order.objects.filter(created_at__date__gte=last_30_days).count()
    month_revenue = Order.objects.filter(
        created_at__date__gte=last_30_days, payment_status='paid'
    ).aggregate(total=Sum('total'))['total'] or Decimal('0')
    
    # الطلبات حسب الحالة
    orders_by_status = Order.objects.values('status').annotate(
        count=Count('id')
    ).order_by('status')
    
    # أحدث الطلبات
    recent_orders = Order.objects.select_related('user').order_by('-created_at')[:10]
    
    # المنتجات الأكثر مبيعاً
    top_products = OnlineProduct.objects.filter(
        is_active=True
    ).order_by('-sales_count')[:5]
    
    # التقييمات الأخيرة
    recent_reviews = ProductReview.objects.select_related(
        'product', 'user'
    ).order_by('-created_at')[:5]
    
    # تقييمات في انتظار الموافقة
    pending_reviews = ProductReview.objects.filter(is_approved=False).count()
    
    # بوابات الدفع النشطة
    active_gateways = PaymentGateway.objects.filter(is_active=True).count()
    
    # شركات الشحن النشطة
    active_shipping = ShippingCompany.objects.filter(is_active=True).count()
    
    context = {
        'total_products': total_products,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'today_orders': today_orders,
        'today_revenue': today_revenue,
        'week_orders': week_orders,
        'week_revenue': week_revenue,
        'month_orders': month_orders,
        'month_revenue': month_revenue,
        'orders_by_status': orders_by_status,
        'recent_orders': recent_orders,
        'top_products': top_products,
        'recent_reviews': recent_reviews,
        'pending_reviews': pending_reviews,
        'active_gateways': active_gateways,
        'active_shipping': active_shipping,
        'page_title': 'لوحة تحكم المتجر',
    }
    return render(request, 'ecommerce/admin/dashboard.html', context)


# ==================== إعدادات المتجر ====================

@admin_login_required
@permission_required('ecommerce.change_ecommercesettings', raise_exception=True)
def store_settings(request):
    """إعدادات المتجر العامة"""
    settings = EcommerceSettings.get_settings()
    
    if request.method == 'POST':
        form = EcommerceSettingsForm(request.POST, request.FILES, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم حفظ إعدادات المتجر بنجاح')
            return redirect('ecommerce:admin_settings')
    else:
        form = EcommerceSettingsForm(instance=settings)
    
    context = {
        'form': form,
        'settings': settings,
        'page_title': 'إعدادات المتجر',
    }
    return render(request, 'ecommerce/admin/store_settings.html', context)


# ==================== بوابات الدفع ====================

@admin_login_required
@permission_required('ecommerce.view_paymentgateway', raise_exception=True)
def payment_gateways_list(request):
    """قائمة بوابات الدفع"""
    gateways = PaymentGateway.objects.all().order_by('sort_order', 'name')
    
    context = {
        'gateways': gateways,
        'page_title': 'بوابات الدفع',
        'available_gateways': PaymentGateway.GATEWAY_CHOICES,
    }
    return render(request, 'ecommerce/admin/payment_gateways.html', context)


@admin_login_required
@permission_required('ecommerce.add_paymentgateway', raise_exception=True)
def payment_gateway_add(request):
    """إضافة بوابة دفع جديدة"""
    if request.method == 'POST':
        form = PaymentGatewayForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم إضافة بوابة الدفع بنجاح')
            return redirect('ecommerce:admin_payment_gateways')
    else:
        form = PaymentGatewayForm()
    
    context = {
        'form': form,
        'page_title': 'إضافة بوابة دفع',
    }
    return render(request, 'ecommerce/admin/payment_gateway_form.html', context)


@admin_login_required
@permission_required('ecommerce.change_paymentgateway', raise_exception=True)
def payment_gateway_edit(request, pk):
    """تعديل بوابة دفع"""
    gateway = get_object_or_404(PaymentGateway, pk=pk)
    
    if request.method == 'POST':
        form = PaymentGatewayForm(request.POST, request.FILES, instance=gateway)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث بوابة الدفع بنجاح')
            return redirect('ecommerce:admin_payment_gateways')
    else:
        form = PaymentGatewayForm(instance=gateway)
    
    context = {
        'form': form,
        'gateway': gateway,
        'page_title': f'تعديل {gateway.name}',
    }
    return render(request, 'ecommerce/admin/payment_gateway_form.html', context)


@admin_login_required
@permission_required('ecommerce.change_paymentgateway', raise_exception=True)
def payment_gateway_toggle(request, pk):
    """تفعيل/تعطيل بوابة دفع"""
    gateway = get_object_or_404(PaymentGateway, pk=pk)
    gateway.is_active = not gateway.is_active
    gateway.save()
    
    status = 'مفعلة' if gateway.is_active else 'معطلة'
    messages.success(request, f'{gateway.name} الآن {status}')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'is_active': gateway.is_active})
    return redirect('ecommerce:admin_payment_gateways')


@admin_login_required
@permission_required('ecommerce.delete_paymentgateway', raise_exception=True)
def payment_gateway_delete(request, pk):
    """حذف بوابة دفع"""
    gateway = get_object_or_404(PaymentGateway, pk=pk)
    name = gateway.name
    gateway.delete()
    messages.success(request, f'تم حذف {name}')
    return redirect('ecommerce:admin_payment_gateways')


# ==================== شركات الشحن ====================

@admin_login_required
@permission_required('ecommerce.view_shippingcompany', raise_exception=True)
def shipping_companies_list(request):
    """قائمة شركات الشحن"""
    companies = ShippingCompany.objects.all().order_by('sort_order', 'name')
    
    context = {
        'companies': companies,
        'page_title': 'شركات الشحن',
        'available_companies': ShippingCompany.COMPANY_CHOICES,
    }
    return render(request, 'ecommerce/admin/shipping_companies.html', context)


@admin_login_required
@permission_required('ecommerce.add_shippingcompany', raise_exception=True)
def shipping_company_add(request):
    """إضافة شركة شحن جديدة"""
    if request.method == 'POST':
        form = ShippingCompanyForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم إضافة شركة الشحن بنجاح')
            return redirect('ecommerce:admin_shipping_companies')
    else:
        form = ShippingCompanyForm()
    
    context = {
        'form': form,
        'page_title': 'إضافة شركة شحن',
    }
    return render(request, 'ecommerce/admin/shipping_company_form.html', context)


@admin_login_required
@permission_required('ecommerce.change_shippingcompany', raise_exception=True)
def shipping_company_edit(request, pk):
    """تعديل شركة شحن"""
    company = get_object_or_404(ShippingCompany, pk=pk)
    
    if request.method == 'POST':
        form = ShippingCompanyForm(request.POST, request.FILES, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث شركة الشحن بنجاح')
            return redirect('ecommerce:admin_shipping_companies')
    else:
        form = ShippingCompanyForm(instance=company)
    
    context = {
        'form': form,
        'company': company,
        'page_title': f'تعديل {company.name}',
    }
    return render(request, 'ecommerce/admin/shipping_company_form.html', context)


@admin_login_required
@permission_required('ecommerce.change_shippingcompany', raise_exception=True)
def shipping_company_toggle(request, pk):
    """تفعيل/تعطيل شركة شحن"""
    company = get_object_or_404(ShippingCompany, pk=pk)
    company.is_active = not company.is_active
    company.save()
    
    status = 'مفعلة' if company.is_active else 'معطلة'
    messages.success(request, f'{company.name} الآن {status}')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'is_active': company.is_active})
    return redirect('ecommerce:admin_shipping_companies')


@admin_login_required
@permission_required('ecommerce.delete_shippingcompany', raise_exception=True)
def shipping_company_delete(request, pk):
    """حذف شركة شحن"""
    company = get_object_or_404(ShippingCompany, pk=pk)
    name = company.name
    company.delete()
    messages.success(request, f'تم حذف {name}')
    return redirect('ecommerce:admin_shipping_companies')


# ==================== التواصل الاجتماعي ====================

@admin_login_required
@permission_required('ecommerce.view_socialmediaintegration', raise_exception=True)
def social_media_list(request):
    """قائمة تكاملات التواصل الاجتماعي"""
    integrations = SocialMediaIntegration.objects.all().order_by('sort_order', 'platform')
    
    context = {
        'integrations': integrations,
        'page_title': 'التواصل الاجتماعي',
        'available_platforms': SocialMediaIntegration.PLATFORM_CHOICES,
    }
    return render(request, 'ecommerce/admin/social_media.html', context)


@admin_login_required
@permission_required('ecommerce.add_socialmediaintegration', raise_exception=True)
def social_media_add(request):
    """إضافة تكامل تواصل اجتماعي"""
    if request.method == 'POST':
        form = SocialMediaIntegrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم إضافة حساب التواصل الاجتماعي بنجاح')
            return redirect('ecommerce:admin_social_media')
    else:
        form = SocialMediaIntegrationForm()
    
    context = {
        'form': form,
        'page_title': 'إضافة حساب تواصل اجتماعي',
    }
    return render(request, 'ecommerce/admin/social_media_form.html', context)


@admin_login_required
@permission_required('ecommerce.change_socialmediaintegration', raise_exception=True)
def social_media_edit(request, pk):
    """تعديل تكامل تواصل اجتماعي"""
    integration = get_object_or_404(SocialMediaIntegration, pk=pk)
    
    if request.method == 'POST':
        form = SocialMediaIntegrationForm(request.POST, instance=integration)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث حساب التواصل الاجتماعي بنجاح')
            return redirect('ecommerce:admin_social_media')
    else:
        form = SocialMediaIntegrationForm(instance=integration)
    
    context = {
        'form': form,
        'integration': integration,
        'page_title': f'تعديل {integration.get_platform_display()}',
    }
    return render(request, 'ecommerce/admin/social_media_form.html', context)


@admin_login_required
@permission_required('ecommerce.change_socialmediaintegration', raise_exception=True)
def social_media_toggle(request, pk):
    """تفعيل/تعطيل تكامل تواصل اجتماعي"""
    integration = get_object_or_404(SocialMediaIntegration, pk=pk)
    integration.is_active = not integration.is_active
    integration.save()
    
    status = 'مفعل' if integration.is_active else 'معطل'
    messages.success(request, f'{integration.get_platform_display()} الآن {status}')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'is_active': integration.is_active})
    return redirect('ecommerce:admin_social_media')


@admin_login_required
@permission_required('ecommerce.delete_socialmediaintegration', raise_exception=True)
def social_media_delete(request, pk):
    """حذف تكامل تواصل اجتماعي"""
    integration = get_object_or_404(SocialMediaIntegration, pk=pk)
    name = integration.get_platform_display()
    integration.delete()
    messages.success(request, f'تم حذف {name}')
    return redirect('ecommerce:admin_social_media')


# ==================== محتوى الصفحات ====================

@admin_login_required
@permission_required('ecommerce.view_storepagecontent', raise_exception=True)
def page_content_list(request):
    """قائمة محتوى الصفحات"""
    pages = StorePageContent.objects.all()
    
    # إنشاء الصفحات الافتراضية إن لم تكن موجودة
    for page_code, page_name in StorePageContent.PAGE_CHOICES:
        StorePageContent.objects.get_or_create(
            page=page_code,
            defaults={'title': page_name, 'content': f'محتوى صفحة {page_name}'}
        )
    
    pages = StorePageContent.objects.all()
    
    context = {
        'pages': pages,
        'page_title': 'محتوى الصفحات',
    }
    return render(request, 'ecommerce/admin/page_content.html', context)


@admin_login_required
@permission_required('ecommerce.change_storepagecontent', raise_exception=True)
def page_content_edit(request, pk):
    """تعديل محتوى صفحة"""
    page = get_object_or_404(StorePageContent, pk=pk)
    
    if request.method == 'POST':
        form = StorePageContentForm(request.POST, instance=page)
        if form.is_valid():
            form.save()
            messages.success(request, f'تم تحديث صفحة {page.get_page_display()} بنجاح')
            return redirect('ecommerce:admin_page_content')
    else:
        form = StorePageContentForm(instance=page)
    
    context = {
        'form': form,
        'page_obj': page,
        'page_title': f'تعديل {page.get_page_display()}',
    }
    return render(request, 'ecommerce/admin/page_content_form.html', context)


# ==================== البانرات ====================

@admin_login_required
@permission_required('ecommerce.view_storebanner', raise_exception=True)
def banners_list(request):
    """قائمة البانرات"""
    banners = StoreBanner.objects.all().order_by('position', 'sort_order')
    
    context = {
        'banners': banners,
        'page_title': 'البانرات والإعلانات',
        'positions': StoreBanner.POSITION_CHOICES,
    }
    return render(request, 'ecommerce/admin/banners.html', context)


@admin_login_required
@permission_required('ecommerce.add_storebanner', raise_exception=True)
def banner_add(request):
    """إضافة بانر جديد"""
    if request.method == 'POST':
        form = StoreBannerForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم إضافة البانر بنجاح')
            return redirect('ecommerce:admin_banners')
    else:
        form = StoreBannerForm()
    
    context = {
        'form': form,
        'page_title': 'إضافة بانر',
    }
    return render(request, 'ecommerce/admin/banner_form.html', context)


@admin_login_required
@permission_required('ecommerce.change_storebanner', raise_exception=True)
def banner_edit(request, pk):
    """تعديل بانر"""
    banner = get_object_or_404(StoreBanner, pk=pk)
    
    if request.method == 'POST':
        form = StoreBannerForm(request.POST, request.FILES, instance=banner)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث البانر بنجاح')
            return redirect('ecommerce:admin_banners')
    else:
        form = StoreBannerForm(instance=banner)
    
    context = {
        'form': form,
        'banner': banner,
        'page_title': f'تعديل {banner.title}',
    }
    return render(request, 'ecommerce/admin/banner_form.html', context)


@admin_login_required
@permission_required('ecommerce.change_storebanner', raise_exception=True)
def banner_toggle(request, pk):
    """تفعيل/تعطيل بانر"""
    banner = get_object_or_404(StoreBanner, pk=pk)
    banner.is_active = not banner.is_active
    banner.save()
    
    status = 'مفعل' if banner.is_active else 'معطل'
    messages.success(request, f'{banner.title} الآن {status}')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'is_active': banner.is_active})
    return redirect('ecommerce:admin_banners')


@admin_login_required
@permission_required('ecommerce.delete_storebanner', raise_exception=True)
def banner_delete(request, pk):
    """حذف بانر"""
    banner = get_object_or_404(StoreBanner, pk=pk)
    title = banner.title
    banner.delete()
    messages.success(request, f'تم حذف {title}')
    return redirect('ecommerce:admin_banners')


# ==================== الكوبونات ====================

@admin_login_required
@permission_required('ecommerce.view_coupon', raise_exception=True)
def coupons_list(request):
    """قائمة الكوبونات"""
    coupons = Coupon.objects.all().order_by('-created_at' if hasattr(Coupon, 'created_at') else '-valid_from')
    
    context = {
        'coupons': coupons,
        'page_title': 'كوبونات الخصم',
    }
    return render(request, 'ecommerce/admin/coupons.html', context)


@admin_login_required
@permission_required('ecommerce.add_coupon', raise_exception=True)
def coupon_add(request):
    """إضافة كوبون جديد"""
    if request.method == 'POST':
        form = CouponForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم إضافة الكوبون بنجاح')
            return redirect('ecommerce:admin_coupons')
    else:
        form = CouponForm()
    
    context = {
        'form': form,
        'page_title': 'إضافة كوبون',
    }
    return render(request, 'ecommerce/admin/coupon_form.html', context)


@admin_login_required
@permission_required('ecommerce.change_coupon', raise_exception=True)
def coupon_edit(request, pk):
    """تعديل كوبون"""
    coupon = get_object_or_404(Coupon, pk=pk)
    
    if request.method == 'POST':
        form = CouponForm(request.POST, instance=coupon)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث الكوبون بنجاح')
            return redirect('ecommerce:admin_coupons')
    else:
        form = CouponForm(instance=coupon)
    
    context = {
        'form': form,
        'coupon': coupon,
        'page_title': f'تعديل كوبون {coupon.code}',
    }
    return render(request, 'ecommerce/admin/coupon_form.html', context)


@admin_login_required
@permission_required('ecommerce.change_coupon', raise_exception=True)
def coupon_toggle(request, pk):
    """تفعيل/تعطيل كوبون"""
    coupon = get_object_or_404(Coupon, pk=pk)
    coupon.is_active = not coupon.is_active
    coupon.save()
    
    status = 'مفعل' if coupon.is_active else 'معطل'
    messages.success(request, f'كوبون {coupon.code} الآن {status}')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'is_active': coupon.is_active})
    return redirect('ecommerce:admin_coupons')


@admin_login_required
@permission_required('ecommerce.delete_coupon', raise_exception=True)
def coupon_delete(request, pk):
    """حذف كوبون"""
    coupon = get_object_or_404(Coupon, pk=pk)
    code = coupon.code
    coupon.delete()
    messages.success(request, f'تم حذف كوبون {code}')
    return redirect('ecommerce:admin_coupons')


# ==================== إدارة الطلبات ====================

@admin_login_required
@permission_required('ecommerce.view_order', raise_exception=True)
def orders_list(request):
    """قائمة الطلبات"""
    orders = Order.objects.select_related('user', 'customer').order_by('-created_at')
    
    # تصفية حسب الحالة
    status = request.GET.get('status')
    if status:
        orders = orders.filter(status=status)
    
    # تصفية حسب حالة الدفع
    payment_status = request.GET.get('payment_status')
    if payment_status:
        orders = orders.filter(payment_status=payment_status)
    
    context = {
        'orders': orders,
        'page_title': 'إدارة الطلبات',
        'status_choices': Order.STATUS_CHOICES,
        'payment_status_choices': Order.PAYMENT_STATUS_CHOICES,
        'current_status': status,
        'current_payment_status': payment_status,
    }
    return render(request, 'ecommerce/admin/orders.html', context)


@admin_login_required
@permission_required('ecommerce.view_order', raise_exception=True)
def order_detail(request, pk):
    """تفاصيل الطلب"""
    order = get_object_or_404(Order.objects.select_related('user', 'customer'), pk=pk)
    items = order.items.select_related('product')
    
    context = {
        'order': order,
        'items': items,
        'page_title': f'طلب #{order.order_number}',
        'status_choices': Order.STATUS_CHOICES,
        'payment_status_choices': Order.PAYMENT_STATUS_CHOICES,
    }
    return render(request, 'ecommerce/admin/order_detail.html', context)


@admin_login_required
@permission_required('ecommerce.change_order', raise_exception=True)
def order_update_status(request, pk):
    """تحديث حالة الطلب"""
    order = get_object_or_404(Order, pk=pk)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        new_payment_status = request.POST.get('payment_status')
        admin_notes = request.POST.get('admin_notes', '')
        
        if new_status:
            order.status = new_status
        if new_payment_status:
            order.payment_status = new_payment_status
        if admin_notes:
            order.admin_notes = admin_notes
        
        order.save()
        messages.success(request, f'تم تحديث حالة الطلب #{order.order_number}')
    
    return redirect('ecommerce:admin_order_detail', pk=pk)


# ==================== إدارة التقييمات ====================

@admin_login_required
@permission_required('ecommerce.view_productreview', raise_exception=True)
def reviews_list(request):
    """قائمة التقييمات"""
    reviews = ProductReview.objects.select_related('product', 'user').order_by('-created_at')
    
    # تصفية حسب حالة الموافقة
    approved = request.GET.get('approved')
    if approved == 'true':
        reviews = reviews.filter(is_approved=True)
    elif approved == 'false':
        reviews = reviews.filter(is_approved=False)
    
    context = {
        'reviews': reviews,
        'page_title': 'إدارة التقييمات',
        'pending_count': ProductReview.objects.filter(is_approved=False).count(),
    }
    return render(request, 'ecommerce/admin/reviews.html', context)


@admin_login_required
@permission_required('ecommerce.change_productreview', raise_exception=True)
def review_approve(request, pk):
    """الموافقة على تقييم"""
    review = get_object_or_404(ProductReview, pk=pk)
    review.is_approved = True
    review.save()
    messages.success(request, 'تم الموافقة على التقييم')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    return redirect('ecommerce:admin_reviews')


@admin_login_required
@permission_required('ecommerce.delete_productreview', raise_exception=True)
def review_delete(request, pk):
    """حذف تقييم"""
    review = get_object_or_404(ProductReview, pk=pk)
    review.delete()
    messages.success(request, 'تم حذف التقييم')
    return redirect('ecommerce:admin_reviews')


# ==================== إدارة المنتجات ====================

@admin_login_required
@permission_required('ecommerce.view_onlineproduct', raise_exception=True)
def products_list(request):
    """قائمة المنتجات"""
    products = OnlineProduct.objects.select_related('category').order_by('-created_at')
    
    # تصفية حسب التصنيف
    category_id = request.GET.get('category')
    if category_id:
        products = products.filter(category_id=category_id)
    
    # تصفية حسب الحالة
    is_active = request.GET.get('is_active')
    if is_active == 'true':
        products = products.filter(is_active=True)
    elif is_active == 'false':
        products = products.filter(is_active=False)
    
    # البحث
    search = request.GET.get('search')
    if search:
        products = products.filter(name__icontains=search)
    
    categories = ProductCategory.objects.all()
    
    context = {
        'products': products,
        'categories': categories,
        'page_title': 'إدارة المنتجات',
        'current_category': category_id,
        'current_status': is_active,
        'search_query': search,
    }
    return render(request, 'ecommerce/admin/products.html', context)


@admin_login_required
@permission_required('ecommerce.add_onlineproduct', raise_exception=True)
def product_add(request):
    """إضافة منتج جديد"""
    if request.method == 'POST':
        form = OnlineProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم إضافة المنتج بنجاح')
            return redirect('ecommerce:admin_products')
    else:
        form = OnlineProductForm()
    
    context = {
        'form': form,
        'page_title': 'إضافة منتج جديد',
    }
    return render(request, 'ecommerce/admin/product_form.html', context)


@admin_login_required
@permission_required('ecommerce.change_onlineproduct', raise_exception=True)
def product_edit(request, pk):
    """تعديل منتج"""
    product = get_object_or_404(OnlineProduct, pk=pk)
    
    if request.method == 'POST':
        form = OnlineProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث المنتج بنجاح')
            return redirect('ecommerce:admin_products')
    else:
        form = OnlineProductForm(instance=product)
    
    context = {
        'form': form,
        'product': product,
        'page_title': f'تعديل {product.name}',
    }
    return render(request, 'ecommerce/admin/product_form.html', context)


@admin_login_required
@permission_required('ecommerce.delete_onlineproduct', raise_exception=True)
def product_delete(request, pk):
    """حذف منتج"""
    product = get_object_or_404(OnlineProduct, pk=pk)
    name = product.name
    product.delete()
    messages.success(request, f'تم حذف المنتج: {name}')
    return redirect('ecommerce:admin_products')


# ==================== إدارة التصنيفات ====================

@admin_login_required
@permission_required('ecommerce.view_productcategory', raise_exception=True)
def categories_list(request):
    """قائمة التصنيفات"""
    categories = ProductCategory.objects.annotate(
        products_count=Count('products')
    ).order_by('name')
    
    context = {
        'categories': categories,
        'page_title': 'إدارة التصنيفات',
    }
    return render(request, 'ecommerce/admin/categories.html', context)


@admin_login_required
@permission_required('ecommerce.add_productcategory', raise_exception=True)
def category_add(request):
    """إضافة تصنيف جديد"""
    if request.method == 'POST':
        form = ProductCategoryForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم إضافة التصنيف بنجاح')
            return redirect('ecommerce:admin_categories')
    else:
        form = ProductCategoryForm()
    
    context = {
        'form': form,
        'page_title': 'إضافة تصنيف جديد',
    }
    return render(request, 'ecommerce/admin/category_form.html', context)


@admin_login_required
@permission_required('ecommerce.change_productcategory', raise_exception=True)
def category_edit(request, pk):
    """تعديل تصنيف"""
    category = get_object_or_404(ProductCategory, pk=pk)
    
    if request.method == 'POST':
        form = ProductCategoryForm(request.POST, request.FILES, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث التصنيف بنجاح')
            return redirect('ecommerce:admin_categories')
    else:
        form = ProductCategoryForm(instance=category)
    
    context = {
        'form': form,
        'category': category,
        'page_title': f'تعديل {category.name}',
    }
    return render(request, 'ecommerce/admin/category_form.html', context)


@admin_login_required
@permission_required('ecommerce.delete_productcategory', raise_exception=True)
def category_delete(request, pk):
    """حذف تصنيف"""
    category = get_object_or_404(ProductCategory, pk=pk)
    if category.products.exists():
        messages.error(request, 'لا يمكن حذف التصنيف لأنه يحتوي على منتجات')
        return redirect('ecommerce:admin_categories')
    
    name = category.name
    category.delete()
    messages.success(request, f'تم حذف التصنيف: {name}')
    return redirect('ecommerce:admin_categories')


# ==========================================
# إدارة العلامات التجارية
# ==========================================

@admin_login_required
def brands_list(request):
    """قائمة العلامات التجارية"""
    brands = Brand.objects.all().order_by('sort_order', 'name')
    
    context = {
        'brands': brands,
        'page_title': 'إدارة العلامات التجارية',
    }
    return render(request, 'ecommerce/admin/brands.html', context)


@admin_login_required
def brand_add(request):
    """إضافة علامة تجارية جديدة"""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        slug = request.POST.get('slug', '').strip()
        description = request.POST.get('description', '').strip()
        website = request.POST.get('website', '').strip()
        is_featured = request.POST.get('is_featured') == 'on'
        is_active = request.POST.get('is_active') == 'on'
        sort_order = int(request.POST.get('sort_order', 0))
        logo = request.FILES.get('logo')
        
        if not name:
            messages.error(request, 'اسم العلامة التجارية مطلوب')
        elif not slug:
            messages.error(request, 'الرابط مطلوب')
        elif Brand.objects.filter(slug=slug).exists():
            messages.error(request, 'هذا الرابط موجود مسبقاً')
        else:
            brand = Brand.objects.create(
                name=name,
                slug=slug,
                description=description,
                website=website,
                is_featured=is_featured,
                is_active=is_active,
                sort_order=sort_order,
                logo=logo
            )
            messages.success(request, f'تم إضافة العلامة التجارية: {brand.name}')
            return redirect('ecommerce:admin_brands')
    
    context = {
        'page_title': 'إضافة علامة تجارية جديدة',
    }
    return render(request, 'ecommerce/admin/brand_form.html', context)


@admin_login_required
def brand_edit(request, pk):
    """تعديل علامة تجارية"""
    brand = get_object_or_404(Brand, pk=pk)
    
    if request.method == 'POST':
        brand.name = request.POST.get('name', '').strip()
        brand.slug = request.POST.get('slug', '').strip()
        brand.description = request.POST.get('description', '').strip()
        brand.website = request.POST.get('website', '').strip()
        brand.is_featured = request.POST.get('is_featured') == 'on'
        brand.is_active = request.POST.get('is_active') == 'on'
        brand.sort_order = int(request.POST.get('sort_order', 0))
        
        if request.FILES.get('logo'):
            brand.logo = request.FILES.get('logo')
        
        if not brand.name:
            messages.error(request, 'اسم العلامة التجارية مطلوب')
        elif not brand.slug:
            messages.error(request, 'الرابط مطلوب')
        elif Brand.objects.filter(slug=brand.slug).exclude(pk=pk).exists():
            messages.error(request, 'هذا الرابط موجود مسبقاً')
        else:
            brand.save()
            messages.success(request, f'تم تحديث العلامة التجارية: {brand.name}')
            return redirect('ecommerce:admin_brands')
    
    context = {
        'brand': brand,
        'page_title': f'تعديل {brand.name}',
    }
    return render(request, 'ecommerce/admin/brand_form.html', context)


@admin_login_required
def brand_delete(request, pk):
    """حذف علامة تجارية"""
    brand = get_object_or_404(Brand, pk=pk)
    name = brand.name
    brand.delete()
    messages.success(request, f'تم حذف العلامة التجارية: {name}')
    return redirect('ecommerce:admin_brands')


# ==========================================
# إدارة العملاء
# ==========================================

@admin_login_required
@permission_required('ecommerce.view_customer', raise_exception=True)
def customers_list(request):
    """قائمة العملاء"""
    customers = Customer.objects.all().select_related('user').order_by('-created_at')
    
    # فلترة البحث
    search = request.GET.get('search', '')
    if search:
        customers = customers.filter(
            user__first_name__icontains=search
        ) | customers.filter(
            user__last_name__icontains=search
        ) | customers.filter(
            user__email__icontains=search
        ) | customers.filter(
            phone__icontains=search
        )
    
    context = {
        'customers': customers,
        'search': search,
        'page_title': 'إدارة العملاء',
    }
    return render(request, 'ecommerce/admin/customers_list.html', context)


@admin_login_required
@permission_required('ecommerce.view_customer', raise_exception=True)
def customer_detail(request, pk):
    """تفاصيل العميل"""
    customer = get_object_or_404(Customer, pk=pk)
    orders = Order.objects.filter(user=customer.user).order_by('-created_at')[:10]
    social_accounts = customer.social_accounts.all()
    addresses = customer.addresses.all()
    
    context = {
        'customer': customer,
        'orders': orders,
        'social_accounts': social_accounts,
        'addresses': addresses,
        'page_title': f'تفاصيل العميل: {customer.name}',
    }
    return render(request, 'ecommerce/admin/customer_detail.html', context)


# ==========================================
# إدارة مزودي تسجيل الدخول الاجتماعي
# ==========================================

@admin_login_required
@permission_required('ecommerce.view_socialauthprovider', raise_exception=True)
def social_auth_providers_list(request):
    """قائمة مزودي تسجيل الدخول الاجتماعي"""
    providers = SocialAuthProvider.objects.all().order_by('sort_order')
    
    context = {
        'providers': providers,
        'page_title': 'مزودي تسجيل الدخول الاجتماعي',
    }
    return render(request, 'ecommerce/admin/social_auth_list.html', context)


@admin_login_required
@permission_required('ecommerce.add_socialauthprovider', raise_exception=True)
def social_auth_provider_add(request):
    """إضافة مزود جديد"""
    if request.method == 'POST':
        form = SocialAuthProviderForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم إضافة مزود تسجيل الدخول بنجاح')
            return redirect('ecommerce:admin_social_auth')
    else:
        form = SocialAuthProviderForm()
    
    context = {
        'form': form,
        'page_title': 'إضافة مزود تسجيل دخول',
    }
    return render(request, 'ecommerce/admin/social_auth_form.html', context)


@admin_login_required
@permission_required('ecommerce.change_socialauthprovider', raise_exception=True)
def social_auth_provider_edit(request, pk):
    """تعديل مزود"""
    provider = get_object_or_404(SocialAuthProvider, pk=pk)
    
    if request.method == 'POST':
        form = SocialAuthProviderForm(request.POST, instance=provider)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث مزود تسجيل الدخول بنجاح')
            return redirect('ecommerce:admin_social_auth')
    else:
        form = SocialAuthProviderForm(instance=provider)
    
    context = {
        'form': form,
        'provider': provider,
        'page_title': f'تعديل {provider.name}',
    }
    return render(request, 'ecommerce/admin/social_auth_form.html', context)


@admin_login_required
@permission_required('ecommerce.change_socialauthprovider', raise_exception=True)
def social_auth_provider_toggle(request, pk):
    """تفعيل/تعطيل مزود"""
    provider = get_object_or_404(SocialAuthProvider, pk=pk)
    provider.is_active = not provider.is_active
    provider.save()
    status = 'تفعيل' if provider.is_active else 'تعطيل'
    messages.success(request, f'تم {status} {provider.name}')
    return redirect('ecommerce:admin_social_auth')


@admin_login_required
@permission_required('ecommerce.delete_socialauthprovider', raise_exception=True)
def social_auth_provider_delete(request, pk):
    """حذف مزود"""
    provider = get_object_or_404(SocialAuthProvider, pk=pk)
    
    # التحقق من عدم وجود حسابات مرتبطة
    linked_accounts = SocialAccount.objects.filter(provider=provider.provider).count()
    if linked_accounts > 0:
        messages.error(request, f'لا يمكن حذف المزود لأنه مرتبط بـ {linked_accounts} حساب')
        return redirect('ecommerce:admin_social_auth')
    
    name = provider.name
    provider.delete()
    messages.success(request, f'تم حذف مزود تسجيل الدخول: {name}')
    return redirect('ecommerce:admin_social_auth')


# ==================== قائمة إعدادات المتجر الرئيسية ====================

@admin_login_required
@permission_required('ecommerce.view_ecommercesettings', raise_exception=True)
def settings_menu(request):
    """قائمة إعدادات المتجر الشاملة"""
    from .models import (
        PaymentGateway, ShippingCompany, ProductReview, Coupon,
        HeaderSettings, FooterSettings, NewsletterSubscriber,
        FlashSale, HomepageSection
    )
    
    # إحصائيات للعرض في القائمة
    active_gateways = PaymentGateway.objects.filter(is_active=True).count()
    active_shipping = ShippingCompany.objects.filter(is_active=True).count()
    pending_reviews = ProductReview.objects.filter(is_approved=False).count()
    active_coupons = Coupon.objects.filter(is_active=True).count()
    
    context = {
        'page_title': 'إعدادات المتجر',
        'active_gateways': active_gateways,
        'active_shipping': active_shipping,
        'pending_reviews': pending_reviews,
        'active_coupons': active_coupons,
    }
    return render(request, 'ecommerce/admin/settings_menu.html', context)


# ==================== إعدادات الهيدر ====================

@admin_login_required
@permission_required('ecommerce.change_ecommercesettings', raise_exception=True)
def header_settings(request):
    """إعدادات رأس المتجر"""
    from .models import HeaderSettings
    from .forms import HeaderSettingsForm
    
    settings = HeaderSettings.get_settings()
    
    if request.method == 'POST':
        form = HeaderSettingsForm(request.POST, request.FILES, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم حفظ إعدادات الهيدر بنجاح')
            return redirect('ecommerce:admin_header_settings')
    else:
        form = HeaderSettingsForm(instance=settings)
    
    context = {
        'form': form,
        'settings': settings,
        'page_title': 'إعدادات الهيدر',
    }
    return render(request, 'ecommerce/admin/header_settings.html', context)


# ==================== إعدادات الفوتر ====================

@admin_login_required
@permission_required('ecommerce.change_ecommercesettings', raise_exception=True)
def footer_settings(request):
    """إعدادات ذيل المتجر"""
    from .models import FooterSettings
    from .forms import FooterSettingsForm
    
    settings = FooterSettings.get_settings()
    
    if request.method == 'POST':
        form = FooterSettingsForm(request.POST, request.FILES, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم حفظ إعدادات الفوتر بنجاح')
            return redirect('ecommerce:admin_footer_settings')
    else:
        form = FooterSettingsForm(instance=settings)
    
    context = {
        'form': form,
        'settings': settings,
        'page_title': 'إعدادات الفوتر',
    }
    return render(request, 'ecommerce/admin/footer_settings.html', context)


# ==================== روابط الهيدر ====================

@admin_login_required
@permission_required('ecommerce.change_ecommercesettings', raise_exception=True)
def header_links_list(request):
    """قائمة روابط الهيدر"""
    from .models import HeaderLink
    
    links = HeaderLink.objects.filter(parent__isnull=True).order_by('sort_order')
    
    context = {
        'links': links,
        'page_title': 'روابط رأس المتجر',
    }
    return render(request, 'ecommerce/admin/header_links.html', context)


# ==================== النشرة البريدية ====================

@admin_login_required
@permission_required('ecommerce.view_ecommercesettings', raise_exception=True)
def newsletter_list(request):
    """إدارة النشرة البريدية"""
    from .models import NewsletterSubscriber, NewsletterCampaign
    
    subscribers = NewsletterSubscriber.objects.filter(is_active=True).order_by('-subscribed_at')
    campaigns = NewsletterCampaign.objects.all().order_by('-created_at')[:10]
    
    total_subscribers = NewsletterSubscriber.objects.filter(is_active=True).count()
    
    context = {
        'subscribers': subscribers[:50],
        'campaigns': campaigns,
        'total_subscribers': total_subscribers,
        'page_title': 'النشرة البريدية',
    }
    return render(request, 'ecommerce/admin/newsletter.html', context)


@admin_login_required
@permission_required('ecommerce.change_ecommercesettings', raise_exception=True)
def newsletter_campaign_add(request):
    """إنشاء حملة بريدية جديدة"""
    from .models import NewsletterCampaign, NewsletterSubscriber
    from .forms import NewsletterCampaignForm
    
    if request.method == 'POST':
        form = NewsletterCampaignForm(request.POST)
        if form.is_valid():
            campaign = form.save(commit=False)
            campaign.created_by = request.user
            campaign.save()
            messages.success(request, 'تم إنشاء الحملة بنجاح')
            return redirect('ecommerce:admin_newsletter')
    else:
        form = NewsletterCampaignForm()
    
    total_subscribers = NewsletterSubscriber.objects.filter(is_active=True).count()
    
    context = {
        'form': form,
        'total_subscribers': total_subscribers,
        'page_title': 'إنشاء حملة بريدية جديدة',
    }
    return render(request, 'ecommerce/admin/newsletter_campaign_form.html', context)


# ==================== العروض السريعة ====================

@admin_login_required
@permission_required('ecommerce.view_ecommercesettings', raise_exception=True)
def flash_sales_list(request):
    """قائمة العروض السريعة"""
    from .models import FlashSale
    
    flash_sales = FlashSale.objects.all().order_by('-start_date')
    
    context = {
        'flash_sales': flash_sales,
        'page_title': 'العروض السريعة',
    }
    return render(request, 'ecommerce/admin/flash_sales.html', context)


@admin_login_required
@permission_required('ecommerce.change_ecommercesettings', raise_exception=True)
def flash_sale_add(request):
    """إضافة عرض سريع"""
    from .models import FlashSale
    from .forms import FlashSaleForm
    
    if request.method == 'POST':
        form = FlashSaleForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم إضافة العرض السريع بنجاح')
            return redirect('ecommerce:admin_flash_sales')
    else:
        form = FlashSaleForm()
    
    context = {
        'form': form,
        'page_title': 'إضافة عرض سريع',
    }
    return render(request, 'ecommerce/admin/flash_sale_form.html', context)


# ==================== أقسام الصفحة الرئيسية ====================

@admin_login_required
@permission_required('ecommerce.view_ecommercesettings', raise_exception=True)
def homepage_sections_list(request):
    """قائمة أقسام الصفحة الرئيسية"""
    from .models import HomepageSection
    
    sections = HomepageSection.objects.all().order_by('sort_order')
    
    context = {
        'sections': sections,
        'page_title': 'أقسام الصفحة الرئيسية',
    }
    return render(request, 'ecommerce/admin/homepage_sections.html', context)


@admin_login_required
@permission_required('ecommerce.change_ecommercesettings', raise_exception=True)
def homepage_section_add(request):
    """إضافة قسم للصفحة الرئيسية"""
    from .models import HomepageSection
    from .forms import HomepageSectionForm
    
    if request.method == 'POST':
        form = HomepageSectionForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم إضافة القسم بنجاح')
            return redirect('ecommerce:admin_homepage_sections')
    else:
        form = HomepageSectionForm()
    
    context = {
        'form': form,
        'page_title': 'إضافة قسم',
    }
    return render(request, 'ecommerce/admin/homepage_section_form.html', context)


# ==================== فئات الشريط الجانبي ====================

@admin_login_required
@permission_required('ecommerce.view_ecommercesettings', raise_exception=True)
def sidebar_categories_list(request):
    """فئات الشريط الجانبي"""
    from .models import SidebarCategory
    
    categories = SidebarCategory.objects.all().order_by('sort_order')
    
    context = {
        'categories': categories,
        'page_title': 'فئات الشريط الجانبي',
    }
    return render(request, 'ecommerce/admin/sidebar_categories.html', context)


# ==================== فئة أقسام الصفحة الرئيسية ====================

@admin_login_required
@permission_required('ecommerce.view_ecommercesettings', raise_exception=True)
def homepage_category(request):
    """إعدادات فئة أقسام الصفحة الرئيسية"""
    from .models import ProductCategory
    
    categories = ProductCategory.objects.filter(parent__isnull=True, is_active=True).order_by('sort_order')
    
    context = {
        'categories': categories,
        'page_title': 'فئة أقسام الصفحة الرئيسية',
    }
    return render(request, 'ecommerce/admin/homepage_category.html', context)


# ==================== تكاليف الشحن ====================

@admin_login_required
@permission_required('ecommerce.view_shippingcompany', raise_exception=True)
def shipping_costs(request):
    """إعدادات تكاليف الشحن"""
    from .models import ShippingZone, ShippingRate
    
    zones = ShippingZone.objects.all()
    rates = ShippingRate.objects.all().select_related('zone', 'company')
    
    context = {
        'zones': zones,
        'rates': rates,
        'page_title': 'تكاليف الشحن',
    }
    return render(request, 'ecommerce/admin/shipping_costs.html', context)
