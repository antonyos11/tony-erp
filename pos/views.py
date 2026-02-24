from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpRequest
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext as _
from django.utils import timezone
from decimal import Decimal
from django.db import models
from datetime import date, timedelta
from inventory.models import Product, Location, Category
from partners.models import Customer
from .models import POSSession, POSOrder, POSOrderLine, POSTable
from showrooms.models import ShowroomEmployee
from showrooms.mixins import get_active_showroom_id
from payments.models import PaymentMethod


@login_required
def dashboard(request: HttpRequest):
    # صلاحية العرض
    if hasattr(request.user, 'has_module_permission') and not request.user.has_module_permission('pos', 'view'):
        return render(request, '403.html', status=403)
    sid = get_active_showroom_id(request)
    session = POSSession.objects.filter(user=request.user, is_open=True)
    if sid:
        # Filter session by the Location's OneToOne reverse name 'showroom_link'
        session = session.filter(location__showroom_link__id=sid)
    session = session.first()
    sessions = POSSession.objects.filter(user=request.user).order_by('-id')
    if sid:
        sessions = sessions.filter(location__showroom_link__id=sid)
    sessions = sessions[:20]
    orders = POSOrder.objects.select_related('customer').order_by('-id')
    if sid:
        # POSOrder has direct FK 'showroom'
        orders = orders.filter(showroom_id=sid)
    orders = orders[:20]
    return render(request, 'pos/dashboard.html', {
        'active_session': session,
        'recent_sessions': sessions,
        'recent_orders': orders,
    })


@login_required
def test_enhancements(request: HttpRequest):
    """صفحة اختبار التحسينات"""
    return render(request, 'pos/test_enhancements.html')


@login_required
def open_session(request: HttpRequest):
    if hasattr(request.user, 'has_module_permission') and not request.user.has_module_permission('pos', 'add'):
        return render(request, '403.html', status=403)
    
    sid = get_active_showroom_id(request)
    
    # السماح لـ superuser أو staff بالوصول حتى بدون معرض محدد
    is_admin = request.user.is_superuser or request.user.is_staff
    
    if sid is None and not is_admin:
        # Require explicit showroom selection for non-admin users
        return render(request, '403.html', status=403)
    
    # التحقق من الموظف للمستخدمين العاديين فقط
    if sid and not is_admin:
        if not ShowroomEmployee.objects.filter(user=request.user, active=True).filter(models.Q(showroom_id=sid) | models.Q(can_cross_access=True)).exists():
            return render(request, '403.html', status=403)
    
    if request.method == 'POST':
        opening_balance = Decimal(request.POST.get('opening_balance') or '0')
        location = None
        if sid:
            showroom_location = Location.objects.filter(showroom_link_id=sid).first()
            location = showroom_location or Location.objects.filter(type='store', showroom_link_id=sid).first()
        if not location:
            # للأدمن، اختر أي موقع متاح
            location = Location.objects.filter(type='store').first() or Location.objects.first()
        if not location:
            return render(request, '403.html', status=403)
        POSSession.objects.create(user=request.user, opening_balance=opening_balance, location=location)
        return redirect('pos:dashboard')
    
    if sid:
        store_locations = Location.objects.filter(showroom_link_id=sid, type='store')
    else:
        # للأدمن، اعرض جميع المواقع
        store_locations = Location.objects.filter(type='store')
    return render(request, 'pos/open_session.html', {'locations': store_locations})


@login_required
def close_session(request: HttpRequest, session_id: int):
    if hasattr(request.user, 'has_module_permission') and not request.user.has_module_permission('pos', 'change'):
        return render(request, '403.html', status=403)
    session = get_object_or_404(POSSession, pk=session_id, user=request.user)
    if request.method == 'POST':
        closing_balance = Decimal(request.POST.get('closing_balance') or '0')
        session.close(closing_balance)
        return redirect('pos:dashboard')
    return render(request, 'pos/close_session.html', {'session': session})


def _ensure_session(user, sid=None):
    qs = POSSession.objects.filter(user=user, is_open=True)
    if sid:
        qs = qs.filter(location__showroom_link__id=sid)
    session = qs.first()
    if session:
        return session
    from inventory.models import Location as L
    loc = None
    if sid:
        loc = L.objects.filter(showroom_link_id=sid, type='store').first() or L.objects.filter(showroom_link_id=sid).first()
    if not loc:
        loc = L.objects.filter(type='store').first() or L.objects.first()
    session = POSSession.objects.create(user=user, opening_balance=0, location=loc)
    return session


@login_required
def new_order(request: HttpRequest):
    if hasattr(request.user, 'has_module_permission') and not request.user.has_module_permission('pos', 'add'):
        return render(request, '403.html', status=403)
    
    # السماح لـ superuser أو staff بالوصول
    is_admin = request.user.is_superuser or request.user.is_staff
    
    sid = get_active_showroom_id(request)
    session = _ensure_session(request.user, sid)
    if sid and session.location and session.location.showroom_id != sid:
        # حاول إيجاد جلسة في نفس المعرض وإلا أنشئ واحدة
        same_showroom_session = POSSession.objects.filter(user=request.user, is_open=True, location__showroom_link__id=sid).first()
        if same_showroom_session:
            session = same_showroom_session
        else:
            session = _ensure_session(request.user, sid)
    
    # التحقق من الموظف للمستخدمين العاديين فقط
    if sid and not is_admin:
        if not ShowroomEmployee.objects.filter(user=request.user, active=True).filter(models.Q(showroom_id=sid) | models.Q(can_cross_access=True)).exists():
            return render(request, '403.html', status=403)
    
    location = session.location or (Location.objects.filter(type='store').first() or Location.objects.first())
    if sid and location.showroom_id != sid:
        # enforce using showroom location
        location = Location.objects.filter(showroom_link_id=sid).first() or location
    order = POSOrder.objects.create(session=session, location=location)
    return redirect('pos:pay_order', order_id=order.id)


@login_required
def add_line(request: HttpRequest, order_id: int):
    # السماح للسوبر يوزر بتجاوز فحص الصلاحيات
    if not (request.user.is_superuser or request.user.is_staff):
        if hasattr(request.user, 'has_module_permission') and not request.user.has_module_permission('pos', 'add'):
            return JsonResponse({'error': _('غير مسموح - ليس لديك صلاحية إضافة منتجات')}, status=403)
    
    sid = get_active_showroom_id(request)
    order = get_object_or_404(POSOrder, pk=order_id)
    
    # السماح للسوبر يوزر بتجاوز فحص المعرض
    if not (request.user.is_superuser or request.user.is_staff):
        if sid and order.location and order.location.showroom_id != sid:
            return JsonResponse({'error': _('غير مسموح - هذا الطلب من معرض آخر')}, status=403)
    
    if order.status != 'draft':
        return JsonResponse({'error': _('لا يمكن إضافة بنود بعد الدفع')}, status=400)
    
    code = request.POST.get('code') or ''
    if not code:
        return JsonResponse({'error': _('لم يتم تحديد المنتج')}, status=400)
    
    qty = int(request.POST.get('qty') or '1')
    
    # البحث عن المنتج بترتيب: ID -> Barcode -> SKU -> Name
    product = None
    # محاولة البحث بالـ ID أولاً (إذا كان رقماً)
    if code.isdigit():
        product = Product.objects.filter(id=int(code)).first()
    
    # إذا لم يُعثر على المنتج، جرب بالباركود
    if not product:
        product = Product.objects.filter(barcode=code).first()
    
    # إذا لم يُعثر على المنتج، جرب بالـ SKU
    if not product:
        product = Product.objects.filter(sku=code).first()
    
    # إذا لم يُعثر على المنتج، جرب بالاسم
    if not product:
        product = Product.objects.filter(name__icontains=code).first()
    
    if not product:
        return JsonResponse({'error': _('لم يتم العثور على منتج برمز: ') + code}, status=404)
    
    try:
        line = POSOrderLine.objects.create(order=order, product=product, quantity=qty, price=product.price)
        return JsonResponse({
            'ok': True, 
            'order_total': float(order.total),
            'line_id': line.id,
            'product_name': product.name
        })
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error creating POSOrderLine: {str(e)}")
        return JsonResponse({'error': _('خطأ في إضافة المنتج: ') + str(e)}, status=500)


