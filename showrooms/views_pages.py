from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext as _
from django.db import models
from django import forms
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Count, Avg, F
from datetime import timedelta
import json
import secrets
from .models import Showroom, ShowroomEmployee, POSDevice, AttendanceRecord, TemporaryWorker, ShowroomRentPayment
from accounting.models import JournalEntry, JournalEntryItem
from pos.models import POSOrder
from inventory.models import Location, Stock
from django.utils import timezone
from django.core.paginator import Paginator


class ShowroomSelectForm(forms.Form):
    showroom = forms.ModelChoiceField(queryset=Showroom.objects.none(), required=False, label=_('المعرض'))
    period = forms.CharField(required=False, label=_('الفترة (YYYY-MM)'))

    def __init__(self, *args, **kwargs):
        qs = kwargs.pop('showroom_qs', Showroom.objects.none())
        super().__init__(*args, **kwargs)
        self.fields['showroom'].queryset = qs


class ShowroomForm(forms.ModelForm):
    class Meta:
        model = Showroom
        fields = ['code', 'name', 'name_ar', 'location', 'manager', 'opening_date', 'address', 'city', 'is_active']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('مثال: S001')}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('اسم المعرض بالإنجليزية')}),
            'name_ar': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('اسم المعرض بالعربية')}),
            'location': forms.Select(attrs={'class': 'form-select'}),
            'manager': forms.Select(attrs={'class': 'form-select'}),
            'opening_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('العنوان التفصيلي')}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('المدينة')}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.fields['location'].queryset = Location.objects.filter(is_active=True).order_by('name')
        self.fields['manager'].queryset = User.objects.filter(is_active=True).order_by('username')
        self.fields['manager'].required = False


def _user_showrooms(user):
    if user.is_superuser:
        return Showroom.objects.all()
    assigned = ShowroomEmployee.objects.filter(user=user, active=True)
    # مدير/مشرف المعرض يرى المعارض المعيّن عليها فقط (حتى لو كان can_cross_access=True)
    if assigned.filter(role__in=['manager', 'supervisor']).exists():
        return Showroom.objects.filter(id__in=assigned.values_list('showroom_id', flat=True))
    if assigned.filter(can_cross_access=True).exists():
        return Showroom.objects.all()
    return Showroom.objects.filter(id__in=assigned.values_list('showroom_id', flat=True))


@login_required
def showroom_list_view(request):
    qs = _user_showrooms(request.user)
    from django.utils import timezone
    today = timezone.now().date()
    # Prefetch related manager to avoid N+1 on manager name
    qs = qs.select_related('manager', 'location')
    # Aggregate per-showroom metrics in one pass each (keep it lightweight)
    from pos.models import POSOrder
    from .models import ShowroomEmployee, POSDevice, AttendanceRecord
    paid_today = POSOrder.objects.filter(status='paid', created_at__date=today, showroom_id__in=qs.values_list('id', flat=True))
    sales_map = paid_today.filter(is_return=False).values('showroom_id').annotate(total=models.Sum('total'))
    returns_map = paid_today.filter(is_return=True).values('showroom_id').annotate(total=models.Sum('total'))
    sales_lookup = {r['showroom_id']: r['total'] or 0 for r in sales_map}
    returns_lookup = {r['showroom_id']: r['total'] or 0 for r in returns_map}
    emp_counts = ShowroomEmployee.objects.filter(active=True, showroom_id__in=qs).values('showroom_id').annotate(c=models.Count('id'))
    emp_lookup = {r['showroom_id']: r['c'] for r in emp_counts}
    dev_counts = POSDevice.objects.filter(is_active=True, showroom_id__in=qs).values('showroom_id').annotate(c=models.Count('id'), last=models.Max('last_seen'))
    dev_lookup = {r['showroom_id']: (r['c'], r['last']) for r in dev_counts}
    att_counts = AttendanceRecord.objects.filter(date=today, showroom_id__in=qs).values('showroom_id').annotate(present=models.Count('id'))
    att_lookup = {r['showroom_id']: r['present'] for r in att_counts}
    
    # إجماليات
    total_employees = sum(emp_lookup.values())
    total_sales = sum(sales_lookup.values())
    total_devices = sum(d[0] for d in dev_lookup.values())
    
    enriched = []
    for s in qs:
        sales = sales_lookup.get(s.id, 0) or 0
        returns = returns_lookup.get(s.id, 0) or 0
        net = sales - returns
        emp_total = emp_lookup.get(s.id, 0)
        dev_info = dev_lookup.get(s.id, (0, None))
        dev_total, last_seen = dev_info
        present = att_lookup.get(s.id, 0)
        enriched.append({
            'obj': s,
            'sales_today': sales,
            'returns_today': returns,
            'net_sales': net,
            'employees': emp_total,
            'devices': dev_total,
            'devices_last_seen': last_seen,
            'attendance_present': present,
        })
    return render(request, 'showrooms/list.html', {
        'showrooms': qs,
        'showrooms_enriched': enriched,
        'total_employees': total_employees,
        'total_sales': total_sales,
        'total_devices': total_devices,
    })


@login_required
def showroom_employees_view(request):
    qs = ShowroomEmployee.objects.select_related('showroom', 'user')
    allowed_showrooms = _user_showrooms(request.user)
    if not request.user.is_superuser:
        qs = qs.filter(showroom__in=allowed_showrooms)
    return render(request, 'showrooms/employees.html', {
        'employees': qs,
        'showrooms': allowed_showrooms,
    })


@login_required
def showroom_kpis_view(request):
    allowed_showrooms = _user_showrooms(request.user)
    showroom_id = request.GET.get('showroom')
    selected = None
    if showroom_id:
        selected = allowed_showrooms.filter(id=showroom_id).first()
    today = timezone.now().date()
    orders = POSOrder.objects.filter(created_at__date=today, status='paid')
    if selected:
        # Filter directly by POSOrder.showroom FK to avoid traversing Location reverse alias
        orders = orders.filter(showroom=selected)
    else:
        orders = orders.filter(showroom__in=allowed_showrooms)
    sales_today = orders.filter(is_return=False).aggregate(total=models.Sum('total')).get('total') or 0
    returns_today = orders.filter(is_return=True).aggregate(total=models.Sum('total')).get('total') or 0
    net_sales = (sales_today or 0) - (returns_today or 0)
    order_count = orders.count()
    avg_ticket = float(net_sales) / order_count if order_count else 0
    context = {
        'showrooms': allowed_showrooms,
        'selected_showroom': selected,
        'metrics': {
            'sales_today': sales_today,
            'returns_today': returns_today,
            'net_sales': net_sales,
            'orders': order_count,
            'avg_ticket': avg_ticket,
        },
    }
    return render(request, 'showrooms/kpis.html', context)


