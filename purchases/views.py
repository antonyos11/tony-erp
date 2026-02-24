from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db.models import Sum, Q
from datetime import date
from django.utils import timezone
from .models import (
    PurchaseBill, PurchaseItem, PurchaseOrder, PurchaseOrderItem,
    PurchaseReturn, PurchaseReturnItem,
)
from partners.models import Supplier
from payments.models import PaymentMethod
from inventory.models import Product, Location
from decimal import Decimal
from typing import Optional, Callable, Any
try:
    from accounting.services import post_purchase_bill_journal as _post_purchase_bill_journal
except Exception:  # pragma: no cover
    _post_purchase_bill_journal = None  # type: ignore
PostPurchaseBillJournalType = Callable[..., Any]
post_purchase_bill_journal: Optional[PostPurchaseBillJournalType] = _post_purchase_bill_journal
from django.db import transaction as _txn


@login_required
def purchase_list(request):
    bills = PurchaseBill.objects.select_related('supplier').prefetch_related('items').filter(is_deleted=False)
    search = request.GET.get('search', '')
    if search:
        bills = bills.filter(Q(number__icontains=search) | Q(supplier__name__icontains=search))
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        bills = bills.filter(date__gte=date_from)
    if date_to:
        bills = bills.filter(date__lte=date_to)
    return render(request, 'purchases/purchase_list.html', {
        'bills': bills,
        'search': search,
        'date_from': date_from,
        'date_to': date_to,
    })


@login_required
def purchase_create(request):
    if request.method == 'POST':
        supplier_id = request.POST.get('supplier')
        discount = request.POST.get('discount', 0)
        payment_method_id = request.POST.get('payment_method') or None
        payment_reference = request.POST.get('payment_reference', '').strip()
        try:
            supplier = get_object_or_404(Supplier, pk=supplier_id)
            last_bill = PurchaseBill.objects.order_by('-id').first()
            if last_bill:
                try:
                    last_number = int(str(last_bill.number).split('-')[-1])
                except Exception:
                    last_number = last_bill.id
                new_number = f"PB-{str(last_number + 1).zfill(6)}"
            else:
                new_number = 'PB-000001'
            bill = PurchaseBill.objects.create(
                number=new_number,
                supplier=supplier,
                discount=discount,
                payment_method=PaymentMethod.objects.filter(pk=payment_method_id).first() if payment_method_id else None,
                payment_reference=payment_reference
            )
            messages.success(request, f'تم إنشاء فاتورة الشراء رقم {new_number} بنجاح')
            return redirect('purchases:purchase_detail', pk=bill.pk)
        except Exception as e:
            messages.error(request, f'خطأ في إنشاء فاتورة الشراء: {e}')
    suppliers = Supplier.objects.all()
    products = Product.objects.all()
    locations = Location.objects.all()
    return render(request, 'purchases/purchase_form.html', {
        'suppliers': suppliers,
        'products': products,
        'locations': locations,
    })


@login_required
def purchase_detail(request, pk):
    """Purchase bill detail view with ability to add items (validated)."""
    bill = get_object_or_404(PurchaseBill, pk=pk)
    suppliers = Supplier.objects.all()
    products = Product.objects.filter(is_active=True)[:500]
    locations = Location.objects.all()[:100]
    # Compute if any bill item still has quantity available for return
    has_returnable_items = True
    try:  # lightweight safe computation
        bill_items = list(getattr(bill, 'items', []).all())  # type: ignore[attr-defined]
        if bill_items:
            from django.db.models import Sum
            returned_map = {
                r['bill_item_id']: r['qty'] or 0
                for r in PurchaseReturnItem.objects.filter(bill_item__bill=bill).values('bill_item_id').annotate(qty=Sum('quantity'))
            }
            has_returnable_items = any((getattr(it, 'quantity', 0) - returned_map.get(getattr(it, 'id', None), 0)) > 0 for it in bill_items)
    except Exception:
        pass
    # Collect related purchase returns (latest first)
    if hasattr(bill, 'purchasereturn_set'):
        purchase_returns = list(bill.purchasereturn_set.all().order_by('-id'))
    else:
        purchase_returns = []
    # Build returned quantity map per bill item id
    returned_qty_map = {}
    try:
        from django.db.models import Sum
        rows = (PurchaseReturnItem.objects
                .filter(bill_item__bill=bill)
                .values('bill_item_id')
                .annotate(qty=Sum('quantity')))
        returned_qty_map = {r['bill_item_id']: r['qty'] or 0 for r in rows}
        # Add return info to each item for template
        bill_items = list(getattr(bill, 'items', []).all()) if hasattr(bill, 'items') else []
        for item in bill_items:
            item.returned_qty = returned_qty_map.get(item.id, 0)
            item.remaining_qty = item.quantity - item.returned_qty
    except Exception:
        pass
    return render(request, 'purchases/purchase_detail_new.html', {
        'bill': bill,
        'suppliers': suppliers,
        'products': products,
        'locations': locations,
        'PAYMENT_METHODS': PaymentMethod.objects.all(),
        'has_returnable_items': has_returnable_items,
        'purchase_returns': purchase_returns,
        'returned_qty_map': returned_qty_map,
    })


@login_required
def purchase_delete(request, pk):
    bill = get_object_or_404(PurchaseBill, pk=pk)
    if request.method == 'GET':
        return render(request, 'purchases/purchase_delete_confirm.html', {'bill': bill})
    if request.method != 'POST':
        messages.error(request, 'طلب غير صالح')
        return redirect('purchases:purchase_detail', pk=pk)
    approver = request.user
    reason = (request.POST.get('delete_reason') or '').strip()
    if not reason or len(reason) < 3:
        messages.error(request, 'سبب الحذف مطلوب (3 أحرف على الأقل).')
        return redirect('purchases:purchase_delete', pk=pk)
    # تفويض: superuser أو لديه صلاحية تغيير في المحاسبة
    has_finance_perm = approver.is_superuser or approver.has_perm('accounting.change_chartofaccount') or approver.has_perm('purchases.delete_purchasebill')
    if not has_finance_perm:
        messages.error(request, 'يتطلب الحذف موافقة مدير مالي / مدير.')
        return redirect('purchases:purchase_delete', pk=pk)
    from django.contrib.auth.hashers import check_password
    pwd = request.POST.get('confirm_password','')
    if not pwd or not check_password(pwd, approver.password):
        messages.error(request, 'فشل التحقق من كلمة المرور.')
        return redirect('purchases:purchase_delete', pk=pk)
    try:
        bill.is_deleted = True
        from django.utils import timezone as _tz
        bill.deleted_at = _tz.now()
        bill.deleted_by = approver
        bill.delete_reason = reason
        bill.save(update_fields=['is_deleted','deleted_at','deleted_by','delete_reason'])
        try:
            from core.models import AuditLog
            AuditLog.objects.create(user=approver, action='delete', model_name='PurchaseBill', app_label='purchases', object_id=str(bill.pk), object_repr=str(bill), extra={'delete_reason': reason})
        except Exception:
            pass
        messages.success(request, f'تم حذف فاتورة الشراء {bill.number} (حذف ناعم).')
        return redirect('purchases:purchase_list')
    except Exception as e:
        messages.error(request, f'تعذّر الحذف: {e}')
        return redirect('purchases:purchase_detail', pk=pk)


