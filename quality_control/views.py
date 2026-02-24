from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db.models import Count, Q
from .models import QualityStandard, InspectionType, QualityInspection, QualityIssue
from .forms import QualityStandardForm, QualityInspectionForm, QualityIssueForm

@login_required
def dashboard(request):
    """Quality control dashboard"""
    total_inspections = QualityInspection.objects.count()
    passed = QualityInspection.objects.filter(status='passed').count()
    failed = QualityInspection.objects.filter(status='failed').count()
    pending = QualityInspection.objects.filter(status='pending').count()
    
    open_issues = QualityIssue.objects.filter(status='open').count()
    critical_issues = QualityIssue.objects.filter(severity='critical', status__in=['open', 'investigating']).count()
    
    recent_inspections = QualityInspection.objects.order_by('-inspection_date')[:10]
    recent_issues = QualityIssue.objects.filter(status__in=['open', 'investigating']).order_by('-created_at')[:10]
    
    context = {
        'total_inspections': total_inspections,
        'passed': passed,
        'failed': failed,
        'pending': pending,
        'open_issues': open_issues,
        'critical_issues': critical_issues,
        'recent_inspections': recent_inspections,
        'recent_issues': recent_issues,
    }
    return render(request, 'quality_control/dashboard.html', context)

@login_required
def inspection_list(request):
    """List all inspections"""
    inspections = QualityInspection.objects.all().select_related('inspection_type', 'product', 'inspector')
    status = request.GET.get('status')
    if status:
        inspections = inspections.filter(status=status)
    return render(request, 'quality_control/inspection_list.html', {'inspections': inspections})

@login_required
def inspection_detail(request, pk):
    """Inspection detail"""
    inspection = get_object_or_404(QualityInspection.objects.select_related('inspection_type', 'product', 'inspector'), pk=pk)
    results = inspection.results.all().select_related('standard')
    return render(request, 'quality_control/inspection_detail.html', {'inspection': inspection, 'results': results})

@login_required
@permission_required('quality_control.add_qualityinspection')
def inspection_create(request):
    """Create new inspection"""
    if request.method == 'POST':
        form = QualityInspectionForm(request.POST)
        if form.is_valid():
            inspection = form.save(commit=False)
            inspection.inspector = request.user
            inspection.code = f"QI-{QualityInspection.objects.count() + 1:05d}"
            inspection.save()
            messages.success(request, 'تم إنشاء الفحص بنجاح')
            return redirect('quality_control:inspection_detail', pk=inspection.pk)
    else:
        form = QualityInspectionForm()
    return render(request, 'quality_control/inspection_form.html', {'form': form, 'title': 'فحص جديد'})

@login_required
def issue_list(request):
    """List quality issues"""
    issues = QualityIssue.objects.all().select_related('product', 'reported_by', 'assigned_to')
    status = request.GET.get('status')
    severity = request.GET.get('severity')
    if status:
        issues = issues.filter(status=status)
    if severity:
        issues = issues.filter(severity=severity)
    return render(request, 'quality_control/issue_list.html', {'issues': issues})

@login_required
def issue_detail(request, pk):
    """Issue detail"""
    issue = get_object_or_404(QualityIssue, pk=pk)
    return render(request, 'quality_control/issue_detail.html', {'issue': issue})

@login_required
@permission_required('quality_control.add_qualityissue')
def issue_create(request):
    """Create new issue"""
    if request.method == 'POST':
        form = QualityIssueForm(request.POST)
        if form.is_valid():
            issue = form.save(commit=False)
            issue.reported_by = request.user
            issue.code = f"QIS-{QualityIssue.objects.count() + 1:05d}"
            issue.save()
            messages.success(request, 'تم تسجيل المشكلة بنجاح')
            return redirect('quality_control:issue_detail', pk=issue.pk)
    else:
        form = QualityIssueForm()
    return render(request, 'quality_control/issue_form.html', {'form': form, 'title': 'تسجيل مشكلة جودة'})