@login_required
def showroom_pnl_view(request):
    allowed_showrooms = _user_showrooms(request.user)
    form = ShowroomSelectForm(request.GET or None, showroom_qs=allowed_showrooms)
    data = None
    if form.is_valid():
        showroom = form.cleaned_data.get('showroom')
        period = form.cleaned_data.get('period')
        entries = JournalEntry.objects.filter(is_posted=True)
        if showroom:
            entries = entries.filter(showroom=showroom)
        if period:
            try:
                year, month = map(int, period.split('-'))
                entries = entries.filter(date__year=year, date__month=month)
            except Exception:
                period = None
        item_qs = JournalEntryItem.objects.filter(journal_entry__in=entries).select_related('account')
        revenue = 0; expense = 0
        for it in item_qs:
            if it.account.account_type == 'revenue':
                revenue += float(it.amount) * (1 if it.type == 'credit' else -1)
            elif it.account.account_type == 'expense':
                expense += float(it.amount) * (1 if it.type == 'debit' else -1)
        gross_profit = revenue - expense
        data = {
            'revenue': revenue,
            'expense': expense,
            'gross_profit': gross_profit,
            'period': period,
            'showroom': showroom,
        }
    return render(request, 'showrooms/pnl.html', {
        'form': form,
        'data': data,
    })


@login_required
def showroom_create_view(request):
    if request.method == 'POST':
        form = ShowroomForm(request.POST)
        if form.is_valid():
            showroom = form.save()
            messages.success(request, _('تم إنشاء المعرض بنجاح'))
            return redirect('showrooms:list')
    else:
        form = ShowroomForm()
    
    return render(request, 'showrooms/create.html', {
        'form': form,
        'title': _('إضافة معرض جديد'),
    })


@login_required
def showroom_edit_view(request, pk):
    showroom = get_object_or_404(Showroom, pk=pk)
    
    if request.method == 'POST':
        form = ShowroomForm(request.POST, instance=showroom)
        if form.is_valid():
            form.save()
            messages.success(request, _('تم تحديث المعرض بنجاح'))
            return redirect('showrooms:list')
    else:
        form = ShowroomForm(instance=showroom)
    
    return render(request, 'showrooms/create.html', {
        'form': form,
        'showroom': showroom,
        'title': _('تعديل المعرض'),
    })


@login_required
def showroom_delete_view(request, pk):
    showroom = get_object_or_404(Showroom, pk=pk)
    
    if request.method == 'POST':
        try:
            showroom.delete()
            messages.success(request, _('تم حذف المعرض بنجاح'))
        except Exception as e:
            messages.error(request, _('لا يمكن حذف المعرض: ') + str(e))
        return redirect('showrooms:list')
    
    return render(request, 'showrooms/delete_confirm.html', {
        'showroom': showroom,
    })


@login_required
def showroom_detail_view(request, pk):
    """صفحة تفاصيل المعرض"""
    showroom = get_object_or_404(Showroom.objects.select_related('location', 'manager'), pk=pk)
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    
    # تحديث المعرض النشط في الجلسة
    from .middleware import SESSION_KEY, ALL_SHOWROOMS_KEY
    if ALL_SHOWROOMS_KEY in request.session:
        del request.session[ALL_SHOWROOMS_KEY]
    request.session[SESSION_KEY] = showroom.id
    
    # إحصائيات المبيعات
    today_orders = POSOrder.objects.filter(showroom=showroom, created_at__date=today, status='paid')
    yesterday_orders = POSOrder.objects.filter(showroom=showroom, created_at__date=yesterday, status='paid')
    
    sales_today = today_orders.filter(is_return=False).aggregate(total=Sum('total'))['total'] or 0
    sales_yesterday = yesterday_orders.filter(is_return=False).aggregate(total=Sum('total'))['total'] or 0
    returns_today = today_orders.filter(is_return=True).aggregate(total=Sum('total'))['total'] or 0
    orders_count = today_orders.count()
    returns_count = today_orders.filter(is_return=True).count()
    
    # تغيير المبيعات
    sales_change = 0
    if sales_yesterday > 0:
        sales_change = ((sales_today - sales_yesterday) / sales_yesterday) * 100
    
    avg_ticket = sales_today / orders_count if orders_count > 0 else 0
    
    # الموظفين والحضور
    employees = ShowroomEmployee.objects.filter(showroom=showroom, active=True).select_related('user')
    attendance_today = AttendanceRecord.objects.filter(showroom=showroom, date=today)
    attendance_ids = set(attendance_today.values_list('employee_id', flat=True))
    
    for emp in employees:
        emp.attendance_today = emp.id in attendance_ids
    
    # الأجهزة
    devices = POSDevice.objects.filter(showroom=showroom)
    
    # أحدث الطلبات
    recent_orders = POSOrder.objects.filter(
        showroom=showroom, status='paid'
    ).select_related('customer').order_by('-created_at')[:10]
    
    # الأكثر مبيعاً
    from pos.models import POSOrderLine
    top_products = POSOrderLine.objects.filter(
        order__showroom=showroom,
        order__created_at__date=today,
        order__status='paid'
    ).values('product__name').annotate(
        total_qty=Sum('quantity'),
        total_sales=Sum(F('quantity') * F('price'))
    ).order_by('-total_sales')[:6]
    
    # بيانات الرسم البياني
    chart_labels = []
    chart_sales = []
    chart_returns = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        chart_labels.append(d.strftime('%a'))
        day_orders = POSOrder.objects.filter(showroom=showroom, created_at__date=d, status='paid')
        chart_sales.append(float(day_orders.filter(is_return=False).aggregate(t=Sum('total'))['t'] or 0))
        chart_returns.append(float(day_orders.filter(is_return=True).aggregate(t=Sum('total'))['t'] or 0))
    
    context = {
        'showroom': showroom,
        'stats': {
            'sales_today': sales_today,
            'sales_change': sales_change,
            'orders_count': orders_count,
            'avg_ticket': avg_ticket,
            'returns_today': returns_today,
            'returns_count': returns_count,
            'attendance_present': len(attendance_ids),
            'total_employees': employees.count(),
        },
        'employees': employees,
        'devices': devices,
        'recent_orders': recent_orders,
        'top_products': top_products,
        'chart_labels': json.dumps(chart_labels),
        'chart_sales': json.dumps(chart_sales),
        'chart_returns': json.dumps(chart_returns),
    }
    return render(request, 'showrooms/detail.html', context)


@login_required
def showroom_devices_view(request, pk):
    """إدارة أجهزة POS"""
    showroom = get_object_or_404(Showroom, pk=pk)
    devices = POSDevice.objects.filter(showroom=showroom)
    
    # إحصائيات
    now = timezone.now()
    online_threshold = now - timedelta(minutes=5)
    
    context = {
        'showroom': showroom,
        'devices': devices,
        'active_count': devices.filter(is_active=True).count(),
        'online_count': devices.filter(is_active=True, last_seen__gte=online_threshold).count(),
    }
    return render(request, 'showrooms/devices.html', context)