@login_required
def purchase_edit(request, pk):
    bill = get_object_or_404(PurchaseBill, pk=pk)
    if request.method == 'POST':
        supplier_id = request.POST.get('supplier')
        discount = request.POST.get('discount', 0)
        paid = request.POST.get('paid', 0)
        payment_reference = request.POST.get('payment_reference','').strip()
        try:
            supplier = get_object_or_404(Supplier, pk=supplier_id)
            bill.supplier = supplier
            bill.discount = discount
            bill.paid = paid
            bill.payment_reference = payment_reference
            bill.save()
            messages.success(request, 'تم تحديث الفاتورة بنجاح')
            return redirect('purchases:purchase_detail', pk=pk)
        except Exception as e:
            messages.error(request, f'فشل التحديث: {e}')
    suppliers = Supplier.objects.all()
    return render(request, 'purchases/purchase_edit.html', {'bill': bill, 'suppliers': suppliers, 'PAYMENT_METHODS': PaymentMethod.objects.all()})


@login_required
def purchase_post(request, pk):
    bill = get_object_or_404(PurchaseBill, pk=pk)
    if request.method == 'POST':
        try:
            je = bill.post(user=request.user)
            if je and je.is_posted:
                messages.success(request, f'تم ترحيل الفاتورة {bill.number}')
            else:
                messages.warning(request, 'لم يتم إنشاء قيد محاسبي (تحقق من البيانات).')
        except Exception as e:
            messages.error(request, f'فشل ترحيل الفاتورة: {e}')
    return redirect('purchases:purchase_detail', pk=bill.pk)


from django.db import transaction

@login_required
def purchase_return_start(request):
    """Simple view to pick a purchase bill to create a return for.

    Allows searching by bill number or supplier name. Redirects to existing
    purchase_return_create view which expects a bill_id.
    """
    q = request.GET.get('q','').strip()
    date_from = request.GET.get('date_from') or ''
    date_to = request.GET.get('date_to') or ''
    bills = PurchaseBill.objects.select_related('supplier').filter(is_deleted=False)
    if q:
        bills = bills.filter(Q(number__icontains=q) | Q(supplier__name__icontains=q))
    if date_from:
        bills = bills.filter(date__gte=date_from)
    if date_to:
        bills = bills.filter(date__lte=date_to)
    bills = bills.order_by('-id')[:100]
    if request.method == 'POST':
        bill_id = request.POST.get('bill_id')
        if bill_id and bill_id.isdigit():
            return redirect('purchases:purchase_return_create', bill_id=int(bill_id))
        messages.error(request, 'يرجى اختيار فاتورة صحيحة')
    return render(request, 'purchases/purchase_return_start.html', {'bills': bills, 'q': q, 'date_from': date_from, 'date_to': date_to})

@login_required
def purchase_return_create(request, bill_id):
    bill = get_object_or_404(PurchaseBill, pk=bill_id)
    if request.method == 'POST':
        try:
            with transaction.atomic():
                last = PurchaseReturn.objects.order_by('-id').first()
                seq = (last.id + 1) if last else 1
                pret = PurchaseReturn.objects.create(number=f"PR-{seq:06d}", bill=bill)
                for it in bill.items.all():
                    # Form field name pattern: return_qty_<item.id>
                    raw = request.POST.get(f'return_qty_{it.id}', '0')
                    try:
                        qty = int(raw)
                    except Exception:
                        qty = 0
                    if qty > 0:
                        if qty > it.quantity:
                            raise ValueError('كمية المرتجع أكبر من المشتراة')
                        pritem = PurchaseReturnItem.objects.create(purchase_return=pret, bill_item=it, quantity=qty)
                        pritem.apply_stock()
                messages.success(request, f'تم إنشاء مرتجع الشراء {pret.number}')
                return redirect('purchases:purchase_return_detail', pk=pret.pk)
        except Exception as e:
            messages.error(request, f'خطأ في إنشاء مرتجع الشراء: {e}')
    return render(request, 'purchases/purchase_return_form.html', {'bill': bill})


@login_required
def purchase_return_detail(request, pk):
    pret = get_object_or_404(PurchaseReturn, pk=pk)
    
    # حساب إجمالي المرتجع
    return_total = 0
    try:
        for item in pret.items.all():
            return_total += item.quantity * item.bill_item.cost
    except Exception:
        pass
    
    return render(request, 'purchases/purchase_return_detail_new.html', {
        'pret': pret,
        'return_total': return_total,
    })


@login_required
def purchase_print(request, pk):
    """طباعة فاتورة الشراء - يدعم A4 و 80mm حراري"""
    bill = get_object_or_404(PurchaseBill, pk=pk)
    print_size = request.GET.get('size', 'a4')  # a4 أو pos
    
    # جلب بيانات الشركة
    from core.models import Company
    company = Company.objects.first()
    
    # حساب إجمالي المرتجع
    return_total = 0
    try:
        from django.db.models import Sum
        return_total = PurchaseReturnItem.objects.filter(bill_item__bill=bill).aggregate(
            total=Sum('quantity')
        )['total'] or 0
    except Exception:
        pass
    
    return render(request, 'purchases/purchase_print.html', {
        'bill': bill,
        'company': company,
        'print_size': print_size,
        'printed_by': request.user,
        'supplier_balance_before': getattr(bill.supplier, 'balance', 0),
        'supplier_balance_after': getattr(bill.supplier, 'balance', 0) + (bill.total - bill.paid),
    })


@login_required
def purchase_return_print(request, pk):
    """طباعة مرتجع الشراء - يدعم A4 و 80mm حراري"""
    pret = get_object_or_404(PurchaseReturn, pk=pk)
    print_size = request.GET.get('size', 'a4')
    
    # جلب بيانات الشركة
    from core.models import Company
    company = Company.objects.first()
    
    # حساب إجمالي المرتجع
    return_total = 0
    try:
        for item in pret.items.all():
            item_cost = getattr(item.bill_item, 'cost', 0) or 0
            return_total += item.quantity * item_cost
    except Exception:
        pass
    
    return render(request, 'purchases/purchase_return_print.html', {
        'pret': pret,
        'company': company,
        'print_size': print_size,
        'printed_by': request.user,
        'return_total': return_total,
    })


