# -*- coding: utf-8 -*-
"""
Views لإدارة وحدات المنتجات النهائية وطباعة الباركود/QR Code
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.template.loader import render_to_string
import json
from io import BytesIO
from datetime import date

from .models import FinishedGoodUnit, ProductionOrder


@login_required
def unit_list(request):
    """قائمة وحدات المنتجات"""
    units = FinishedGoodUnit.objects.select_related(
        'product', 'production_order', 'dealer', 'warranty_policy'
    ).order_by('-created_at')
    
    # البحث
    search = request.GET.get('search', '')
    if search:
        units = units.filter(
            Q(unit_serial__icontains=search) |
            Q(barcode__icontains=search) |
            Q(product__name__icontains=search) |
            Q(customer_name__icontains=search) |
            Q(customer_phone__icontains=search)
        )
    
    # فلترة حسب الحالة
    status = request.GET.get('status', '')
    if status:
        units = units.filter(status=status)
    
    # فلترة حسب تسجيل الضمان
    warranty = request.GET.get('warranty', '')
    if warranty == 'registered':
        units = units.filter(warranty_registered=True)
    elif warranty == 'not_registered':
        units = units.filter(warranty_registered=False)
    
    # فلترة حسب التاريخ
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        units = units.filter(manufacture_date__gte=date_from)
    if date_to:
        units = units.filter(manufacture_date__lte=date_to)
    
    # Pagination
    paginator = Paginator(units, 50)
    page = request.GET.get('page', 1)
    units = paginator.get_page(page)
    
    # إحصائيات
    stats = {
        'total': FinishedGoodUnit.objects.count(),
        'produced': FinishedGoodUnit.objects.filter(status='produced').count(),
        'in_stock': FinishedGoodUnit.objects.filter(status='in_stock').count(),
        'sold_dealer': FinishedGoodUnit.objects.filter(status='sold_to_dealer').count(),
        'sold_customer': FinishedGoodUnit.objects.filter(status='sold_to_customer').count(),
        'warranty_registered': FinishedGoodUnit.objects.filter(warranty_registered=True).count(),
    }
    
    context = {
        'units': units,
        'stats': stats,
        'search': search,
        'status_choices': FinishedGoodUnit.STATUS_CHOICES,
        'selected_status': status,
        'selected_warranty': warranty,
        'page_title': 'وحدات المنتجات النهائية',
    }
    return render(request, 'production/units/list.html', context)


@login_required
def unit_create(request):
    """إنشاء وحدة منتج نهائي يدوياً."""
    orders = ProductionOrder.objects.select_related('product').order_by('-created_at')[:500]

    if request.method == 'POST':
        production_order_id = (request.POST.get('production_order') or '').strip()
        unit_serial = (request.POST.get('unit_serial') or '').strip()
        barcode = (request.POST.get('barcode') or '').strip()
        size_text = (request.POST.get('size_text') or '').strip()
        status = (request.POST.get('status') or 'produced').strip() or 'produced'
        manufacture_date = (request.POST.get('manufacture_date') or '').strip()
        expiry_date = (request.POST.get('expiry_date') or '').strip()


        order = None
        if not production_order_id:
            messages.error(request, 'يرجى اختيار أمر الإنتاج')
        else:
            try:
                order_id_int = int(production_order_id)
            except (TypeError, ValueError):
                messages.error(request, 'أمر الإنتاج غير صحيح')
            else:
                order = get_object_or_404(ProductionOrder, pk=order_id_int)


        if order is not None:
            # التحقق من الحالة
            if status not in dict(FinishedGoodUnit.STATUS_CHOICES):
                status = 'produced'

            # توليد رقم تسلسلي إذا لم يُرسل
            if not unit_serial:
                seq = order.finished_units.count() + 1
                while True:
                    candidate = f"{order.number}-{seq:04d}"
                    if not FinishedGoodUnit.objects.filter(unit_serial=candidate).exists():
                        unit_serial = candidate
                        break
                    seq += 1
            elif FinishedGoodUnit.objects.filter(unit_serial=unit_serial).exists():
                messages.error(request, 'رقم الوحدة (Serial) موجود مسبقاً')
                return render(request, 'production/units/create.html', {
                    'orders': orders,
                    'status_choices': FinishedGoodUnit.STATUS_CHOICES,
                    'page_title': 'إضافة وحدة جديدة',
                })

            # توليد باركود إذا لم يُرسل
            if not barcode:
                from inventory.barcode_utils import validate_barcode

                seq_hint = order.finished_units.count() + 1
                for attempt in range(1, 5000):
                    raw_code = f"{order.id:06d}{(seq_hint + attempt - 1):04d}"
                    barcode_candidate = raw_code.ljust(12, '0')
                    is_valid, _ = validate_barcode(barcode_candidate)
                    if not is_valid:
                        barcode_candidate = f"{int(timezone.now().timestamp())}"[-12:]

                    if not FinishedGoodUnit.objects.filter(barcode=barcode_candidate).exists():
                        barcode = barcode_candidate
                        break
            elif FinishedGoodUnit.objects.filter(barcode=barcode).exists():
                messages.error(request, 'الباركود موجود مسبقاً')
                return render(request, 'production/units/create.html', {
                    'orders': orders,
                    'status_choices': FinishedGoodUnit.STATUS_CHOICES,
                    'page_title': 'إضافة وحدة جديدة',
                })

            # تحويل التواريخ
            mfg = date.fromisoformat(manufacture_date) if manufacture_date else timezone.now().date()
            exp = date.fromisoformat(expiry_date) if expiry_date else None

            unit = FinishedGoodUnit.objects.create(
                product=order.product,
                production_order=order,
                unit_serial=unit_serial,
                barcode=barcode,
                manufacture_date=mfg,
                expiry_date=exp,
                size_text=size_text,
                status=status,
            )

            messages.success(request, 'تم إضافة الوحدة بنجاح')
            return redirect('production:unit_detail', pk=unit.pk)

    return render(request, 'production/units/create.html', {
        'orders': orders,
        'status_choices': FinishedGoodUnit.STATUS_CHOICES,
        'page_title': 'إضافة وحدة جديدة',
    })


@login_required
def unit_detail(request, pk):
    """تفاصيل وحدة منتج"""
    unit = get_object_or_404(
        FinishedGoodUnit.objects.select_related(
            'product', 'production_order', 'dealer', 'dealer_invoice', 'warranty_policy'
        ),
        pk=pk
    )
    
    context = {
        'unit': unit,
        'page_title': f'تفاصيل الوحدة: {unit.unit_serial}',
    }
    return render(request, 'production/units/detail.html', context)


@login_required
def unit_print_label(request, pk):
    """طباعة ملصق الباركود/QR Code لوحدة واحدة"""
    unit = get_object_or_404(FinishedGoodUnit, pk=pk)
    
    context = {
        'unit': unit,
        'print_date': timezone.now(),
    }
    return render(request, 'production/units/print_label.html', context)


@login_required
def unit_print_batch(request):
    """طباعة ملصقات لمجموعة من الوحدات"""
    unit_ids = request.GET.get('ids', '').split(',')
    unit_ids = [int(id) for id in unit_ids if id.isdigit()]
    
    if not unit_ids:
        messages.error(request, 'لم يتم تحديد أي وحدات للطباعة')
        return redirect('production:unit_list')
    
    units = FinishedGoodUnit.objects.filter(pk__in=unit_ids).select_related('product')
    
    context = {
        'units': units,
        'print_date': timezone.now(),
    }
    return render(request, 'production/units/print_batch.html', context)


@login_required
def unit_print_from_order(request, order_id):
    """طباعة جميع ملصقات الوحدات من أمر إنتاج"""
    order = get_object_or_404(ProductionOrder, pk=order_id)
    units = order.finished_units.all().select_related('product')
    
    if not units.exists():
        messages.warning(request, 'لا توجد وحدات منتهية لهذا الأمر')
        return redirect('production:order_detail', pk=order_id)
    
    context = {
        'units': units,
        'order': order,
        'print_date': timezone.now(),
    }
    return render(request, 'production/units/print_batch.html', context)


@login_required
@require_http_methods(["POST"])
def unit_update_status(request, pk):
    """تحديث حالة الوحدة"""
    unit = get_object_or_404(FinishedGoodUnit, pk=pk)
    
    new_status = request.POST.get('status')
    if new_status and new_status in dict(FinishedGoodUnit.STATUS_CHOICES):
        unit.status = new_status
        unit.save(update_fields=['status', 'updated_at'])
        messages.success(request, f'تم تحديث حالة الوحدة إلى: {unit.get_status_display()}')
    else:
        messages.error(request, 'حالة غير صالحة')
    
    return redirect('production:unit_detail', pk=pk)


@login_required
@require_http_methods(["POST"])
def unit_sell_to_dealer(request, pk):
    """تسجيل بيع الوحدة لتاجر"""
    unit = get_object_or_404(FinishedGoodUnit, pk=pk)
    
    dealer_id = request.POST.get('dealer_id')
    sale_price = request.POST.get('sale_price')
    invoice_id = request.POST.get('invoice_id')
    
    if dealer_id:
        from partners.models import Partner
        unit.dealer = Partner.objects.filter(pk=dealer_id).first()
    
    if sale_price:
        unit.dealer_sale_price = sale_price
    
    if invoice_id:
        from sales.models import Invoice
        unit.dealer_invoice = Invoice.objects.filter(pk=invoice_id).first()
    
    unit.dealer_sale_date = timezone.now().date()
    unit.status = 'sold_to_dealer'
    unit.save()
    
    messages.success(request, 'تم تسجيل البيع للتاجر بنجاح')
    return redirect('production:unit_detail', pk=pk)


@login_required
@require_http_methods(["POST"])
def unit_register_customer(request, pk):
    """تسجيل بيانات العميل النهائي"""
    unit = get_object_or_404(FinishedGoodUnit, pk=pk)
    
    unit.customer_name = request.POST.get('customer_name', '')
    unit.customer_phone = request.POST.get('customer_phone', '')
    unit.customer_email = request.POST.get('customer_email', '')
    unit.customer_address = request.POST.get('customer_address', '')
    unit.customer_national_id = request.POST.get('customer_national_id', '')
    
    sale_price = request.POST.get('customer_sale_price')
    if sale_price:
        unit.customer_sale_price = sale_price
    
    unit.customer_sale_date = timezone.now().date()
    unit.status = 'sold_to_customer'
    unit.save()
    
    messages.success(request, 'تم تسجيل بيانات العميل بنجاح')
    return redirect('production:unit_detail', pk=pk)


@login_required
def unit_verify_api(request):
    """API للتحقق من وحدة منتج"""
    code = request.GET.get('code', '').strip()
    
    if not code:
        return JsonResponse({'success': False, 'error': 'الكود مطلوب'})
    
    # البحث بالـ serial أو barcode
    unit = FinishedGoodUnit.objects.filter(
        Q(unit_serial=code) | Q(barcode=code)
    ).select_related('product', 'production_order', 'warranty_policy').first()
    
    if not unit:
        return JsonResponse({'success': False, 'error': 'لم يتم العثور على الوحدة'})
    
    data = {
        'success': True,
        'unit': {
            'id': unit.id,
            'serial': unit.unit_serial,
            'barcode': unit.barcode,
            'product_name': unit.product.name if unit.product else '',
            'manufacture_date': unit.manufacture_date.isoformat() if unit.manufacture_date else '',
            'status': unit.status,
            'status_display': unit.get_status_display(),
            'warranty_registered': unit.warranty_registered,
            'warranty_valid': unit.is_warranty_valid,
            'warranty_end_date': unit.warranty_end_date.isoformat() if unit.warranty_end_date else '',
            'warranty_remaining_days': unit.warranty_remaining_days,
            'customer_name': unit.customer_name,
            'customer_phone': unit.customer_phone,
        }
    }
    
    return JsonResponse(data)


@login_required
def unit_generate_labels(request, order_id):
    """توليد ملصقات لأمر إنتاج (إذا لم تُنشأ)"""
    order = get_object_or_404(ProductionOrder, pk=order_id)
    
    existing_count = order.finished_units.count()
    target_count = int(order.produced_quantity or 0)
    
    if existing_count >= target_count:
        messages.info(request, f'الملصقات موجودة بالفعل ({existing_count} وحدة)')
        return redirect('production:unit_print_from_order', order_id=order_id)
    
    # إنشاء الوحدات المتبقية
    from inventory.barcode_utils import validate_barcode
    from datetime import timedelta
    
    # إعدادات الصلاحية والمقاس الافتراضي
    shelf_life = 0
    default_size = ''
    try:
        from .models import ProductManufacturingProfile
        profile = ProductManufacturingProfile.objects.get(product=order.product)
        shelf_life = int(profile.shelf_life_days or 0)
        default_size = profile.default_size_text or ''
    except:
        pass
    
    mfg_date = order.actual_end_date or timezone.now().date()
    expiry = (mfg_date + timedelta(days=shelf_life)) if shelf_life > 0 else None
    
    created_count = 0
    for i in range(existing_count + 1, target_count + 1):
        raw_code = f"{order.id:06d}{i:04d}"
        barcode_code = raw_code.ljust(12, '0')
        is_valid, _ = validate_barcode(barcode_code)
        if not is_valid:
            barcode_code = f"{int(timezone.now().timestamp())}"[-12:]
        
        unit = FinishedGoodUnit.objects.create(
            product=order.product,
            production_order=order,
            unit_serial=f"{order.number}-{i:04d}",
            barcode=barcode_code,
            manufacture_date=mfg_date,
            expiry_date=expiry,
            size_text=default_size,
            status='produced',
        )
        created_count += 1
    
    messages.success(request, f'تم إنشاء {created_count} ملصق جديد')
    return redirect('production:unit_print_from_order', order_id=order_id)


# ==========================================
# صفحات تسجيل الضمان للعميل (من المتجر)
# ==========================================

def warranty_verify_unit(request):
    """صفحة التحقق من الوحدة وتسجيل الضمان"""
    unit = None
    error = None
    
    code = request.GET.get('code', '').strip()
    if code:
        unit = FinishedGoodUnit.objects.filter(
            Q(unit_serial=code) | Q(barcode=code)
        ).select_related('product', 'production_order', 'warranty_policy').first()
        
        if not unit:
            error = 'لم يتم العثور على المنتج بهذا الكود'
    
    context = {
        'unit': unit,
        'error': error,
        'code': code,
    }
    return render(request, 'production/warranty/verify_unit.html', context)


def warranty_register_unit(request):
    """تسجيل الضمان للوحدة من المتجر"""
    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        
        unit = FinishedGoodUnit.objects.filter(
            Q(unit_serial=code) | Q(barcode=code)
        ).first()
        
        if not unit:
            messages.error(request, 'لم يتم العثور على المنتج')
            return redirect('production:warranty_verify_unit')
        
        if unit.warranty_registered:
            messages.warning(request, 'هذا المنتج مسجل الضمان بالفعل')
            return redirect('production:warranty_verify_unit')
        
        # تسجيل بيانات العميل
        customer_data = {
            'name': request.POST.get('customer_name', ''),
            'phone': request.POST.get('customer_phone', ''),
            'email': request.POST.get('customer_email', ''),
            'address': request.POST.get('customer_address', ''),
            'national_id': request.POST.get('customer_national_id', ''),
        }
        
        # حفظ صورة الفاتورة
        if 'invoice_image' in request.FILES:
            unit.customer_invoice_image = request.FILES['invoice_image']
        
        # تفعيل الضمان
        unit.activate_warranty(customer_data)
        
        messages.success(request, 'تم تسجيل الضمان بنجاح!')
        return redirect('production:warranty_success', pk=unit.pk)
    
    code = request.GET.get('code', '')
    unit = None
    if code:
        unit = FinishedGoodUnit.objects.filter(
            Q(unit_serial=code) | Q(barcode=code)
        ).select_related('product').first()
    
    context = {
        'unit': unit,
        'code': code,
    }
    return render(request, 'production/warranty/register_form.html', context)


def warranty_success(request, pk):
    """صفحة نجاح تسجيل الضمان"""
    unit = get_object_or_404(FinishedGoodUnit, pk=pk)
    
    context = {
        'unit': unit,
    }
    return render(request, 'production/warranty/success.html', context)

def warranty_claim_unit(request, unit_id):
    """معالجة مطالبة الضمان لوحدة إنتاج"""
    unit = get_object_or_404(FinishedGoodUnit, pk=unit_id)
    
    if not unit.warranty_registered:
        messages.error(request, 'هذه الوحدة غير مسجلة للضمان')
        return redirect('production:warranty_verify_unit')
    
    if not unit.is_warranty_valid:
        messages.error(request, 'هذا الضمان منتهي الصلاحية')
        return redirect('production:warranty_verify_unit')
    
    if request.method == 'POST':
        issue_type = request.POST.get('issue_type', '')
        description = request.POST.get('description', '')
        contact_phone = request.POST.get('contact_phone', '')
        preferred_solution = request.POST.get('preferred_solution', 'repair')
        
        # حفظ المطالبة في ملاحظات الوحدة (يمكن تطويره لجدول منفصل لاحقاً)
        claim_data = {
            'date': timezone.now().isoformat(),
            'issue_type': issue_type,
            'description': description,
            'contact_phone': contact_phone,
            'preferred_solution': preferred_solution,
            'status': 'pending'
        }
        
        # إضافة للملاحظات
        existing_notes = unit.notes or ''
        claim_note = f"\n\n--- مطالبة ضمان ({timezone.now().strftime('%Y-%m-%d %H:%M')}) ---\n"
        claim_note += f"نوع المشكلة: {issue_type}\n"
        claim_note += f"الوصف: {description}\n"
        claim_note += f"رقم التواصل: {contact_phone}\n"
        claim_note += f"الحل المفضل: {preferred_solution}\n"
        
        unit.notes = existing_notes + claim_note
        unit.status = 'warranty_claim'
        unit.save()
        
        messages.success(request, 'تم تقديم مطالبة الضمان بنجاح! سيتم التواصل معك قريباً.')
        return redirect('production:warranty_success', pk=unit.pk)
    
    return redirect('ecommerce:warranty_check')