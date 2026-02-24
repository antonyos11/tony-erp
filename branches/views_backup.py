"""
Views وحدة الفروع الموحدة
تم دمج وحدة المعارض في هذه الوحدة
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Count, Q, F
from django.db import transaction
from django.utils import timezone
from django.core.paginator import Paginator
from decimal import Decimal

from .models import (
    Branch, BranchStaff, BranchTransfer, BranchTransferItem,
    POSDevice, BranchAttendance, BranchExpense, BranchPurchase,
    BranchPayroll, BranchShift, BranchStockMovement
)
from .forms import (
    BranchForm, BranchStaffForm, BranchTransferForm, BranchTransferItemFormSet,
    POSDeviceForm, BranchExpenseForm, BranchPayrollForm, BranchShiftForm
)


def generate_transfer_number():
    today = timezone.now()
    prefix = f"TR{today.strftime('%Y%m%d')}"
    last = BranchTransfer.objects.filter(transfer_number__startswith=prefix).order_by('-transfer_number').first()
    new_num = int(last.transfer_number[-4:]) + 1 if last else 1
    return f"{prefix}{new_num:04d}"


# ==================== الفروع ====================

@login_required
def branches_dashboard(request):
    branches = Branch.objects.filter(is_active=True)
    stats = {
        'total_branches': Branch.objects.count(),
        'active_branches': branches.count(),
        'pending_transfers': BranchTransfer.objects.filter(status='pending').count(),
        'in_transit': BranchTransfer.objects.filter(status='in_transit').count(),
        'pending_expenses': BranchExpense.objects.filter(status='submitted').count(),
        'today_attendance': BranchAttendance.objects.filter(date=timezone.now().date()).count(),
    }
    recent_transfers = BranchTransfer.objects.select_related('from_branch', 'to_branch').order_by('-created_at')[:10]
    recent_expenses = BranchExpense.objects.select_related('branch').order_by('-created_at')[:5]
    
    return render(request, 'branches/dashboard.html', {
        'branches': branches,
        'stats': stats,
        'recent_transfers': recent_transfers,
        'recent_expenses': recent_expenses,
        'page_title': 'إدارة الفروع والمعارض'
    })


@login_required
def branch_list(request):
    branches = Branch.objects.select_related('manager', 'parent_branch').all()
    status = request.GET.get('status')
    branch_type = request.GET.get('type')
    search = request.GET.get('q')
    
    if status:
        branches = branches.filter(status=status)
    if branch_type:
        branches = branches.filter(branch_type=branch_type)
    if search:
        branches = branches.filter(Q(code__icontains=search) | Q(name__icontains=search))
    
    paginator = Paginator(branches, 20)
    branches = paginator.get_page(request.GET.get('page'))
    
    return render(request, 'branches/branch_list.html', {
        'branches': branches,
        'page_title': 'قائمة الفروع والمعارض',
        'status_choices': Branch.STATUS_CHOICES,
        'type_choices': Branch.BRANCH_TYPE_CHOICES
    })


@login_required
def branch_create(request):
    if request.method == 'POST':
        form = BranchForm(request.POST)
        if form.is_valid():
            branch = form.save(commit=False)
            branch.created_by = request.user
            branch.save()
            messages.success(request, f'تم إنشاء الفرع "{branch.name}" بنجاح')
            return redirect('branches:branch_detail', pk=branch.pk)
    else:
        form = BranchForm()
    return render(request, 'branches/branch_form.html', {'form': form, 'page_title': 'إنشاء فرع جديد'})


@login_required
def branch_detail(request, pk):
    branch = get_object_or_404(Branch.objects.select_related('manager', 'parent_branch'), pk=pk)
    staff = branch.staff.select_related('user').filter(is_active=True)
    transfers_out = branch.transfers_out.select_related('to_branch').order_by('-created_at')[:5]
    transfers_in = branch.transfers_in.select_related('from_branch').order_by('-created_at')[:5]
    recent_expenses = branch.expenses.order_by('-created_at')[:5]
    pos_devices = branch.pos_devices.all()
    
    return render(request, 'branches/branch_detail.html', {
        'branch': branch,
        'staff': staff,
        'transfers_out': transfers_out,
        'transfers_in': transfers_in,
        'recent_expenses': recent_expenses,
        'pos_devices': pos_devices,
        'page_title': f'تفاصيل: {branch.name}'
    })


@login_required
def branch_edit(request, pk):
    branch = get_object_or_404(Branch, pk=pk)
    if request.method == 'POST':
        form = BranchForm(request.POST, instance=branch)
        if form.is_valid():
            form.save()
            messages.success(request, f'تم تحديث الفرع "{branch.name}" بنجاح')
            return redirect('branches:branch_detail', pk=branch.pk)
    else:
        form = BranchForm(instance=branch)
    return render(request, 'branches/branch_form.html', {'form': form, 'branch': branch, 'page_title': f'تعديل: {branch.name}'})


@login_required
def branch_delete(request, pk):
    branch = get_object_or_404(Branch, pk=pk)
    if request.method == 'POST':
        if branch.transfers_out.exists() or branch.transfers_in.exists():
            messages.error(request, 'لا يمكن حذف الفرع لوجود تحويلات مرتبطة')
            return redirect('branches:branch_detail', pk=pk)
        name = branch.name
        branch.delete()
        messages.success(request, f'تم حذف الفرع "{name}"')
        return redirect('branches:branch_list')
    return render(request, 'branches/branch_confirm_delete.html', {'branch': branch, 'page_title': f'حذف: {branch.name}'})


# ==================== التحويلات ====================

@login_required
def transfer_list(request):
    transfers = BranchTransfer.objects.select_related('from_branch', 'to_branch', 'requested_by')
    status = request.GET.get('status')
    search = request.GET.get('q')
    
    if status:
        transfers = transfers.filter(status=status)
    if search:
        transfers = transfers.filter(transfer_number__icontains=search)
    
    paginator = Paginator(transfers, 20)
    transfers = paginator.get_page(request.GET.get('page'))
    
    return render(request, 'branches/transfer_list.html', {
        'transfers': transfers,
        'branches': Branch.objects.filter(is_active=True),
        'status_choices': BranchTransfer.STATUS_CHOICES,
        'page_title': 'التحويلات بين الفروع'
    })


@login_required
def transfer_create(request):
    if request.method == 'POST':
        form = BranchTransferForm(request.POST)
        formset = BranchTransferItemFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                transfer = form.save(commit=False)
                transfer.transfer_number = generate_transfer_number()
                transfer.requested_by = request.user
                transfer.status = 'pending'
                transfer.save()
                formset.instance = transfer
                formset.save()
                messages.success(request, f'تم إنشاء التحويل {transfer.transfer_number}')
                return redirect('branches:transfer_detail', pk=transfer.pk)
    else:
        form = BranchTransferForm(initial={'transfer_date': timezone.now().date()})
        formset = BranchTransferItemFormSet()
    return render(request, 'branches/transfer_form.html', {'form': form, 'formset': formset, 'page_title': 'إنشاء تحويل جديد'})


@login_required
def transfer_detail(request, pk):
    transfer = get_object_or_404(
        BranchTransfer.objects.select_related('from_branch', 'to_branch', 'requested_by', 'approved_by', 'received_by')
        .prefetch_related('items__product'), pk=pk
    )
    return render(request, 'branches/transfer_detail.html', {
        'transfer': transfer,
        'items': transfer.items.all(),
        'page_title': f'التحويل: {transfer.transfer_number}'
    })


@login_required
def transfer_approve(request, pk):
    transfer = get_object_or_404(BranchTransfer, pk=pk, status='pending')
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve':
            transfer.approve(request.user)
            messages.success(request, f'تمت الموافقة على التحويل {transfer.transfer_number}')
        elif action == 'reject':
            transfer.reject(request.user, request.POST.get('rejection_reason', ''))
            messages.warning(request, f'تم رفض التحويل {transfer.transfer_number}')
        return redirect('branches:transfer_detail', pk=pk)
    return render(request, 'branches/transfer_approve.html', {'transfer': transfer, 'page_title': f'الموافقة: {transfer.transfer_number}'})


@login_required
def transfer_ship(request, pk):
    transfer = get_object_or_404(BranchTransfer, pk=pk, status='approved')
    if request.method == 'POST':
        transfer.status = 'in_transit'
        transfer.save()
        messages.success(request, f'تم شحن التحويل {transfer.transfer_number}')
        return redirect('branches:transfer_detail', pk=pk)
    return render(request, 'branches/transfer_ship.html', {'transfer': transfer, 'page_title': f'شحن: {transfer.transfer_number}'})


@login_required
def transfer_receive(request, pk):
    transfer = get_object_or_404(BranchTransfer, pk=pk, status='in_transit')
    if request.method == 'POST':
        with transaction.atomic():
            for item in transfer.items.all():
                received_qty = request.POST.get(f'received_{item.id}')
                if received_qty:
                    item.received_quantity = int(received_qty)
                    item.save()
            transfer.receive(request.user)
            messages.success(request, f'تم استلام التحويل {transfer.transfer_number}')
        return redirect('branches:transfer_detail', pk=pk)
    return render(request, 'branches/transfer_receive.html', {'transfer': transfer, 'items': transfer.items.all(), 'page_title': f'استلام: {transfer.transfer_number}'})


@login_required
def transfer_cancel(request, pk):
    transfer = get_object_or_404(BranchTransfer, pk=pk)
    if transfer.status in ['received', 'cancelled']:
        messages.error(request, 'لا يمكن إلغاء هذا التحويل')
        return redirect('branches:transfer_detail', pk=pk)
    if request.method == 'POST':
        transfer.status = 'cancelled'
        transfer.save()
        messages.warning(request, f'تم إلغاء التحويل {transfer.transfer_number}')
        return redirect('branches:transfer_detail', pk=pk)
    return render(request, 'branches/transfer_cancel.html', {'transfer': transfer, 'page_title': f'إلغاء: {transfer.transfer_number}'})


# ==================== الموظفين ====================

@login_required
def staff_list(request):
    staff = BranchStaff.objects.select_related('branch', 'user').all()
    branch_id = request.GET.get('branch')
    role = request.GET.get('role')
    
    if branch_id:
        staff = staff.filter(branch_id=branch_id)
    if role:
        staff = staff.filter(role=role)
    
    paginator = Paginator(staff, 20)
    staff = paginator.get_page(request.GET.get('page'))
    
    return render(request, 'branches/staff_list.html', {
        'staff': staff,
        'branches': Branch.objects.filter(is_active=True),
        'role_choices': BranchStaff.ROLE_CHOICES,
        'page_title': 'موظفو الفروع'
    })


@login_required
def staff_create(request):
    if request.method == 'POST':
        form = BranchStaffForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم إضافة الموظف للفرع بنجاح')
            return redirect('branches:staff_list')
    else:
        form = BranchStaffForm()
    return render(request, 'branches/staff_form.html', {'form': form, 'page_title': 'إضافة موظف للفرع'})


# ==================== المصروفات ====================

@login_required
def expense_list(request):
    expenses = BranchExpense.objects.select_related('branch', 'created_by').all()
    branch_id = request.GET.get('branch')
    status = request.GET.get('status')
    category = request.GET.get('category')
    
    if branch_id:
        expenses = expenses.filter(branch_id=branch_id)
    if status:
        expenses = expenses.filter(status=status)
    if category:
        expenses = expenses.filter(category=category)
    
    paginator = Paginator(expenses, 20)
    expenses = paginator.get_page(request.GET.get('page'))
    
    return render(request, 'branches/expense_list.html', {
        'expenses': expenses,
        'branches': Branch.objects.filter(is_active=True),
        'category_choices': BranchExpense.ExpenseType.choices,
        'status_choices': BranchExpense.Status.choices,
        'page_title': 'مصروفات الفروع'
    })


@login_required
def expense_create(request):
    if request.method == 'POST':
        form = BranchExpenseForm(request.POST, request.FILES)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.created_by = request.user
            expense.save()
            messages.success(request, 'تم تسجيل المصروف بنجاح')
            return redirect('branches:expense_list')
    else:
        form = BranchExpenseForm()
    return render(request, 'branches/expense_form.html', {'form': form, 'page_title': 'تسجيل مصروف جديد'})


@login_required
def expense_detail(request, pk):
    expense = get_object_or_404(BranchExpense.objects.select_related('branch', 'created_by', 'approved_by'), pk=pk)
    return render(request, 'branches/expense_detail.html', {'expense': expense, 'page_title': f'مصروف: {expense.pk}'})


@login_required
def expense_approve(request, pk):
    expense = get_object_or_404(BranchExpense, pk=pk, status='submitted')
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve':
            expense.approve(request.user)
            messages.success(request, 'تم اعتماد المصروف')
        elif action == 'reject':
            expense.reject(request.user, request.POST.get('reason', ''))
            messages.warning(request, 'تم رفض المصروف')
        return redirect('branches:expense_detail', pk=pk)
    return render(request, 'branches/expense_approve.html', {'expense': expense, 'page_title': 'اعتماد المصروف'})


# ==================== الحضور ====================

@login_required
def attendance_list(request):
    records = BranchAttendance.objects.select_related('branch', 'employee__user').all()
    branch_id = request.GET.get('branch')
    date_filter = request.GET.get('date')
    
    if branch_id:
        records = records.filter(branch_id=branch_id)
    if date_filter:
        records = records.filter(date=date_filter)
    else:
        records = records.filter(date=timezone.now().date())
    
    paginator = Paginator(records, 30)
    records = paginator.get_page(request.GET.get('page'))
    
    return render(request, 'branches/attendance_list.html', {
        'records': records,
        'branches': Branch.objects.filter(is_active=True),
        'page_title': 'سجلات الحضور'
    })


@login_required
def attendance_punch(request):
    """تسجيل حضور/انصراف"""
    if request.method == 'POST':
        branch_id = request.POST.get('branch')
        employee_id = request.POST.get('employee')
        action = request.POST.get('action')
        
        branch = get_object_or_404(Branch, pk=branch_id)
        employee = get_object_or_404(BranchStaff, pk=employee_id)
        
        record, created = BranchAttendance.objects.get_or_create(
            branch=branch,
            employee=employee,
            user=employee.user,
            date=timezone.now().date()
        )
        
        if action == 'in':
            if record.punch_in():
                messages.success(request, 'تم تسجيل الحضور')
            else:
                messages.warning(request, 'تم تسجيل الحضور مسبقاً')
        elif action == 'out':
            if record.punch_out():
                messages.success(request, 'تم تسجيل الانصراف')
            else:
                messages.warning(request, 'تم تسجيل الانصراف مسبقاً')
        
        return redirect('branches:attendance_list')
    
    return render(request, 'branches/attendance_punch.html', {
        'branches': Branch.objects.filter(is_active=True),
        'page_title': 'تسجيل حضور/انصراف'
    })


# ==================== أجهزة نقاط البيع ====================

@login_required
def pos_device_list(request):
    devices = POSDevice.objects.select_related('branch').all()
    branch_id = request.GET.get('branch')
    
    if branch_id:
        devices = devices.filter(branch_id=branch_id)
    
    return render(request, 'branches/pos_device_list.html', {
        'devices': devices,
        'branches': Branch.objects.filter(is_active=True),
        'page_title': 'أجهزة نقاط البيع'
    })


@login_required
def pos_device_create(request):
    if request.method == 'POST':
        form = POSDeviceForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم إضافة الجهاز بنجاح')
            return redirect('branches:pos_device_list')
    else:
        form = POSDeviceForm()
    return render(request, 'branches/pos_device_form.html', {'form': form, 'page_title': 'إضافة جهاز نقطة بيع'})


# ==================== الرواتب ====================

@login_required
def payroll_list(request):
    entries = BranchPayroll.objects.select_related('branch', 'employee__user').all()
    branch_id = request.GET.get('branch')
    status = request.GET.get('status')
    
    if branch_id:
        entries = entries.filter(branch_id=branch_id)
    if status:
        entries = entries.filter(status=status)
    
    paginator = Paginator(entries, 20)
    entries = paginator.get_page(request.GET.get('page'))
    
    return render(request, 'branches/payroll_list.html', {
        'entries': entries,
        'branches': Branch.objects.filter(is_active=True),
        'status_choices': BranchPayroll.Status.choices,
        'page_title': 'رواتب الفروع'
    })


@login_required
def payroll_create(request):
    if request.method == 'POST':
        form = BranchPayrollForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم إضافة قيد الراتب بنجاح')
            return redirect('branches:payroll_list')
    else:
        form = BranchPayrollForm()
    return render(request, 'branches/payroll_form.html', {'form': form, 'page_title': 'إضافة قيد راتب'})


# ==================== الورديات ====================

@login_required
def shift_list(request):
    shifts = BranchShift.objects.select_related('branch').all()
    branch_id = request.GET.get('branch')
    
    if branch_id:
        shifts = shifts.filter(branch_id=branch_id)
    
    return render(request, 'branches/shift_list.html', {
        'shifts': shifts,
        'branches': Branch.objects.filter(is_active=True),
        'page_title': 'ورديات الفروع'
    })


@login_required
def shift_create(request):
    if request.method == 'POST':
        form = BranchShiftForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم إضافة الوردية بنجاح')
            return redirect('branches:shift_list')
    else:
        form = BranchShiftForm()
    return render(request, 'branches/shift_form.html', {'form': form, 'page_title': 'إضافة وردية'})


# ==================== التقارير ====================

@login_required
def branch_stock_report(request, pk):
    branch = get_object_or_404(Branch, pk=pk)
    movements = BranchStockMovement.objects.filter(branch=branch).select_related('product').order_by('-created_at')[:50]
    return render(request, 'branches/reports/stock_report.html', {'branch': branch, 'movements': movements, 'page_title': f'مخزون: {branch.name}'})


@login_required
def transfer_report(request):
    transfers = BranchTransfer.objects.all()
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if date_from:
        transfers = transfers.filter(transfer_date__gte=date_from)
    if date_to:
        transfers = transfers.filter(transfer_date__lte=date_to)
    
    stats = transfers.aggregate(total_count=Count('id'))
    return render(request, 'branches/reports/transfer_report.html', {'transfers': transfers[:100], 'stats': stats, 'page_title': 'تقرير التحويلات'})


@login_required
def expense_report(request):
    expenses = BranchExpense.objects.all()
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    branch_id = request.GET.get('branch')
    
    if date_from:
        expenses = expenses.filter(date__gte=date_from)
    if date_to:
        expenses = expenses.filter(date__lte=date_to)
    if branch_id:
        expenses = expenses.filter(branch_id=branch_id)
    
    stats = expenses.aggregate(
        total_count=Count('id'),
        total_amount=Sum('amount')
    )
    
    by_category = expenses.values('category').annotate(
        count=Count('id'),
        total=Sum('amount')
    ).order_by('-total')
    
    return render(request, 'branches/reports/expense_report.html', {
        'expenses': expenses[:100],
        'stats': stats,
        'by_category': by_category,
        'branches': Branch.objects.filter(is_active=True),
        'page_title': 'تقرير المصروفات'
    })


@login_required
def consolidated_report(request):
    branches = Branch.objects.filter(is_active=True).annotate(
        transfers_out_count=Count('transfers_out'),
        transfers_in_count=Count('transfers_in'),
        staff_count=Count('staff', filter=Q(staff__is_active=True)),
        expense_total=Sum('expenses__amount', filter=Q(expenses__status='approved'))
    )
    return render(request, 'branches/reports/consolidated_report.html', {'branches': branches, 'page_title': 'التقرير الموحد'})


# ==================== API ====================

@login_required
def api_branches_list(request):
    branches = Branch.objects.filter(is_active=True).values('id', 'code', 'name', 'city', 'branch_type')
    return JsonResponse(list(branches), safe=False)


@login_required
def api_branch_stock(request, pk):
    branch = get_object_or_404(Branch, pk=pk)
    stock = []
    if branch.location:
        from inventory.models import Stock
        stock = list(Stock.objects.filter(location=branch.location).select_related('product').values(
            'product__id', 'product__name', 'quantity'
        ))
    return JsonResponse({'branch': branch.name, 'stock': stock})


@login_required
def api_branch_staff(request, pk):
    branch = get_object_or_404(Branch, pk=pk)
    staff = list(branch.staff.filter(is_active=True).values('id', 'user__username', 'role', 'position'))
    return JsonResponse({'branch': branch.name, 'staff': staff})