@login_required
def device_add_view(request, showroom_id):
    """إضافة جهاز جديد"""
    showroom = get_object_or_404(Showroom, pk=showroom_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        identifier = request.POST.get('identifier')
        is_active = request.POST.get('is_active') == 'on'
        
        api_key = secrets.token_hex(32)
        
        POSDevice.objects.create(
            showroom=showroom,
            name=name,
            identifier=identifier,
            api_key=api_key,
            is_active=is_active
        )
        messages.success(request, _('تم إضافة الجهاز بنجاح'))
    
    return redirect('showrooms:devices', pk=showroom_id)


@login_required
def device_toggle_view(request, pk):
    """تفعيل/تعطيل جهاز"""
    device = get_object_or_404(POSDevice, pk=pk)
    device.is_active = not device.is_active
    device.save()
    messages.success(request, _('تم تحديث حالة الجهاز'))
    return redirect('showrooms:devices', pk=device.showroom_id)


@login_required
def device_delete_view(request, pk):
    """حذف جهاز"""
    device = get_object_or_404(POSDevice, pk=pk)
    showroom_id = device.showroom_id
    device.delete()
    messages.success(request, _('تم حذف الجهاز'))
    return redirect('showrooms:devices', pk=showroom_id)


@login_required
def device_regenerate_key_view(request, pk):
    """إعادة توليد API Key"""
    device = get_object_or_404(POSDevice, pk=pk)
    device.api_key = secrets.token_hex(32)
    device.save()
    messages.success(request, _('تم إعادة توليد API Key'))
    return redirect('showrooms:devices', pk=device.showroom_id)


@login_required
def showroom_transfer_view(request, pk):
    """تحويل المخزون بين المعارض"""
    showroom = get_object_or_404(Showroom, pk=pk)
    other_showrooms = Showroom.objects.exclude(pk=pk).filter(is_active=True)
    
    # المخزون المتاح
    available_stock = Stock.objects.filter(
        location=showroom.location,
        quantity__gt=0
    ).select_related('product')
    
    if request.method == 'POST':
        to_showroom_id = request.POST.get('to_showroom')
        action = request.POST.get('action')
        notes = request.POST.get('notes', '')
        
        to_showroom = get_object_or_404(Showroom, pk=to_showroom_id)
        
        # معالجة المنتجات
        from inventory.models import StockTransfer, StockTransferItem
        
        transfer = StockTransfer.objects.create(
            from_location=showroom.location,
            to_location=to_showroom.location,
            notes=notes,
            created_by=request.user,
            status='draft' if action == 'draft' else 'pending'
        )
        
        # إضافة العناصر
        product_count = 0
        for key in request.POST:
            if key.startswith('products[') and key.endswith('][id]'):
                idx = key.split('[')[1].split(']')[0]
                product_id = request.POST.get(f'products[{idx}][id]')
                qty = int(request.POST.get(f'products[{idx}][qty]', 0))
                
                if product_id and qty > 0:
                    from inventory.models import Product
                    product = Product.objects.get(pk=product_id)
                    StockTransferItem.objects.create(
                        transfer=transfer,
                        product=product,
                        quantity=qty
                    )
                    product_count += 1
        
        if product_count > 0:
            if action == 'confirm':
                transfer.status = 'completed'
                transfer.save()
                messages.success(request, _('تم تأكيد التحويل بنجاح'))
            else:
                messages.success(request, _('تم حفظ التحويل كمسودة'))
        else:
            transfer.delete()
            messages.error(request, _('يجب إضافة منتج واحد على الأقل'))
        
        return redirect('showrooms:detail', pk=pk)
    
    context = {
        'showroom': showroom,
        'other_showrooms': other_showrooms,
        'available_stock': available_stock,
    }
    return render(request, 'showrooms/transfer.html', context)


@login_required
def showroom_employees_v2_view(request):
    """صفحة إدارة الموظفين المحسنة"""
    allowed_showrooms = _user_showrooms(request.user)
    selected_showroom_id = request.GET.get('showroom')
    selected_showroom = None
    
    employees = ShowroomEmployee.objects.select_related('showroom', 'user')
    if not request.user.is_superuser:
        employees = employees.filter(showroom__in=allowed_showrooms)
    
    if selected_showroom_id:
        selected_showroom = allowed_showrooms.filter(id=selected_showroom_id).first()
        if selected_showroom:
            employees = employees.filter(showroom=selected_showroom)
    
    # إحصائيات
    today = timezone.now().date()
    attendance_today = AttendanceRecord.objects.filter(date=today)
    attendance_ids = set(attendance_today.values_list('employee_id', flat=True))
    
    for emp in employees:
        emp.attendance_today = attendance_today.filter(employee=emp).first()
    
    # المستخدمين المتاحين للإضافة
    from django.contrib.auth import get_user_model
    User = get_user_model()
    assigned_users = ShowroomEmployee.objects.values_list('user_id', flat=True)
    available_users = User.objects.filter(is_active=True).exclude(id__in=assigned_users)
    
    context = {
        'employees': employees,
        'showrooms': allowed_showrooms,
        'selected_showroom': selected_showroom,
        'active_count': employees.filter(active=True).count(),
        'present_today': len([e for e in employees if e.attendance_today]),
        'available_users': available_users,
    }
    return render(request, 'showrooms/employees_v2.html', context)


@login_required
def employee_add_view(request):
    """إضافة موظف جديد"""
    if request.method == 'POST':
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        user_id = request.POST.get('user')
        showroom_id = request.POST.get('showroom')
        role = request.POST.get('role')
        active = request.POST.get('active') == 'on'
        can_cross_access = request.POST.get('can_cross_access') == 'on'
        
        user = get_object_or_404(User, pk=user_id)
        showroom = get_object_or_404(Showroom, pk=showroom_id)
        
        ShowroomEmployee.objects.create(
            user=user,
            showroom=showroom,
            role=role,
            active=active,
            can_cross_access=can_cross_access
        )
        messages.success(request, _('تم إضافة الموظف بنجاح'))
    
    return redirect('showrooms:employees_v2')


@login_required
def employee_toggle_view(request, pk):
    """تفعيل/تعطيل موظف"""
    emp = get_object_or_404(ShowroomEmployee, pk=pk)
    emp.active = not emp.active
    emp.save()
    messages.success(request, _('تم تحديث حالة الموظف'))
    return redirect('showrooms:employees_v2')


@login_required
def employee_delete_view(request, pk):
    """حذف موظف"""
    emp = get_object_or_404(ShowroomEmployee, pk=pk)
    emp.delete()
    messages.success(request, _('تم حذف الموظف'))
    return redirect('showrooms:employees_v2')


@login_required
def showroom_dashboard_view(request):
    """لوحة مؤشرات شاملة لجميع المعارض"""
    allowed_showrooms = _user_showrooms(request.user)
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    
    period = request.GET.get('period', 'today')
    if period == 'week':
        start_date = today - timedelta(days=7)
    elif period == 'month':
        start_date = today - timedelta(days=30)
    else:
        start_date = today
    
    # إجمالي المبيعات
    orders = POSOrder.objects.filter(
        showroom__in=allowed_showrooms,
        created_at__date__gte=start_date,
        status='paid'
    )
    total_sales = orders.filter(is_return=False).aggregate(t=Sum('total'))['t'] or 0
    total_returns = orders.filter(is_return=True).aggregate(t=Sum('total'))['t'] or 0
    total_orders = orders.count()
    avg_ticket = total_sales / total_orders if total_orders > 0 else 0
    
    # مبيعات الأمس للمقارنة
    yesterday_sales = POSOrder.objects.filter(
        showroom__in=allowed_showrooms,
        created_at__date=yesterday,
        status='paid',
        is_return=False
    ).aggregate(t=Sum('total'))['t'] or 0
    
    sales_change = 0
    if yesterday_sales > 0:
        sales_change = ((total_sales - yesterday_sales) / yesterday_sales) * 100
    
    # الحضور
    employees = ShowroomEmployee.objects.filter(showroom__in=allowed_showrooms, active=True)
    total_employees = employees.count()
    attendance = AttendanceRecord.objects.filter(showroom__in=allowed_showrooms, date=today)
    present_count = attendance.count()
    attendance_rate = (present_count / total_employees * 100) if total_employees > 0 else 0
    
    # الأجهزة
    now = timezone.now()
    devices = POSDevice.objects.filter(showroom__in=allowed_showrooms)
    total_devices = devices.count()
    online_devices = devices.filter(is_active=True, last_seen__gte=now - timedelta(minutes=5)).count()
    
    # أداء كل معرض
    showrooms_performance = []
    for showroom in allowed_showrooms:
        s_orders = orders.filter(showroom=showroom)
        s_sales = s_orders.filter(is_return=False).aggregate(t=Sum('total'))['t'] or 0
        s_orders_count = s_orders.count()
        s_avg = s_sales / s_orders_count if s_orders_count > 0 else 0
        
        s_emps = employees.filter(showroom=showroom).count()
        s_present = attendance.filter(showroom=showroom).count()
        s_att_pct = (s_present / s_emps * 100) if s_emps > 0 else 0
        
        # حساب الأداء (مبسط)
        performance = min(100, (s_sales / 10000 * 50) + (s_att_pct / 2))
        
        showrooms_performance.append({
            'showroom': showroom,
            'sales': s_sales,
            'orders': s_orders_count,
            'avg_ticket': s_avg,
            'attendance_pct': s_att_pct,
            'performance': performance,
        })
    
    # ترتيب حسب المبيعات
    showrooms_performance.sort(key=lambda x: x['sales'], reverse=True)
    
    # بيانات الرسوم البيانية
    showroom_labels = json.dumps([s.name_ar or s.name for s in allowed_showrooms])
    showroom_sales = json.dumps([float(next((p['sales'] for p in showrooms_performance if p['showroom'] == s), 0)) for s in allowed_showrooms])
    showroom_returns = json.dumps([0 for _ in allowed_showrooms])  # يمكن تحسينها لاحقاً
    
    # الأكثر مبيعاً
    from pos.models import POSOrderLine
    top_products = POSOrderLine.objects.filter(
        order__showroom__in=allowed_showrooms,
        order__created_at__date__gte=start_date,
        order__status='paid'
    ).values('product__name').annotate(
        qty=Sum('quantity'),
        total=Sum(F('quantity') * F('price'))
    ).order_by('-total')[:5]
    
    top_products_list = [{'name': p['product__name'], 'qty': p['qty'], 'total': p['total']} for p in top_products]
    
    # التنبيهات
    alerts = []
    for showroom in allowed_showrooms:
        # معرض بدون حضور
        s_emps = employees.filter(showroom=showroom).count()
        s_present = attendance.filter(showroom=showroom).count()
        if s_emps > 0 and s_present == 0:
            alerts.append({
                'showroom': showroom.name_ar or showroom.name,
                'message': _('لا يوجد حضور مسجل اليوم'),
                'type': 'warning',
                'icon': 'fa-user-clock'
            })
        
        # معرض بدون أجهزة نشطة
        s_devices = devices.filter(showroom=showroom, is_active=True).count()
        if s_devices == 0:
            alerts.append({
                'showroom': showroom.name_ar or showroom.name,
                'message': _('لا توجد أجهزة نشطة'),
                'type': 'danger',
                'icon': 'fa-desktop'
            })
    
    context = {
        'total_sales': total_sales,
        'total_orders': total_orders,
        'avg_ticket': avg_ticket,
        'sales_change': sales_change,
        'total_employees': total_employees,
        'present_count': present_count,
        'attendance_rate': attendance_rate,
        'total_devices': total_devices,
        'online_devices': online_devices,
        'showrooms_performance': showrooms_performance,
        'showroom_labels': showroom_labels,
        'showroom_sales': showroom_sales,
        'showroom_returns': showroom_returns,
        'top_products': top_products_list,
        'alerts': alerts,
        'period': period,
    }
    return render(request, 'showrooms/dashboard.html', context)


@login_required
def showroom_expense_add_view(request, pk):
    """إضافة مصروف للمعرض"""
    from .models import ShowroomExpense
    showroom = get_object_or_404(Showroom, pk=pk)
    
    if request.method == 'POST':
        amount = request.POST.get('amount')
        category = request.POST.get('category')
        description = request.POST.get('description', '')
        
        ShowroomExpense.objects.create(
            showroom=showroom,
            amount=amount,
            category=category,
            description=description,
            created_by=request.user
        )
        messages.success(request, _('تم تسجيل المصروف بنجاح'))
        return redirect('showrooms:detail', pk=pk)
    
    context = {
        'showroom': showroom,
        'expense_types': ShowroomExpense.ExpenseType.choices
    }
    return render(request, 'showrooms/expense_add.html', context)


# ============================================
# ميزة البحث عن المنتجات في المعارض الأخرى
# ============================================

@login_required
def product_availability_search(request):
    """
    البحث عن توفر منتج معين في جميع المعارض
    """
    from inventory.models import Product, Stock
    
    showrooms = _user_showrooms(request.user).filter(is_active=True)
    products = []
    search_results = []
    current_showroom = None
    
    # الحصول على المعرض الحالي للمستخدم
    employee = ShowroomEmployee.objects.filter(user=request.user, active=True).first()
    if employee:
        current_showroom = employee.showroom
    
    # البحث عن المنتجات
    query = request.GET.get('q', '').strip()
    product_id = request.GET.get('product_id')
    selected_showroom_id = request.GET.get('showroom_id')
    
    if selected_showroom_id:
        current_showroom = Showroom.objects.filter(id=selected_showroom_id).first()
    
    if query:
        products = Product.objects.filter(
            models.Q(name__icontains=query) | 
            models.Q(sku__icontains=query) |
            models.Q(barcode__icontains=query)
        )[:20]
    
    if product_id:
        product = get_object_or_404(Product, id=product_id)
        
        # جمع معلومات المخزون من جميع المعارض
        for showroom in showrooms:
            if showroom.location:
                stock = Stock.objects.filter(
                    product=product,
                    location=showroom.location
                ).first()
                
                qty = stock.quantity if stock else 0
                is_current = current_showroom and showroom.id == current_showroom.id
                
                search_results.append({
                    'showroom': showroom,
                    'quantity': qty,
                    'available': qty > 0,
                    'is_current': is_current,
                })
        
        context = {
            'product': product,
            'search_results': search_results,
            'current_showroom': current_showroom,
            'total_available': sum(r['quantity'] for r in search_results),
            'showrooms_with_stock': sum(1 for r in search_results if r['available']),
        }
        return render(request, 'showrooms/product_availability_result.html', context)
    
    context = {
        'query': query,
        'products': products,
        'showrooms': showrooms,
        'current_showroom': current_showroom,
    }
    return render(request, 'showrooms/product_availability_search.html', context)


@login_required
def product_availability_api(request):
    """
    API للبحث السريع عن توفر المنتج (AJAX)
    """
    from inventory.models import Product, Stock
    
    product_id = request.GET.get('product_id')
    if not product_id:
        return JsonResponse({'error': 'product_id required'}, status=400)
    
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)
    
    showrooms = _user_showrooms(request.user).filter(is_active=True)
    results = []
    
    for showroom in showrooms:
        if showroom.location:
            stock = Stock.objects.filter(
                product=product,
                location=showroom.location
            ).first()
            
            qty = stock.quantity if stock else 0
            results.append({
                'showroom_id': showroom.id,
                'showroom_code': showroom.code,
                'showroom_name': showroom.name_ar or showroom.name,
                'city': showroom.city,
                'quantity': qty,
                'available': qty > 0,
            })
    
    return JsonResponse({
        'product_id': product.id,
        'product_name': product.name,
        'product_sku': product.sku,
        'results': results,
        'total_quantity': sum(r['quantity'] for r in results),
    })


