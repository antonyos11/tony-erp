"""Fleet app views.

Rewritten (full overwrite) to ensure clean indentation (spaces only) and remove any
hidden or non-printable characters that previously triggered intermittent
IndentationError in the Django autoreloader (observed around vehicle_create).
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden, HttpResponse
from django.utils import timezone
from django.db.models import Sum, Q
from django.utils.dateparse import parse_date
from django import forms
import csv
from openpyxl import Workbook  # type: ignore
try:
    import reportlab  # noqa: F401
    _REPORTLAB_AVAILABLE = True
except Exception:
    _REPORTLAB_AVAILABLE = False

from .models import (
    Vehicle,
    Driver,
    Trip,
    VehicleExpense,
    VehicleDocument,
    DriverViolation,
    DriverAdvance,
)
from .utils import log_activity


def require_fleet_access(view_func):
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())
        has_perm = getattr(request.user, 'has_module_permission', None)
        if callable(has_perm) and has_perm('fleet', 'view'):
            return view_func(request, *args, **kwargs)
        return HttpResponseForbidden('ليست لديك صلاحية الوصول لوحدة الأسطول')
    return _wrapped


def require_fleet_permission(codename):
    """تحقق من صلاحية محددة داخل تطبيق الأسطول.

    الصلاحيات معرفة في Meta لكل موديل (manage_vehicle, manage_trip ...الخ).
    يسمح للمستخدم الخارق دائماً.
    """
    def decorator(view_func):
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(request.get_full_path())
            if request.user.is_superuser or request.user.has_perm(f"fleet.{codename}"):
                return view_func(request, *args, **kwargs)
            return HttpResponseForbidden('ليست لديك الصلاحية المطلوبة')
        return _wrapped
    return decorator


class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = [
            "name",
            "plate_number",
            "type",
            "model_year",
            "status",
            "current_odometer",
            "notes",
        ]


class DriverForm(forms.ModelForm):
    class Meta:
        model = Driver
        fields = [
            "name",
            "phone",
            "license_number",
            "license_expiry",
            "active",
            "notes",
        ]


class TripForm(forms.ModelForm):
    class Meta:
        model = Trip
        fields = [
            "vehicle",
            "driver",
            "start_time",
            "end_time",
            "origin",
            "destination",
            "odometer_start",
            "odometer_end",
            "distance_km",
            "purpose",
            "notes",
        ]
        widgets = {
            "start_time": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "end_time": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }


class VehicleExpenseForm(forms.ModelForm):
    class Meta:
        model = VehicleExpense
        fields = [
            "vehicle",
            "driver",
            "category",
            "description",
            "amount",
            "date",
            "advance",
        ]
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}


class MaintenanceExpenseForm(VehicleExpenseForm):
    """نموذج مختصر لإضافة مصروف صيانة فقط.

    يثبت التصنيف على "maintenance" ويخفيه من الواجهة.
    """
    class Meta(VehicleExpenseForm.Meta):
        fields = [
            "vehicle",
            "driver",
            "description",
            "amount",
            "date",
            "advance",
        ]
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}


class VehicleDocumentForm(forms.ModelForm):
    class Meta:
        model = VehicleDocument
        fields = ["vehicle", "doc_type", "file", "expiry_date", "notes"]
        widgets = {"expiry_date": forms.DateInput(attrs={"type": "date"})}


class DriverViolationForm(forms.ModelForm):
    class Meta:
        model = DriverViolation
        fields = [
            "driver",
            "vehicle",
            "violation_type",
            "date",
            "amount",
            "receipt",
            "is_paid",
            "notes",
        ]
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}


class DriverAdvanceForm(forms.ModelForm):
    class Meta:
        model = DriverAdvance
        fields = [
            "driver",
            "date",
            "amount",
            "description",
            "status",
            "settlement_date",
            "notes",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "settlement_date": forms.DateInput(attrs={"type": "date"}),
        }


@require_fleet_access
def dashboard(request):
    vehicles = Vehicle.objects.all()
    today = timezone.now().date()
    stats = {
        'vehicles': vehicles.count(),
        'drivers': Driver.objects.count(),
        'trips_today': Trip.objects.filter(start_time__date=today).count(),
        'expenses_month': VehicleExpense.objects.filter(
            date__month=today.month, date__year=today.year
        ).aggregate(total=Sum('amount'))['total'] or 0,
        'unpaid_violations': DriverViolation.objects.filter(is_paid=False).count(),
        'open_advances': DriverAdvance.objects.filter(status='open').count(),
    }
    top_expenses = (
        VehicleExpense.objects.values('vehicle__plate_number')
        .annotate(total=Sum('amount'))
        .order_by('-total')[:5]
    )
    expiring_docs = VehicleDocument.objects.expiring_within(30).order_by('expiry_date')[:20]
    expired_docs = VehicleDocument.objects.expired().order_by('-expiry_date')[:20]
    context = {
        'stats': stats,
        'top_expenses': top_expenses,
        'vehicles': vehicles,
        'expiring_docs': expiring_docs,
        'expired_docs': expired_docs,
    }
    return render(request, 'fleet/dashboard.html', context)


@require_fleet_access
def distance_report(request):
    """تقرير المسافات المقطوعة لكل مركبة شهرياً مع الإجمالي.
    يدعم نطاق تواريخ (start,end) اختيارياً.
    """
    from django.utils.dateparse import parse_date
    start = parse_date(request.GET.get('start')) if request.GET.get('start') else None
    end = parse_date(request.GET.get('end')) if request.GET.get('end') else None

    trips = Trip.objects.select_related('vehicle')
    if start:
        trips = trips.filter(start_time__date__gte=start)
    if end:
        trips = trips.filter(start_time__date__lte=end)

    # تجميع حسب المركبة والشهر
    from django.db.models.functions import TruncMonth
    monthly = (
        trips.annotate(month=TruncMonth('start_time'))
             .values('vehicle__plate_number', 'month')
             .annotate(total_km=Sum('distance_km'))
             .order_by('vehicle__plate_number', 'month')
    )

    # إعادة تشكيل لعرض جدولي: {vehicle: {month_str: total_km}}
    data = {}
    months_order = []
    for row in monthly:
        month_str = row['month'].strftime('%Y-%m') if row['month'] else 'غير محدد'
        if month_str not in months_order:
            months_order.append(month_str)
        veh = row['vehicle__plate_number'] or 'غير معروف'
        data.setdefault(veh, {})[month_str] = float(row['total_km'] or 0)

    # إجمالي لكل مركبة
    summary_rows = []
    for veh, km_map in data.items():
        total = sum(km_map.values())
        summary_rows.append({
            'vehicle': veh,
            'months': km_map,
            'total': total,
        })
    # ترتيب تنازلي حسب الإجمالي
    summary_rows.sort(key=lambda r: r['total'], reverse=True)

    # حساب مصروفات الوقود لكل مركبة في نفس النطاق لرصد المركبات ذات مسافة عالية بدون وقود
    fuel_expenses_qs = VehicleExpense.objects.filter(category='fuel')
    if start:
        fuel_expenses_qs = fuel_expenses_qs.filter(date__gte=start)
    if end:
        fuel_expenses_qs = fuel_expenses_qs.filter(date__lte=end)
    fuel_map = {
        row['vehicle__plate_number']: float(row['total'] or 0)
        for row in fuel_expenses_qs.values('vehicle__plate_number').annotate(total=Sum('amount'))
    }
    anomalies = []
    for r in summary_rows:
        fuel_total = fuel_map.get(r['vehicle'], 0.0)
        if r['total'] >= 1000 and fuel_total == 0:  # قاعدة بسيطة: أكثر من 1000 كم بلا وقود
            anomalies.append({
                'vehicle': r['vehicle'],
                'distance': r['total'],
                'fuel': fuel_total,
            })

    # إعداد بيانات الرسم البياني: أعلى 5 مركبات حسب الإجمالي
    import json
    top_for_chart = summary_rows[:5]
    chart_labels = months_order
    chart_datasets = []
    colors = ['#0d6efd', '#198754', '#dc3545', '#fd7e14', '#20c997']
    for idx, row in enumerate(top_for_chart):
        data_points = [row['months'].get(m, 0) for m in months_order]
        chart_datasets.append({
            'label': row['vehicle'],
            'data': data_points,
            'borderColor': colors[idx % len(colors)],
            'backgroundColor': colors[idx % len(colors)] + '33',
            'tension': 0.25,
        })

    context = {
        'rows': summary_rows,
        'months_order': months_order,
        'start': start,
        'end': end,
        'anomalies': anomalies,
        'chart_labels_json': json.dumps(chart_labels, ensure_ascii=False),
        'chart_datasets_json': json.dumps(chart_datasets, ensure_ascii=False),
    }
    return render(request, 'fleet/distance_report.html', context)


@require_fleet_access
def vehicle_list(request):
    return render(request, 'fleet/vehicle_list.html', {'vehicles': Vehicle.objects.all()})


@require_fleet_access
def vehicle_detail(request, pk):
    v = get_object_or_404(Vehicle, pk=pk)
    recent_expenses = v.expenses.select_related('vehicle').order_by('-date')[:20]
    trips = v.trips.select_related('driver').order_by('-start_time')[:20]
    return render(
        request,
        'fleet/vehicle_detail.html',
        {
            'vehicle': v,
            'recent_expenses': recent_expenses,
            'trips': trips,
            'by_cat': v.expenses_by_category(),
        },
    )


@require_fleet_access
@require_fleet_permission('manage_vehicle')
def vehicle_create(request):
    form = VehicleForm(request.POST or None)
    # NOTE: This block was previously implicated in an IndentationError due to
    # an invisible character after the 'if' line. Rewriting ensures only ASCII
    # spaces are used for indentation.
    if form.is_valid():
        obj = form.save()
        log_activity(
            request,
            'create_vehicle',
            object_id=obj.pk,
            description=f'إنشاء مركبة {obj.plate_number}',
        )
        return redirect('fleet:vehicle_list')
    return render(
        request,
        'fleet/form.html',
        {'form': form, 'title': 'مركبة جديدة'},
    )


@require_fleet_access
@require_fleet_permission('manage_vehicle')
def vehicle_update(request, pk):
    v = get_object_or_404(Vehicle, pk=pk)
    form = VehicleForm(request.POST or None, instance=v)
    if form.is_valid():
        obj = form.save()
        log_activity(
            request,
            'update_vehicle',
            object_id=obj.pk,
            description=f'تعديل مركبة {obj.plate_number}',
        )
        return redirect('fleet:vehicle_detail', pk=v.pk)
    return render(
        request,
        'fleet/form.html',
        {'form': form, 'title': f'تعديل مركبة {v.plate_number}'},
    )


@require_fleet_access
@require_fleet_permission('manage_vehicle')
def vehicle_delete(request, pk):
    v = get_object_or_404(Vehicle, pk=pk)
    if request.method == 'POST':
        v.delete()
        log_activity(request, 'delete_vehicle', object_id=pk, description='حذف مركبة')
        return redirect('fleet:vehicle_list')
    return render(
        request,
        'fleet/confirm_delete.html',
        {'object': v, 'title': f'حذف مركبة {v.plate_number}'},
    )


@require_fleet_access
def driver_list(request):
    return render(request, 'fleet/driver_list.html', {'drivers': Driver.objects.all()})


@require_fleet_access
@require_fleet_permission('manage_driver')
def driver_create(request):
    form = DriverForm(request.POST or None)
    if form.is_valid():
        obj = form.save()
        log_activity(
            request,
            'create_driver',
            object_id=obj.pk,
            description=f'إنشاء سائق {obj.name}',
        )
        return redirect('fleet:driver_list')
    return render(request, 'fleet/form.html', {'form': form, 'title': 'سائق جديد'})


@require_fleet_access
@require_fleet_permission('manage_driver')
def driver_update(request, pk):
    d = get_object_or_404(Driver, pk=pk)
    form = DriverForm(request.POST or None, instance=d)
    if form.is_valid():
        obj = form.save()
        log_activity(
            request,
            'update_driver',
            object_id=obj.pk,
            description=f'تعديل سائق {obj.name}',
        )
        return redirect('fleet:driver_list')
    return render(request, 'fleet/form.html', {'form': form, 'title': f'تعديل سائق {d.name}'})


@require_fleet_access
@require_fleet_permission('manage_driver')
def driver_delete(request, pk):
    d = get_object_or_404(Driver, pk=pk)
    if request.method == 'POST':
        d.delete()
        log_activity(request, 'delete_driver', object_id=pk, description='حذف سائق')
        return redirect('fleet:driver_list')
    return render(
        request,
        'fleet/confirm_delete.html',
        {'object': d, 'title': f'حذف سائق {d.name}'},
    )


@require_fleet_access
def trip_list(request):
    trips = Trip.objects.select_related('vehicle', 'driver')[:200]
    return render(request, 'fleet/trip_list.html', {'trips': trips})


@require_fleet_access
@require_fleet_permission('manage_trip')
def trip_create(request):
    form = TripForm(request.POST or None)
    if form.is_valid():
        obj = form.save()
        log_activity(
            request,
            'create_trip',
            object_id=obj.pk,
            description=f'رحلة {obj.origin}->{obj.destination}',
        )
        return redirect('fleet:trip_list')
    return render(request, 'fleet/form.html', {'form': form, 'title': 'رحلة جديدة'})


@require_fleet_access
@require_fleet_permission('manage_trip')
def trip_update(request, pk):
    t = get_object_or_404(Trip, pk=pk)
    form = TripForm(request.POST or None, instance=t)
    if form.is_valid():
        obj = form.save()
        log_activity(request, 'update_trip', object_id=obj.pk, description='تعديل رحلة')
        return redirect('fleet:trip_list')
    return render(request, 'fleet/form.html', {'form': form, 'title': 'تعديل رحلة'})


@require_fleet_access
@require_fleet_permission('manage_trip')
def trip_close(request, pk):
    """إغلاق رحلة: ضبط end_time الآن إن لم يكن محدداً، وملء odometer_end بالعداد الحالي عند الحاجة."""
    trip = get_object_or_404(Trip, pk=pk)
    changed = False
    now = timezone.now()
    if not trip.end_time:
        trip.end_time = now
        changed = True
    # ملء odometer_end إذا مفقود
    if trip.odometer_start is not None and trip.odometer_end is None and trip.vehicle:
        # استخدم العداد الحالي للمركبة لو أعلى أو مساوي للبداية
        if trip.vehicle.current_odometer >= trip.odometer_start:
            trip.odometer_end = trip.vehicle.current_odometer
            changed = True
    # لو لا توجد أي قراءات وعداد المركبة موجود، نضع بداية ونهاية متماثلين (لا مسافة)
    if trip.odometer_start is None and trip.odometer_end is None and trip.vehicle:
        trip.odometer_start = trip.vehicle.current_odometer
        trip.odometer_end = trip.vehicle.current_odometer
        changed = True
    if changed:
        trip.save()
        log_activity(request, 'close_trip', object_id=trip.pk, description='إغلاق رحلة')
    return redirect('fleet:trip_list')


@require_fleet_access
@require_fleet_permission('manage_trip')
def trip_delete(request, pk):
    t = get_object_or_404(Trip, pk=pk)
    if request.method == 'POST':
        t.delete()
        log_activity(request, 'delete_trip', object_id=pk, description='حذف رحلة')
        return redirect('fleet:trip_list')
    return render(request, 'fleet/confirm_delete.html', {'object': t, 'title': 'حذف رحلة'})


@require_fleet_access
def expense_list(request):
    expenses = VehicleExpense.objects.select_related('vehicle')[:200]
    categories = VehicleExpense.objects.values('category').annotate(total=Sum('amount'))
    return render(
        request,
        'fleet/expense_list.html',
        {'expenses': expenses, 'categories': categories},
    )


@require_fleet_access
def maintenance_list(request):
    """عرض مصروفات الصيانة فقط مع إجمالي حسب المركبة واليوم والشهر."""
    qs = VehicleExpense.objects.select_related('vehicle').filter(category='maintenance')
    today = timezone.now().date()
    totals = {
        'today': qs.filter(date=today).aggregate(s=Sum('amount'))['s'] or 0,
        'month': qs.filter(date__year=today.year, date__month=today.month).aggregate(s=Sum('amount'))['s'] or 0,
        'all': qs.aggregate(s=Sum('amount'))['s'] or 0,
    }
    per_vehicle = (
        qs.values('vehicle__plate_number')
          .annotate(total=Sum('amount'))
          .order_by('-total')[:50]
    )
    return render(request, 'fleet/maintenance_list.html', {
        'expenses': qs.order_by('-date', '-id')[:300],
        'totals': totals,
        'per_vehicle': per_vehicle,
    })


@require_fleet_access
@require_fleet_permission('manage_vehicleexpense')
def maintenance_create(request):
    """إنشاء بند صيانة بسرعة (يلتقط category=maintenance)."""
    if request.method == 'POST':
        form = MaintenanceExpenseForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.category = 'maintenance'
            if request.user.is_authenticated:
                obj.created_by = request.user
            obj.save()
            # محاولة إنشاء قيد محاسبي تلقائي وفق إعدادات الأسطول
            try:
                obj.ensure_journal_entry(user=request.user)
            except Exception:
                pass
            log_activity(
                request,
                'create_maintenance_expense',
                object_id=obj.pk,
                description=f'صيانة {obj.vehicle.plate_number} بقيمة {obj.amount}',
            )
            return redirect('fleet:maintenance_list')
    else:
        form = MaintenanceExpenseForm()
    return render(request, 'fleet/form.html', {'form': form, 'title': 'مصروف صيانة جديد'})


@require_fleet_access
@require_fleet_permission('manage_vehicleexpense')
def expense_create(request):
    form = VehicleExpenseForm(request.POST or None)
    if form.is_valid():
        obj = form.save(commit=False)
        if request.user.is_authenticated:
            obj.created_by = request.user
        obj.save()
        log_activity(
            request,
            'create_expense',
            object_id=obj.pk,
            description=f'مصروف {obj.get_category_display()} {obj.amount}',
        )
        return redirect('fleet:expense_list')
    return render(request, 'fleet/form.html', {'form': form, 'title': 'مصروف مركبة جديد'})


@require_fleet_access
@require_fleet_permission('manage_vehicleexpense')
def expense_update(request, pk):
    e = get_object_or_404(VehicleExpense, pk=pk)
    form = VehicleExpenseForm(request.POST or None, instance=e)
    if form.is_valid():
        obj = form.save()
        log_activity(request, 'update_expense', object_id=obj.pk, description='تعديل مصروف مركبة')
        return redirect('fleet:expense_list')
    return render(request, 'fleet/form.html', {'form': form, 'title': 'تعديل مصروف مركبة'})


@require_fleet_access
@require_fleet_permission('manage_vehicleexpense')
def expense_delete(request, pk):
    e = get_object_or_404(VehicleExpense, pk=pk)
    if request.method == 'POST':
        e.delete()
        log_activity(request, 'delete_expense', object_id=pk, description='حذف مصروف مركبة')
        return redirect('fleet:expense_list')
    return render(request, 'fleet/confirm_delete.html', {'object': e, 'title': 'حذف مصروف مركبة'})


@require_fleet_access
@require_fleet_permission('manage_vehicle')
def documents_upload(request):
    form = VehicleDocumentForm(request.POST or None, request.FILES or None)
    docs = VehicleDocument.objects.select_related('vehicle').order_by('-uploaded_at')[:100]
    if form.is_valid():
        doc = form.save()
        log_activity(request, 'upload_document', object_id=doc.pk, description='رفع مستند مركبة')
        return redirect('fleet:documents_upload')
    return render(request, 'fleet/documents.html', {'form': form, 'docs': docs})


@require_fleet_access
def document_delete(request, pk):
    d = get_object_or_404(VehicleDocument, pk=pk)
    if request.method == 'POST':
        d.delete()
        log_activity(request, 'delete_document', object_id=pk, description='حذف مستند مركبة')
        return redirect('fleet:documents_upload')
    return render(request, 'fleet/confirm_delete.html', {'object': d, 'title': 'حذف مستند مركبة'})


@require_fleet_access
def driver_performance(request):
    drivers = Driver.objects.all()
    data = []
    for d in drivers:
        trips_qs = d.trips.all()
        data.append(
            {
                'driver': d,
                'trips_count': trips_qs.count(),
                'total_distance': trips_qs.aggregate(s=Sum('distance_km'))['s'] or 0,
                'expenses_total': d.expenses.aggregate(s=Sum('amount'))['s'] or 0,
                'fines_total': d.violations.aggregate(s=Sum('amount'))['s'] or 0,
                'advances_total': d.advances.aggregate(s=Sum('amount'))['s'] or 0,
                'advances_utilized': sum(a.utilized_amount for a in d.advances.all()),
                'advances_remaining': sum(a.remaining_amount for a in d.advances.all()),
            }
        )
    return render(request, 'fleet/driver_performance.html', {'performance': data})


# CRUD مخالفات
@require_fleet_access
def violation_list(request):
    qs = DriverViolation.objects.select_related('driver', 'vehicle').all()
    driver_id = request.GET.get('driver')
    paid = request.GET.get('paid')  # 'yes'/'no'
    date_from = parse_date(request.GET.get('from') or '')
    date_to = parse_date(request.GET.get('to') or '')
    search = request.GET.get('q', '').strip()
    if driver_id:
        qs = qs.filter(driver_id=driver_id)
    if paid == 'yes':
        qs = qs.filter(is_paid=True)
    elif paid == 'no':
        qs = qs.filter(is_paid=False)
    if date_from:
        qs = qs.filter(date__gte=date_from)
    if date_to:
        qs = qs.filter(date__lte=date_to)
    if search:
        qs = qs.filter(
            Q(violation_type__icontains=search)
            | Q(notes__icontains=search)
            | Q(vehicle__plate_number__icontains=search)
            | Q(driver__name__icontains=search)
        )
    qs = qs.order_by('-date', '-id')
    export = request.GET.get('export')
    if export == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="violations.csv"'
        writer = csv.writer(response)
        writer.writerow(['ID', 'Driver', 'Vehicle', 'Type', 'Date', 'Amount', 'Paid'])
        for v in qs:
            writer.writerow(
                [
                    v.id,
                    v.driver.name,
                    v.vehicle.plate_number if v.vehicle_id else '',
                    v.violation_type,
                    v.date,
                    v.amount,
                    'YES' if v.is_paid else 'NO',
                ]
            )
        return response
    elif export == 'xlsx':
        wb = Workbook()
        ws = wb.active
        ws.title = 'Violations'
        if ws: ws.append(['ID', 'Driver', 'Vehicle', 'Type', 'Date', 'Amount', 'Paid'])
        for v in qs:
            if ws: ws.append(
                [
                    v.id,
                    v.driver.name,
                    v.vehicle.plate_number if v.vehicle_id else '',
                    v.violation_type,
                    v.date.isoformat(),
                    float(v.amount),
                    'YES' if v.is_paid else 'NO',
                ]
            )
        from io import BytesIO
        bio = BytesIO()
        wb.save(bio)
        bio.seek(0)
        response = HttpResponse(
            bio.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = 'attachment; filename="violations.xlsx"'
        return response
    elif export == 'pdf':
        if not _REPORTLAB_AVAILABLE:
            return HttpResponse('PDF generation not available (reportlab missing)', status=501)
        from reportlab.pdfgen import canvas  # type: ignore
        from reportlab.lib.pagesizes import A4  # type: ignore
        from io import BytesIO
        bio = BytesIO()
        c = canvas.Canvas(bio, pagesize=A4)
        width, height = A4
        y = height - 40
        c.setFont('Helvetica-Bold', 14)
        c.drawString(40, y, 'قائمة المخالفات')
        y -= 30
        c.setFont('Helvetica', 9)
        headers = ['ID','Driver','Vehicle','Type','Date','Amount','Paid']
        x_positions = [40,80,150,220,320,400,460]
        for h, x in zip(headers, x_positions):
            c.drawString(x, y, h)
        y -= 18
        for v in qs[:500]:
            if y < 60:
                c.showPage(); y = height - 40; c.setFont('Helvetica', 9)
            values = [str(v.id), v.driver.name[:12], (v.vehicle.plate_number if v.vehicle_id else '')[:10], v.violation_type[:14], v.date.isoformat(), f"{v.amount}", 'Y' if v.is_paid else 'N']
            for val, x in zip(values, x_positions):
                c.drawString(x, y, val)
            y -= 14
        c.showPage(); c.save()
        pdf_data = bio.getvalue()
        response = HttpResponse(pdf_data, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="violations.pdf"'
        return response
    drivers = Driver.objects.all()
    return render(
        request,
        'fleet/violation_list.html',
        {
            'violations': qs[:500],
            'violations_total_amount': qs.aggregate(s=Sum('amount'))['s'] or 0,
            'drivers': drivers,
            'filters': {
                'driver': driver_id,
                'paid': paid,
                'from': date_from,
                'to': date_to,
                'q': search,
            },
        },
    )


@require_fleet_access
@require_fleet_permission('manage_driverviolation')
def violation_create(request):
    form = DriverViolationForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        v = form.save()
        log_activity(request, 'create_violation', object_id=v.pk, description='إضافة مخالفة')
        return redirect('fleet:violation_list')
    return render(request, 'fleet/form.html', {'form': form, 'title': 'مخالفة جديدة'})


@require_fleet_access
@require_fleet_permission('manage_driverviolation')
def violation_update(request, pk):
    obj = get_object_or_404(DriverViolation, pk=pk)
    form = DriverViolationForm(request.POST or None, request.FILES or None, instance=obj)
    if form.is_valid():
        form.save()
        log_activity(request, 'update_violation', object_id=obj.pk, description='تعديل مخالفة')
        return redirect('fleet:violation_list')
    return render(request, 'fleet/form.html', {'form': form, 'title': 'تعديل مخالفة'})


@require_fleet_access
@require_fleet_permission('manage_driverviolation')
def violation_delete(request, pk):
    obj = get_object_or_404(DriverViolation, pk=pk)
    if request.method == 'POST':
        obj.delete()
        log_activity(request, 'delete_violation', object_id=pk, description='حذف مخالفة')
        return redirect('fleet:violation_list')
    return render(request, 'fleet/confirm_delete.html', {'object': obj, 'title': 'حذف مخالفة'})


# CRUD عهد السائق
@require_fleet_access
def advance_list(request):
    qs = DriverAdvance.objects.select_related('driver').all()
    driver_id = request.GET.get('driver')
    status = request.GET.get('status')  # open / settled
    date_from = parse_date(request.GET.get('from') or '')
    date_to = parse_date(request.GET.get('to') or '')
    if driver_id:
        qs = qs.filter(driver_id=driver_id)
    if status in ('open', 'settled'):
        qs = qs.filter(status=status)
    if date_from:
        qs = qs.filter(date__gte=date_from)
    if date_to:
        qs = qs.filter(date__lte=date_to)
    qs = qs.order_by('-date', '-id')
    export = request.GET.get('export')
    if export == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="advances.csv"'
        writer = csv.writer(response)
        writer.writerow(['ID', 'Driver', 'Date', 'Amount', 'Status', 'Remaining'])
        for a in qs:
            writer.writerow([a.id, a.driver.name, a.date, a.amount, a.status, a.remaining_amount])
        return response
    elif export == 'xlsx':
        wb = Workbook()
        ws = wb.active
        ws.title = 'Advances'
        if ws: ws.append(['ID', 'Driver', 'Date', 'Amount', 'Status', 'Remaining'])
        for a in qs:
            if ws: ws.append([a.id, a.driver.name, a.date.isoformat(), float(a.amount), a.status, float(a.remaining_amount)])
        from io import BytesIO
        bio = BytesIO()
        wb.save(bio)
        bio.seek(0)
        response = HttpResponse(bio.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="advances.xlsx"'
        return response
    elif export == 'pdf':
        if not _REPORTLAB_AVAILABLE:
            return HttpResponse('PDF generation not available (reportlab missing)', status=501)
        from reportlab.pdfgen import canvas  # type: ignore
        from reportlab.lib.pagesizes import A4  # type: ignore
        from io import BytesIO
        bio = BytesIO()
        c = canvas.Canvas(bio, pagesize=A4)
        width, height = A4
        y = height - 40
        c.setFont('Helvetica-Bold', 14); c.drawString(40, y, 'قائمة العهد')
        y -= 30; c.setFont('Helvetica', 9)
        headers = ['ID','Driver','Date','Amount','Status','Remaining']
        x_positions = [40,80,150,240,310,380]
        for h,x in zip(headers,x_positions): c.drawString(x,y,h)
        y -= 18
        for a in qs[:500]:
            if y < 60:
                c.showPage(); y = height - 40; c.setFont('Helvetica',9)
            values = [str(a.id), a.driver.name[:12], a.date.isoformat(), f"{a.amount}", a.status, f"{a.remaining_amount}"]
            for val,x in zip(values,x_positions): c.drawString(x,y,val)
            y -= 14
        c.showPage(); c.save(); pdf_data = bio.getvalue()
        response = HttpResponse(pdf_data, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="advances.pdf"'
        return response
    drivers = Driver.objects.all()
    advances_slice = list(qs[:500])
    advances_total_amount = qs.aggregate(s=Sum('amount'))['s'] or 0
    # المتبقي الإجمالي يُحسب من كل العناصر (المقطوعة المعروضة فقط قد تقلل الدقة؛ نستخدم كل queryset)
    remaining_total = 0
    for a in qs:  # إذا حجم البيانات كبير يمكن تحسينها لاحقاً
        try:
            remaining_total += a.remaining_amount
        except Exception:
            pass
    return render(request, 'fleet/advance_list.html', {
        'advances': advances_slice,
        'advances_total_amount': advances_total_amount,
        'advances_remaining_total': remaining_total,
        'drivers': drivers,
        'filters': {'driver': driver_id, 'status': status, 'from': date_from, 'to': date_to},
    })


@require_fleet_access
@require_fleet_permission('manage_driveradvance')
def advance_create(request):
    form = DriverAdvanceForm(request.POST or None)
    if form.is_valid():
        adv = form.save()
        log_activity(request, 'create_advance', object_id=adv.pk, description='إضافة عهدة سائق')
        return redirect('fleet:advance_list')
    return render(request, 'fleet/form.html', {'form': form, 'title': 'عهدة جديدة'})


@require_fleet_access
@require_fleet_permission('manage_driveradvance')
def advance_update(request, pk):
    adv = get_object_or_404(DriverAdvance, pk=pk)
    form = DriverAdvanceForm(request.POST or None, instance=adv)
    if form.is_valid():
        form.save()
        if adv.can_settle() and adv.status == 'open':
            adv.settle()
        log_activity(request, 'update_advance', object_id=adv.pk, description='تعديل عهدة')
        return redirect('fleet:advance_list')
    return render(request, 'fleet/form.html', {'form': form, 'title': 'تعديل عهدة'})


@require_fleet_access
@require_fleet_permission('manage_driveradvance')
def advance_settle(request, pk):
    adv = get_object_or_404(DriverAdvance, pk=pk)
    if request.method == 'POST':
        if adv.can_settle() and adv.status == 'open':
            adv.settle()
            log_activity(request, 'settle_advance', object_id=adv.pk, description='تصفية عهدة')
        return redirect('fleet:advance_list')
    return HttpResponseForbidden('غير مسموح')


@require_fleet_access
@require_fleet_permission('manage_driveradvance')
def advance_delete(request, pk):
    adv = get_object_or_404(DriverAdvance, pk=pk)
    if request.method == 'POST':
        adv.delete()
        log_activity(request, 'delete_advance', object_id=pk, description='حذف عهدة')
        return redirect('fleet:advance_list')
    return render(request, 'fleet/confirm_delete.html', {'object': adv, 'title': 'حذف عهدة'})


# ===== أنواع المركبات =====
@require_fleet_access
def vehicle_type_list(request):
    """قائمة أنواع المركبات"""
    return render(request, 'fleet/vehicle_types/list.html')


@require_fleet_access
def vehicle_handover_list(request):
    """تسليم واستلام المركبات"""
    return render(request, 'fleet/vehicle_handover/list.html')


@require_fleet_access
def garage_list(request):
    """قائمة الكراجات"""
    return render(request, 'fleet/garages/list.html')


@require_fleet_access
def holiday_list(request):
    """قائمة الإجازات"""
    return render(request, 'fleet/holidays/list.html')


@require_fleet_access
def spare_part_list(request):
    """قائمة قطع الغيار"""
    return render(request, 'fleet/spare_parts/list.html')


@require_fleet_access
def maintenance_type_list(request):
    """قائمة أنواع الصيانة"""
    return render(request, 'fleet/maintenance_types/list.html')


@require_fleet_access
def expense_type_list(request):
    """قائمة أنواع المصروفات"""
    return render(request, 'fleet/expense_types/list.html')


@require_fleet_access
def unified_expense_list(request):
    """المصروفات الموحدة"""
    return render(request, 'fleet/unified_expenses/list.html')


@require_fleet_access
def maintenance_permission_list(request):
    """إذونات الصيانة"""
    return render(request, 'fleet/maintenance_permissions/list.html')


@require_fleet_access
def spare_parts_permission_list(request):
    """إذونات قطع الغيار"""
    return render(request, 'fleet/spare_parts_permissions/list.html')


@require_fleet_access
def oil_type_list(request):
    """أنواع الزيوت"""
    return render(request, 'fleet/oil_types/list.html')


@require_fleet_access
def maintenance_alert_list(request):
    """تنبيهات الصيانة"""
    return render(request, 'fleet/maintenance_alerts/list.html')


@require_fleet_access
def odometer_adjustment_list(request):
    """تعديلات العداد"""
    return render(request, 'fleet/odometer_adjustments/list.html')


# ===== الوقود =====
@require_fleet_access
def fuel_list(request):
    """سجلات الوقود"""
    return render(request, 'fleet/fuel/list.html')


@require_fleet_access
def fuel_import(request):
    """استيراد بيانات الوقود"""
    return render(request, 'fleet/fuel/import.html')


@require_fleet_access
def fuel_station_list(request):
    """محطات الوقود"""
    return render(request, 'fleet/fuel/stations.html')


@require_fleet_access
def fuel_reports(request):
    """تقارير الوقود"""
    return render(request, 'fleet/fuel/reports.html')


# ===== النقليات =====
@require_fleet_access
def transfer_bill_list(request):
    """بوالص النقل"""
    return render(request, 'fleet/transfers/bills.html')


@require_fleet_access
def transfer_reports(request):
    """تقارير النقل"""
    return render(request, 'fleet/transfers/reports.html')


# ===== الكاوش (الإطارات) =====
@require_fleet_access
def tire_brand_list(request):
    """ماركات الإطارات"""
    return render(request, 'fleet/tires/brands.html')


@require_fleet_access
def tire_inventory_list(request):
    """مخزون الإطارات"""
    return render(request, 'fleet/tires/inventory.html')


@require_fleet_access
def tire_movement_list(request):
    """حركة الإطارات"""
    return render(request, 'fleet/tires/movements.html')


@require_fleet_access
def tire_pressure_list(request):
    """ضغط الإطارات"""
    return render(request, 'fleet/tires/pressure.html')


@require_fleet_access
def tire_maintenance_list(request):
    """صيانة الإطارات"""
    return render(request, 'fleet/tires/maintenance.html')


@require_fleet_access
def tire_performance_report(request):
    """تقرير أداء الإطارات"""
    return render(request, 'fleet/tires/performance.html')


@require_fleet_access
def tire_comparison_report(request):
    """مقارنة الإطارات"""
    return render(request, 'fleet/tires/comparison.html')


@require_fleet_access
def tire_low_stock(request):
    """الإطارات منخفضة المخزون"""
    return render(request, 'fleet/tires/low_stock.html')


@require_fleet_access
def tire_overdue(request):
    """الإطارات المتأخرة"""
    return render(request, 'fleet/tires/overdue.html')


# ===== تقارير إضافية =====
@require_fleet_access
def fuel_report(request):
    """تقرير الوقود"""
    return render(request, 'fleet/reports/fuel.html')


@require_fleet_access
def maintenance_report(request):
    """تقرير الصيانة"""
    return render(request, 'fleet/reports/maintenance.html')


@require_fleet_access
def working_days_report(request):
    """تقرير أيام العمل"""
    return render(request, 'fleet/reports/working_days.html')


@require_fleet_access
def driver_performance_report(request):
    """تقرير أداء السائقين"""
    return render(request, 'fleet/reports/driver_performance.html')


@require_fleet_access
def load_comparison_report(request):
    """مقارنة الحمولات"""
    return render(request, 'fleet/reports/load_comparison.html')


@require_fleet_access
def oil_status_report(request):
    """تقرير حالة الزيوت"""
    return render(request, 'fleet/reports/oil_status.html')

