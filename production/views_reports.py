"""
تقارير التكاليف والإنتاجية ولوحة KPIs لصاحب المصنع
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Avg, Q, F, DecimalField
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal
from django.db import models


@login_required
def product_cost_report(request):
    """تقرير تكلفة المنتج المفصل"""
    from inventory.models import Product
    from production.services.costing_service import ProductCostingService
    
    # الفلترة
    product_id = request.GET.get('product')
    quantity = Decimal(request.GET.get('quantity', '1'))
    
    if product_id:
        product = get_object_or_404(Product, id=product_id)
        cost_data = ProductCostingService.calculate_full_product_cost(product, quantity)
    else:
        product = None
        cost_data = None
    
    # قائمة المنتجات للاختيار
    products = Product.objects.filter(is_active=True).order_by('name')[:200]
    
    context = {
        'product': product,
        'quantity': quantity,
        'cost_data': cost_data,
        'products': products,
    }
    
    return render(request, 'production/product_cost_report.html', context)


@login_required
def all_products_cost_summary(request):
    """ملخص تكلفة جميع المنتجات"""
    from inventory.models import Product
    from production.services.costing_service import ProductCostingService
    
    # فقط المنتجات النشطة التي لها BOM
    from production.models import BillOfMaterials
    
    products_with_bom = BillOfMaterials.objects.filter(
        is_active=True
    ).values_list('product_id', flat=True)
    
    products = Product.objects.filter(
        id__in=products_with_bom,
        is_active=True
    ).order_by('name')
    
    products_cost = []
    for product in products:
        cost_data = ProductCostingService.calculate_full_product_cost(product, Decimal('1'))
        products_cost.append({
            'product': product,
            'cost_per_unit': cost_data['cost_per_unit'],
            'material_cost': cost_data['material_cost'],
            'labor_cost': cost_data['labor_cost'],
            'overhead_cost': cost_data['overhead_cost'],
            'selling_price': cost_data['selling_price'],
            'profit_margin': cost_data['profit_margin'],
            'profit_percentage': cost_data['profit_percentage'],
        })
    
    context = {
        'products_cost': products_cost,
    }
    
    return render(request, 'production/all_products_cost_summary.html', context)


@login_required
def worker_productivity_report(request):
    """تقرير إنتاجية العمال"""
    from hr.models import Employee, Department
    from production.services.costing_service import WorkerProductivityService
    from production.models import WorkerProductionEntry
    
    # الفترة (افتراضي: آخر 30 يوم)
    end_date = date.today()
    start_date_param = request.GET.get('start_date')
    end_date_param = request.GET.get('end_date')
    department_id = request.GET.get('department')
    
    if start_date_param:
        start_date = date.fromisoformat(start_date_param)
    else:
        start_date = end_date - timedelta(days=30)
    
    if end_date_param:
        end_date = date.fromisoformat(end_date_param)
    
    # فلترة حسب القسم
    employees = Employee.objects.filter(status='active')
    if department_id:
        employees = employees.filter(department_id=department_id)
    
    # حساب إنتاجية كل عامل
    workers_productivity = []
    for employee in employees:
        productivity = WorkerProductivityService.calculate_worker_production(
            employee, start_date, end_date
        )
        
        # إحصائيات إضافية
        entries = WorkerProductionEntry.objects.filter(
            employee=employee,
            date__range=[start_date, end_date]
        )
        
        total_entries = entries.count()
        approved_entries = entries.filter(status='approved').count()
        rejected_entries = entries.filter(status='rejected').count()
        total_quantity = entries.aggregate(Sum('quantity'))['quantity__sum'] or Decimal('0')
        
        workers_productivity.append({
            'employee': employee,
            'total_entries': total_entries,
            'approved_entries': approved_entries,
            'rejected_entries': rejected_entries,
            'total_quantity': total_quantity,
            'total_hours': productivity['total_hours'],
            'units_per_hour': total_quantity / productivity['total_hours'] if productivity['total_hours'] > 0 else Decimal('0'),
            'days_worked': productivity['days_worked'],
        })
    
    # ترتيب حسب الإنتاجية
    workers_productivity.sort(key=lambda x: x['total_quantity'], reverse=True)
    
    # الأقسام للفلترة
    departments = Department.objects.all()
    
    context = {
        'workers_productivity': workers_productivity,
        'start_date': start_date,
        'end_date': end_date,
        'departments': departments,
        'selected_department': int(department_id) if department_id else None,
    }
    
    return render(request, 'production/worker_productivity_report.html', context)


@login_required
def factory_owner_dashboard(request):
    """لوحة KPIs لصاحب المصنع"""
    from inventory.models import Product, Stock
    from production.models import ProductionOrder, WorkerProductionEntry
    from production.services.costing_service import ProductCostingService, OverheadDistributionService
    from accounting.models import Loan, Cheque
    from hr.models import Employee
    
    today = timezone.now().date()
    current_month_start = today.replace(day=1)
    last_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
    
    # 1. التكاليف والربحية
    # أهم 5 منتجات
    from production.models import BillOfMaterials
    top_products = Product.objects.filter(
        id__in=BillOfMaterials.objects.filter(is_active=True).values_list('product_id', flat=True)
    ).order_by('-price')[:5]
    
    products_analysis = []
    for product in top_products:
        cost_data = ProductCostingService.calculate_full_product_cost(product, Decimal('1'))
        products_analysis.append({
            'product_name': product.name,
            'cost_per_unit': cost_data['cost_per_unit'],
            'selling_price': cost_data['selling_price'],
            'profit_margin': cost_data['profit_margin'],
            'profit_percentage': cost_data['profit_percentage'],
        })
    
    # 2. الإنتاج
    month_production = ProductionOrder.objects.filter(
        actual_end_date__gte=current_month_start,
        status='completed'
    ).aggregate(
        count=Count('id'),
        quantity=Sum('produced_quantity')
    )
    
    month_worker_entries = WorkerProductionEntry.objects.filter(
        date__gte=current_month_start,
        status='approved'
    ).aggregate(
        count=Count('id'),
        quantity=Sum('quantity')
    )
    
    # 3. استهلاك الخامات
    from production.models import MaterialConsumption
    month_materials = MaterialConsumption.objects.filter(
        created_at__gte=current_month_start
    ).aggregate(
        total_cost=Sum(
            F('consumed_quantity') * F('unit_cost'),
            output_field=DecimalField()
        )
    )
    
    # 4. إنتاجية أفضل 5 عمال
    from django.db.models import Sum as DSum
    top_workers = WorkerProductionEntry.objects.filter(
        date__gte=current_month_start,
        status='approved'
    ).values('employee__arabic_name').annotate(
        total_quantity=DSum('quantity')
    ).order_by('-total_quantity')[:5]
    
    # 5. المخزون
    total_inventory_value = Stock.objects.filter(
        quantity__gt=0
    ).aggregate(
        total=Sum(
            F('quantity') * F('product__cost'),
            output_field=DecimalField()
        )
    )['total'] or Decimal('0')
    
    # 6. الالتزامات القادمة (30 يوم)
    end_date = today + timedelta(days=30)
    
    upcoming_loan_payments = Loan.objects.filter(
        status='active'
    ).aggregate(
        total=Sum(
            F('principal_amount') / F('duration_months'),
            output_field=DecimalField()
        )
    )['total'] or Decimal('0')
    
    upcoming_cheques = Cheque.objects.filter(
        cheque_type='outgoing',
        status__in=['pending', 'deposited'],
        due_date__range=[today, end_date]
    ).aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0')
    
    total_obligations_30days = upcoming_loan_payments + upcoming_cheques
    
    # 7. نسب التشغيل
    active_employees = Employee.objects.filter(
        status='active'
    ).count()
    
    working_employees = WorkerProductionEntry.objects.filter(
        date__gte=current_month_start
    ).values('employee').distinct().count()
    
    utilization_rate = (working_employees / active_employees * 100) if active_employees > 0 else 0
    
    # 8. المصاريف غير المباشرة
    overhead = OverheadDistributionService.collect_monthly_overhead_expenses(
        today.year, today.month
    )
    
    context = {
        'today': today,
        'products_analysis': products_analysis,
        'month_production': month_production,
        'month_worker_entries': month_worker_entries,
        'month_materials_cost': month_materials.get('total_cost', Decimal('0')),
        'top_workers': top_workers,
        'total_inventory_value': total_inventory_value,
        'total_obligations_30days': total_obligations_30days,
        'active_employees': active_employees,
        'working_employees': working_employees,
        'utilization_rate': utilization_rate,
        'overhead': overhead,
    }
    
    return render(request, 'production/factory_owner_dashboard.html', context)