# ============================================
# ميزة تحويل الأموال بين المعارض
# ============================================

@login_required
def money_transfer_list(request):
    """
    قائمة تحويلات الأموال بين المعارض
    """
    from .models import ShowroomMoneyTransfer
    
    showrooms = _user_showrooms(request.user)
    showroom_ids = list(showrooms.values_list('id', flat=True))
    
    transfers = ShowroomMoneyTransfer.objects.filter(
        models.Q(from_showroom_id__in=showroom_ids) |
        models.Q(to_showroom_id__in=showroom_ids)
    ).select_related(
        'from_showroom', 'to_showroom', 'created_by', 'approved_by'
    ).order_by('-created_at')
    
    # فلترة
    status_filter = request.GET.get('status')
    if status_filter:
        transfers = transfers.filter(status=status_filter)
    
    showroom_filter = request.GET.get('showroom')
    if showroom_filter:
        transfers = transfers.filter(
            models.Q(from_showroom_id=showroom_filter) |
            models.Q(to_showroom_id=showroom_filter)
        )
    
    # إحصائيات
    pending_count = transfers.filter(status='pending').count()
    completed_today = transfers.filter(
        status='completed',
        completed_at__date=timezone.now().date()
    ).count()
    total_pending_amount = transfers.filter(status='pending').aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    context = {
        'transfers': transfers[:100],
        'showrooms': showrooms,
        'status_choices': ShowroomMoneyTransfer.Status.choices,
        'pending_count': pending_count,
        'completed_today': completed_today,
        'total_pending_amount': total_pending_amount,
        'current_status': status_filter,
        'current_showroom': showroom_filter,
    }
    return render(request, 'showrooms/money_transfer_list.html', context)