@login_required
def vendors_statement(request):
    """كشف مجمع للموردين أو كشف مورد مفرد.

    المداخل:
      - supplier: (اختياري) رقم المورد لعرض كشفه مباشرة.
      - date_from/date_to: نطاق تاريخ.
    في حالة عدم اختيار مورد يعرض قائمة الموردين مع أزرار سريعة.
    """
    from django.utils.dateparse import parse_date
    try:
        from accounting.services import build_supplier_statement
    except Exception:
        build_supplier_statement = None  # type: ignore

    supplier_id = request.GET.get('supplier') or ''
    date_from_raw = request.GET.get('date_from') or ''
    date_to_raw = request.GET.get('date_to') or ''
    export = request.GET.get('export') or ''
    want_print = request.GET.get('print') == '1'

    df = parse_date(date_from_raw) if date_from_raw else None
    dt = parse_date(date_to_raw) if date_to_raw else None

    suppliers = Supplier.objects.all().order_by('name')[:500]
    selected_supplier = None
    statement = None
    error = None

    if supplier_id.isdigit():
        selected_supplier = Supplier.objects.filter(pk=int(supplier_id)).first()
        if selected_supplier and build_supplier_statement:
            from django.core.cache import cache
            cache_key = f"vendor_stmt_{selected_supplier.id}_{date_from_raw or 'none'}_{date_to_raw or 'none'}"
            statement = cache.get(cache_key)
            if statement is None:
                try:
                    statement = build_supplier_statement(selected_supplier, date_from=df, date_to=dt)
                    # خزن لمدة 5 دقائق
                    cache.set(cache_key, statement, 300)
                except Exception as e:  # pragma: no cover
                    error = f'تعذر بناء كشف المورد: {e}'
        elif selected_supplier is None:
            error = 'المورد غير موجود'

    # تصدير CSV
    if export == 'csv':
        if not (selected_supplier and statement):
            from django.http import HttpResponse
            resp = HttpResponse('يجب اختيار مورد للتصدير', content_type='text/plain; charset=utf-8')
            resp.status_code = 400
            return resp
        import csv
        from io import StringIO
        buff = StringIO()
        w = csv.writer(buff)
        w.writerow(['Supplier','Date From','Date To'])
        w.writerow([selected_supplier.name, date_from_raw, date_to_raw])
        w.writerow([])
        w.writerow(['Opening Balance', statement.get('opening_balance', '')])
        w.writerow([])
        w.writerow(['Date','Type','Number','Debit','Credit','Balance','Remaining','Description'])
        for row in statement.get('timeline', []):
            w.writerow([
                getattr(row.get('date'), 'isoformat', lambda: row.get('date'))(),
                'BILL' if row.get('type') == 'bill' else 'PAY',
                row.get('number',''),
                row.get('debit') or '',
                row.get('credit') or '',
                row.get('balance') or '',
                row.get('remaining') if row.get('type') == 'bill' else '',
                row.get('description','')
            ])
        w.writerow([])
        aging = statement.get('aging', {}) or {}
        w.writerow(['Aging'])
        w.writerow(['0-30', aging.get('bucket_0_30')])
        w.writerow(['31-60', aging.get('bucket_31_60')])
        w.writerow(['61-90', aging.get('bucket_61_90')])
        w.writerow(['90+', aging.get('bucket_90_plus')])
        w.writerow(['Total', aging.get('total')])
        from django.http import HttpResponse
        resp = HttpResponse(buff.getvalue().encode('utf-8-sig'), content_type='text/csv; charset=utf-8')
        resp['Content-Disposition'] = f'attachment; filename=supplier_statement_{selected_supplier.id}.csv'
        return resp

    ctx = {
        'suppliers': suppliers,
        'selected_supplier': selected_supplier,
        'statement': statement,
        'date_from': date_from_raw,
        'date_to': date_to_raw,
        'error': error,
        'export': export,
        'print': want_print,
    }
    if want_print and selected_supplier and statement:
        return render(request, 'purchases/vendors_statement_print.html', ctx)
    return render(request, 'purchases/vendors_statement.html', ctx)