@login_required
def delete_line(request: HttpRequest, order_id: int, line_id: int):
    """حذف بند من طلب POS"""
    # السماح للسوبر يوزر بتجاوز فحص الصلاحيات
    if not (request.user.is_superuser or request.user.is_staff):
        if hasattr(request.user, 'has_module_permission') and not request.user.has_module_permission('pos', 'delete'):
            return JsonResponse({'error': _('غير مسموح - ليس لديك صلاحية حذف منتجات')}, status=403)
    
    sid = get_active_showroom_id(request)
    order = get_object_or_404(POSOrder, pk=order_id)
    
    # السماح للسوبر يوزر بتجاوز فحص المعرض
    if not (request.user.is_superuser or request.user.is_staff):
        if sid and order.location and order.location.showroom_id != sid:
            return JsonResponse({'error': _('غير مسموح - هذا الطلب من معرض آخر')}, status=403)
    
    if order.status != 'draft':
        return JsonResponse({'error': _('لا يمكن حذف بنود بعد الدفع')}, status=400)
    line = get_object_or_404(POSOrderLine, pk=line_id, order=order)
    line.delete()
    return JsonResponse({'ok': True, 'order_total': float(order.total)})


@login_required
def update_line_qty(request: HttpRequest, order_id: int, line_id: int):
    """تحديث كمية بند في طلب POS"""
    # السماح للسوبر يوزر بتجاوز فحص الصلاحيات
    if not (request.user.is_superuser or request.user.is_staff):
        if hasattr(request.user, 'has_module_permission') and not request.user.has_module_permission('pos', 'change'):
            return JsonResponse({'error': _('غير مسموح - ليس لديك صلاحية تعديل الكميات')}, status=403)
    
    sid = get_active_showroom_id(request)
    order = get_object_or_404(POSOrder, pk=order_id)
    
    # السماح للسوبر يوزر بتجاوز فحص المعرض
    if not (request.user.is_superuser or request.user.is_staff):
        if sid and order.location and order.location.showroom_id != sid:
            return JsonResponse({'error': _('غير مسموح - هذا الطلب من معرض آخر')}, status=403)
    
    if order.status != 'draft':
        return JsonResponse({'error': _('لا يمكن تعديل بنود بعد الدفع')}, status=400)
    
    line = get_object_or_404(POSOrderLine, pk=line_id, order=order)
    
    import json
    try:
        data = json.loads(request.body)
        new_qty = int(data.get('quantity', 1))
    except:
        new_qty = int(request.POST.get('quantity', 1))
    
    if new_qty <= 0:
        line.delete()
        return JsonResponse({'ok': True, 'deleted': True, 'order_total': float(order.total)})
    
    line.quantity = new_qty
    line.save(update_fields=['quantity'])
    return JsonResponse({'ok': True, 'order_total': float(order.total), 'line_total': float(line.total)})


@login_required
def pay_order(request: HttpRequest, order_id: int):
    if hasattr(request.user, 'has_module_permission') and not request.user.has_module_permission('pos', 'change'):
        return render(request, '403.html', status=403)
    sid = get_active_showroom_id(request)
    order = get_object_or_404(POSOrder, pk=order_id)
    if sid and order.location and order.location.showroom_id != sid:
        return render(request, '403.html', status=403)
    if request.method == 'POST':
        if 'code' in request.POST:
            return add_line(request, order_id)
        amount = Decimal(request.POST.get('amount') or '0')
        payment_method_id = request.POST.get('payment_method')
        payment_method = None
        if payment_method_id:
            payment_method = PaymentMethod.objects.filter(id=payment_method_id).first()
        cust_name = request.POST.get('customer_name')
        if cust_name:
            customer = Customer.objects.filter(name__iexact=cust_name).first()
            if customer:
                order.customer = customer
                order.save(update_fields=['customer'])
        order.finalize_payment(amount, payment_method)
        return redirect('pos:receipt', order_id=order.id)
    
    lines = order.lines.select_related('product')
    
    # جلب بيانات المنتجات والفئات والعملاء
    # جلب جميع المنتجات النشطة مع فلترة حسب المخزون
    from django.db.models import Sum, Q
    from inventory.models import Stock
    
    # الحصول على المنتجات التي لديها مخزون
    product_ids_with_stock = Stock.objects.filter(
        quantity__gt=0
    ).values_list('product_id', flat=True).distinct()
    
    # جلب المنتجات النشطة التي لديها مخزون أو جميع المنتجات للسوبر يوزر
    if request.user.is_superuser or request.user.is_staff:
        # عرض جميع المنتجات للأدمن (بحد أقصى معقول)
        products = Product.objects.all().select_related('category').order_by('-id')[:500]
    else:
        # عرض المنتجات التي لها مخزون فقط
        products = Product.objects.filter(
            id__in=product_ids_with_stock
        ).select_related('category').order_by('-id')
    
    categories = Category.objects.filter(is_active=True).order_by('sort_order', 'name')
    brands = []  # سيتم إضافتها لاحقاً إذا كان هناك نموذج Brand
    customers = Customer.objects.all().order_by('-id')[:100]
    location = order.location
    
    # الوردية النشطة
    active_session = POSSession.objects.filter(user=request.user, is_open=True).first()
    
    # طرق الدفع
    payment_methods = PaymentMethod.objects.filter(is_active=True).order_by('display_order', 'name')
    
    # خطط التقسيط المتاحة
    installment_plans = []
    try:
        from installments.models import InstallmentPlan as SmartInstallmentPlan
        # تحويل إلى list لاكتشاف أي خطأ في قاعدة البيانات هنا
        installment_plans = list(SmartInstallmentPlan.objects.filter(is_active=True).order_by('duration_months'))
    except Exception:
        # في حالة عدم وجود الجدول أو أي خطأ آخر
        installment_plans = []
    
    # جلب بيانات الشركة للفاتورة الضريبية
    from core.models import Company
    company = Company.objects.first()
    company_vat_rate = str(company.default_vat_rate) if company and hasattr(company, 'default_vat_rate') and company.default_vat_rate else '14'
    company_tax_id = company.tax_id if company else ''
    company_name = company.name if company else ''
    
    return render(request, 'pos/pos_main.html', {
        'order': order, 
        'lines': lines, 
        'remaining': order.remaining,
        'products': products,
        'categories': categories,
        'brands': brands,
        'customers': customers,
        'location': location,
        'active_session': active_session,
        'payment_methods': payment_methods,
        'installment_plans': installment_plans,
        'company_vat_rate': company_vat_rate,
        'company_tax_id': company_tax_id,
        'company_name': company_name,
    })


@login_required
def product_lookup_api(request: HttpRequest):
    if hasattr(request.user, 'has_module_permission') and not request.user.has_module_permission('pos', 'view'):
        return JsonResponse({'results': []}, status=403)
    from django.db.models import Q
    q = request.GET.get('q', '').strip()
    if not q:
        return JsonResponse({'results': []})
    sid = get_active_showroom_id(request)
    qs = Product.objects.filter(Q(name__icontains=q) | Q(sku__icontains=q) | Q(barcode__icontains=q))
    if sid:
        # يمكن توسيعها لاحقاً لاستعمال مخزون المعرض فقط
        pass
    qs = qs[:15]
    data = [{
        'id': p.id,
        'name': p.name,
        'price': float(p.price),
        'sku': p.sku,
        'barcode': p.barcode,
        'stock': p.current_stock,
    } for p in qs]
    return JsonResponse({'results': data})