@login_required
def money_transfer_create(request):
    """
    إنشاء تحويل أموال جديد
    """
    from .models import ShowroomMoneyTransfer
    
    showrooms = _user_showrooms(request.user).filter(is_active=True)
    
    if request.method == 'POST':
        from_showroom_id = request.POST.get('from_showroom')
        to_showroom_id = request.POST.get('to_showroom')
        amount = request.POST.get('amount')
        transfer_method = request.POST.get('transfer_method', 'cash')
        reason = request.POST.get('reason', '')
        notes = request.POST.get('notes', '')
        
        # التحقق
        if from_showroom_id == to_showroom_id:
            messages.error(request, _('لا يمكن التحويل لنفس المعرض'))
            return redirect('showrooms:money_transfer_create')
        
        try:
            from_showroom = Showroom.objects.get(id=from_showroom_id)
            to_showroom = Showroom.objects.get(id=to_showroom_id)
            amount = float(amount)
            
            if amount <= 0:
                messages.error(request, _('المبلغ يجب أن يكون أكبر من صفر'))
                return redirect('showrooms:money_transfer_create')
            
            # إنشاء التحويل
            transfer = ShowroomMoneyTransfer.objects.create(
                from_showroom=from_showroom,
                to_showroom=to_showroom,
                amount=amount,
                transfer_method=transfer_method,
                reason=reason,
                notes=notes,
                created_by=request.user,
                bank_name=request.POST.get('bank_name', ''),
                bank_account=request.POST.get('bank_account', ''),
                cheque_number=request.POST.get('cheque_number', ''),
                cheque_date=request.POST.get('cheque_date') or None,
                reference_number=request.POST.get('reference_number', ''),
            )
            
            messages.success(request, _('تم إنشاء طلب التحويل بنجاح - رقم: %(num)s') % {'num': transfer.transfer_number})
            return redirect('showrooms:money_transfer_detail', pk=transfer.pk)
            
        except Exception as e:
            messages.error(request, _('حدث خطأ: %(error)s') % {'error': str(e)})
            return redirect('showrooms:money_transfer_create')
    
    context = {
        'showrooms': showrooms,
        'transfer_methods': ShowroomMoneyTransfer.TransferMethod.choices,
    }
    return render(request, 'showrooms/money_transfer_form.html', context)


