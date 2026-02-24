"""
Views لنظام الضمان - Warranty System Views
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST, require_GET
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.urls import reverse

from .models import (
    ProductWarranty, WarrantyCard, WarrantyRegistration, 
    WarrantyClaim, OnlineProduct
)
from .forms import (
    ProductWarrantyForm, WarrantyCardForm, WarrantyRegistrationForm,
    WarrantyClaimForm, WarrantySearchForm, WarrantyReviewForm
)
from .decorators import store_login_required, admin_login_required

# استيراد نظام الإنتاج
try:
    from production.models import FinishedGoodUnit
    PRODUCTION_AVAILABLE = True
except ImportError:
    PRODUCTION_AVAILABLE = False

# استيراد أنظمة ERP
try:
    from warranty_management.models import (
        Warranty as ERPWarranty, 
        WarrantyPolicy as ERPWarrantyPolicy,
        WarrantyClaim as ERPWarrantyClaim
    )
    ERP_WARRANTY_AVAILABLE = True
except ImportError:
    ERP_WARRANTY_AVAILABLE = False

try:
    from crm.models import Customer as CRMCustomer
    CRM_AVAILABLE = True
except ImportError:
    CRM_AVAILABLE = False

try:
    from partners.models import Customer as ERPCustomer
    PARTNERS_AVAILABLE = True
except ImportError:
    PARTNERS_AVAILABLE = False


# =====================================================
# صفحات العميل - Customer Pages
# =====================================================

def warranty_landing(request):
    """الصفحة الرئيسية للضمان - للعملاء"""
    form = WarrantySearchForm()
    return render(request, 'ecommerce/warranty/landing.html', {
        'form': form,
        'page_title': 'تفعيل الضمان'
    })


def warranty_check(request):
    """التحقق من حالة الضمان"""
    warranty_card = None
    finished_unit = None
    error = None
    
    if request.method == 'POST' or request.GET.get('code'):
        code = request.POST.get('warranty_code') or request.GET.get('code', '')
        code = code.strip().upper()
        
        # إزالة بادئة WARRANTY: إذا كانت موجودة (من QR code)
        if code.startswith('WARRANTY:'):
            code = code.replace('WARRANTY:', '')
        
        if code:
            # البحث أولاً في WarrantyCard
            try:
                warranty_card = WarrantyCard.objects.select_related(
                    'product', 'inventory_product', 'warranty_policy'
                ).get(warranty_code=code)
            except WarrantyCard.DoesNotExist:
                # البحث في FinishedGoodUnit (وحدات الإنتاج)
                try:
                    from production.models import FinishedGoodUnit
                    finished_unit = FinishedGoodUnit.objects.select_related(
                        'product', 'production_order', 'warranty_policy'
                    ).filter(
                        Q(unit_serial__iexact=code) | Q(barcode=code)
                    ).first()
                    
                    if not finished_unit:
                        error = 'رمز الضمان غير صحيح'
                except:
                    error = 'رمز الضمان غير صحيح'
    
    return render(request, 'ecommerce/warranty/check.html', {
        'warranty_card': warranty_card,
        'finished_unit': finished_unit,
        'error': error,
        'page_title': 'التحقق من الضمان'
    })


def warranty_register(request):
    """تسجيل وتفعيل الضمان"""
    initial_code = request.GET.get('code', '')
    
    # إزالة بادئة WARRANTY: إذا كانت موجودة
    if initial_code.startswith('WARRANTY:'):
        initial_code = initial_code.replace('WARRANTY:', '')
    
    if request.method == 'POST':
        form = WarrantyRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            registration = form.save(commit=False)
            
            # ربط المستخدم إذا كان مسجل دخول
            if request.user.is_authenticated:
                registration.user = request.user
            
            # ربط بطاقة الضمان
            code = form.cleaned_data['warranty_code_entered']
            try:
                warranty_card = WarrantyCard.objects.get(warranty_code=code)
                registration.warranty_card = warranty_card
            except WarrantyCard.DoesNotExist:
                pass
            
            registration.save()
            
            messages.success(request, 'تم إرسال طلب تفعيل الضمان بنجاح! سيتم مراجعته والرد عليك قريباً.')
            return redirect('ecommerce:warranty_registration_success', pk=registration.pk)
    else:
        initial_data = {'warranty_code_entered': initial_code}
        if request.user.is_authenticated:
            initial_data.update({
                'customer_name': request.user.get_full_name() or request.user.username,
                'customer_email': request.user.email,
            })
        form = WarrantyRegistrationForm(initial=initial_data)
    
    return render(request, 'ecommerce/warranty/register.html', {
        'form': form,
        'page_title': 'تفعيل الضمان'
    })


def warranty_registration_success(request, pk):
    """صفحة نجاح تسجيل الضمان"""
    registration = get_object_or_404(WarrantyRegistration, pk=pk)
    return render(request, 'ecommerce/warranty/registration_success.html', {
        'registration': registration,
        'page_title': 'تم استلام طلبك'
    })


def warranty_claim_submit(request, warranty_code):
    """تقديم مطالبة ضمان - يدعم كلا النظامين (WarrantyCard و FinishedGoodUnit)"""
    warranty_card = None
    production_unit = None
    
    # البحث في نظام WarrantyCard أولاً
    try:
        warranty_card = WarrantyCard.objects.get(warranty_code=warranty_code)
    except WarrantyCard.DoesNotExist:
        pass
    
    # البحث في نظام الإنتاج إذا لم يُوجد في WarrantyCard
    if not warranty_card and PRODUCTION_AVAILABLE:
        try:
            production_unit = FinishedGoodUnit.objects.select_related(
                'product', 'warranty_policy'
            ).get(
                Q(unit_serial=warranty_code) | Q(barcode=warranty_code)
            )
        except FinishedGoodUnit.DoesNotExist:
            pass
    
    # إذا لم يُوجد في أي نظام
    if not warranty_card and not production_unit:
        messages.error(request, 'لم يتم العثور على الضمان بهذا الرمز')
        return redirect('ecommerce:warranty_check')
    
    # التعامل مع وحدة الإنتاج
    if production_unit:
        # التحقق من صلاحية الضمان
        if not production_unit.warranty_registered:
            messages.error(request, 'هذه الوحدة غير مسجلة للضمان بعد')
            return redirect('ecommerce:warranty_check')
        
        if not production_unit.is_warranty_valid:
            messages.error(request, 'هذا الضمان منتهي الصلاحية')
            return redirect('ecommerce:warranty_check')
        
        # عرض صفحة مطالبة خاصة بوحدات الإنتاج
        return render(request, 'ecommerce/warranty/claim_production_unit.html', {
            'unit': production_unit,
            'page_title': 'مطالبة ضمان المنتج'
        })
    
    # التعامل مع WarrantyCard
    # التحقق من صلاحية الضمان
    if not warranty_card.is_valid:
        messages.error(request, 'هذا الضمان غير صالح أو منتهي')
        return redirect('ecommerce:warranty_check')
    
    if request.method == 'POST':
        form = WarrantyClaimForm(request.POST, request.FILES)
        if form.is_valid():
            claim = form.save(commit=False)
            claim.warranty_card = warranty_card
            claim.save()
            
            messages.success(request, 'تم تقديم مطالبة الضمان بنجاح! سيتم التواصل معك قريباً.')
            return redirect('ecommerce:warranty_claim_success', pk=claim.pk)
    else:
        form = WarrantyClaimForm()
    
    return render(request, 'ecommerce/warranty/claim_submit.html', {
        'form': form,
        'warranty_card': warranty_card,
        'page_title': 'مطالبة الضمان'
    })


def warranty_claim_success(request, pk):
    """صفحة نجاح تقديم المطالبة"""
    claim = get_object_or_404(WarrantyClaim, pk=pk)
    return render(request, 'ecommerce/warranty/claim_success.html', {
        'claim': claim,
        'page_title': 'تم استلام مطالبتك'
    })


# =====================================================
# API Endpoints
# =====================================================

def warranty_verify_api(request):
    """API للتحقق من رمز الضمان"""
    code = request.GET.get('code', '').strip().upper()
    
    if code.startswith('WARRANTY:'):
        code = code.replace('WARRANTY:', '')
    
    if not code:
        return JsonResponse({'valid': False, 'error': 'يرجى إدخال رمز الضمان'})
    
    try:
        warranty_card = WarrantyCard.objects.select_related(
            'product', 'inventory_product', 'warranty_policy'
        ).get(warranty_code=code)
        
        product_name = ''
        if warranty_card.product:
            product_name = warranty_card.product.name
        elif warranty_card.inventory_product:
            product_name = warranty_card.inventory_product.name
        
        return JsonResponse({
            'valid': True,
            'code': warranty_card.warranty_code,
            'status': warranty_card.status,
            'status_display': warranty_card.get_status_display(),
            'product_name': product_name,
            'purchase_date': warranty_card.purchase_date.isoformat() if warranty_card.purchase_date else None,
            'warranty_end_date': warranty_card.warranty_end_date.isoformat() if warranty_card.warranty_end_date else None,
            'is_valid': warranty_card.is_valid,
            'days_remaining': warranty_card.days_remaining,
            'warranty_policy': warranty_card.warranty_policy.name if warranty_card.warranty_policy else None,
        })
    except WarrantyCard.DoesNotExist:
        return JsonResponse({'valid': False, 'error': 'رمز الضمان غير صحيح'})


# =====================================================
# صفحات الإدارة - Admin Pages
# =====================================================

@admin_login_required
def warranty_admin_dashboard(request):
    """لوحة تحكم الضمان"""
    # إحصائيات
    pending_registrations = WarrantyRegistration.objects.filter(status='pending').count()
    active_warranties = WarrantyCard.objects.filter(status='active').count()
    pending_claims = WarrantyClaim.objects.filter(status__in=['submitted', 'under_review']).count()
    total_policies = ProductWarranty.objects.filter(is_active=True).count()
    
    # آخر التسجيلات
    recent_registrations = WarrantyRegistration.objects.select_related(
        'warranty_card', 'user'
    ).order_by('-created_at')[:10]
    
    # آخر المطالبات
    recent_claims = WarrantyClaim.objects.select_related(
        'warranty_card'
    ).order_by('-submitted_at')[:10]
    
    return render(request, 'ecommerce/admin/warranty/dashboard.html', {
        'pending_registrations': pending_registrations,
        'active_warranties': active_warranties,
        'pending_claims': pending_claims,
        'total_policies': total_policies,
        'recent_registrations': recent_registrations,
        'recent_claims': recent_claims,
        'page_title': 'إدارة الضمان'
    })


@admin_login_required
def warranty_policy_list(request):
    """قائمة سياسات الضمان"""
    policies = ProductWarranty.objects.all().order_by('-created_at')
    
    paginator = Paginator(policies, 20)
    page = request.GET.get('page')
    policies = paginator.get_page(page)
    
    return render(request, 'ecommerce/admin/warranty/policy_list.html', {
        'policies': policies,
        'page_title': 'سياسات الضمان'
    })


@admin_login_required
def warranty_policy_create(request):
    """إنشاء سياسة ضمان"""
    if request.method == 'POST':
        form = ProductWarrantyForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم إنشاء سياسة الضمان بنجاح')
            return redirect('ecommerce:warranty_policy_list')
    else:
        form = ProductWarrantyForm()
    
    return render(request, 'ecommerce/admin/warranty/policy_form.html', {
        'form': form,
        'page_title': 'إنشاء سياسة ضمان'
    })


@admin_login_required
def warranty_policy_edit(request, pk):
    """تعديل سياسة ضمان"""
    policy = get_object_or_404(ProductWarranty, pk=pk)
    
    if request.method == 'POST':
        form = ProductWarrantyForm(request.POST, instance=policy)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث سياسة الضمان بنجاح')
            return redirect('ecommerce:warranty_policy_list')
    else:
        form = ProductWarrantyForm(instance=policy)
    
    return render(request, 'ecommerce/admin/warranty/policy_form.html', {
        'form': form,
        'policy': policy,
        'page_title': 'تعديل سياسة الضمان'
    })


@admin_login_required
def warranty_policy_delete(request, pk):
    """حذف سياسة ضمان"""
    policy = get_object_or_404(ProductWarranty, pk=pk)
    
    if request.method == 'POST':
        policy.delete()
        messages.success(request, 'تم حذف سياسة الضمان')
        return redirect('ecommerce:warranty_policy_list')
    
    return render(request, 'ecommerce/admin/warranty/policy_delete.html', {
        'policy': policy,
        'page_title': 'حذف سياسة الضمان'
    })


@admin_login_required
def warranty_card_list(request):
    """قائمة بطاقات الضمان"""
    cards = WarrantyCard.objects.select_related(
        'product', 'inventory_product', 'warranty_policy'
    ).order_by('-created_at')
    
    # فلترة
    status = request.GET.get('status')
    if status:
        cards = cards.filter(status=status)
    
    search = request.GET.get('search')
    if search:
        cards = cards.filter(
            Q(warranty_code__icontains=search) |
            Q(serial_number__icontains=search)
        )
    
    paginator = Paginator(cards, 20)
    page = request.GET.get('page')
    cards = paginator.get_page(page)
    
    return render(request, 'ecommerce/admin/warranty/card_list.html', {
        'cards': cards,
        'status_choices': WarrantyCard.STATUS_CHOICES,
        'current_status': status,
        'search': search,
        'page_title': 'بطاقات الضمان'
    })


@admin_login_required
def warranty_card_create(request):
    """إنشاء بطاقة ضمان"""
    if request.method == 'POST':
        form = WarrantyCardForm(request.POST)
        if form.is_valid():
            card = form.save()
            messages.success(request, f'تم إنشاء بطاقة الضمان برمز: {card.warranty_code}')
            return redirect('ecommerce:warranty_card_detail', pk=card.pk)
    else:
        form = WarrantyCardForm()
    
    return render(request, 'ecommerce/admin/warranty/card_form.html', {
        'form': form,
        'page_title': 'إنشاء بطاقة ضمان'
    })


@admin_login_required
def warranty_card_detail(request, pk):
    """تفاصيل بطاقة الضمان"""
    card = get_object_or_404(
        WarrantyCard.objects.select_related(
            'product', 'inventory_product', 'warranty_policy',
            'order', 'sales_invoice', 'activated_by'
        ),
        pk=pk
    )
    
    registrations = card.registrations.all().order_by('-created_at')
    claims = card.claims.all().order_by('-submitted_at')
    
    return render(request, 'ecommerce/admin/warranty/card_detail.html', {
        'card': card,
        'registrations': registrations,
        'claims': claims,
        'page_title': f'بطاقة الضمان - {card.warranty_code}'
    })


@admin_login_required
def warranty_card_print(request, pk):
    """طباعة بطاقة الضمان"""
    card = get_object_or_404(
        WarrantyCard.objects.select_related(
            'product', 'inventory_product', 'warranty_policy'
        ),
        pk=pk
    )
    
    return render(request, 'ecommerce/admin/warranty/card_print.html', {
        'card': card,
        'page_title': f'طباعة الضمان - {card.warranty_code}'
    })


@admin_login_required
def warranty_registration_list(request):
    """قائمة طلبات تفعيل الضمان"""
    registrations = WarrantyRegistration.objects.select_related(
        'warranty_card', 'user', 'reviewed_by'
    ).order_by('-created_at')
    
    # فلترة
    status = request.GET.get('status')
    if status:
        registrations = registrations.filter(status=status)
    
    paginator = Paginator(registrations, 20)
    page = request.GET.get('page')
    registrations = paginator.get_page(page)
    
    return render(request, 'ecommerce/admin/warranty/registration_list.html', {
        'registrations': registrations,
        'status_choices': WarrantyRegistration.STATUS_CHOICES,
        'current_status': status,
        'page_title': 'طلبات تفعيل الضمان'
    })


@admin_login_required
def warranty_registration_review(request, pk):
    """مراجعة طلب تفعيل الضمان"""
    registration = get_object_or_404(
        WarrantyRegistration.objects.select_related('warranty_card', 'user'),
        pk=pk
    )
    
    if request.method == 'POST':
        form = WarrantyReviewForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            notes = form.cleaned_data.get('notes', '')
            
            if action == 'approve':
                registration.approve(request.user)
                messages.success(request, 'تم تفعيل الضمان بنجاح')
            else:
                registration.reject(request.user, notes)
                messages.warning(request, 'تم رفض طلب تفعيل الضمان')
            
            return redirect('ecommerce:warranty_registration_list')
    else:
        form = WarrantyReviewForm()
    
    return render(request, 'ecommerce/admin/warranty/registration_review.html', {
        'registration': registration,
        'form': form,
        'page_title': 'مراجعة طلب تفعيل الضمان'
    })


@admin_login_required
def warranty_claim_list(request):
    """قائمة مطالبات الضمان"""
    claims = WarrantyClaim.objects.select_related(
        'warranty_card', 'assigned_to'
    ).order_by('-submitted_at')
    
    # فلترة
    status = request.GET.get('status')
    if status:
        claims = claims.filter(status=status)
    
    paginator = Paginator(claims, 20)
    page = request.GET.get('page')
    claims = paginator.get_page(page)
    
    return render(request, 'ecommerce/admin/warranty/claim_list.html', {
        'claims': claims,
        'status_choices': WarrantyClaim.STATUS_CHOICES,
        'current_status': status,
        'page_title': 'مطالبات الضمان'
    })


@admin_login_required
def warranty_claim_detail(request, pk):
    """تفاصيل مطالبة الضمان"""
    claim = get_object_or_404(
        WarrantyClaim.objects.select_related(
            'warranty_card', 'warranty_card__product', 
            'warranty_card__inventory_product', 'assigned_to'
        ),
        pk=pk
    )
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        notes = request.POST.get('notes', '')
        
        if new_status and new_status in dict(WarrantyClaim.STATUS_CHOICES):
            claim.status = new_status
            if notes:
                claim.resolution_notes = notes
            if new_status in ['completed', 'rejected', 'replaced']:
                claim.resolved_at = timezone.now()
            claim.assigned_to = request.user
            claim.save()
            messages.success(request, 'تم تحديث حالة المطالبة')
            return redirect('ecommerce:warranty_claim_list')
    
    return render(request, 'ecommerce/admin/warranty/claim_detail.html', {
        'claim': claim,
        'status_choices': WarrantyClaim.STATUS_CHOICES,
        'page_title': f'مطالبة الضمان #{claim.pk}'
    })


# =====================================================
# إنشاء ضمان تلقائي مع الفاتورة
# =====================================================

def create_warranty_for_order(order, invoice=None):
    """
    إنشاء بطاقات ضمان تلقائية مع طلب المتجر + ربطها بنظام ERP
    
    Args:
        order: طلب المتجر (ecommerce.Order)
        invoice: فاتورة ERP (sales.Invoice) - اختياري
    
    Returns:
        list: قائمة بطاقات الضمان المنشأة
    """
    import logging
    logger = logging.getLogger(__name__)
    created_cards = []
    
    for order_item in order.items.all():
        online_product = order_item.product
        if not online_product:
            continue
        
        inventory_product = getattr(online_product, 'inventory_item', None)
        
        # البحث عن سياسة ضمان
        warranty_policy = ProductWarranty.objects.filter(is_active=True).first()
        
        if not warranty_policy:
            continue  # لا توجد سياسة ضمان نشطة
        
        # إنشاء بطاقة ضمان لكل وحدة من المنتج
        for i in range(int(order_item.quantity)):
            try:
                card = WarrantyCard.objects.create(
                    product=online_product,
                    inventory_product=inventory_product,
                    warranty_policy=warranty_policy,
                    order=order,
                    sales_invoice=invoice,
                    purchase_date=timezone.now().date(),
                )
                created_cards.append(card)
                logger.info(f"Created warranty card {card.warranty_code} for order {order.order_number}")
            except Exception as e:
                logger.error(f"Error creating warranty card for order {order.order_number}: {e}")
    
    # ✅ مزامنة مع نظام ERP warranty_management
    if ERP_WARRANTY_AVAILABLE and created_cards:
        _sync_warranty_cards_to_erp(created_cards, order)
    
    return created_cards


def _sync_warranty_cards_to_erp(cards, order):
    """
    مزامنة بطاقات الضمان مع نظام warranty_management في ERP
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # البحث عن عميل CRM
    crm_customer = None
    if CRM_AVAILABLE:
        try:
            crm_customer = CRMCustomer.objects.filter(
                Q(email=order.customer_email) | Q(phone=order.customer_phone)
            ).first()
            
            if not crm_customer:
                import random, string
                code = 'WEB-' + ''.join(random.choices(string.digits, k=6))
                name_parts = (order.customer_name or '').split(' ', 1)
                crm_customer = CRMCustomer.objects.create(
                    customer_code=code,
                    first_name=name_parts[0] if name_parts else order.customer_name,
                    last_name=name_parts[1] if len(name_parts) > 1 else '',
                    email=order.customer_email or '',
                    phone=order.customer_phone or '',
                    address_line1=order.shipping_address or '',
                    city=getattr(order, 'shipping_city', ''),
                )
                logger.info(f"Created CRM customer for warranty: {crm_customer.first_name}")
        except Exception as e:
            logger.warning(f"Could not get/create CRM customer: {e}")
    
    if not crm_customer:
        return
    
    for card in cards:
        try:
            inv_product = card.inventory_product
            if not inv_product:
                continue
            
            # البحث عن سياسة ERP مطابقة أو إنشاء واحدة
            erp_policy = ERPWarrantyPolicy.objects.filter(
                product=inv_product, is_active=True
            ).first()
            
            if not erp_policy:
                # إنشاء سياسة من بيانات الضمان الإلكتروني
                duration = card.warranty_policy.duration if card.warranty_policy else 12
                erp_policy = ERPWarrantyPolicy.objects.create(
                    name=card.warranty_policy.name if card.warranty_policy else f'ضمان {inv_product.name}',
                    product=inv_product,
                    duration_months=duration,
                    coverage_type='full',
                    terms_conditions=card.warranty_policy.terms_and_conditions if card.warranty_policy else 'ضمان شامل',
                    is_active=True,
                )
            
            # حساب تاريخ الانتهاء
            from dateutil.relativedelta import relativedelta
            start = card.purchase_date
            end = start + relativedelta(months=erp_policy.duration_months)
            
            # إنشاء ضمان ERP
            erp_warranty = ERPWarranty.objects.create(
                warranty_number=card.warranty_code,
                policy=erp_policy,
                customer=crm_customer,
                product=inv_product,
                serial_number=card.serial_number or '',
                start_date=start,
                end_date=end,
                status='active' if card.status == 'active' else 'active',
            )
            logger.info(f"Synced warranty {card.warranty_code} to ERP as {erp_warranty.warranty_number}")
            
        except Exception as e:
            logger.error(f"Error syncing warranty card {card.warranty_code} to ERP: {e}")


# التوافق مع الاسم القديم
def create_warranty_for_invoice(invoice, items):
    """دالة قديمة للتوافق - تستخدم create_warranty_for_order الآن"""
    import logging
    logging.getLogger(__name__).warning(
        "create_warranty_for_invoice is deprecated, use create_warranty_for_order"
    )
    return []