@login_required
def receipt(request: HttpRequest, order_id: int):
    if hasattr(request.user, 'has_module_permission') and not request.user.has_module_permission('pos', 'view'):
        return render(request, '403.html', status=403)
    sid = get_active_showroom_id(request)
    order = get_object_or_404(POSOrder, pk=order_id)
    if sid and order.location and order.location.showroom_id != sid:
        return render(request, '403.html', status=403)
    lines = order.lines.select_related('product')
    
    # جلب بيانات الشركة من Company model (صفحة بيانات الشركة)
    company_data = {
        'name': 'Tony ERP',
        'address': '',
        'phone': '',
        'vat_number': '',
        'logo': None,
    }
    try:
        from core.models import Company
        company = Company.objects.first()
        if company:
            company_data['name'] = company.name or 'Tony ERP'
            company_data['address'] = company.address or ''
            company_data['phone'] = company.phone or ''
            company_data['vat_number'] = company.tax_id or ''
            company_data['logo'] = company.logo.url if company.logo else None
    except:
        pass
    
    # بيانات المعرض/نقطة البيع
    branch_data = {
        'name': order.location.name if order.location else '',
        'code': order.location.code if order.location else '',
    }
    
    # بيانات الكاشير
    cashier_name = ''
    if order.session and order.session.user:
        user = order.session.user
        cashier_name = user.first_name or user.username
    
    # اختيار القالب: حراري أو عادي
    thermal = request.GET.get('thermal', '0') == '1'
    auto_print = request.GET.get('auto', '0') == '1'
    template_name = 'pos/thermal_receipt.html' if thermal else 'pos/receipt.html'
    
    return render(request, template_name, {
        'order': order, 
        'lines': lines,
        'auto_print': auto_print,
        'company': company_data,
        'branch': branch_data,
        'cashier_name': cashier_name,
    })


@login_required
def printer_test(request: HttpRequest):
    """صفحة اختبار الطابعة الحرارية"""
    return render(request, 'pos/printer_test.html')


# ===== الصفحات الإضافية =====
@login_required
def tables(request: HttpRequest):
    """إدارة الطاولات"""
    if hasattr(request.user, 'has_module_permission') and not request.user.has_module_permission('pos', 'view'):
        return render(request, '403.html', status=403)
    
    sid = get_active_showroom_id(request)
    
    # جلب الطاولات
    tables_qs = POSTable.objects.select_related('location', 'current_order').filter(is_active=True)
    if sid:
        tables_qs = tables_qs.filter(location__showroom_link__id=sid)
    
    # جلب المواقع
    locations = Location.objects.all()
    if sid:
        locations = locations.filter(showroom_link__id=sid)
    
    # تصنيف حسب الطابق/المنطقة
    floors = tables_qs.values_list('floor', flat=True).distinct()
    
    # إحصائيات
    stats = {
        'total': tables_qs.count(),
        'available': tables_qs.filter(status='available').count(),
        'occupied': tables_qs.filter(status='occupied').count(),
        'reserved': tables_qs.filter(status='reserved').count(),
        'cleaning': tables_qs.filter(status='cleaning').count(),
    }
    
    return render(request, 'pos/tables.html', {
        'tables': tables_qs,
        'locations': locations,
        'floors': floors,
        'stats': stats,
    })


@login_required
def table_action(request: HttpRequest, table_id: int):
    """إجراءات على الطاولة"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    table = get_object_or_404(POSTable, pk=table_id)
    action = request.POST.get('action')
    
    if action == 'occupy':
        # إنشاء طلب جديد للطاولة
        session = POSSession.objects.filter(user=request.user, is_open=True).first()
        if not session:
            return JsonResponse({'error': 'لا توجد وردية مفتوحة'}, status=400)
        order = POSOrder.objects.create(
            session=session,
            location=table.location,
        )
        table.occupy(order)
        return JsonResponse({'success': True, 'order_id': order.id, 'redirect': f'/pos/order/{order.id}/pay/'})
    
    elif action == 'release':
        table.release()
        return JsonResponse({'success': True})
    
    elif action == 'cleaning':
        table.set_cleaning()
        return JsonResponse({'success': True})
    
    elif action == 'reserve':
        table.reserve()
        return JsonResponse({'success': True})
    
    elif action == 'available':
        table.status = 'available'
        table.save(update_fields=['status'])
        return JsonResponse({'success': True})
    
    return JsonResponse({'error': 'إجراء غير معروف'}, status=400)


@login_required
def table_save(request: HttpRequest):
    """حفظ طاولة جديدة أو تعديل موجودة"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    table_id = request.POST.get('table_id')
    name = request.POST.get('name', '').strip()
    location_id = request.POST.get('location')
    capacity = int(request.POST.get('capacity', 4))
    shape = request.POST.get('shape', 'square')
    floor = request.POST.get('floor', '').strip()
    
    if not name:
        return JsonResponse({'error': 'اسم الطاولة مطلوب'}, status=400)
    
    if not location_id:
        return JsonResponse({'error': 'الموقع مطلوب'}, status=400)
    
    location = get_object_or_404(Location, pk=location_id)
    
    if table_id:
        # تعديل
        table = get_object_or_404(POSTable, pk=table_id)
        table.name = name
        table.location = location
        table.capacity = capacity
        table.shape = shape
        table.floor = floor
        table.save()
    else:
        # إضافة جديدة
        table = POSTable.objects.create(
            name=name,
            location=location,
            capacity=capacity,
            shape=shape,
            floor=floor,
        )
    
    return JsonResponse({'success': True, 'table_id': table.id})