@login_required
def money_transfer_detail(request, pk):
    """
    تفاصيل تحويل أموال
    """
    from .models import ShowroomMoneyTransfer
    
    transfer = get_object_or_404(ShowroomMoneyTransfer, pk=pk)
    
    # التحقق من الصلاحية
    showrooms = _user_showrooms(request.user)
    if not showrooms.filter(id__in=[transfer.from_showroom_id, transfer.to_showroom_id]).exists():
        messages.error(request, _('لا تملك صلاحية الوصول لهذا التحويل'))
        return redirect('showrooms:money_transfer_list')
    
    context = {
        'transfer': transfer,
    }
    return render(request, 'showrooms/money_transfer_detail.html', context)


@login_required
def money_transfer_action(request, pk, action):
    """
    إجراءات على تحويل الأموال (اعتماد، إتمام، رفض، إلغاء)
    """
    from .models import ShowroomMoneyTransfer
    
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    transfer = get_object_or_404(ShowroomMoneyTransfer, pk=pk)
    
    # التحقق من الصلاحية
    showrooms = _user_showrooms(request.user)
    if not showrooms.filter(id__in=[transfer.from_showroom_id, transfer.to_showroom_id]).exists():
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    success = False
    message = ''
    
    if action == 'approve':
        success = transfer.approve(request.user)
        message = _('تم اعتماد التحويل') if success else _('لا يمكن اعتماد هذا التحويل')
    
    elif action == 'complete':
        success = transfer.complete(request.user)
        message = _('تم إتمام التحويل') if success else _('لا يمكن إتمام هذا التحويل')
    
    elif action == 'reject':
        reason = request.POST.get('reason', '')
        success = transfer.reject(request.user, reason)
        message = _('تم رفض التحويل') if success else _('لا يمكن رفض هذا التحويل')
    
    elif action == 'cancel':
        success = transfer.cancel(request.user)
        message = _('تم إلغاء التحويل') if success else _('لا يمكن إلغاء هذا التحويل')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': success,
            'message': message,
            'status': transfer.status,
        })
    
    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)
    
    return redirect('showrooms:money_transfer_detail', pk=pk)


@login_required
def money_transfer_print(request, pk):
    """
    طباعة إيصال تحويل الأموال
    """
    from .models import ShowroomMoneyTransfer
    
    transfer = get_object_or_404(ShowroomMoneyTransfer, pk=pk)
    
    context = {
        'transfer': transfer,
    }
    return render(request, 'showrooms/money_transfer_print.html', context)


# ==========================================
# طلبات نقل المخزون بين المعارض
# ==========================================

@login_required
def stock_request_list(request):
    """
    قائمة طلبات نقل المخزون
    """
    from .models import ShowroomStockRequest
    
    showrooms = _user_showrooms(request.user)
    
    # جلب الطلبات المتعلقة بمعارض المستخدم
    requests_out = ShowroomStockRequest.objects.filter(requesting_showroom__in=showrooms)
    requests_in = ShowroomStockRequest.objects.filter(source_showroom__in=showrooms)
    all_requests = (requests_out | requests_in).distinct().select_related(
        'requesting_showroom', 'source_showroom', 'product', 'requested_by'
    ).order_by('-created_at')
    
    # فلترة
    status = request.GET.get('status')
    priority = request.GET.get('priority')
    direction = request.GET.get('direction')
    
    if status:
        all_requests = all_requests.filter(status=status)
    if priority:
        all_requests = all_requests.filter(priority=priority)
    if direction == 'out':
        all_requests = requests_out
    elif direction == 'in':
        all_requests = requests_in
    
    # إحصائيات
    stats = {
        'total': all_requests.count(),
        'pending': all_requests.filter(status='pending').count(),
        'in_transit': all_requests.filter(status='in_transit').count(),
        'delivered': all_requests.filter(status='delivered').count(),
    }
    
    context = {
        'requests': all_requests[:100],
        'stats': stats,
        'showrooms': showrooms,
        'status_choices': ShowroomStockRequest.Status.choices,
        'priority_choices': ShowroomStockRequest.Priority.choices,
        'page_title': _('طلبات نقل المخزون'),
    }
    return render(request, 'showrooms/stock_request_list.html', context)


@login_required  
def stock_request_create(request):
    """
    إنشاء طلب نقل مخزون جديد
    """
    from .models import ShowroomStockRequest, Showroom
    from inventory.models import Product
    
    showrooms = _user_showrooms(request.user)
    all_showrooms = Showroom.objects.filter(is_active=True)
    
    if request.method == 'POST':
        try:
            requesting_showroom = get_object_or_404(Showroom, pk=request.POST.get('requesting_showroom'))
            source_showroom = get_object_or_404(Showroom, pk=request.POST.get('source_showroom'))
            product = get_object_or_404(Product, pk=request.POST.get('product'))
            
            # التحقق من أن المعرض الطالب تابع للمستخدم
            if not showrooms.filter(pk=requesting_showroom.pk).exists():
                messages.error(request, _('ليس لديك صلاحية لهذا المعرض'))
                return redirect('showrooms:stock_request_create')
            
            stock_request = ShowroomStockRequest.objects.create(
                requesting_showroom=requesting_showroom,
                source_showroom=source_showroom,
                product=product,
                quantity_requested=int(request.POST.get('quantity', 1)),
                priority=request.POST.get('priority', 'normal'),
                reason=request.POST.get('reason', ''),
                customer_name=request.POST.get('customer_name', ''),
                customer_phone=request.POST.get('customer_phone', ''),
                needed_by=request.POST.get('needed_by') or None,
                notes=request.POST.get('notes', ''),
                requested_by=request.user,
            )
            
            messages.success(request, _('تم إنشاء طلب نقل المخزون بنجاح: {}').format(stock_request.request_number))
            return redirect('showrooms:stock_request_detail', pk=stock_request.pk)
        except Exception as e:
            messages.error(request, str(e))
    
    # جلب المنتجات للبحث
    products = Product.objects.all()[:100]
    
    context = {
        'showrooms': showrooms,
        'all_showrooms': all_showrooms,
        'products': products,
        'priority_choices': ShowroomStockRequest.Priority.choices,
        'page_title': _('طلب نقل مخزون جديد'),
    }
    return render(request, 'showrooms/stock_request_form.html', context)


