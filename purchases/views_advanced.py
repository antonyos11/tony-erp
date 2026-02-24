"""
Views لنظام إدارة المشتريات المتقدم
=====================================
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db.models import Sum, Q, Avg, Min, Max, Count, F
from django.db import transaction
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from decimal import Decimal
from datetime import datetime, timedelta
import json

from .models_advanced import (
    PurchaseRequest, PurchaseRequestItem,
    RFQ, RFQItem, RFQSupplier,
    SupplierQuotation, QuotationItem,
    ProductPriceHistory, SupplierLeadTime,
    Shipment, GoodsReceipt, GoodsReceiptItem
)
from .models import PurchaseOrder, PurchaseOrderItem, PurchaseBill
from partners.models import Partner, SupplierProduct
from inventory.models import Product, Location
from django.contrib.auth.models import User


# =============================
# طلبات الشراء (PR)
# =============================

@login_required
def purchase_request_list(request):
    """قائمة طلبات الشراء"""
    requests = PurchaseRequest.objects.select_related('requested_by', 'approved_by', 'purchase_order')
    
    # الفلترة
    status_filter = request.GET.get('status', '')
    priority_filter = request.GET.get('priority', '')
    search = request.GET.get('search', '')
    
    if status_filter:
        requests = requests.filter(status=status_filter)
    if priority_filter:
        requests = requests.filter(priority=priority_filter)
    if search:
        requests = requests.filter(
            Q(number__icontains=search) |
            Q(department__icontains=search) |
            Q(requested_by__username__icontains=search)
        )
    
    # الإحصائيات
    stats = {
        'total': PurchaseRequest.objects.count(),
        'pending': PurchaseRequest.objects.filter(status='pending').count(),
        'approved': PurchaseRequest.objects.filter(status='approved').count(),
        'urgent': PurchaseRequest.objects.filter(priority='urgent').count(),
    }
    
    context = {
        'requests': requests,
        'stats': stats,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'search': search,
        'status_choices': PurchaseRequest.STATUS_CHOICES,
        'priority_choices': PurchaseRequest.PRIORITY_CHOICES,
    }
    return render(request, 'purchases/pr/list.html', context)


@login_required
def purchase_request_create(request):
    """إنشاء طلب شراء جديد"""
    if request.method == 'POST':
        try:
            with transaction.atomic():
                pr = PurchaseRequest.objects.create(
                    department=request.POST.get('department', ''),
                    requested_by=request.user,
                    date=request.POST.get('date') or timezone.now().date(),
                    required_date=request.POST.get('required_date') or None,
                    priority=request.POST.get('priority', 'normal'),
                    notes=request.POST.get('notes', ''),
                    justification=request.POST.get('justification', ''),
                )

                # إضافة البنود
                items_data = json.loads(request.POST.get('items', '[]'))
                for item_data in items_data:
                    PurchaseRequestItem.objects.create(
                        request=pr,
                        product_id=item_data['product_id'],
                        quantity=Decimal(item_data['quantity']),
                        unit=item_data.get('unit', ''),
                        estimated_price=Decimal(item_data.get('estimated_price', 0)),
                        specifications=item_data.get('specifications', ''),
                        notes=item_data.get('notes', ''),
                    )

                messages.success(request, f'تم إنشاء طلب الشراء {pr.number} بنجاح')
                return redirect('purchases:pr_detail', pk=pr.pk)
        except Exception as e:
            messages.error(request, f'خطأ: {e}')

    # جلب المنتجات مع أسعار الموردين
    products = Product.objects.filter(is_active=True).select_related('category')

    # جلب أسعار الموردين المفضلين
    supplier_prices = {}
    for sp in SupplierProduct.objects.filter(is_active=True, is_preferred=True).select_related('product', 'supplier'):
        supplier_prices[sp.product_id] = {
            'price': float(sp.price),
            'uom': sp.uom,
            'supplier_name': sp.supplier.name,
        }

    # خيارات الوحدات
    uom_choices = Product.UOM_CHOICES

    context = {
        'products': products,
        'supplier_prices': json.dumps(supplier_prices),
        'uom_choices': uom_choices,
    }
    return render(request, 'purchases/pr/form.html', context)


@login_required
def purchase_request_detail(request, pk):
    """تفاصيل طلب شراء"""
    pr = get_object_or_404(PurchaseRequest.objects.select_related('requested_by', 'approved_by', 'purchase_order'), pk=pk)
    items = pr.items.select_related('product')
    
    context = {
        'pr': pr,
        'items': items,
    }
    return render(request, 'purchases/pr/detail.html', context)


@login_required
@permission_required('purchases.change_purchaserequest', raise_exception=True)
def purchase_request_approve(request, pk):
    """اعتماد طلب شراء"""
    pr = get_object_or_404(PurchaseRequest, pk=pk)
    
    if pr.status != 'pending':
        messages.error(request, 'الطلب ليس قيد المراجعة')
        return redirect('purchases:pr_detail', pk=pk)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve':
            pr.status = 'approved'
            pr.approved_by = request.user
            pr.approved_at = timezone.now()
            pr.approval_notes = request.POST.get('approval_notes', '')
            pr.save()
            messages.success(request, f'تم اعتماد طلب الشراء {pr.number}')
        elif action == 'reject':
            pr.status = 'rejected'
            pr.approved_by = request.user
            pr.approved_at = timezone.now()
            pr.approval_notes = request.POST.get('approval_notes', '')
            pr.save()
            messages.warning(request, f'تم رفض طلب الشراء {pr.number}')
        
        return redirect('purchases:pr_detail', pk=pk)
    
    return render(request, 'purchases/pr/approve.html', {'pr': pr})


@login_required
def purchase_request_to_po(request, pk):
    """تحويل طلب شراء إلى أمر شراء"""
    pr = get_object_or_404(PurchaseRequest, pk=pk)
    
    if pr.status != 'approved':
        messages.error(request, 'يجب أن يكون الطلب معتمداً أولاً')
        return redirect('purchases:pr_detail', pk=pk)
    
    if pr.purchase_order:
        messages.info(request, f'تم تحويل هذا الطلب مسبقاً إلى أمر الشراء {pr.purchase_order.number}')
        return redirect('purchases:po_detail', pk=pr.purchase_order.pk)
    
    if request.method == 'POST':
        supplier_id = request.POST.get('supplier')
        location_id = request.POST.get('location')
        
        try:
            with transaction.atomic():
                supplier = get_object_or_404(Supplier, pk=supplier_id)
                location = get_object_or_404(Location, pk=location_id)
                
                # إنشاء أمر الشراء
                po = PurchaseOrder.objects.create(
                    supplier=supplier,
                    date=timezone.now().date(),
                    expected_date=pr.required_date,
                    notes=f'محوّل من طلب الشراء {pr.number}\n{pr.notes}',
                    created_by=request.user,
                )
                
                # نسخ البنود
                for item in pr.items.all():
                    PurchaseOrderItem.objects.create(
                        order=po,
                        product=item.product,
                        location=location,
                        quantity=int(item.quantity),
                        cost=item.estimated_price,
                    )
                
                # تحديث حالة طلب الشراء
                pr.status = 'converted'
                pr.purchase_order = po
                pr.save()
                
                messages.success(request, f'تم تحويل طلب الشراء {pr.number} إلى أمر الشراء {po.number}')
                return redirect('purchases:po_detail', pk=po.pk)
        except Exception as e:
            messages.error(request, f'خطأ: {e}')
    
    suppliers = Partner.objects.filter(partner_type__in=['supplier', 'both'])
    locations = Location.objects.all()

    context = {
        'pr': pr,
        'suppliers': suppliers,
        'locations': locations,
    }
    return render(request, 'purchases/pr/to_po.html', context)


# =============================
# طلب عروض أسعار (RFQ)
# =============================

@login_required
def rfq_list(request):
    """قائمة طلبات عروض الأسعار"""
    rfqs = RFQ.objects.select_related('purchase_request', 'created_by')
    
    status_filter = request.GET.get('status', '')
    search = request.GET.get('search', '')
    
    if status_filter:
        rfqs = rfqs.filter(status=status_filter)
    if search:
        rfqs = rfqs.filter(
            Q(number__icontains=search) |
            Q(title__icontains=search)
        )
    
    context = {
        'rfqs': rfqs,
        'status_filter': status_filter,
        'search': search,
        'status_choices': RFQ.STATUS_CHOICES,
    }
    return render(request, 'purchases/rfq/list.html', context)


@login_required
def rfq_create(request):
    """إنشاء طلب عروض أسعار"""
    if request.method == 'POST':
        try:
            with transaction.atomic():
                rfq = RFQ.objects.create(
                    purchase_request_id=request.POST.get('purchase_request') or None,
                    title=request.POST.get('title'),
                    date=request.POST.get('date') or timezone.now().date(),
                    deadline=request.POST.get('deadline'),
                    terms_conditions=request.POST.get('terms_conditions', ''),
                    payment_terms=request.POST.get('payment_terms', ''),
                    delivery_terms=request.POST.get('delivery_terms', ''),
                    notes=request.POST.get('notes', ''),
                    created_by=request.user,
                )
                
                # إضافة البنود
                items_data = json.loads(request.POST.get('items', '[]'))
                for item_data in items_data:
                    RFQItem.objects.create(
                        rfq=rfq,
                        product_id=item_data['product_id'],
                        quantity=Decimal(item_data['quantity']),
                        unit=item_data.get('unit', ''),
                        specifications=item_data.get('specifications', ''),
                        target_price=Decimal(item_data.get('target_price', 0)) if item_data.get('target_price') else None,
                    )
                
                # إضافة الموردين المدعوين
                supplier_ids = request.POST.getlist('suppliers[]')
                for supplier_id in supplier_ids:
                    RFQSupplier.objects.create(
                        rfq=rfq,
                        supplier_id=supplier_id,
                    )
                
                messages.success(request, f'تم إنشاء طلب عروض الأسعار {rfq.number}')
                return redirect('purchases:rfq_detail', pk=rfq.pk)
        except Exception as e:
            messages.error(request, f'خطأ: {e}')
    
    products = Product.objects.all()
    suppliers = Partner.objects.filter(partner_type__in=['supplier', 'both'])
    purchase_requests = PurchaseRequest.objects.filter(status='approved')
    
    context = {
        'products': products,
        'suppliers': suppliers,
        'purchase_requests': purchase_requests,
    }
    return render(request, 'purchases/rfq/form.html', context)


@login_required
def rfq_detail(request, pk):
    """تفاصيل طلب عروض الأسعار"""
    rfq = get_object_or_404(RFQ.objects.select_related('purchase_request', 'created_by'), pk=pk)
    items = rfq.items.select_related('product')
    invited_suppliers = rfq.invited_suppliers.select_related('supplier')
    quotations = rfq.quotations.select_related('supplier')
    
    context = {
        'rfq': rfq,
        'items': items,
        'invited_suppliers': invited_suppliers,
        'quotations': quotations,
    }
    return render(request, 'purchases/rfq/detail.html', context)


@login_required
def rfq_send(request, pk):
    """إرسال طلب عروض الأسعار للموردين"""
    rfq = get_object_or_404(RFQ, pk=pk)

    if rfq.status != 'draft':
        messages.error(request, 'لا يمكن إرسال طلب عروض أسعار تم إرساله مسبقاً')
        return redirect('purchases:rfq_list')

    # تحديث حالة الطلب إلى "مرسل"
    rfq.status = 'sent'
    rfq.save()

    messages.success(request, f'تم إرسال طلب عروض الأسعار {rfq.number} بنجاح')
    return redirect('purchases:rfq_list')


@login_required
def rfq_edit(request, pk):
    """تعديل طلب عروض الأسعار"""
    rfq = get_object_or_404(RFQ, pk=pk)

    if rfq.status != 'draft':
        messages.error(request, 'لا يمكن تعديل طلب عروض أسعار تم إرساله')
        return redirect('purchases:rfq_detail', pk=pk)

    if request.method == 'POST':
        try:
            with transaction.atomic():
                rfq.title = request.POST.get('title', rfq.title)
                rfq.deadline = request.POST.get('deadline') or rfq.deadline
                rfq.terms_conditions = request.POST.get('terms_conditions', rfq.terms_conditions)
                rfq.payment_terms = request.POST.get('payment_terms', rfq.payment_terms)
                rfq.delivery_terms = request.POST.get('delivery_terms', rfq.delivery_terms)
                rfq.notes = request.POST.get('notes', rfq.notes)
                rfq.save()

                messages.success(request, f'تم تحديث طلب عروض الأسعار {rfq.number}')
                return redirect('purchases:rfq_detail', pk=rfq.pk)
        except Exception as e:
            messages.error(request, f'خطأ: {e}')

    products = Product.objects.all()
    suppliers = Partner.objects.filter(partner_type__in=['supplier', 'both'])
    purchase_requests = PurchaseRequest.objects.filter(status='approved')
    selected_suppliers = list(rfq.invited_suppliers.values_list('supplier_id', flat=True))

    context = {
        'rfq': rfq,
        'products': products,
        'suppliers': suppliers,
        'purchase_requests': purchase_requests,
        'selected_suppliers': selected_suppliers,
    }
    return render(request, 'purchases/rfq/form.html', context)


# =============================
# عروض الموردين ومقارنتها
# =============================

@login_required
def quotation_list(request):
    """قائمة عروض الأسعار"""
    quotations = SupplierQuotation.objects.select_related('rfq', 'supplier', 'evaluated_by')

    status_filter = request.GET.get('status', '')
    supplier_filter = request.GET.get('supplier', '')
    search = request.GET.get('search', '')

    if status_filter:
        quotations = quotations.filter(status=status_filter)
    if supplier_filter:
        quotations = quotations.filter(supplier_id=supplier_filter)
    if search:
        quotations = quotations.filter(
            Q(number__icontains=search) |
            Q(rfq__number__icontains=search)
        )

    suppliers = Partner.objects.filter(partner_type__in=['supplier', 'both'])
    rfqs = RFQ.objects.all()

    # حساب الإحصائيات
    all_quotations = SupplierQuotation.objects.all()
    stats = {
        'total': all_quotations.count(),
        'pending': all_quotations.filter(status__in=['draft', 'submitted', 'under_review']).count(),
        'accepted': all_quotations.filter(status='accepted').count(),
        'converted': all_quotations.filter(status='accepted').exclude(rfq__purchase_request__purchase_order__isnull=True).count(),
    }

    context = {
        'quotations': quotations,
        'status_filter': status_filter,
        'supplier_filter': supplier_filter,
        'search': search,
        'suppliers': suppliers,
        'rfqs': rfqs,
        'status_choices': SupplierQuotation.STATUS_CHOICES,
        'stats': stats,
    }
    return render(request, 'purchases/quotation/list.html', context)


@login_required
def quotation_create(request, rfq_id):
    """إنشاء عرض سعر من مورد"""
    rfq = get_object_or_404(RFQ, pk=rfq_id)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                quotation = SupplierQuotation.objects.create(
                    rfq=rfq,
                    supplier_id=request.POST.get('supplier'),
                    quotation_date=request.POST.get('quotation_date') or timezone.now().date(),
                    valid_until=request.POST.get('valid_until'),
                    payment_terms=request.POST.get('payment_terms', ''),
                    delivery_time=int(request.POST.get('delivery_time', 0)),
                    warranty_period=request.POST.get('warranty_period', ''),
                    shipping_cost=Decimal(request.POST.get('shipping_cost', 0)),
                    tax_amount=Decimal(request.POST.get('tax_amount', 0)),
                    discount=Decimal(request.POST.get('discount', 0)),
                    notes=request.POST.get('notes', ''),
                )
                
                # إضافة بنود العرض
                items_data = json.loads(request.POST.get('items', '[]'))
                for item_data in items_data:
                    QuotationItem.objects.create(
                        quotation=quotation,
                        rfq_item_id=item_data['rfq_item_id'],
                        product_id=item_data['product_id'],
                        quantity=Decimal(item_data['quantity']),
                        unit_price=Decimal(item_data['unit_price']),
                        unit=item_data.get('unit', ''),
                        brand=item_data.get('brand', ''),
                        model=item_data.get('model', ''),
                        specifications=item_data.get('specifications', ''),
                    )
                
                # تحديث حالة الـ RFQSupplier
                RFQSupplier.objects.filter(rfq=rfq, supplier=quotation.supplier).update(quotation_received=True)
                
                messages.success(request, f'تم إنشاء عرض السعر {quotation.number}')
                return redirect('purchases:quotation_detail', pk=quotation.pk)
        except Exception as e:
            messages.error(request, f'خطأ: {e}')
    
    rfq_items = rfq.items.select_related('product')
    suppliers = Partner.objects.filter(partner_type__in=['supplier', 'both'])

    context = {
        'rfq': rfq,
        'rfq_items': rfq_items,
        'suppliers': suppliers,
    }
    return render(request, 'purchases/quotation/form.html', context)


@login_required
def quotation_detail(request, pk):
    """تفاصيل عرض السعر"""
    quotation = get_object_or_404(
        SupplierQuotation.objects.select_related('rfq', 'supplier', 'evaluated_by'),
        pk=pk
    )
    items = quotation.items.select_related('rfq_item', 'product')
    
    context = {
        'quotation': quotation,
        'items': items,
    }
    return render(request, 'purchases/quotation/detail.html', context)


@login_required
def quotation_compare(request, rfq_id):
    """مقارنة عروض الأسعار لـ RFQ معين"""
    rfq = get_object_or_404(RFQ, pk=rfq_id)
    quotations = rfq.quotations.select_related('supplier').prefetch_related('items__product')
    
    # بناء جدول المقارنة
    comparison_data = []
    rfq_items = rfq.items.select_related('product')
    
    for rfq_item in rfq_items:
        item_comparison = {
            'rfq_item': rfq_item,
            'quotations': []
        }
        
        for quotation in quotations:
            quote_item = quotation.items.filter(rfq_item=rfq_item).first()
            item_comparison['quotations'].append({
                'quotation': quotation,
                'item': quote_item,
            })
        
        comparison_data.append(item_comparison)
    
    # حساب إجماليات
    totals = []
    for quotation in quotations:
        totals.append({
            'quotation': quotation,
            'subtotal': quotation.subtotal,
            'total': quotation.total,
        })
    
    context = {
        'rfq': rfq,
        'quotations': quotations,
        'comparison_data': comparison_data,
        'totals': totals,
    }
    return render(request, 'purchases/quotation/compare.html', context)


# =============================
# السجل التاريخي للأسعار
# =============================

@login_required
def product_price_history(request, product_id):
    """السجل التاريخي لأسعار منتج معين"""
    product = get_object_or_404(Product, pk=product_id)
    
    history = ProductPriceHistory.objects.filter(product=product).select_related('supplier')
    
    supplier_filter = request.GET.get('supplier', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    if supplier_filter:
        history = history.filter(supplier_id=supplier_filter)
    if date_from:
        history = history.filter(date__gte=date_from)
    if date_to:
        history = history.filter(date__lte=date_to)
    
    # إحصائيات
    stats = history.aggregate(
        avg_price=Avg('price'),
        min_price=Min('price'),
        max_price=Max('price'),
        total_purchases=Sum('quantity')
    )
    
    # أفضل سعر لكل مورد
    best_prices_by_supplier = history.values('supplier__name').annotate(
        best_price=Min('price'),
        last_price=Max('price', filter=Q(date=Max('date'))),
        total_qty=Sum('quantity')
    ).order_by('best_price')
    
    suppliers = Partner.objects.filter(partner_type__in=['supplier', 'both'])

    context = {
        'product': product,
        'history': history,
        'stats': stats,
        'best_prices_by_supplier': best_prices_by_supplier,
        'suppliers': suppliers,
        'supplier_filter': supplier_filter,
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'purchases/price_history/detail.html', context)


@login_required
def price_comparison_report(request):
    """تقرير مقارنة الأسعار عبر المنتجات"""
    products = Product.objects.all()
    product_filter = request.GET.get('product', '')
    
    if product_filter:
        products = products.filter(pk=product_filter)
    
    comparison_data = []
    for product in products[:50]:  # حد أقصى 50 منتج
        # SQLite لا يدعم DISTINCT ON؛ احصل على أحدث سعر لكل مورد يدوياً
        history_qs = ProductPriceHistory.objects.filter(product=product).select_related('supplier').order_by('supplier_id', '-date', '-id')
        latest_by_supplier = []
        seen_suppliers = set()
        for row in history_qs:
            if row.supplier_id in seen_suppliers:
                continue
            latest_by_supplier.append(row)
            seen_suppliers.add(row.supplier_id)
            if len(latest_by_supplier) >= 5:  # لا نحتاج أكثر من 5 موردين لكل منتج
                break
        
        if latest_by_supplier:
            # قوائم لاحتساب المتوسط والأدنى
            price_values = [p.price for p in latest_by_supplier]
            comparison_data.append({
                'product': product,
                'prices': latest_by_supplier,
                'avg_price': sum(price_values) / len(price_values) if price_values else None,
                'min_price': min(price_values) if price_values else None,
            })
    
    all_products = Product.objects.all()
    
    context = {
        'comparison_data': comparison_data,
        'all_products': all_products,
        'product_filter': product_filter,
    }
    return render(request, 'purchases/price_history/comparison.html', context)


# =============================
# جدول التسليم والشحنات
# =============================

@login_required
def shipment_list(request):
    """قائمة الشحنات"""
    shipments = Shipment.objects.select_related('purchase_order', 'supplier')
    
    status_filter = request.GET.get('status', '')
    search = request.GET.get('search', '')
    
    if status_filter:
        shipments = shipments.filter(status=status_filter)
    if search:
        shipments = shipments.filter(
            Q(number__icontains=search) |
            Q(tracking_number__icontains=search) |
            Q(awb_bl_number__icontains=search)
        )
    
    # الشحنات المتأخرة
    delayed_shipments = shipments.filter(
        estimated_arrival__lt=timezone.now().date(),
        actual_arrival__isnull=True
    ).exclude(status__in=['received', 'cancelled'])
    
    context = {
        'shipments': shipments,
        'delayed_shipments': delayed_shipments,
        'status_filter': status_filter,
        'search': search,
        'status_choices': Shipment.STATUS_CHOICES,
    }
    return render(request, 'purchases/shipment/list.html', context)


@login_required
def shipment_create(request, po_id):
    """إنشاء شحنة لأمر شراء"""
    po = get_object_or_404(PurchaseOrder, pk=po_id)
    
    if request.method == 'POST':
        try:
            shipment = Shipment.objects.create(
                purchase_order=po,
                supplier=po.supplier,
                shipping_method=request.POST.get('shipping_method', ''),
                carrier=request.POST.get('carrier', ''),
                tracking_number=request.POST.get('tracking_number', ''),
                awb_bl_number=request.POST.get('awb_bl_number', ''),
                shipped_date=request.POST.get('shipped_date') or None,
                estimated_arrival=request.POST.get('estimated_arrival') or None,
                shipping_cost=Decimal(request.POST.get('shipping_cost', 0)),
                customs_cost=Decimal(request.POST.get('customs_cost', 0)),
                insurance_cost=Decimal(request.POST.get('insurance_cost', 0)),
                notes=request.POST.get('notes', ''),
            )
            messages.success(request, f'تم إنشاء الشحنة {shipment.number}')
            return redirect('purchases:shipment_detail', pk=shipment.pk)
        except Exception as e:
            messages.error(request, f'خطأ: {e}')
    
    context = {'po': po}
    return render(request, 'purchases/shipment/form.html', context)


@login_required
def shipment_detail(request, pk):
    """تفاصيل الشحنة"""
    shipment = get_object_or_404(Shipment.objects.select_related('purchase_order', 'supplier'), pk=pk)
    
    context = {'shipment': shipment}
    return render(request, 'purchases/shipment/detail.html', context)


@login_required
def shipment_track(request, pk):
    """تتبع الشحنة وتحديث الحالة"""
    shipment = get_object_or_404(Shipment, pk=pk)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        actual_arrival = request.POST.get('actual_arrival') or None
        
        shipment.status = new_status
        if actual_arrival:
            shipment.actual_arrival = actual_arrival
        shipment.notes += f"\n[{timezone.now()}] تحديث الحالة: {new_status}"
        shipment.save()
        
        messages.success(request, 'تم تحديث حالة الشحنة')
        return redirect('purchases:shipment_detail', pk=pk)
    
    context = {
        'shipment': shipment,
        'status_choices': Shipment.STATUS_CHOICES,
    }
    return render(request, 'purchases/shipment/track.html', context)


# =============================
# استلام الواردات
# =============================

@login_required
def goods_receipt_list(request):
    """قائمة سندات الاستلام"""
    receipts = GoodsReceipt.objects.select_related('purchase_order', 'location', 'received_by', 'inspected_by')
    
    status_filter = request.GET.get('status', '')
    quality_filter = request.GET.get('quality_status', '')
    search = request.GET.get('search', '')
    
    if status_filter:
        receipts = receipts.filter(status=status_filter)
    if quality_filter:
        receipts = receipts.filter(quality_status=quality_filter)
    if search:
        receipts = receipts.filter(
            Q(number__icontains=search) |
            Q(purchase_order__number__icontains=search)
        )
    
    context = {
        'receipts': receipts,
        'object_list': receipts,
        'status_filter': status_filter,
        'quality_filter': quality_filter,
        'search': search,
        'status_choices': GoodsReceipt.STATUS_CHOICES,
        'quality_choices': GoodsReceipt.QUALITY_STATUS_CHOICES,
    }
    return render(request, 'purchases/receipt/list.html', context)


@login_required
def goods_receipt_create(request, po_id):
    """إنشاء سند استلام"""
    po = get_object_or_404(PurchaseOrder, pk=po_id)
    po_items = po.items.select_related('product', 'location')
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                receipt = GoodsReceipt.objects.create(
                    purchase_order=po,
                    shipment_id=request.POST.get('shipment') or None,
                    location_id=request.POST.get('location'),
                    received_by=request.user,
                    notes=request.POST.get('notes', ''),
                )
                
                # إضافة البنود
                items_data = json.loads(request.POST.get('items', '[]'))
                for item_data in items_data:
                    GoodsReceiptItem.objects.create(
                        receipt=receipt,
                        purchase_order_item_id=item_data['po_item_id'],
                        product_id=item_data['product_id'],
                        ordered_quantity=Decimal(item_data['ordered_quantity']),
                        received_quantity=Decimal(item_data['received_quantity']),
                        accepted_quantity=Decimal(item_data.get('accepted_quantity', item_data['received_quantity'])),
                        rejected_quantity=Decimal(item_data.get('rejected_quantity', 0)),
                        quality_grade=item_data.get('quality_grade', 'good'),
                        quality_notes=item_data.get('quality_notes', ''),
                        variance_reason=item_data.get('variance_reason', ''),
                    )
                
                messages.success(request, f'تم إنشاء سند الاستلام {receipt.number}')
                return redirect('purchases:receipt_detail', pk=receipt.pk)
        except Exception as e:
            messages.error(request, f'خطأ: {e}')
    
    shipments = Shipment.objects.filter(purchase_order=po)
    locations = Location.objects.all()
    
    context = {
        'po': po,
        'po_items': po_items,
        'shipments': shipments,
        'locations': locations,
    }
    return render(request, 'purchases/receipt/form.html', context)


@login_required
def goods_receipt_detail(request, pk):
    """تفاصيل سند الاستلام"""
    receipt = get_object_or_404(
        GoodsReceipt.objects.select_related('purchase_order', 'location', 'received_by', 'inspected_by'),
        pk=pk
    )
    items = receipt.items.select_related('purchase_order_item', 'product')
    
    context = {
        'receipt': receipt,
        'items': items,
    }
    return render(request, 'purchases/receipt/detail.html', context)


@login_required
def goods_receipt_inspect(request, pk):
    """فحص الجودة لسند الاستلام"""
    receipt = get_object_or_404(GoodsReceipt, pk=pk)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                receipt.inspected_by = request.user
                receipt.inspection_date = timezone.now()
                receipt.inspection_notes = request.POST.get('inspection_notes', '')
                receipt.quality_status = request.POST.get('quality_status')
                receipt.save()
                
                # تحديث بنود الفحص
                items_data = json.loads(request.POST.get('items', '[]'))
                for item_data in items_data:
                    item = receipt.items.get(pk=item_data['item_id'])
                    item.quality_grade = item_data['quality_grade']
                    item.quality_notes = item_data.get('quality_notes', '')
                    item.accepted_quantity = Decimal(item_data['accepted_quantity'])
                    item.rejected_quantity = Decimal(item_data['rejected_quantity'])
                    item.rejection_reason = item_data.get('rejection_reason', '')
                    item.save()
                
                messages.success(request, 'تم حفظ نتائج الفحص')
                return redirect('purchases:receipt_detail', pk=pk)
        except Exception as e:
            messages.error(request, f'خطأ: {e}')
    
    items = receipt.items.select_related('product')
    
    context = {
        'receipt': receipt,
        'items': items,
        'quality_choices': GoodsReceiptItem.QUALITY_CHOICES,
        'quality_status_choices': GoodsReceipt.QUALITY_STATUS_CHOICES,
    }
    return render(request, 'purchases/receipt/inspect.html', context)


# =============================
# تقارير متقدمة
# =============================

@login_required
def supplier_performance_report(request):
    """تقرير أداء الموردين"""
    suppliers = Partner.objects.filter(partner_type__in=['supplier', 'both']).annotate(
        total_orders=Count('purchase_orders'),
        total_quotations=Count('quotations'),
        avg_delivery_time=Avg('quotations__delivery_time'),
        total_shipments=Count('shipments'),
    )
    
    # تفاصيل إضافية لكل مورد
    supplier_data = []
    for supplier in suppliers:
        # معدل التأخير في الشحنات
        delayed_shipments = Shipment.objects.filter(
            supplier=supplier,
            actual_arrival__gt=F('estimated_arrival')
        ).count()
        total_completed_shipments = Shipment.objects.filter(
            supplier=supplier,
            status='received'
        ).count()
        
        delay_rate = (delayed_shipments / total_completed_shipments * 100) if total_completed_shipments > 0 else 0
        
        # معدل رفض الجودة
        total_received = GoodsReceiptItem.objects.filter(
            receipt__purchase_order__supplier=supplier
        ).aggregate(total=Sum('received_quantity'))['total'] or 0
        
        total_rejected = GoodsReceiptItem.objects.filter(
            receipt__purchase_order__supplier=supplier
        ).aggregate(total=Sum('rejected_quantity'))['total'] or 0
        
        rejection_rate = (total_rejected / total_received * 100) if total_received > 0 else 0
        
        supplier_data.append({
            'supplier': supplier,
            'delay_rate': round(delay_rate, 2),
            'rejection_rate': round(rejection_rate, 2),
        })
    
    context = {
        'supplier_data': supplier_data,
    }
    return render(request, 'purchases/reports/supplier_performance.html', context)


@login_required
def purchasing_analytics(request):
    """تحليلات المشتريات"""
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # فلترة حسب التاريخ
    pr_filter = Q()
    po_filter = Q()
    
    if date_from:
        pr_filter &= Q(date__gte=date_from)
        po_filter &= Q(date__gte=date_from)
    if date_to:
        pr_filter &= Q(date__lte=date_to)
        po_filter &= Q(date__lte=date_to)
    
    # إحصائيات طلبات الشراء
    pr_stats = {
        'total': PurchaseRequest.objects.filter(pr_filter).count(),
        'by_status': PurchaseRequest.objects.filter(pr_filter).values('status').annotate(count=Count('id')),
        'by_priority': PurchaseRequest.objects.filter(pr_filter).values('priority').annotate(count=Count('id')),
    }
    
    # إحصائيات أوامر الشراء
    po_stats = {
        'total': PurchaseOrder.objects.filter(po_filter).count(),
        'total_value': PurchaseOrderItem.objects.filter(order__date__gte=date_from if date_from else '2000-01-01').aggregate(
            total=Sum(F('quantity') * F('cost'))
        )['total'] or 0,
        'by_supplier': PurchaseOrder.objects.filter(po_filter).values('supplier__name').annotate(
            count=Count('id'),
            total=Sum(F('items__quantity') * F('items__cost'))
        ).order_by('-total')[:10],
    }
    
    # إحصائيات RFQ والعروض
    rfq_stats = {
        'total_rfqs': RFQ.objects.count(),
        'total_quotations': SupplierQuotation.objects.count(),
        'avg_quotations_per_rfq': SupplierQuotation.objects.values('rfq').annotate(count=Count('id')).aggregate(avg=Avg('count'))['avg'] or 0,
    }
    
    context = {
        'pr_stats': pr_stats,
        'po_stats': po_stats,
        'rfq_stats': rfq_stats,
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'purchases/reports/analytics.html', context)


@login_required
def purchasing_attention(request):
    """لوحة متابعة المشتريات والإنذارات"""
    today = timezone.now().date()
    soon = today + timedelta(days=3)

    rfqs_overdue = RFQ.objects.filter(status__in=['draft', 'sent'], deadline__lt=today)
    rfqs_due_soon = RFQ.objects.filter(status__in=['draft', 'sent'], deadline__gte=today, deadline__lte=soon)
    rfqs_no_quotes = RFQ.objects.annotate(q_count=Count('quotations')).filter(q_count=0)

    quotations_pending = SupplierQuotation.objects.select_related('supplier', 'rfq').filter(status__in=['submitted', 'under_review'])
    quotations_expiring = SupplierQuotation.objects.select_related('supplier', 'rfq').filter(
        status__in=['draft', 'submitted', 'under_review'],
        valid_until__lte=soon
    )

    pos_delayed = PurchaseOrder.objects.filter(status__in=['draft', 'confirmed'], expected_date__lt=today)
    pos_due_soon = PurchaseOrder.objects.filter(status__in=['draft', 'confirmed'], expected_date__gte=today, expected_date__lte=soon)

    shipments_delayed = Shipment.objects.select_related('purchase_order', 'supplier').filter(
        status__in=['pending', 'in_transit', 'customs'],
        estimated_arrival__lt=today
    )
    shipments_due_soon = Shipment.objects.select_related('purchase_order', 'supplier').filter(
        status__in=['pending', 'in_transit', 'customs'],
        estimated_arrival__gte=today,
        estimated_arrival__lte=soon
    )

    receipts_pending_qc = GoodsReceipt.objects.select_related('purchase_order', 'location').filter(quality_status='pending')
    receipts_with_variance = GoodsReceipt.objects.select_related('purchase_order', 'location').filter(status='with_variance')

    context = {
        'rfqs_overdue': rfqs_overdue,
        'rfqs_due_soon': rfqs_due_soon,
        'rfqs_no_quotes': rfqs_no_quotes,
        'quotations_pending': quotations_pending,
        'quotations_expiring': quotations_expiring,
        'pos_delayed': pos_delayed,
        'pos_due_soon': pos_due_soon,
        'shipments_delayed': shipments_delayed,
        'shipments_due_soon': shipments_due_soon,
        'receipts_pending_qc': receipts_pending_qc,
        'receipts_with_variance': receipts_with_variance,
        'today': today,
        'soon': soon,
    }
    return render(request, 'purchases/reports/attention.html', context)


@login_required
@permission_required('purchases.view_purchaserequest', raise_exception=True)
def warehouse_purchase_requests(request):
    """عرض طلبات الشراء الواردة من المخازن (عبر نظام طلبات خامات الإنتاج)"""
    # عرض طلبات الشراء التي تم إنشاؤها من قبل موظفي المخزن
    # أو المرتبطة بطلبات خامات من الإنتاج
    
    # الفلترة
    status_filter = request.GET.get('status', '')
    search = request.GET.get('search', '')
    
    # طلبات الشراء التي أنشأها موظفو المخزن أو مرتبطة بطلبات خامات
    requests = PurchaseRequest.objects.select_related('requested_by', 'approved_by', 'purchase_order')
    
    # فلترة حسب المصدر (طلبات من المخازن)
    # يمكن تحديد ذلك بناءً على القسم أو المستخدم
    warehouse_users = User.objects.filter(
        Q(groups__name__icontains='مخزن') | 
        Q(groups__name__icontains='warehouse') |
        Q(user_permissions__codename__in=['add_stock', 'change_stock'])
    ).distinct()
    
    requests = requests.filter(
        Q(requested_by__in=warehouse_users) |
        Q(department__icontains='مخزن') |
        Q(department__icontains='warehouse')
    )
    
    if status_filter:
        requests = requests.filter(status=status_filter)
    if search:
        requests = requests.filter(
            Q(number__icontains=search) |
            Q(department__icontains=search) |
            Q(requested_by__username__icontains=search)
        )
    
    # الإحصائيات
    stats = {
        'total': requests.count(),
        'pending': requests.filter(status='pending').count(),
        'approved': requests.filter(status='approved').count(),
        'converted': requests.filter(status='converted').count(),
    }
    
    context = {
        'requests': requests,
        'stats': stats,
        'status_filter': status_filter,
        'search': search,
        'status_choices': PurchaseRequest.STATUS_CHOICES,
        'page_title': 'طلبات شراء من المخازن',
    }
    return render(request, 'purchases/pr/warehouse_list.html', context)


# =============================
# Views إضافية لطلبات الشراء
# =============================

@login_required
def purchase_request_edit(request, pk):
    """تعديل طلب شراء"""
    pr = get_object_or_404(PurchaseRequest, pk=pk)
    
    # التحقق من إمكانية التعديل
    if pr.status not in ['pending', 'draft']:
        messages.error(request, 'لا يمكن تعديل طلب شراء تمت الموافقة عليه أو تحويله')
        return redirect('purchases:pr_detail', pk=pk)
    
    if request.method == 'POST':
        pr.department = request.POST.get('department', pr.department)
        pr.notes = request.POST.get('notes', pr.notes)
        pr.priority = request.POST.get('priority', pr.priority)
        pr.required_date = request.POST.get('required_date') or pr.required_date
        pr.save()
        messages.success(request, f'تم تحديث طلب الشراء {pr.number}')
        return redirect('purchases:pr_detail', pk=pk)
    
    context = {
        'pr': pr,
        'items': pr.items.all(),
        'page_title': f'تعديل طلب الشراء {pr.number}',
    }
    return render(request, 'purchases/pr/pr_edit.html', context)


@login_required
def purchase_request_reject(request, pk):
    """رفض طلب شراء"""
    pr = get_object_or_404(PurchaseRequest, pk=pk)
    
    if pr.status != 'pending':
        messages.error(request, 'يمكن رفض الطلبات المعلقة فقط')
        return redirect('purchases:pr_detail', pk=pk)
    
    if request.method == 'POST':
        rejection_reason = request.POST.get('rejection_reason', '')
        pr.status = 'rejected'
        pr.notes = f"{pr.notes}\n\nسبب الرفض: {rejection_reason}".strip()
        pr.approved_by = request.user
        pr.approved_date = timezone.now()
        pr.save()
        messages.success(request, f'تم رفض طلب الشراء {pr.number}')
        return redirect('purchases:pr_list')
    
    context = {
        'pr': pr,
        'page_title': f'رفض طلب الشراء {pr.number}',
    }
    return render(request, 'purchases/pr/pr_reject.html', context)


@login_required
def price_history_list(request):
    """قائمة تاريخ الأسعار"""
    history = ProductPriceHistory.objects.select_related(
        'product', 'supplier'
    ).order_by('-date')[:100]
    
    # فلترة حسب المنتج
    product_id = request.GET.get('product')
    supplier_id = request.GET.get('supplier')
    
    if product_id:
        history = history.filter(product_id=product_id)
    if supplier_id:
        history = history.filter(supplier_id=supplier_id)
    
    # إحصائيات
    products = Product.objects.filter(
        id__in=ProductPriceHistory.objects.values('product_id').distinct()
    )
    suppliers = Partner.objects.filter(
        partner_type__in=['supplier', 'both'],
        id__in=ProductPriceHistory.objects.values('supplier_id').distinct()
    )
    
    context = {
        'history': history,
        'products': products,
        'suppliers': suppliers,
        'selected_product': product_id,
        'selected_supplier': supplier_id,
        'page_title': 'تاريخ الأسعار',
    }
    return render(request, 'purchases/price_history/list.html', context)