@login_required
def standard_list(request):
    """List quality standards"""
    standards = QualityStandard.objects.all()
    return render(request, 'quality_control/standard_list.html', {'standards': standards})

@login_required
@permission_required('quality_control.add_qualitystandard')
def standard_create(request):
    """Create quality standard"""
    if request.method == 'POST':
        form = QualityStandardForm(request.POST)
        if form.is_valid():
            standard = form.save(commit=False)
            standard.created_by = request.user
            standard.save()
            messages.success(request, 'تم إنشاء المعيار بنجاح')
            return redirect('quality_control:standard_list')
    else:
        form = QualityStandardForm()
    return render(request, 'quality_control/standard_form.html', {'form': form, 'title': 'معيار جديد'})


# ==================== Product Traceability ====================

@login_required
def traceability_dashboard(request):
    """Product traceability dashboard with search"""
    context = {
        'title': 'تتبع المنتجات',
        'page_description': 'بحث وتتبع المنتجات بواسطة رقم الدفعة أو الرقم التسلسلي',
    }
    return render(request, 'quality_control/traceability/dashboard.html', context)


@login_required
def traceability_search(request):
    """Search for products by batch or serial number"""
    query = request.GET.get('q', '')
    search_type = request.GET.get('type', 'batch')  # batch or serial
    
    results = []
    if query:
        from inventory.models import Product, StockMovement
        
        if search_type == 'batch':
            # Search by batch number
            movements = StockMovement.objects.filter(
                Q(batch_number__icontains=query)
            ).select_related('product', 'source_location', 'destination_location')[:50]
        else:
            # Search by serial number
            movements = StockMovement.objects.filter(
                Q(serial_number__icontains=query)
            ).select_related('product', 'source_location', 'destination_location')[:50]
        
        results = list(movements)
    
    context = {
        'query': query,
        'search_type': search_type,
        'results': results,
        'title': 'نتائج البحث',
    }
    return render(request, 'quality_control/traceability/search_results.html', context)


@login_required
def batch_trace(request, batch_number):
    """Trace product batch history"""
    from inventory.models import StockMovement, Product
    from sales.models import SalesInvoice, SalesInvoiceItem
    from purchases.models import PurchaseInvoice, PurchaseItem
    
    # Get all movements for this batch
    movements = StockMovement.objects.filter(
        batch_number=batch_number
    ).select_related('product', 'source_location', 'destination_location').order_by('created_at')
    
    # Get related sales
    sales = SalesInvoiceItem.objects.filter(
        batch_number=batch_number
    ).select_related('invoice', 'product')
    
    # Get related purchases
    purchases = PurchaseItem.objects.filter(
        batch_number=batch_number
    ).select_related('invoice', 'product')
    
    # Get quality inspections for this batch
    inspections = QualityInspection.objects.filter(
        batch_number=batch_number
    ).select_related('product', 'inspector')
    
    context = {
        'batch_number': batch_number,
        'movements': movements,
        'sales': sales,
        'purchases': purchases,
        'inspections': inspections,
        'title': f'تتبع الدفعة {batch_number}',
    }
    return render(request, 'quality_control/traceability/batch_trace.html', context)


@login_required
def serial_trace(request, serial_number):
    """Trace product by serial number"""
    from inventory.models import StockMovement
    from sales.models import SalesInvoiceItem
    from purchases.models import PurchaseItem
    
    # Get all movements for this serial number
    movements = StockMovement.objects.filter(
        serial_number=serial_number
    ).select_related('product', 'source_location', 'destination_location').order_by('created_at')
    
    # Get related sales
    sales = SalesInvoiceItem.objects.filter(
        serial_number=serial_number
    ).select_related('invoice', 'product')
    
    # Get related purchases
    purchases = PurchaseItem.objects.filter(
        serial_number=serial_number
    ).select_related('invoice', 'product')
    
    context = {
        'serial_number': serial_number,
        'movements': movements,
        'sales': sales,
        'purchases': purchases,
        'title': f'تتبع الرقم التسلسلي {serial_number}',
    }
    return render(request, 'quality_control/traceability/serial_trace.html', context)