@login_required
def stock_request_detail(request, pk):
    """
    تفاصيل طلب نقل المخزون
    """
    from .models import ShowroomStockRequest
    
    stock_request = get_object_or_404(
        ShowroomStockRequest.objects.select_related(
            'requesting_showroom', 'source_showroom', 'product',
            'requested_by', 'approved_by', 'shipped_by', 'received_by'
        ),
        pk=pk
    )
    
    # التحقق من الصلاحية
    showrooms = _user_showrooms(request.user)
    has_access = showrooms.filter(
        id__in=[stock_request.requesting_showroom_id, stock_request.source_showroom_id]
    ).exists()
    
    if not has_access and not request.user.is_superuser:
        messages.error(request, _('ليس لديك صلاحية لعرض هذا الطلب'))
        return redirect('showrooms:stock_request_list')
    
    # التحقق من المخزون المتاح في المعرض المصدر
    from inventory.models import Stock
    available_stock = 0
    try:
        stock = Stock.objects.get(
            product=stock_request.product,
            location=stock_request.source_showroom.location
        )
        available_stock = stock.quantity
    except Stock.DoesNotExist:
        pass
    
    context = {
        'request_obj': stock_request,
        'available_stock': available_stock,
        'is_requester': showrooms.filter(pk=stock_request.requesting_showroom_id).exists(),
        'is_source': showrooms.filter(pk=stock_request.source_showroom_id).exists(),
        'page_title': f"طلب نقل {stock_request.request_number}",
    }
    return render(request, 'showrooms/stock_request_detail.html', context)


@login_required
def stock_request_action(request, pk, action):
    """
    إجراءات على طلب نقل المخزون
    """
    from .models import ShowroomStockRequest
    
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    stock_request = get_object_or_404(ShowroomStockRequest, pk=pk)
    
    # التحقق من الصلاحية
    showrooms = _user_showrooms(request.user)
    is_requester = showrooms.filter(pk=stock_request.requesting_showroom_id).exists()
    is_source = showrooms.filter(pk=stock_request.source_showroom_id).exists()
    
    if not is_requester and not is_source and not request.user.is_superuser:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    success = False
    message = ''
    
    if action == 'approve' and is_source:
        quantity = request.POST.get('quantity')
        quantity = int(quantity) if quantity else None
        success = stock_request.approve(request.user, quantity)
        message = _('تم اعتماد الطلب') if success else _('لا يمكن اعتماد هذا الطلب')
    
    elif action == 'ship' and is_source:
        success = stock_request.ship(request.user)
        message = _('تم بدء الشحن') if success else _('لا يمكن شحن هذا الطلب')
    
    elif action == 'deliver' and is_requester:
        quantity = request.POST.get('quantity')
        quantity = int(quantity) if quantity else None
        success = stock_request.deliver(request.user, quantity)
        message = _('تم تأكيد الاستلام') if success else _('لا يمكن تأكيد استلام هذا الطلب')
    
    elif action == 'reject' and is_source:
        reason = request.POST.get('reason', '')
        success = stock_request.reject(request.user, reason)
        message = _('تم رفض الطلب') if success else _('لا يمكن رفض هذا الطلب')
    
    elif action == 'cancel':
        success = stock_request.cancel(request.user)
        message = _('تم إلغاء الطلب') if success else _('لا يمكن إلغاء هذا الطلب')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': success,
            'message': message,
            'status': stock_request.status,
        })
    
    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)
    
    return redirect('showrooms:stock_request_detail', pk=pk)


@login_required
def stock_request_from_search(request):
    """
    إنشاء طلب نقل مخزون من صفحة البحث عن المنتجات
    """
    from .models import ShowroomStockRequest, Showroom
    from inventory.models import Product
    
    if request.method != 'POST':
        return redirect('showrooms:product_search')
    
    showrooms = _user_showrooms(request.user)
    
    try:
        product = get_object_or_404(Product, pk=request.POST.get('product_id'))
        source_showroom = get_object_or_404(Showroom, pk=request.POST.get('source_showroom_id'))
        requesting_showroom = get_object_or_404(Showroom, pk=request.POST.get('requesting_showroom_id'))
        
        # التحقق من أن المعرض الطالب تابع للمستخدم
        if not showrooms.filter(pk=requesting_showroom.pk).exists():
            messages.error(request, _('ليس لديك صلاحية لهذا المعرض'))
            return redirect('showrooms:product_search')
        
        stock_request = ShowroomStockRequest.objects.create(
            requesting_showroom=requesting_showroom,
            source_showroom=source_showroom,
            product=product,
            quantity_requested=int(request.POST.get('quantity', 1)),
            priority=request.POST.get('priority', 'normal'),
            reason=_('طلب من صفحة البحث عن المنتجات'),
            requested_by=request.user,
        )
        
        messages.success(request, _('تم إنشاء طلب نقل المخزون بنجاح: {}').format(stock_request.request_number))
        return redirect('showrooms:stock_request_detail', pk=stock_request.pk)
    
    except Exception as e:
        messages.error(request, str(e))
        return redirect('showrooms:product_search')


# ============================================
# إدارة ملكية المعارض - Property Management
# ============================================

@login_required
def property_management_view(request):
    """صفحة إدارة ملكية المعارض"""
    showrooms = _user_showrooms(request.user)
    
    # إحصائيات
    stats = {
        'total': showrooms.count(),
        'owned': showrooms.filter(property_type='owned').count(),
        'rented': showrooms.filter(property_type='rented').count(),
        'temporary': showrooms.filter(property_type='temporary').count(),
        'total_rent': showrooms.filter(property_type='rented').aggregate(
            total=Sum('monthly_rent'))['total'] or 0,
    }
    
    # المعارض المستأجرة مع الدفعات القادمة
    rented_showrooms = showrooms.filter(property_type='rented')
    
    # الدفعات المتأخرة
    overdue_payments = ShowroomRentPayment.objects.filter(
        showroom__in=showrooms,
        status='overdue'
    ).select_related('showroom')
    
    # العقود القريبة من الانتهاء (30 يوم)
    from datetime import date, timedelta
    expiring_soon = showrooms.filter(
        contract_end_date__isnull=False,
        contract_end_date__lte=date.today() + timedelta(days=30),
        contract_end_date__gte=date.today()
    )
    
    context = {
        'showrooms': showrooms,
        'stats': stats,
        'rented_showrooms': rented_showrooms,
        'overdue_payments': overdue_payments,
        'expiring_soon': expiring_soon,
        'title': _('إدارة ملكية المعارض'),
    }
    return render(request, 'showrooms/property_management.html', context)


@login_required
def temporary_workers_list(request):
    """قائمة العمالة المؤقتة"""
    showrooms = _user_showrooms(request.user)
    workers = TemporaryWorker.objects.filter(showroom__in=showrooms).select_related('showroom')
    
    # فلتر حسب المعرض
    showroom_id = request.GET.get('showroom')
    if showroom_id:
        workers = workers.filter(showroom_id=showroom_id)
    
    # فلتر حسب الحالة
    status = request.GET.get('status')
    if status == 'active':
        workers = workers.filter(is_active=True)
    elif status == 'inactive':
        workers = workers.filter(is_active=False)
    
    # إحصائيات
    stats = {
        'total': workers.count(),
        'active': workers.filter(is_active=True).count(),
        'total_wages': workers.filter(is_active=True).aggregate(
            total=Sum(F('daily_wage') * F('days_worked')))['total'] or 0,
    }
    
    paginator = Paginator(workers, 20)
    page = request.GET.get('page')
    workers = paginator.get_page(page)
    
    context = {
        'workers': workers,
        'showrooms': showrooms,
        'stats': stats,
        'title': _('العمالة المؤقتة'),
    }
    return render(request, 'showrooms/temporary_workers_list.html', context)