@login_required
def vendors_balances(request):
    """تقرير أرصدة الموردين (نسخة تعتمد على خدمة compute_vendor_balances)."""
    from purchases.services.vendor_balances import compute_vendor_balances
    from django.core.cache import cache
    q = (request.GET.get('q') or '').strip()
    show_all = request.GET.get('show') == 'all'
    bucket = request.GET.get('bucket') or None
    date_from = request.GET.get('date_from') or ''
    date_to = request.GET.get('date_to') or ''
    sort = request.GET.get('sort') or 'remaining'
    direction = request.GET.get('dir') or 'desc'
    export = request.GET.get('export') or ''
    use_orm = request.GET.get('agg') == '1'
    force_refresh = request.GET.get('refresh') == '1'
    cache_key = f"vendors_balances_v2::{q or '_'}::{show_all}::{bucket or '_'}::{date_from or '_'}::{date_to or '_'}::{sort}::{direction}::{int(use_orm)}"
    context = None
    if not force_refresh and export not in ('csv','xlsx'):
        context = cache.get(cache_key)
    if context is None:
        context = compute_vendor_balances(
            q=q,
            show_all=show_all,
            date_from=date_from,
            date_to=date_to,
            sort=sort,
            direction=direction,
            bucket=bucket,
            use_orm_agg=use_orm,
        )
        cache.set(cache_key, context, 300)
    rows = context['rows']
    if export == 'csv':
        import csv
        from io import StringIO
        from django.http import HttpResponse
        buff = StringIO()
        w = csv.writer(buff)
        w.writerow(['Supplier ID','Supplier Name','Total','Paid','Remaining','Open Bills'])
        for r in rows:
            w.writerow([r['supplier_id'], r['name'], r['total'], r['paid'], r['remaining'], r['open_bills']])
        w.writerow([])
        w.writerow(['Grand Totals','', context['grand_total'], context['grand_paid'], context['grand_remaining'], context['open_bills_total']])
        resp = HttpResponse(buff.getvalue().encode('utf-8-sig'), content_type='text/csv; charset=utf-8')
        resp['Content-Disposition'] = 'attachment; filename=vendors_balances.csv'
        return resp
    if export == 'xlsx':
        try:
            from openpyxl import Workbook  # type: ignore
            from django.http import HttpResponse
            wb = Workbook()
            ws = wb.active
            ws.title = 'Vendors Balances'
            if ws: ws.append(['Supplier ID','Supplier Name','Total','Paid','Remaining','Open Bills','% Remaining'])
            grand_remaining = context['grand_remaining'] or 0
            for r in rows:
                pct = float(r['remaining'] / grand_remaining * 100) if grand_remaining else 0.0
                if ws: ws.append([r['supplier_id'], r['name'], float(r['total']), float(r['paid']), float(r['remaining']), r['open_bills'], pct])
            if ws: ws.append([])
            if ws: ws.append(['Grand Totals','', float(context['grand_total']), float(context['grand_paid']), float(context['grand_remaining']), context['open_bills_total'], 100.0 if grand_remaining else 0.0])
            from io import BytesIO
            buff = BytesIO()
            wb.save(buff)
            resp = HttpResponse(buff.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            resp['Content-Disposition'] = 'attachment; filename=vendors_balances.xlsx'
            return resp
        except Exception as e:
            messages.error(request, f'فشل إنشاء ملف Excel: {e}')
    want_print = request.GET.get('print') == '1'
    if want_print:
        return render(request, 'purchases/vendors_balances_print.html', context)
    return render(request, 'purchases/vendors_balances.html', context)


@login_required
def supplier_payment_create(request, supplier_id=None, bill_id=None):
    """إنشاء دفعة مورد عامة أو مرتبطة بفاتورة (إن تم تمرير bill_id)."""
    from .models import SupplierPayment, PurchaseBill
    supplier = None
    bill = None
    if bill_id:
        bill = get_object_or_404(PurchaseBill, pk=bill_id)
        supplier = bill.supplier
    elif supplier_id:
        supplier = get_object_or_404(Supplier, pk=supplier_id)
    else:
        messages.error(request, 'المورد غير محدد')
        return redirect('purchases:purchase_list')

    if request.method == 'POST':
        try:
            amount = Decimal(request.POST.get('amount') or '0')
            if amount <= 0:
                raise ValueError('المبلغ غير صالح')
            payment_method_id = request.POST.get('payment_method') or None
            reference = (request.POST.get('reference') or '').strip()
            description = (request.POST.get('description') or '').strip()
            sp = SupplierPayment.objects.create(
                supplier=supplier,
                bill=bill,
                amount=amount,
                payment_method=PaymentMethod.objects.filter(pk=payment_method_id).first() if payment_method_id else None,
                reference=reference,
                description=description,
                created_by=request.user if request.user.is_authenticated else None,
            )
            sp.post(user=request.user)
            messages.success(request, f'تم إنشاء دفعة المورد {sp.receipt_number}')
            if bill:
                return redirect('purchases:purchase_detail', pk=bill.pk)
            # محاولة إعادة المستخدم إلى كشف المورد إن وجد رابط سابق
            return redirect('accounting:supplier_statement', supplier_id=supplier.id)
        except Exception as e:
            messages.error(request, f'خطأ في إنشاء الدفعة: {e}')

    ctx = {
        'supplier': supplier,
        'bill': bill,
        'PAYMENT_METHODS': PaymentMethod.objects.all(),
    }
    return render(request, 'purchases/supplier_payment_form.html', ctx)


@login_required
def supplier_payment_new_entry(request):
    """Generic entry point for creating a supplier payment without a predefined supplier.

    Shows a simple supplier selection form then redirects to the existing
    supplier-specific URL which handles the creation logic. This satisfies
    navigation links pointing to /purchases/payments/new.
    """
    from partners.models import Supplier
    suppliers = Supplier.objects.all().order_by('name')[:500]
    if request.method == 'POST':
        supplier_id = request.POST.get('supplier') or ''
        if supplier_id.isdigit():
            return redirect('purchases:supplier_payment_create', supplier_id=int(supplier_id))
        messages.error(request, 'يرجى اختيار مورد صالح')
    return render(request, 'purchases/supplier_payment_new_entry.html', {'suppliers': suppliers})


# =============================
# Purchase Orders (أوامر الشراء)
# =============================

@login_required
def po_list(request):
    orders = PurchaseOrder.objects.select_related('supplier').prefetch_related('items').all()

    status_filter = request.GET.get('status')
    if status_filter in ['draft','confirmed','partial','completed','cancelled']:
        orders = orders.filter(status=status_filter)

    search = request.GET.get('search', '')
    if search:
        orders = orders.filter(
            Q(number__icontains=search) | Q(supplier__name__icontains=search)
        )

    # حساب عدد الأوامر التي تحتاج متابعة (partial أو متأخرة) باستعلام واحد
    from datetime import date as _d
    from django.db.models import Case, When, Value, BooleanField, Q as _Q
    today = _d.today()
    attention_count = (
        PurchaseOrder.objects.filter(status__in=['confirmed','partial'])
        .annotate(
            is_delayed=Case(
                When(_Q(expected_date__lt=today) & ~_Q(status='partial') & _Q(expected_date__isnull=False), then=Value(True)),
                default=Value(False), output_field=BooleanField()
            )
        )
        .filter(_Q(status='partial') | _Q(is_delayed=True))
        .count()
    )

    context = {
        'orders': orders,
        'search': search,
        'status_filter': status_filter,
        'attention_count': attention_count,
    }
    return render(request, 'purchases/po_list.html', context)


@login_required
def po_from_inventory(request):
    """أوامر شراء منشأة من طلبات خامات (معلّمة بـ REQ# في الملاحظات)."""
    orders = PurchaseOrder.objects.select_related('supplier').filter(notes__icontains='REQ#')
    search = request.GET.get('search', '')
    if search:
        orders = orders.filter(Q(number__icontains=search) | Q(supplier__name__icontains=search))
    return render(request, 'purchases/po_list.html', {
        'orders': orders,
        'search': search,
        'status_filter': '',
        'attention_count': None,
        'title': 'طلبات شراء من المخازن',
    })


@login_required
def po_create(request):
    if request.method == 'POST':
        supplier_id = request.POST.get('supplier')
        try:
            supplier = get_object_or_404(Supplier, pk=supplier_id)
            order = PurchaseOrder.objects.create(supplier=supplier)
            messages.success(request, f'تم إنشاء أمر الشراء {order.number}')
            return redirect('purchases:po_detail', pk=order.pk)
        except Exception as e:
            messages.error(request, f'خطأ في إنشاء أمر الشراء: {e}')

    suppliers = Supplier.objects.all()
    products = Product.objects.all()
    locations = Location.objects.all()
    return render(request, 'purchases/po_form.html', {
        'suppliers': suppliers,
        'products': products,
        'locations': locations,
    })


@login_required
def po_detail(request, pk):
    order = get_object_or_404(PurchaseOrder, pk=pk)
    # Detect source requisition from notes pattern: REQ#<id>
    source_requisition = None
    try:
        if order.notes and 'REQ#' in order.notes:
            token = str(order.notes)
            part = token.split('REQ#', 1)[1]
            raw_id = part.split(None, 1)[0].strip().rstrip(':').rstrip('-')
            req_id = int(''.join(ch for ch in raw_id if ch.isdigit()))
            if req_id:
                from inventory.models import Requisition  # local import to avoid circulars
                source_requisition = Requisition.objects.filter(pk=req_id).only('id','number','status').first()
    except Exception:
        source_requisition = None

    if request.method == 'POST' and order.is_editable:
        product_id = request.POST.get('product')
        location_id = request.POST.get('location')
        quantity = int(request.POST.get('quantity', 0))
        cost = float(request.POST.get('cost', 0))

        try:
            product = get_object_or_404(Product, pk=product_id)
            location = get_object_or_404(Location, pk=location_id)

            PurchaseOrderItem.objects.create(
                order=order, product=product, location=location, quantity=quantity, cost=cost
            )
            messages.success(request, 'تم إضافة البند إلى أمر الشراء')
        except Exception as e:
            messages.error(request, f'خطأ في إضافة البند: {e}')

        return redirect('purchases:po_detail', pk=pk)

    products = Product.objects.all()
    locations = Location.objects.all()
    return render(request, 'purchases/po_detail.html', {
        'order': order,
        'products': products,
        'locations': locations,
        'source_requisition': source_requisition,
    })


@login_required
@permission_required('purchases.change_purchaseorder', raise_exception=True)
def po_confirm(request, pk):
    order = get_object_or_404(PurchaseOrder, pk=pk)
    if order.status != 'draft':
        messages.warning(request, 'لا يمكن تأكيد هذا الأمر')
        return redirect('purchases:po_detail', pk=pk)

    order.status = 'confirmed'
    order.save()
    messages.success(request, 'تم تأكيد أمر الشراء')
    return redirect('purchases:po_detail', pk=pk)


@login_required
@permission_required('purchases.add_purchasebill', raise_exception=True)
def po_to_bill(request, pk):
    """Convert a confirmed Purchase Order to a Purchase Bill and copy items (atomic)."""
    order = get_object_or_404(PurchaseOrder, pk=pk)
    if order.status not in ['confirmed','partial']:
        messages.warning(request, 'يجب أن يكون أمر الشراء مؤكد أو في حالة استلام جزئي')
        return redirect('purchases:po_detail', pk=pk)
    if order.status == 'completed':
        messages.info(request, 'تم تنفيذ هذا الأمر بالكامل')
        return redirect('purchases:po_detail', pk=pk)
    if order.bill:
        messages.info(request, 'تم إنشاء فاتورة لهذا الأمر مسبقاً')
        return redirect('purchases:purchase_detail', pk=order.bill.pk)
    try:
        with _txn.atomic():
            last_bill = PurchaseBill.objects.order_by('-id').select_for_update().first()
            if last_bill:
                try:
                    last_no = int(str(last_bill.number).split('-')[-1])
                except Exception:
                    last_no = last_bill.id
                new_bill_no = f"PB-{str(last_no + 1).zfill(6)}"
            else:
                new_bill_no = 'PB-000001'
            bill = PurchaseBill.objects.create(
                number=new_bill_no,
                supplier=order.supplier,
                discount=order.discount,
                date=date.today(),
            )
            items_data = []
            for it in order.items.all():
                items_data.append(PurchaseItem(
                    bill=bill,
                    product=it.product,
                    location=it.location,
                    quantity=it.quantity,
                    cost=it.cost,
                ))
            if items_data:
                PurchaseItem.objects.bulk_create(items_data)
            order.bill = bill
            order.save(update_fields=['bill'])
            try:
                order.refresh_fulfillment_status()
            except Exception:
                pass
            if post_purchase_bill_journal is not None:
                try:
                    je = post_purchase_bill_journal(bill, user=request.user)
                    if je and je.is_posted:
                        messages.success(request, f'تم إنشاء الفاتورة {new_bill_no} وترحيل القيد {getattr(je, "number", je.id)}')
                    else:
                        messages.warning(request, f'تم إنشاء الفاتورة {new_bill_no} لكن لم يُرحل القيد تلقائياً')
                except Exception as e:
                    messages.error(request, f'تم إنشاء الفاتورة لكن حدث خطأ في الترحيل المحاسبي: {e}')
            else:
                messages.success(request, f'تم إنشاء فاتورة الشراء رقم {new_bill_no} من أمر الشراء')
    except Exception as ex:
        messages.error(request, f'فشل تحويل الأمر إلى فاتورة: {ex}')
        return redirect('purchases:po_detail', pk=pk)
    return redirect('purchases:purchase_detail', pk=bill.pk)


# =============================
# تقارير / لوحات متابعة
# =============================
@login_required
@permission_required('purchases.view_purchaseorder', raise_exception=True)
def po_attention(request):
    """أوامر الشراء التي تحتاج متابعة: استلام جزئي أو مؤكد وتجاوز التاريخ المتوقع."""
    if not request.user.has_perm('purchases.view_purchaseorder'):
        return redirect('login')
    today = date.today()
    from django.db.models import BooleanField, Case, When, Value, Q as _Q
    base = (
        PurchaseOrder.objects.select_related('supplier')
        .filter(status__in=['confirmed','partial'])
        .annotate(
            is_delayed=Case(
                When(_Q(expected_date__lt=today) & ~_Q(status='partial') & _Q(expected_date__isnull=False), then=Value(True)),
                default=Value(False), output_field=BooleanField()
            ),
            is_partial=Case(
                When(status='partial', then=Value(True)),
                default=Value(False), output_field=BooleanField()
            )
        )
        .filter(_Q(is_delayed=True) | _Q(is_partial=True))
        .prefetch_related('items')
    )
    orders = list(base)
    export = request.GET.get('export')
    if export == 'csv':
        import csv
        from io import StringIO
        buff = StringIO()
        w = csv.writer(buff)
        w.writerow(['Number','Supplier','Date','Expected','Status','Total','Reason'])
        for po in orders:
            reason = 'PARTIAL' if po.status == 'partial' else ('DELAYED' if po.is_delayed else '')
            w.writerow([
                po.number,
                po.supplier.name if po.supplier else '',
                po.date.isoformat(),
                po.expected_date.isoformat() if po.expected_date else '',
                po.status,
                float(po.total or 0),
                reason
            ])
        from django.http import HttpResponse
        resp = HttpResponse(buff.getvalue().encode('utf-8-sig'), content_type='text/csv; charset=utf-8')
        resp['Content-Disposition'] = 'attachment; filename=po_attention.csv'
        return resp
    return render(request, 'purchases/po_attention.html', {'orders': orders, 'today': today})


@login_required
@permission_required('purchases.change_purchaseorder', raise_exception=True)
def po_receive(request, pk):
    """استلام جزئي أو كامل مع تحقق وحدات متبقية (نسخة منسقة)."""
    order = get_object_or_404(PurchaseOrder, pk=pk)
    if order.status in ['cancelled', 'completed']:
        messages.warning(request, 'لا يمكن الاستلام لهذا الأمر.')
        return redirect('purchases:po_detail', pk=pk)
    bill = order.bill
    if not bill:
        bill = PurchaseBill.objects.create(
            supplier=order.supplier,
            discount=order.discount,
            date=date.today(),
        )
        order.bill = bill
        order.save(update_fields=['bill'])
    order_items = list(order.items.select_related('product', 'location'))
    bill_items = list(bill.items.all())
    received_map = {}
    for bi in bill_items:
        key = (bi.product_id, bi.location_id)
        received_map[key] = received_map.get(key, 0) + bi.quantity
    rows = []
    for oi in order_items:
        key = (oi.product_id, oi.location_id)
        rec = received_map.get(key, 0)
        remaining = max(oi.quantity - rec, 0)
        rows.append({'item': oi, 'received': rec, 'remaining': remaining})
    if request.method == 'POST':
        try:
            with _txn.atomic():
                per_item_changes = {}
                any_added = False
                for r in rows:
                    raw = (request.POST.get(f'receive_{r["item"].id}', '') or '').strip()
                    if raw == '':
                        continue
                    try:
                        add_qty = int(raw)
                    except Exception:
                        raise ValueError('قيمة غير صالحة')
                    if add_qty < 0:
                        raise ValueError('كمية سالبة')
                    if add_qty == 0:
                        continue
                    if add_qty > r['remaining']:
                        raise ValueError(f"الكمية المدخلة للبند {r['item'].product} تتجاوز المتبقي")
                    PurchaseItem.objects.create(
                        bill=bill,
                        product=r['item'].product,
                        location=r['item'].location,
                        quantity=add_qty,
                        cost=r['item'].cost,
                    )
                    per_item_changes[str(r['item'].id)] = {'product': str(r['item'].product), 'added': add_qty}
                    any_added = True
                if any_added:
                    try:
                        from core.models import AuditLog
                        AuditLog.objects.create(
                            user=request.user,
                            action='update',
                            model_name='PurchaseOrder',
                            app_label='purchases',
                            object_id=str(order.pk),
                            object_repr=str(order),
                            changes={'received_now': per_item_changes}
                        )
                    except Exception:
                        pass
                    order.refresh_fulfillment_status(user=request.user)
                    messages.success(request, 'تم تسجيل الاستلام.')
                else:
                    messages.info(request, 'لم تُدخل أية كميات.')
            return redirect('purchases:po_receive', pk=order.pk)
        except Exception as e:
            messages.error(request, f'فشل الاستلام: {e}')
            return redirect('purchases:po_receive', pk=order.pk)
    return render(request, 'purchases/po_receive.html', {'order': order, 'rows': rows, 'bill': bill})


# ============================================================================
# Purchase Requisitions (PR) Views
# ============================================================================

from .models import PurchaseRequisition, PurchaseRequisitionItem


@login_required
def pr_list(request):
    """قائمة طلبات الشراء"""
    prs = PurchaseRequisition.objects.select_related(
        'requested_by', 'approved_by', 'purchase_order'
    ).prefetch_related('items').all()
    
    # Filters
    search = request.GET.get('search', '')
    if search:
        prs = prs.filter(
            Q(number__icontains=search) |
            Q(department__icontains=search) |
            Q(requested_by__username__icontains=search)
        )
    
    status_filter = request.GET.get('status', '')
    if status_filter:
        prs = prs.filter(status=status_filter)
    
    priority_filter = request.GET.get('priority', '')
    if priority_filter:
        prs = prs.filter(priority=priority_filter)
    
    # Stats
    stats = {
        'total': PurchaseRequisition.objects.count(),
        'draft': PurchaseRequisition.objects.filter(status='draft').count(),
        'submitted': PurchaseRequisition.objects.filter(status='submitted').count(),
        'under_review': PurchaseRequisition.objects.filter(status='under_review').count(),
        'approved': PurchaseRequisition.objects.filter(status='approved').count(),
        'rejected': PurchaseRequisition.objects.filter(status='rejected').count(),
        'converted': PurchaseRequisition.objects.filter(status='converted').count(),
    }
    
    context = {
        'requests': prs,
        'search': search,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'status_choices': PurchaseRequisition.STATUS_CHOICES,
        'priority_choices': PurchaseRequisition.PRIORITY_CHOICES,
        'stats': stats,
    }
    return render(request, 'purchases/pr/pr_list.html', context)


@login_required
def pr_create(request):
    """إنشاء طلب شراء جديد"""
    if request.method == 'POST':
        try:
            with _txn.atomic():
                pr = PurchaseRequisition.objects.create(
                    department=request.POST.get('department', ''),
                    requested_by=request.user,
                    required_date=request.POST.get('required_date') or None,
                    priority=request.POST.get('priority', 'normal'),
                    justification=request.POST.get('justification', ''),
                    notes=request.POST.get('notes', ''),
                )
                
                # Add items
                product_ids = request.POST.getlist('product_id[]')
                location_ids = request.POST.getlist('location_id[]')
                quantities = request.POST.getlist('quantity[]')
                estimated_prices = request.POST.getlist('estimated_price[]')
                item_notes = request.POST.getlist('item_notes[]')
                
                for i, product_id in enumerate(product_ids):
                    if not product_id or not quantities[i]:
                        continue
                    
                    product = Product.objects.get(id=product_id)
                    location = Location.objects.get(id=location_ids[i])
                    
                    # Get current stock
                    from inventory.models import Stock
                    stock = Stock.objects.filter(
                        product=product,
                        location=location
                    ).first()
                    current_stock = stock.quantity if stock else Decimal('0')
                    
                    PurchaseRequisitionItem.objects.create(
                        requisition=pr,
                        product=product,
                        location=location,
                        quantity=int(quantities[i]),
                        estimated_price=Decimal(estimated_prices[i]) if estimated_prices[i] else None,
                        current_stock=current_stock,
                        notes=item_notes[i] if i < len(item_notes) else ''
                    )
                
                messages.success(request, f'تم إنشاء طلب الشراء {pr.number} بنجاح')
                return redirect('purchases:pr_detail', pk=pr.pk)
        
        except Exception as e:
            messages.error(request, f'خطأ: {str(e)}')
    
    products = Product.objects.filter(is_active=True)
    locations = Location.objects.all()
    
    context = {
        'products': products,
        'locations': locations,
        'priority_choices': PurchaseRequisition.PRIORITY_CHOICES,
    }
    return render(request, 'purchases/pr/pr_create.html', context)


@login_required
def pr_detail(request, pk):
    """تفاصيل طلب شراء"""
    pr = get_object_or_404(
        PurchaseRequisition.objects.select_related(
            'requested_by', 'reviewed_by', 'approved_by', 'rejected_by',
            'converted_by', 'purchase_order'
        ).prefetch_related('items__product', 'items__location'),
        pk=pk
    )
    
    context = {
        'pr': pr,
        'can_edit': pr.is_editable and (request.user == pr.requested_by or request.user.is_staff),
        'can_submit': pr.status == 'draft' and (request.user == pr.requested_by or request.user.is_staff),
        'can_review': request.user.has_perm('purchases.can_review_pr') and pr.status in ['submitted', 'under_review'],
        'can_approve': request.user.has_perm('purchases.can_approve_pr') and pr.can_be_approved,
        'can_convert': request.user.has_perm('purchases.can_convert_pr_to_po') and pr.status == 'approved' and not pr.purchase_order,
    }
    return render(request, 'purchases/pr/pr_detail.html', context)


@login_required
def pr_submit(request, pk):
    """تقديم طلب للمراجعة"""
    pr = get_object_or_404(PurchaseRequisition, pk=pk)
    
    if request.user != pr.requested_by and not request.user.is_staff:
        messages.error(request, 'غير مصرح لك بتقديم هذا الطلب')
        return redirect('purchases:pr_detail', pk=pk)
    
    if pr.submit(request.user):
        messages.success(request, 'تم تقديم الطلب للمراجعة')
    else:
        messages.error(request, 'لا يمكن تقديم الطلب في حالته الحالية')
    
    return redirect('purchases:pr_detail', pk=pk)


@login_required
@permission_required('purchases.can_review_pr', raise_exception=True)
def pr_review(request, pk):
    """مراجعة طلب شراء"""
    pr = get_object_or_404(PurchaseRequisition, pk=pk)
    
    if request.method == 'POST':
        notes = request.POST.get('review_notes', '')
        if pr.review(request.user, notes):
            messages.success(request, 'تمت مراجعة الطلب')
        else:
            messages.error(request, 'لا يمكن مراجعة الطلب في حالته الحالية')
        return redirect('purchases:pr_detail', pk=pk)
    
    return render(request, 'purchases/pr/pr_review.html', {'pr': pr})


@login_required
@permission_required('purchases.can_approve_pr', raise_exception=True)
def pr_approve(request, pk):
    """اعتماد طلب شراء"""
    pr = get_object_or_404(PurchaseRequisition, pk=pk)
    
    if request.method == 'POST':
        notes = request.POST.get('approval_notes', '')
        if pr.approve(request.user, notes):
            messages.success(request, 'تم اعتماد الطلب')
        else:
            messages.error(request, 'لا يمكن اعتماد الطلب في حالته الحالية')
        return redirect('purchases:pr_detail', pk=pk)
    
    return render(request, 'purchases/pr/pr_approve.html', {'pr': pr})


@login_required
@permission_required('purchases.can_approve_pr', raise_exception=True)
def pr_reject(request, pk):
    """رفض طلب شراء"""
    pr = get_object_or_404(PurchaseRequisition, pk=pk)
    
    if request.method == 'POST':
        reason = request.POST.get('rejection_reason', '')
        if not reason:
            messages.error(request, 'يجب إدخال سبب الرفض')
            return redirect('purchases:pr_detail', pk=pk)
        
        if pr.reject(request.user, reason):
            messages.success(request, 'تم رفض الطلب')
        else:
            messages.error(request, 'لا يمكن رفض الطلب في حالته الحالية')
        return redirect('purchases:pr_detail', pk=pk)
    
    return render(request, 'purchases/pr/pr_reject.html', {'pr': pr})


@login_required
@permission_required('purchases.can_convert_pr_to_po', raise_exception=True)
def pr_to_po(request, pk):
    """تحويل طلب شراء لأمر شراء"""
    pr = get_object_or_404(PurchaseRequisition, pk=pk)
    
    if pr.status != 'approved':
        messages.error(request, 'يجب اعتماد الطلب أولاً')
        return redirect('purchases:pr_detail', pk=pk)
    
    if pr.purchase_order:
        messages.info(request, 'تم تحويل هذا الطلب بالفعل')
        return redirect('purchases:po_detail', pk=pr.purchase_order.pk)
    
    if request.method == 'POST':
        supplier_id = request.POST.get('supplier')
        if not supplier_id:
            messages.error(request, 'يجب اختيار مورد')
            return redirect('purchases:pr_to_po', pk=pk)
        
        supplier = get_object_or_404(Supplier, pk=supplier_id)
        
        try:
            po = pr.convert_to_po(request.user, supplier)
            if po:
                messages.success(request, f'تم تحويل الطلب لأمر شراء {po.number}')
                return redirect('purchases:po_detail', pk=po.pk)
            else:
                messages.error(request, 'فشل التحويل')
        except Exception as e:
            messages.error(request, f'خطأ: {str(e)}')
        
        return redirect('purchases:pr_detail', pk=pk)
    
    suppliers = Supplier.objects.filter(is_active=True)
    context = {
        'pr': pr,
        'suppliers': suppliers,
    }
    return render(request, 'purchases/pr/pr_to_po.html', context)


@login_required
def warehouse_purchase_requests(request):
    """طلبات شراء من المخازن فقط"""
    # Filter PRs where requested_by is a warehouse staff
    # For now, show all PRs - can be enhanced with role filtering
    prs = PurchaseRequisition.objects.select_related(
        'requested_by', 'approved_by', 'purchase_order'
    ).filter(
        department__icontains='مخزن'  # Simple filter, can be enhanced
    ) | PurchaseRequisition.objects.filter(
        requested_by__groups__name__icontains='warehouse'
    )
    
    # Apply same filters as pr_list
    search = request.GET.get('search', '')
    if search:
        prs = prs.filter(
            Q(number__icontains=search) |
            Q(department__icontains=search) |
            Q(requested_by__username__icontains=search)
        )
    
    status_filter = request.GET.get('status', '')
    if status_filter:
        prs = prs.filter(status=status_filter)
    
    prs = prs.distinct()
    
    stats = {
        'total': prs.count(),
        'pending': prs.filter(status__in=['submitted', 'under_review']).count(),
        'approved': prs.filter(status='approved').count(),
        'converted': prs.filter(status='converted').count(),
    }
    
    context = {
        'requests': prs,
        'search': search,
        'status_filter': status_filter,
        'status_choices': PurchaseRequisition.STATUS_CHOICES,
        'stats': stats,
    }
    return render(request, 'purchases/pr/warehouse_list.html', context)


@login_required
def supplier_material_prices(request):
    """أسعار المواد الخام لكل مورد"""
    from inventory.models import SupplierProductPrice
    from partners.models import Partner
    from django.db.models import Count, Avg, Min, Max

    # جلب جميع الموردين مع عدد المنتجات
    suppliers = Supplier.objects.annotate(
        products_count=Count('product_prices', distinct=True)
    ).order_by('name')

    # فلترة حسب المورد
    supplier_filter = request.GET.get('supplier', '')
    if supplier_filter:
        suppliers = suppliers.filter(id=supplier_filter)

    # بناء بيانات الموردين ومنتجاتهم
    supplier_data = []
    for supplier in suppliers:
        # جلب أسعار المنتجات لهذا المورد (بما في ذلك الأسعار غير المرتبطة بمنتج)
        from django.db.models import Q
        prices = SupplierProductPrice.objects.filter(
            Q(product__product_type='raw_material') | Q(product__isnull=True),
            supplier=supplier
        ).select_related('product', 'product__category').order_by('product__name', 'material_name')

        # فلترة حسب الحالة
        status_filter = request.GET.get('status', '')
        if status_filter == 'active':
            prices = prices.filter(is_active=True)
        elif status_filter == 'inactive':
            prices = prices.filter(is_active=False)

        # إحصائيات
        stats = prices.aggregate(
            avg_price=Avg('cost'),
            min_price=Min('cost'),
            max_price=Max('cost'),
            total_products=Count('id')
        )

        if prices.exists():
            supplier_data.append({
                'supplier': supplier,
                'prices': prices,
                'stats': stats,
            })

    # جلب جميع الموردين للفلتر
    all_suppliers = Supplier.objects.order_by('name')

    context = {
        'supplier_data': supplier_data,
        'all_suppliers': all_suppliers,
        'supplier_filter': supplier_filter,
        'status_filter': request.GET.get('status', ''),
    }
    return render(request, 'purchases/supplier_material_prices.html', context)


@login_required
def supplier_price_create(request):
    """إضافة سعر جديد للمنتج من مورد"""
    from .forms import SupplierProductPriceForm
    from inventory.models import SupplierProductPrice, PackagingUnit, Product

    # دعم التحديد المسبق للمادة الخام عند الإحالة من صفحة المادة الخام
    initial_product_id = request.GET.get('product', '')
    initial_product = None
    if initial_product_id:
        try:
            initial_product = Product.objects.get(
                pk=int(initial_product_id),
                product_type='raw_material'
            )
        except (Product.DoesNotExist, ValueError):
            pass

    if request.method == 'POST':
        form = SupplierProductPriceForm(request.POST)
        if form.is_valid():
            supplier = form.cleaned_data['supplier']
            material_mode = form.cleaned_data.get('material_mode', 'existing')
            product = form.cleaned_data.get('product')
            new_material_name = form.cleaned_data.get('new_material_name', '')
            purchase_unit = form.cleaned_data['purchase_unit']
            cost = form.cleaned_data['cost']

            # التحقق من عدم وجود سعر مكرر
            existing = None
            if material_mode == 'existing' and product:
                existing = SupplierProductPrice.objects.filter(
                    product=product, supplier=supplier
                ).first()
            elif material_mode == 'new' and new_material_name:
                existing = SupplierProductPrice.objects.filter(
                    material_name=new_material_name, supplier=supplier, product__isnull=True
                ).first()

            if existing:
                messages.warning(request, f'هذا السعر موجود بالفعل لهذا المورد. يمكنك تعديله من هنا.')
                return redirect('purchases:supplier_price_edit', pk=existing.pk)

            # إنشاء سعر المورد
            try:
                SupplierProductPrice.objects.create(
                    product=product if material_mode == 'existing' else None,
                    material_name=new_material_name if material_mode == 'new' else '',
                    supplier=supplier,
                    cost=cost,
                    purchase_unit=purchase_unit,
                    currency='EGP',
                    is_active=True,
                )
            except Exception as e:
                messages.error(request, f'حدث خطأ أثناء الحفظ: {str(e)}')
                return redirect('purchases:supplier_material_prices')

            uom_display = dict(Product.UOM_CHOICES).get(purchase_unit, purchase_unit)
            display_name = product.name if material_mode == 'existing' and product else new_material_name
            messages.success(request, f'✅ تم إضافة {display_name} بسعر {cost} ج.م/{uom_display} من {supplier.name}')
            # إذا جاء من صفحة المادة الخام، ارجع إليها
            return_to = request.POST.get('return_to', '')
            if return_to:
                return redirect(return_to)
            return redirect('purchases:supplier_material_prices')
    else:
        # تحديد مسبق للمادة الخام إذا وُجدت
        initial = {}
        if initial_product:
            initial['product'] = initial_product
        form = SupplierProductPriceForm(initial=initial)

    context = {
        'form': form,
        'title': 'إضافة سعر مورد جديد',
        'initial_product': initial_product,
    }
    return render(request, 'purchases/supplier_price_form.html', context)


@login_required
def supplier_price_edit(request, pk):
    """تعديل سعر المنتج من مورد"""
    from .forms import SupplierProductPriceForm
    from inventory.models import SupplierProductPrice, PackagingUnit, Product
    import logging
    logger = logging.getLogger(__name__)

    price_obj = get_object_or_404(SupplierProductPrice, pk=pk)

    if request.method == 'POST':
        form = SupplierProductPriceForm(request.POST)
        if form.is_valid():
            old_cost = price_obj.cost
            supplier = form.cleaned_data['supplier']
            material_mode = form.cleaned_data.get('material_mode', 'existing')
            product = form.cleaned_data.get('product')
            new_material_name = form.cleaned_data.get('new_material_name', '')
            purchase_unit = form.cleaned_data['purchase_unit']
            cost = form.cleaned_data['cost']

            # تحديث السعر مباشرة في قاعدة البيانات
            try:
                SupplierProductPrice.objects.filter(pk=pk).update(
                    supplier=supplier,
                    product=product if material_mode == 'existing' else None,
                    material_name=new_material_name if material_mode == 'new' else '',
                    cost=cost,
                    purchase_unit=purchase_unit,
                )
                # إعادة تحميل الكائن وحفظه لتنفيذ التحديثات المرتبطة
                price_obj.refresh_from_db()
                price_obj.save()
            except Exception as e:
                logger.error(f'Error saving supplier price {pk}: {e}')
                messages.error(request, f'حدث خطأ أثناء الحفظ: {str(e)}')
                return redirect('purchases:supplier_material_prices')

            uom_display = dict(Product.UOM_CHOICES).get(purchase_unit, purchase_unit)
            display_name = product.name if material_mode == 'existing' and product else new_material_name
            success_msg = f'✅ تم تحديث {display_name}'
            if old_cost != cost:
                success_msg += f' (من {old_cost} إلى {cost} ج.م/{uom_display})'

            messages.success(request, success_msg)
            return redirect('purchases:supplier_material_prices')
        else:
            logger.warning(f'Form validation errors for price {pk}: {form.errors}')
    else:
        initial_data = {
            'supplier': price_obj.supplier_id,
            'purchase_unit': price_obj.purchase_unit,
            'cost': price_obj.cost,
        }
        if price_obj.product:
            initial_data['material_mode'] = 'existing'
            initial_data['product'] = price_obj.product_id
        else:
            initial_data['material_mode'] = 'new'
            initial_data['new_material_name'] = price_obj.material_name
            
        form = SupplierProductPriceForm(initial=initial_data)

    display_name = price_obj.product.name if price_obj.product else price_obj.material_name
    context = {
        'form': form,
        'title': f'تعديل سعر {display_name}',
        'price': price_obj,
    }
    return render(request, 'purchases/supplier_price_form.html', context)


@login_required
def supplier_price_delete(request, pk):
    """حذف سعر مورد مع تحذير إذا المادة مرتبطة بـ BOM"""
    from inventory.models import SupplierProductPrice, Stock
    from production.models import BOMItem, BillOfMaterials
    from django.db.models import Sum

    price_obj = get_object_or_404(SupplierProductPrice, pk=pk)

    if request.method == 'POST':
        product_name = price_obj.product.name if price_obj.product else price_obj.material_name
        supplier_name = price_obj.supplier.name if price_obj.supplier else 'غير معروف'
        price_obj.delete()
        messages.success(request, f'✅ تم حذف سعر "{product_name}" من المورد "{supplier_name}" بنجاح')
        return redirect('purchases:supplier_material_prices')

    # GET - عرض صفحة التأكيد مع التحذيرات
    warnings = []

    if price_obj.product:
        # 1. فحص ارتباط المادة بـ BOM
        bom_items = BOMItem.objects.filter(
            material=price_obj.product
        ).select_related('bom', 'bom__product')

        if bom_items.exists():
            bom_list = []
            for item in bom_items:
                bom_name = item.bom.product.name if item.bom and item.bom.product else str(item.bom)
                bom_list.append({
                    'name': bom_name,
                    'quantity': item.quantity,
                })
            warnings.append({
                'severity': 'danger',
                'icon': 'fas fa-industry',
                'title': f'هذه المادة مستخدمة في {len(bom_list)} قائمة مواد (BOM)',
                'message': 'حذف السعر قد يؤثر على حساب تكاليف المنتجات التالية:',
                'items': bom_list,
            })

        # 2. فحص هل هذا المورد الوحيد
        other_prices = SupplierProductPrice.objects.filter(
            product=price_obj.product, is_active=True
        ).exclude(pk=pk).count()

        if other_prices == 0:
            warnings.append({
                'severity': 'warning',
                'icon': 'fas fa-exclamation-triangle',
                'title': 'هذا هو المورد الوحيد لهذه المادة!',
                'message': 'لن يكون هناك سعر مرجعي بعد الحذف. قد تحتاج لإضافة مورد بديل أولاً.',
                'items': [],
            })

        # 3. فحص هل المورد مفضل
        if hasattr(price_obj.product, 'preferred_supplier') and price_obj.product.preferred_supplier == price_obj.supplier:
            warnings.append({
                'severity': 'warning',
                'icon': 'fas fa-star',
                'title': 'هذا هو المورد المفضل لهذه المادة!',
                'message': 'ستحتاج لتعيين مورد مفضل جديد بعد الحذف.',
                'items': [],
            })

        # 4. فحص المخزون الحالي
        total_stock = Stock.objects.filter(
            product=price_obj.product, quantity__gt=0
        ).aggregate(total=Sum('quantity'))['total'] or 0

        if total_stock > 0:
            warnings.append({
                'severity': 'info',
                'icon': 'fas fa-boxes',
                'title': f'يوجد مخزون حالي: {total_stock} وحدة',
                'message': 'حذف السعر لن يؤثر على المخزون الحالي، لكن لن يكون هناك سعر مرجعي من هذا المورد.',
                'items': [],
            })

    context = {
        'price': price_obj,
        'warnings': warnings,
        'has_critical_warnings': any(w['severity'] == 'danger' for w in warnings),
        'title': 'حذف سعر مورد',
    }
    return render(request, 'purchases/supplier_price_delete_confirm.html', context)


@login_required
def api_supplier_materials(request):
    """
    AJAX: جلب المواد الخام وأسعارها لمورد محدد
    GET ?supplier_id=X  → قائمة المواد + أسعارها
    GET ?supplier_id=X&product_id=Y → سعر مادة محددة
    """
    from django.http import JsonResponse
    from inventory.models import SupplierProductPrice, Product

    supplier_id = request.GET.get('supplier_id', '')
    product_id = request.GET.get('product_id', '')

    if not supplier_id:
        return JsonResponse({'error': 'supplier_id required'}, status=400)

    try:
        sup_id = int(supplier_id)
    except ValueError:
        return JsonResponse({'error': 'invalid supplier_id'}, status=400)

    # إذا طُلب سعر مادة محددة
    if product_id:
        try:
            sp = SupplierProductPrice.objects.select_related('product').get(
                supplier_id=sup_id, product_id=int(product_id)
            )
            return JsonResponse({
                'cost': str(sp.cost),
                'purchase_unit': sp.purchase_unit,
                'conversion_to_base': str(sp.conversion_to_base or '1'),
                'currency': sp.currency,
            })
        except SupplierProductPrice.DoesNotExist:
            return JsonResponse({'cost': '', 'purchase_unit': 'unit'})

    # جلب كل المواد المتاحة من هذا المورد (لها أسعار مسجلة)
    prices = SupplierProductPrice.objects.filter(
        supplier_id=sup_id,
        product__product_type='raw_material',
        is_active=True,
    ).select_related('product').order_by('product__name')

    # كل المواد الخام + تمييز من له سعر عند هذا المورد
    all_materials = Product.objects.filter(
        product_type='raw_material', is_active=True
    ).order_by('name')

    priced_ids = {p.product_id: p for p in prices}

    materials = []
    for m in all_materials:
        sp = priced_ids.get(m.pk)
        materials.append({
            'id': m.pk,
            'name': m.name,
            'sku': m.sku,
            'has_price': bool(sp),
            'cost': str(sp.cost) if sp else '',
            'purchase_unit': sp.purchase_unit if sp else 'unit',
            'conversion_to_base': str(sp.conversion_to_base) if sp else '1',
        })

    return JsonResponse({'materials': materials})