@login_required
def table_delete(request: HttpRequest, table_id: int):
    """حذف طاولة"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    table = get_object_or_404(POSTable, pk=table_id)
    
    if table.status == 'occupied' and table.current_order:
        return JsonResponse({'error': 'لا يمكن حذف طاولة مشغولة'}, status=400)
    
    table.is_active = False
    table.save(update_fields=['is_active'])
    
    return JsonResponse({'success': True})


@login_required
def shifts(request: HttpRequest):
    """تقارير الورديات"""
    if hasattr(request.user, 'has_module_permission') and not request.user.has_module_permission('pos', 'view'):
        return render(request, '403.html', status=403)
    sessions = POSSession.objects.select_related('user', 'location').order_by('-opened_at')[:50]
    return render(request, 'pos/shifts.html', {'sessions': sessions})


@login_required
def sales_details(request: HttpRequest):
    """تفاصيل البيع"""
    if hasattr(request.user, 'has_module_permission') and not request.user.has_module_permission('pos', 'view'):
        return render(request, '403.html', status=403)
    orders = POSOrder.objects.select_related('customer', 'session', 'session__user').order_by('-created_at')[:100]
    return render(request, 'pos/sales_details.html', {'orders': orders})


@login_required
def cashier_report(request: HttpRequest):
    """تقرير الكاشير والوردية"""
    if hasattr(request.user, 'has_module_permission') and not request.user.has_module_permission('pos', 'view'):
        return render(request, '403.html', status=403)
    from django.db.models import Sum, Count, Q
    active_session = POSSession.objects.filter(user=request.user, is_open=True).first()
    session = active_session
    context = {
        'active_session': active_session,
        'session': session,
        'cashier': request.user,
        'total_sales': 0,
        'cash_sales': 0,
        'card_sales': 0,
        'total_returns': 0,
        'orders_count': 0,
        'orders': [],
    }
    if session:
        orders = POSOrder.objects.filter(session=session)
        stats = orders.aggregate(
            total=Sum('total'),
            count=Count('id'),
        )
        context['total_sales'] = stats.get('total') or 0
        context['orders_count'] = stats.get('count') or 0
        context['orders'] = orders.order_by('-created_at')[:50]
        # Calculate cash vs card sales via payments relation
        try:
            from pos.models import POSPayment
            cash_total = POSPayment.objects.filter(order__session=session, method='cash').aggregate(t=Sum('amount'))['t'] or 0
            card_total = POSPayment.objects.filter(order__session=session, method='card').aggregate(t=Sum('amount'))['t'] or 0
            context['cash_sales'] = cash_total
            context['card_sales'] = card_total
        except Exception:
            context['cash_sales'] = 0
            context['card_sales'] = 0
        # Returns
        return_orders = orders.filter(is_return=True)
        context['total_returns'] = return_orders.aggregate(t=Sum('total'))['t'] or 0
    return render(request, 'pos/cashier_report.html', context)


@login_required
def deleted_items(request: HttpRequest):
    """تقرير الأصناف المحذوفة"""
    if hasattr(request.user, 'has_module_permission') and not request.user.has_module_permission('pos', 'view'):
        return render(request, '403.html', status=403)
    return render(request, 'pos/deleted_items.html')


@login_required
def printer_settings(request: HttpRequest):
    """إعدادات الطابعة"""
    if hasattr(request.user, 'has_module_permission') and not request.user.has_module_permission('pos', 'change'):
        return render(request, '403.html', status=403)
    return render(request, 'pos/printer_settings.html')


@login_required
def add_expense(request: HttpRequest):
    """إضافة مصروف من شاشة POS"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    if hasattr(request.user, 'has_module_permission') and not request.user.has_module_permission('pos', 'add'):
        return JsonResponse({'error': 'غير مصرح لك بهذه العملية'}, status=403)
    
    try:
        from accounting.models import Expense, Account
        from django.utils import timezone
        
        # Get form data
        description = request.POST.get('expense_category', '') + ' - ' + request.POST.get('expense_subcategory', '')
        if request.POST.get('expense_notes'):
            description += '\n' + request.POST.get('expense_notes')
        
        amount = Decimal(request.POST.get('total', '0'))
        expense_date = request.POST.get('expense_date') or timezone.now().date()
        
        # Create expense record
        expense = Expense.objects.create(
            date=expense_date,
            description=description,
            amount=amount,
        )
        
        return JsonResponse({
            'success': True,
            'expense_id': expense.id,
            'message': 'تم إضافة المصروف بنجاح'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# ===== Installment Views =====

@login_required
def create_installment(request: HttpRequest, order_id: int):
    """إنشاء خطة تقسيط جديدة - نظام تقسيط ذكي محسّن"""
    from .models_installment import InstallmentPlan
    from partners.models import Customer
    from decimal import Decimal
    from datetime import datetime
    from django.db import transaction
    
    if request.method != 'POST':
        return JsonResponse({'error': _('طريقة غير مسموحة')}, status=405)
    
    order = get_object_or_404(POSOrder, pk=order_id)
    
    # التحقق من أن الطلب لم يتم دفعه بالكامل
    if order.status == 'paid':
        return JsonResponse({'error': _('هذا الطلب مدفوع بالكامل بالفعل')}, status=400)
    
    # التحقق من وجود بنود في الطلب
    if not order.lines.exists():
        return JsonResponse({'error': _('لا توجد منتجات في الطلب')}, status=400)
    
    try:
        with transaction.atomic():
            # استخراج البيانات
            customer_name = request.POST.get('customer_name', '').strip()
            customer_phone = request.POST.get('customer_phone', '').strip()
            customer_phone2 = request.POST.get('customer_phone2', '').strip()
            customer_national_id = request.POST.get('customer_national_id', '').strip()
            customer_address = request.POST.get('customer_address', '').strip()
            
            guarantor_name = request.POST.get('guarantor_name', '').strip()
            guarantor_phone = request.POST.get('guarantor_phone', '').strip()
            guarantor_national_id = request.POST.get('guarantor_national_id', '').strip()
            
            down_payment = Decimal(request.POST.get('down_payment', '0') or '0')
            interest_rate = Decimal(request.POST.get('interest_rate', '0') or '0')
            number_of_installments = int(request.POST.get('number_of_installments', '6') or '6')
            start_date_str = request.POST.get('start_date', '')
            notes = request.POST.get('notes', '').strip()
            plan_id = request.POST.get('plan_id', '').strip()
            
            # التحقق من البيانات المطلوبة
            if not customer_name:
                return JsonResponse({'error': _('اسم العميل مطلوب')}, status=400)
            if not customer_phone:
                return JsonResponse({'error': _('رقم الموبايل مطلوب')}, status=400)
            if not customer_address:
                return JsonResponse({'error': _('العنوان مطلوب')}, status=400)
            if not start_date_str:
                return JsonResponse({'error': _('تاريخ أول قسط مطلوب')}, status=400)
            if number_of_installments < 2:
                return JsonResponse({'error': _('عدد الأقساط يجب أن يكون 2 على الأقل')}, status=400)
            
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            
            # إذا تم اختيار خطة تقسيط ذكية، استخدم إعداداتها
            smart_plan = None
            if plan_id:
                try:
                    from installments.models import InstallmentPlan as SmartInstallmentPlan
                    smart_plan = SmartInstallmentPlan.objects.filter(id=plan_id, is_active=True).first()
                    if smart_plan:
                        number_of_installments = smart_plan.duration_months
                        interest_rate = smart_plan.annual_interest_rate
                        # التحقق من الحد الأدنى للمقدم
                        min_down = order.total * (smart_plan.min_down_payment_percentage / Decimal('100'))
                        if down_payment < min_down:
                            return JsonResponse({
                                'error': _('الحد الأدنى للمقدم هو') + f' {min_down:.2f}'
                            }, status=400)
                except ImportError:
                    pass
            
            # إنشاء أو البحث عن العميل
            customer, created = Customer.objects.get_or_create(
                phone=customer_phone,
                defaults={
                    'name': customer_name,
                    'address': customer_address,
                }
            )
            if not created:
                # تحديث بيانات العميل
                customer.name = customer_name
                customer.address = customer_address
                customer.save()
            
            # إعادة حساب إجمالي الطلب
            order.recalc_total()
            total_amount = order.total
            
            # التحقق من أن المقدم لا يتجاوز الإجمالي
            if down_payment >= total_amount:
                return JsonResponse({'error': _('الدفعة المقدمة لا يمكن أن تساوي أو تتجاوز الإجمالي')}, status=400)
            
            # حساب التقسيط
            remaining_amount = total_amount - down_payment
            
            # حساب الفائدة (فائدة بسيطة)
            if interest_rate > 0:
                monthly_rate = interest_rate / Decimal('12') / Decimal('100')
                n = number_of_installments
                # صيغة القسط الشهري مع الفائدة المركبة
                if monthly_rate > 0:
                    factor = (monthly_rate * (1 + monthly_rate) ** n) / ((1 + monthly_rate) ** n - 1)
                    installment_amount = remaining_amount * factor
                else:
                    installment_amount = remaining_amount / n
                total_with_interest = installment_amount * n
                total_interest = total_with_interest - remaining_amount
            else:
                installment_amount = remaining_amount / Decimal(str(number_of_installments))
                total_with_interest = remaining_amount
                total_interest = Decimal('0')
            
            # إنشاء خطة التقسيط
            plan = InstallmentPlan.objects.create(
                order=order,
                customer=customer,
                total_amount=total_amount,
                down_payment=down_payment,
                remaining_amount=total_with_interest,
                number_of_installments=number_of_installments,
                installment_amount=installment_amount.quantize(Decimal('0.01')),
                interest_rate=interest_rate,
                start_date=start_date,
                customer_phone=customer_phone,
                customer_phone2=customer_phone2 or None,
                customer_address=customer_address,
                customer_national_id=customer_national_id or None,
                guarantor_name=guarantor_name or None,
                guarantor_phone=guarantor_phone or None,
                guarantor_national_id=guarantor_national_id or None,
                notes=notes or None,
                created_by=request.user,
            )
            
            # إنشاء جدول الأقساط
            plan.generate_installments()
            
            # تسجيل الدفعة المقدمة إذا وجدت
            if down_payment > 0:
                order.finalize_payment(down_payment, None)
            
            # ربط العميل بالطلب وتحديث الحالة
            order.customer = customer
            order.save(update_fields=['customer'])
            
            return JsonResponse({
                'success': True,
                'plan_id': plan.id,
                'contract_number': f'INST-{plan.id:05d}',
                'redirect_url': f'/pos/installment/{plan.id}/',
                'message': _('تم إنشاء خطة التقسيط بنجاح'),
                'details': {
                    'total_amount': float(total_amount),
                    'down_payment': float(down_payment),
                    'financed_amount': float(remaining_amount),
                    'total_interest': float(total_interest),
                    'monthly_payment': float(installment_amount.quantize(Decimal('0.01'))),
                    'number_of_installments': number_of_installments,
                }
            })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def calculate_installment_api(request: HttpRequest):
    """API لحساب التقسيط ديناميكياً"""
    from decimal import Decimal
    
    try:
        total_amount = Decimal(request.GET.get('total', '0') or '0')
        down_payment = Decimal(request.GET.get('down_payment', '0') or '0')
        months = int(request.GET.get('months', '6') or '6')
        annual_rate = Decimal(request.GET.get('rate', '0') or '0')
        plan_id = request.GET.get('plan_id', '')
        
        # إذا تم تحديد خطة، استخدم إعداداتها
        min_down_percentage = Decimal('0')
        if plan_id:
            try:
                from installments.models import InstallmentPlan as SmartPlan
                plan = SmartPlan.objects.filter(id=plan_id, is_active=True).first()
                if plan:
                    months = plan.duration_months
                    annual_rate = plan.annual_interest_rate
                    min_down_percentage = plan.min_down_payment_percentage
            except ImportError:
                pass
        
        financed_amount = total_amount - down_payment
        
        # حساب القسط الشهري
        if annual_rate > 0 and months > 0:
            monthly_rate = annual_rate / Decimal('12') / Decimal('100')
            n = months
            if monthly_rate > 0:
                factor = (monthly_rate * (1 + monthly_rate) ** n) / ((1 + monthly_rate) ** n - 1)
                monthly_payment = financed_amount * factor
            else:
                monthly_payment = financed_amount / n
            total_interest = (monthly_payment * n) - financed_amount
        else:
            monthly_payment = financed_amount / months if months > 0 else Decimal('0')
            total_interest = Decimal('0')
        
        grand_total = financed_amount + total_interest
        min_down_amount = total_amount * (min_down_percentage / Decimal('100'))
        
        # إنشاء جدول الأقساط
        schedule = []
        from datetime import date
        from dateutil.relativedelta import relativedelta
        
        start_date_str = request.GET.get('start_date', '')
        if start_date_str:
            try:
                current_date = date.fromisoformat(start_date_str)
            except ValueError:
                current_date = date.today() + relativedelta(months=1)
                current_date = current_date.replace(day=1)
        else:
            current_date = date.today() + relativedelta(months=1)
            current_date = current_date.replace(day=1)
        
        for i in range(1, months + 1):
            schedule.append({
                'number': i,
                'date': current_date.isoformat(),
                'amount': float(monthly_payment.quantize(Decimal('0.01')))
            })
            current_date = current_date + relativedelta(months=1)
        
        return JsonResponse({
            'success': True,
            'calculation': {
                'total_amount': float(total_amount),
                'down_payment': float(down_payment),
                'financed_amount': float(financed_amount),
                'annual_rate': float(annual_rate),
                'months': months,
                'monthly_payment': float(monthly_payment.quantize(Decimal('0.01'))),
                'total_interest': float(total_interest.quantize(Decimal('0.01'))),
                'grand_total': float(grand_total.quantize(Decimal('0.01'))),
                'min_down_amount': float(min_down_amount.quantize(Decimal('0.01'))),
                'min_down_percentage': float(min_down_percentage),
            },
            'schedule': schedule
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def installment_plans_api(request: HttpRequest):
    """API للحصول على خطط التقسيط المتاحة"""
    plans = []
    
    try:
        from installments.models import InstallmentPlan as SmartPlan
        for plan in SmartPlan.objects.filter(is_active=True).order_by('duration_months'):
            plans.append({
                'id': plan.id,
                'name': plan.name,
                'description': plan.description or '',
                'duration_months': plan.duration_months,
                'annual_interest_rate': float(plan.annual_interest_rate),
                'min_down_payment_percentage': float(plan.min_down_payment_percentage),
                'admin_fee_type': plan.admin_fee_type,
                'admin_fee_value': float(plan.admin_fee_value),
                'requires_guarantor': plan.requires_guarantor,
                'min_amount': float(plan.min_amount),
                'max_amount': float(plan.max_amount) if plan.max_amount else None,
            })
    except ImportError:
        pass
    
    return JsonResponse({'plans': plans})


@login_required
def print_installment_contract(request: HttpRequest, plan_id: int):
    """طباعة عقد التقسيط"""
    from .models_installment import InstallmentPlan
    
    plan = get_object_or_404(InstallmentPlan, pk=plan_id)
    installments = plan.installments.all()
    
    # بيانات الشركة
    company_data = {
        'name': 'Tony ERP',
        'address': '',
        'phone': '',
        'logo': None,
    }
    try:
        from core.models import Company
        company = Company.objects.first()
        if company:
            company_data['name'] = company.name or 'Tony ERP'
            company_data['address'] = company.address or ''
            company_data['phone'] = company.phone or ''
            company_data['logo'] = company.logo.url if company.logo else None
    except:
        pass
    
    return render(request, 'pos/installment_contract_print.html', {
        'plan': plan,
        'installments': installments,
        'company': company_data,
    })


@login_required
def installments_list(request: HttpRequest):
    """قائمة خطط التقسيط"""
    from .models_installment import InstallmentPlan
    
    plans = InstallmentPlan.objects.select_related('customer', 'order').order_by('-created_at')
    
    # التصفية
    status = request.GET.get('status')
    if status:
        plans = plans.filter(status=status)
    
    search = request.GET.get('q')
    if search:
        plans = plans.filter(
            models.Q(customer__name__icontains=search) |
            models.Q(customer_phone__icontains=search) |
            models.Q(id__icontains=search)
        )
    
    return render(request, 'pos/installments_list.html', {
        'plans': plans,
        'status_filter': status,
        'search': search,
    })


@login_required
def installment_detail(request: HttpRequest, plan_id: int):
    """تفاصيل خطة تقسيط"""
    from .models_installment import InstallmentPlan
    
    plan = get_object_or_404(InstallmentPlan, pk=plan_id)
    installments = plan.installments.all()
    
    return render(request, 'pos/installment_detail.html', {
        'plan': plan,
        'installments': installments,
    })


@login_required
def pay_installment(request: HttpRequest, plan_id: int, installment_id: int):
    """تسجيل دفع قسط"""
    from .models_installment import InstallmentPlan, Installment
    
    if request.method != 'POST':
        return JsonResponse({'error': _('طريقة غير مسموحة')}, status=405)
    
    plan = get_object_or_404(InstallmentPlan, pk=plan_id)
    installment = get_object_or_404(Installment, pk=installment_id, plan=plan)
    
    if installment.is_paid:
        return JsonResponse({'error': _('هذا القسط مدفوع بالفعل')}, status=400)
    
    try:
        amount = Decimal(request.POST.get('amount', '0') or '0')
        payment_method = request.POST.get('payment_method', '')
        receipt_number = request.POST.get('receipt_number', '')
        
        installment.mark_as_paid(
            user=request.user,
            amount=amount or installment.amount,
            payment_method=payment_method,
            receipt_number=receipt_number
        )
        
        return JsonResponse({
            'success': True,
            'message': _('تم تسجيل الدفع بنجاح'),
            'paid_count': plan.paid_installments_count,
            'remaining': float(plan.remaining_to_pay),
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def update_order_status(request: HttpRequest, order_id: int):
    """تحديث حالة الطلب (مسودة، عرض سعر، معلق)"""
    if request.method != 'POST':
        return JsonResponse({'error': _('طريقة غير مسموحة')}, status=405)
    
    order = get_object_or_404(POSOrder, pk=order_id)
    
    try:
        import json
        data = json.loads(request.body)
        new_status = data.get('status', '')
        
        valid_statuses = ['draft', 'quote', 'hold', 'pending', 'completed']
        if new_status not in valid_statuses:
            return JsonResponse({'error': _('حالة غير صالحة')}, status=400)
        
        # تحديث الحالة
        order.status = new_status
        order.save(update_fields=['status'])
        
        status_messages = {
            'draft': _('تم حفظ الطلب كمسودة'),
            'quote': _('تم تحويل الطلب إلى عرض سعر'),
            'hold': _('تم تعليق الطلب'),
            'pending': _('الطلب معلق'),
            'completed': _('تم إتمام الطلب'),
        }
        
        return JsonResponse({
            'success': True,
            'message': status_messages.get(new_status, _('تم تحديث الحالة')),
            'new_status': new_status,
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def apply_discount(request: HttpRequest, order_id: int):
    """تطبيق خصم على الطلب"""
    if request.method != 'POST':
        return JsonResponse({'error': _('طريقة غير مسموحة')}, status=405)
    
    order = get_object_or_404(POSOrder, pk=order_id)
    
    try:
        import json
        from django.db.models import Sum, F
        data = json.loads(request.body)
        
        discount_type = data.get('discount_type', 'percentage')
        discount_value = Decimal(str(data.get('discount_value', 0)))
        reason = data.get('reason', '')
        
        # حساب الإجمالي الفرعي
        agg = order.lines.aggregate(total=Sum(F('quantity') * F('price')))
        subtotal = agg['total'] or Decimal('0')
        
        # حساب قيمة الخصم
        if discount_type == 'percentage':
            calculated_amount = (subtotal * discount_value) / 100
        else:
            calculated_amount = discount_value
        
        # التأكد من أن الخصم لا يتجاوز الإجمالي
        calculated_amount = min(calculated_amount, subtotal)
        
        # تحديث الطلب
        order.discount_amount = calculated_amount
        order.save(update_fields=['discount_amount'])
        order.recalc_total()
        
        return JsonResponse({
            'success': True,
            'message': _('تم تطبيق الخصم بنجاح'),
            'discount_amount': float(calculated_amount),
            'new_total': float(order.total),
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def remove_discount(request: HttpRequest, order_id: int):
    """إزالة الخصم من الطلب"""
    if request.method != 'POST':
        return JsonResponse({'error': _('طريقة غير مسموحة')}, status=405)
    
    order = get_object_or_404(POSOrder, pk=order_id)
    
    try:
        order.discount_amount = Decimal('0')
        order.save(update_fields=['discount_amount'])
        order.recalc_total()
        
        return JsonResponse({
            'success': True,
            'message': _('تم إزالة الخصم'),
            'new_total': float(order.total),
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def update_order_taxes(request: HttpRequest, order_id: int):
    """تحديث الضرائب ومصاريف الشحن للطلب"""
    if request.method != 'POST':
        return JsonResponse({'error': _('طريقة غير مسموحة')}, status=405)
    
    order = get_object_or_404(POSOrder, pk=order_id)
    
    try:
        action = request.POST.get('action', '')
        
        if action == 'toggle_tax_invoice':
            # تفعيل/إلغاء الفاتورة الضريبية
            is_tax = request.POST.get('is_tax_invoice') == '1'
            order.is_tax_invoice = is_tax
            
            # جلب بيانات الشركة
            from core.models import Company
            company = Company.objects.first()
            company_name = ''
            company_tax_id = ''
            
            if is_tax:
                # جلب نسبة الضريبة من إعدادات الشركة
                if company:
                    order.vat_rate = company.default_vat_rate if hasattr(company, 'default_vat_rate') and company.default_vat_rate else Decimal('14')
                    company_name = company.name or ''
                    company_tax_id = company.tax_id or ''
                elif not order.vat_rate:
                    order.vat_rate = Decimal('14')
            
            order.save(update_fields=['is_tax_invoice', 'vat_rate'])
            order.recalc_total()
            
            # حساب المبلغ قبل الضريبة
            subtotal_before_tax = float(order.total) - float(order.tax_amount or 0)
            
            return JsonResponse({
                'success': True,
                'is_tax_invoice': order.is_tax_invoice,
                'vat_rate': float(order.vat_rate),
                'tax_amount': float(order.tax_amount),
                'total': float(order.total),
                'subtotal_before_tax': subtotal_before_tax,
                'company_name': company_name,
                'company_tax_id': company_tax_id,
            })
        
        elif action == 'set_withholding_tax':
            # تحديث نسبة ضريبة المنبع
            rate = Decimal(request.POST.get('withholding_rate', '0'))
            order.withholding_tax_rate = rate
            order.save(update_fields=['withholding_tax_rate'])
            order.recalc_total()
            
            return JsonResponse({
                'success': True,
                'withholding_rate': float(order.withholding_tax_rate),
                'withholding_amount': float(order.withholding_tax_amount),
                'total': float(order.total),
            })
        
        elif action == 'set_shipping_cost':
            # تحديث مصاريف الشحن
            cost = Decimal(request.POST.get('shipping_cost', '0'))
            order.shipping_cost = cost
            order.save(update_fields=['shipping_cost'])
            order.recalc_total()
            
            return JsonResponse({
                'success': True,
                'shipping_cost': float(order.shipping_cost),
                'total': float(order.total),
            })
        
        else:
            return JsonResponse({'error': _('إجراء غير معروف')}, status=400)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def quote_print(request: HttpRequest, order_id: int):
    """طباعة عرض السعر"""
    order = get_object_or_404(POSOrder, pk=order_id)
    lines = order.lines.select_related('product')
    
    return render(request, 'pos/quote_print.html', {
        'order': order,
        'lines': lines,
    })


# ===== الطباعة الحرارية المباشرة =====
@login_required
def direct_print(request: HttpRequest, order_id: int):
    """
    طباعة مباشرة على طابعة حرارية XPrinter
    GET: الحصول على قائمة الطابعات المتاحة
    POST: طباعة الإيصال
    """
    # استخدام النظام الجديد للطباعة العربية كصورة
    from .thermal_printer_arabic import ArabicThermalPrinter, print_arabic_receipt
    
    if request.method == 'GET':
        # إرجاع قائمة الطابعات المتاحة
        printer = ArabicThermalPrinter()
        printers = printer.get_available_printers()
        return JsonResponse({
            'printers': printers,
            'default': printer.get_default_printer()
        })
    
    elif request.method == 'POST':
        import json
        
        try:
            data = json.loads(request.body) if request.body else {}
        except json.JSONDecodeError:
            data = {}
        
        printer_name = data.get('printer_name')
        open_drawer = data.get('open_drawer', False)
        
        # استخدام الطباعة العربية كصورة
        result = print_arabic_receipt(order_id, printer_name, open_drawer)
        
        if result['success']:
            return JsonResponse({
                'success': True,
                'message': f"تم طباعة الفاتورة {result.get('order_number', '')} بنجاح",
                'printer': result.get('printer')
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'فشلت الطباعة')
            }, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required  
def printer_test(request: HttpRequest):
    """اختبار الطابعة الحرارية بالعربية"""
    from .thermal_printer_arabic import ArabicThermalPrinter
    
    printer_name = request.GET.get('printer')
    
    printer = ArabicThermalPrinter(printer_name)
    
    if not printer.connect():
        return JsonResponse({
            'success': False,
            'error': 'فشل الاتصال بالطابعة'
        }, status=400)
    
    try:
        success = printer.print_test()
        return JsonResponse({
            'success': success,
            'message': 'تم إرسال اختبار الطباعة بالعربية' if success else 'فشل اختبار الطباعة',
            'printer': printer.printer_name
        })
    finally:
        printer.disconnect()


@login_required
def qz_setup(request: HttpRequest):
    """صفحة إعداد QZ Tray للطباعة المباشرة"""
    return render(request, 'pos/qz_setup.html')


# ===== طباعة فاتورة A4 =====
@login_required
def invoice_a4(request: HttpRequest, order_id: int):
    """
    عرض وطباعة فاتورة A4
    GET: عرض الفاتورة (مع طباعة تلقائية إذا auto_print=1)
    POST: طباعة مباشرة
    """
    from datetime import datetime
    
    order = get_object_or_404(POSOrder, pk=order_id)
    lines = order.lines.select_related('product')
    
    # جلب بيانات الشركة
    company_data = {
        'name': 'Tony ERP',
        'address': '',
        'phone': '',
        'mobile': '',
        'email': '',
        'vat_number': '',
        'tax_id': '',
        'commercial_register': '',
        'website': '',
        'whatsapp': '',
        'facebook': '',
        'instagram': '',
        'twitter': '',
        'tiktok': '',
        'youtube': '',
        'linkedin': '',
        'logo': None,
    }
    try:
        from core.models import Company
        company = Company.objects.first()
        if company:
            company_data['name'] = company.name or 'Tony ERP'
            company_data['address'] = company.address or ''
            company_data['phone'] = company.phone or ''
            company_data['mobile'] = getattr(company, 'mobile', '') or ''
            company_data['email'] = getattr(company, 'email', '') or ''
            company_data['vat_number'] = company.tax_id or ''
            company_data['tax_id'] = company.tax_id or ''
            company_data['commercial_register'] = getattr(company, 'commercial_register', '') or ''
            company_data['website'] = getattr(company, 'website', '') or ''
            company_data['whatsapp'] = getattr(company, 'whatsapp', '') or ''
            company_data['facebook'] = getattr(company, 'facebook', '') or ''
            company_data['instagram'] = getattr(company, 'instagram', '') or ''
            company_data['twitter'] = getattr(company, 'twitter', '') or ''
            company_data['tiktok'] = getattr(company, 'tiktok', '') or ''
            company_data['youtube'] = getattr(company, 'youtube', '') or ''
            company_data['linkedin'] = getattr(company, 'linkedin', '') or ''
            if company.logo:
                company_data['logo'] = company.logo.url
    except:
        pass
    
    # بيانات الكاشير
    cashier_name = ''
    if order.session and order.session.user:
        user = order.session.user
        cashier_name = user.first_name or user.username
    
    # حساب المتبقي
    remaining = 0
    if order.paid_amount:
        remaining = float(order.total) - float(order.paid_amount)
    
    # اسم الفرع وبياناته
    branch_name = order.location.name if order.location else ''
    branch_phone = ''
    branch_address = ''
    
    # جلب بيانات المعرض الكاملة
    if order.location:
        try:
            from showrooms.models import Showroom
            showroom = Showroom.objects.filter(location=order.location).first()
            if showroom:
                branch_name = showroom.name_ar or showroom.name or order.location.name
                branch_phone = showroom.contact_phone or ''
                branch_address = showroom.address or ''
        except:
            pass
    
    auto_print = request.GET.get('auto_print', '0') == '1'
    
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
    
    if request.method == 'GET':
        return render(request, 'pos/invoice_a4.html', {
            'order': order,
            'lines': lines,
            'company': company_data,
            'cashier_name': cashier_name,
            'branch_name': branch_name,
            'branch_phone': branch_phone,
            'branch_address': branch_address,
            'all_branches': all_branches,
            'remaining': remaining,
            'now': datetime.now(),
            'auto_print': auto_print,
        })
    
    elif request.method == 'POST':
        return JsonResponse({
            'success': True,
            'message': 'سيتم فتح نافذة الطباعة',
            'print_url': f'/pos/order/{order_id}/invoice-a4/?auto_print=1'
        })
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def a4_printers_list(request: HttpRequest):
    """قائمة طابعات A4 المتاحة"""
    from .a4_printer import A4Printer
    
    printer = A4Printer()
    printers = printer.get_available_printers()
    
    # فلترة الطابعات (استبعاد الطابعات الحرارية و PDF)
    a4_printers = [
        p for p in printers 
        if not any(x in p['name'].lower() for x in ['xp-', 'thermal', 'pos', 'receipt'])
    ]
    
    return JsonResponse({
        'printers': a4_printers,
        'default': printer.get_default_printer(),
        'all_printers': printers
    })


# ===== Customer Installment Payment Views =====

@login_required
def customer_installments_api(request: HttpRequest):
    """API للبحث عن أقساط العميل"""
    from .models_installment import InstallmentPlan, Installment
    from partners.models import Customer
    from django.db.models import Q, Sum
    
    search = request.GET.get('q', '').strip()
    customer_id = request.GET.get('customer_id', '').strip()
    
    if not search and not customer_id:
        return JsonResponse({'customers': [], 'installments': []})
    
    try:
        # البحث عن العملاء
        customers_data = []
        if search:
            customers = Customer.objects.filter(
                Q(name__icontains=search) | 
                Q(phone__icontains=search)
            )[:10]
            
            for cust in customers:
                # التحقق من وجود أقساط للعميل
                plans_count = InstallmentPlan.objects.filter(
                    customer=cust, 
                    status='active'
                ).count()
                
                if plans_count > 0:
                    customers_data.append({
                        'id': cust.id,
                        'name': cust.name,
                        'phone': cust.phone or '',
                        'plans_count': plans_count,
                    })
        
        # جلب تفاصيل أقساط عميل محدد
        installments_data = []
        plans_data = []
        
        if customer_id:
            plans = InstallmentPlan.objects.filter(
                customer_id=customer_id,
                status='active'
            ).select_related('order')
            
            for plan in plans:
                # الأقساط غير المدفوعة
                pending_installments = plan.installments.filter(is_paid=False).order_by('due_date')
                paid_count = plan.installments.filter(is_paid=True).count()
                total_count = plan.installments.count()
                
                plan_info = {
                    'id': plan.id,
                    'order_number': plan.order.number if plan.order else f'#{plan.id}',
                    'total_amount': float(plan.total_amount),
                    'down_payment': float(plan.down_payment),
                    'remaining_amount': float(plan.remaining_amount),
                    'paid_amount': float(plan.paid_amount),
                    'remaining_to_pay': float(plan.remaining_to_pay),
                    'installment_amount': float(plan.installment_amount),
                    'number_of_installments': plan.number_of_installments,
                    'paid_count': paid_count,
                    'total_count': total_count,
                    'start_date': plan.start_date.isoformat() if plan.start_date else None,
                    'status': plan.status,
                    'installments': []
                }
                
                for inst in pending_installments:
                    plan_info['installments'].append({
                        'id': inst.id,
                        'number': inst.installment_number,
                        'amount': float(inst.amount),
                        'due_date': inst.due_date.isoformat(),
                        'due_date_formatted': inst.due_date.strftime('%Y/%m/%d'),
                        'is_overdue': inst.is_overdue,
                        'days_overdue': inst.days_overdue,
                        'late_fee': float(inst.late_fee),
                        'total_due': float(inst.amount + inst.late_fee),
                    })
                
                plans_data.append(plan_info)
        
        return JsonResponse({
            'success': True,
            'customers': customers_data,
            'plans': plans_data,
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def pay_customer_installment(request: HttpRequest):
    """تسديد قسط من واجهة POS"""
    from .models_installment import InstallmentPlan, Installment
    from decimal import Decimal
    from django.db import transaction
    import uuid
    
    if request.method != 'POST':
        return JsonResponse({'error': _('طريقة غير مسموحة')}, status=405)
    
    try:
        installment_id = request.POST.get('installment_id')
        amount = Decimal(request.POST.get('amount', '0') or '0')
        payment_method = request.POST.get('payment_method', 'cash')
        notes = request.POST.get('notes', '').strip()
        
        if not installment_id:
            return JsonResponse({'error': _('لم يتم تحديد القسط')}, status=400)
        
        with transaction.atomic():
            installment = get_object_or_404(Installment, pk=installment_id)
            plan = installment.plan
            
            if installment.is_paid:
                return JsonResponse({'error': _('هذا القسط مدفوع بالفعل')}, status=400)
            
            # التحقق من المبلغ
            total_due = installment.amount + installment.late_fee
            if amount <= 0:
                amount = total_due
            
            # إنشاء رقم إيصال فريد
            receipt_number = f"RCP-{uuid.uuid4().hex[:8].upper()}"
            
            # تسجيل الدفع
            installment.mark_as_paid(
                user=request.user,
                amount=amount,
                payment_method=payment_method,
                receipt_number=receipt_number
            )
            
            if notes:
                installment.notes = notes
                installment.save(update_fields=['notes'])
            
            # حساب الباقي
            remaining_installments = plan.installments.filter(is_paid=False).count()
            remaining_amount = plan.remaining_to_pay
            
            return JsonResponse({
                'success': True,
                'message': _('تم تسديد القسط بنجاح'),
                'receipt_number': receipt_number,
                'receipt_url': f'/pos/installment-receipt/{installment.id}/',
                'details': {
                    'installment_number': installment.installment_number,
                    'paid_amount': float(amount),
                    'remaining_installments': remaining_installments,
                    'remaining_amount': float(remaining_amount),
                    'plan_status': plan.status,
                }
            })
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def installment_payment_receipt(request: HttpRequest, installment_id: int):
    """طباعة إيصال تسديد القسط"""
    from .models_installment import Installment
    
    installment = get_object_or_404(Installment, pk=installment_id)
    plan = installment.plan
    
    # الأقساط المتبقية
    remaining_installments = plan.installments.filter(is_paid=False).order_by('due_date')[:3]
    paid_installments_count = plan.installments.filter(is_paid=True).count()
    
    # بيانات الشركة
    company_data = {
        'name': 'Tony ERP',
        'address': '',
        'phone': '',
        'logo': None,
    }
    try:
        from core.models import Company
        company = Company.objects.first()
        if company:
            company_data['name'] = company.name or 'Tony ERP'
            company_data['address'] = company.address or ''
            company_data['phone'] = company.phone or ''
            company_data['logo'] = company.logo.url if company.logo else None
    except:
        pass
    
    return render(request, 'pos/installment_payment_receipt.html', {
        'installment': installment,
        'plan': plan,
        'remaining_installments': remaining_installments,
        'paid_installments_count': paid_installments_count,
        'total_installments': plan.number_of_installments,
        'remaining_amount': plan.remaining_to_pay,
        'company': company_data,
        'cashier': request.user,
    })


# =========== APIs إدارة الطابعات ===========

@login_required
def list_printers_api(request: HttpRequest):
    """API للحصول على قائمة الطابعات المتاحة"""
    try:
        from .thermal_printer import ThermalPrinter, IS_LINUX, CUPS_AVAILABLE, WIN32_AVAILABLE
        
        printer = ThermalPrinter()
        printers = printer.get_available_printers()
        default_printer = printer.get_default_printer()
        
        return JsonResponse({
            'success': True,
            'printers': printers,
            'default_printer': default_printer,
            'system_info': {
                'is_linux': IS_LINUX,
                'cups_available': CUPS_AVAILABLE,
                'win32_available': WIN32_AVAILABLE,
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'printers': []
        })


@login_required  
def test_printer_api(request: HttpRequest):
    """API لاختبار الطباعة"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        import json
        data = json.loads(request.body) if request.body else {}
        printer_name = data.get('printer_name')
        
        from .thermal_printer import ThermalPrinter
        
        printer = ThermalPrinter(printer_name=printer_name)
        if not printer.connect():
            return JsonResponse({
                'success': False,
                'error': 'فشل الاتصال بالطابعة. تأكد من أنها متصلة ومعرّفة في النظام.'
            })
        
        try:
            success = printer.test_print()
            return JsonResponse({
                'success': success,
                'message': 'تم إرسال صفحة الاختبار للطابعة بنجاح' if success else 'فشل إرسال صفحة الاختبار'
            })
        finally:
            printer.disconnect()
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
def print_barcode_api(request: HttpRequest):
    """API لطباعة الباركود على الطابعة الحرارية"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        import json
        data = json.loads(request.body) if request.body else {}
        
        barcode_value = data.get('barcode')
        product_name = data.get('product_name', '')
        price = data.get('price', '')
        copies = int(data.get('copies', 1))
        printer_name = data.get('printer_name')
        
        if not barcode_value:
            return JsonResponse({
                'success': False,
                'error': 'رقم الباركود مطلوب'
            })
        
        from .thermal_printer import ThermalPrinter
        from inventory.barcode_utils import BarcodeGenerator
        
        # توليد صورة الباركود
        generator = BarcodeGenerator()
        barcode_buffer, barcode_base64 = generator.generate_barcode_image(
            barcode_value, 
            barcode_type='code128',
            width=2.0,
            height=12.0
        )
        
        if not barcode_buffer:
            return JsonResponse({
                'success': False,
                'error': 'فشل توليد صورة الباركود'
            })
        
        # الاتصال بالطابعة
        printer = ThermalPrinter(printer_name=printer_name)
        if not printer.connect():
            return JsonResponse({
                'success': False,
                'error': 'فشل الاتصال بالطابعة'
            })
        
        try:
            success = True
            for _ in range(copies):
                # طباعة النص أعلى الباركود
                if product_name:
                    printer.print_text(product_name, align='center')
                if price:
                    printer.print_text(f"السعر: {price}", align='center')
                
                # طباعة الباركود كنص (الرقم)
                printer.print_text(barcode_value, bold=True, align='center', cut=True)
            
            return JsonResponse({
                'success': success,
                'message': f'تم طباعة {copies} نسخة من الباركود بنجاح',
                'barcode': barcode_value
            })
        finally:
            printer.disconnect()
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
def printer_status_api(request: HttpRequest):
    """API للحصول على حالة الطابعة"""
    try:
        from .thermal_printer import ThermalPrinter, IS_LINUX, CUPS_AVAILABLE, WIN32_AVAILABLE
        import subprocess
        
        status = {
            'is_linux': IS_LINUX,
            'cups_available': CUPS_AVAILABLE,
            'win32_available': WIN32_AVAILABLE,
            'printers': [],
            'cups_status': None,
        }
        
        # فحص حالة CUPS على Linux
        if IS_LINUX:
            try:
                result = subprocess.run(['lpstat', '-p'], capture_output=True, text=True)
                status['cups_status'] = 'running' if result.returncode == 0 else 'stopped'
                
                # فحص كل طابعة
                if result.returncode == 0:
                    for line in result.stdout.strip().split('\n'):
                        if line:
                            parts = line.split()
                            if len(parts) >= 2 and parts[0] == 'printer':
                                printer_status = 'online' if 'idle' in line.lower() or 'is idle' in line.lower() else 'offline'
                                status['printers'].append({
                                    'name': parts[1],
                                    'status': printer_status,
                                    'details': ' '.join(parts[2:]) if len(parts) > 2 else ''
                                })
            except Exception as e:
                status['cups_error'] = str(e)
        
        return JsonResponse({
            'success': True,
            **status
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