@login_required
def temporary_worker_create(request):
    """إضافة عامل مؤقت"""
    showrooms = _user_showrooms(request.user)
    
    if request.method == 'POST':
        try:
            worker = TemporaryWorker.objects.create(
                showroom_id=request.POST.get('showroom'),
                worker_name=request.POST.get('worker_name'),
                worker_phone=request.POST.get('worker_phone'),
                national_id=request.POST.get('national_id'),
                job_title=request.POST.get('job_title'),
                worker_type=request.POST.get('worker_type', 'daily'),
                daily_wage=request.POST.get('daily_wage') or None,
                total_contract_amount=request.POST.get('total_contract_amount') or None,
                start_date=request.POST.get('start_date'),
                end_date=request.POST.get('end_date') or None,
                days_worked=request.POST.get('days_worked') or 0,
                notes=request.POST.get('notes'),
                created_by=request.user,
            )
            messages.success(request, _('تم إضافة العامل بنجاح: {}').format(worker.worker_name))
            return redirect('showrooms:temporary_workers')
        except Exception as e:
            messages.error(request, str(e))
    
    context = {
        'showrooms': showrooms,
        'title': _('إضافة عامل مؤقت'),
    }
    return render(request, 'showrooms/temporary_worker_form.html', context)


@login_required
def temporary_worker_detail(request, pk):
    """تفاصيل العامل المؤقت"""
    showrooms = _user_showrooms(request.user)
    worker = get_object_or_404(TemporaryWorker, pk=pk, showroom__in=showrooms)
    
    context = {
        'worker': worker,
        'title': worker.worker_name,
    }
    return render(request, 'showrooms/temporary_worker_detail.html', context)


@login_required  
def temporary_worker_pay(request, pk):
    """دفع أجر العامل المؤقت"""
    showrooms = _user_showrooms(request.user)
    worker = get_object_or_404(TemporaryWorker, pk=pk, showroom__in=showrooms)
    
    if request.method == 'POST':
        try:
            from .accounting_helpers import create_temporary_worker_payment_entry
            
            payment_method = request.POST.get('payment_method', 'cash')
            notes = request.POST.get('notes', '')
            
            # تسجيل القيد المحاسبي
            entry = create_temporary_worker_payment_entry(worker, request.user)
            
            # تحديث حالة العامل
            worker.is_paid = True
            worker.is_active = False
            worker.save()
            
            messages.success(request, _('تم دفع أجر العامل بنجاح'))
            return redirect('showrooms:temporary_worker_detail', pk=pk)
        except Exception as e:
            messages.error(request, str(e))
    
    context = {
        'worker': worker,
        'title': _('دفع أجر العامل'),
    }
    return render(request, 'showrooms/temporary_worker_pay.html', context)


@login_required
def rent_payments_list(request):
    """قائمة دفعات الإيجار"""
    showrooms = _user_showrooms(request.user)
    payments = ShowroomRentPayment.objects.filter(showroom__in=showrooms).select_related('showroom')
    
    # فلتر حسب المعرض
    showroom_id = request.GET.get('showroom')
    if showroom_id:
        payments = payments.filter(showroom_id=showroom_id)
    
    # فلتر حسب الحالة
    status = request.GET.get('status')
    if status:
        payments = payments.filter(status=status)
    
    # إحصائيات
    stats = {
        'total': payments.count(),
        'pending': payments.filter(status='pending').count(),
        'paid': payments.filter(status='paid').count(),
        'overdue': payments.filter(status='overdue').count(),
        'total_pending_amount': payments.filter(status='pending').aggregate(
            total=Sum('amount'))['total'] or 0,
        'total_overdue_amount': payments.filter(status='overdue').aggregate(
            total=Sum('amount'))['total'] or 0,
    }
    
    paginator = Paginator(payments.order_by('-payment_date'), 20)
    page = request.GET.get('page')
    payments = paginator.get_page(page)
    
    context = {
        'payments': payments,
        'showrooms': showrooms.filter(property_type='rented'),
        'stats': stats,
        'title': _('دفعات الإيجار'),
    }
    return render(request, 'showrooms/rent_payments_list.html', context)


@login_required
def rent_payment_create(request):
    """إنشاء دفعة إيجار"""
    showrooms = _user_showrooms(request.user).filter(property_type='rented')
    
    if request.method == 'POST':
        try:
            payment = ShowroomRentPayment.objects.create(
                showroom_id=request.POST.get('showroom'),
                payment_date=request.POST.get('payment_date'),
                amount=request.POST.get('amount'),
                notes=request.POST.get('notes'),
            )
            messages.success(request, _('تم إنشاء دفعة الإيجار بنجاح'))
            return redirect('showrooms:rent_payments')
        except Exception as e:
            messages.error(request, str(e))
    
    context = {
        'showrooms': showrooms,
        'title': _('إنشاء دفعة إيجار'),
    }
    return render(request, 'showrooms/rent_payment_form.html', context)


@login_required
def rent_payment_pay(request, pk):
    """سداد دفعة الإيجار"""
    showrooms = _user_showrooms(request.user)
    payment = get_object_or_404(ShowroomRentPayment, pk=pk, showroom__in=showrooms)
    
    if request.method == 'POST':
        try:
            payment_ref = request.POST.get('payment_reference', '')
            notes = request.POST.get('notes', '')
            
            # تسجيل السداد
            payment.mark_as_paid(user=request.user, payment_ref=payment_ref)
            
            messages.success(request, _('تم سداد دفعة الإيجار بنجاح'))
            return redirect('showrooms:rent_payments')
        except Exception as e:
            messages.error(request, str(e))
    
    context = {
        'payment': payment,
        'title': _('سداد دفعة الإيجار'),
    }
    return render(request, 'showrooms/rent_payment_pay.html', context)


@login_required
def auto_generate_rent_payments(request, showroom_id):
    """إنشاء دفعات إيجار تلقائية"""
    showrooms = _user_showrooms(request.user)
    showroom = get_object_or_404(Showroom, pk=showroom_id, pk__in=showrooms)
    
    if request.method == 'POST':
        try:
            from .accounting_helpers import auto_create_monthly_rent_payments
            
            months = int(request.POST.get('months', 12))
            payments = auto_create_monthly_rent_payments(showroom, months=months)
            
            messages.success(request, _('تم إنشاء {} دفعة إيجار بنجاح').format(len(payments)))
            return redirect('showrooms:rent_payments')
        except Exception as e:
            messages.error(request, str(e))
    
    return redirect('showrooms:property_management')
