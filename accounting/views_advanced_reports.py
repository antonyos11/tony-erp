"""
Advanced Accounting Reports - Phase 1 Implementation
تقارير محاسبية متقدمة - المرحلة الأولى

This module implements:
1. Budget vs Actual Report (تقرير الموازنة مقابل الفعلي)
2. Product/Customer Profitability Analysis (تحليل الربحية)
3. Standard Costing foundations (أساسيات التكلفة المعيارية)
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Q, F, DecimalField, Case, When, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, timedelta
import json

from accounting.models import (
    Account, JournalEntry, JournalEntryItem, 
    CostCenter, CostCenterBudget, FiscalYear
)
from sales.models import Invoice, InvoiceItem
from production.models import ProductionOrder, BillOfMaterials
from inventory.models import Product


@login_required
def budget_vs_actual_report(request):
    """
    تقرير مقارنة الموازنة بالفعلي
    
    يعرض:
    - الموازنة المخططة لكل مركز تكلفة
    - المصروفات الفعلية
    - الانحراف (Variance)
    - نسبة الاستخدام
    """
    # الحصول على الفترة من الطلب أو استخدام الشهر الحالي
    year = int(request.GET.get('year', timezone.now().year))
    month = int(request.GET.get('month', timezone.now().month))
    cost_center_id = request.GET.get('cost_center')
    
    # تحديد تواريخ الفترة
    start_date = datetime(year, month, 1).date()
    if month == 12:
        end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
    else:
        end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)
    
    # الحصول على مراكز التكلفة
    cost_centers = CostCenter.objects.filter(is_active=True)
    if cost_center_id:
        cost_centers = cost_centers.filter(id=cost_center_id)
    
    results = []
    total_budget = Decimal('0')
    total_actual = Decimal('0')
    total_variance = Decimal('0')
    
    for cc in cost_centers:
        # الحصول على الموازنة للفترة (موازنة سنوية مقسمة على 12 شهر)
        budget_data = CostCenterBudget.objects.filter(
            cost_center=cc,
            fiscal_year__start_date__lte=end_date,
            fiscal_year__end_date__gte=start_date
        ).aggregate(total=Sum('total_budget'))['total'] or Decimal('0')
        
        # تقسيم الموازنة السنوية على عدد الأشهر للحصول على الموازنة الشهرية
        budget = budget_data / 12 if budget_data > 0 else Decimal('0')
        
        # الحصول على المصروفات الفعلية
        actual = JournalEntryItem.objects.filter(
            cost_center=cc,
            journal_entry__is_posted=True,
            journal_entry__date__gte=start_date,
            journal_entry__date__lte=end_date,
            type='debit',
            account__account_type='expense'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        # حساب الانحراف
        variance = budget - actual
        variance_pct = (variance / budget * 100) if budget > 0 else Decimal('0')
        utilization_pct = (actual / budget * 100) if budget > 0 else Decimal('0')
        
        # تحديد حالة التنبيه
        status = 'success'
        if utilization_pct > 100:
            status = 'danger'  # تجاوز الموازنة
        elif utilization_pct > 90:
            status = 'warning'  # قريب من الحد
        
        results.append({
            'cost_center': cc,
            'budget': budget,
            'actual': actual,
            'variance': variance,
            'variance_pct': variance_pct,
            'utilization_pct': utilization_pct,
            'status': status
        })
        
        total_budget += budget
        total_actual += actual
        total_variance += variance
    
    # إذا كان الطلب JSON، نرجع البيانات
    if request.GET.get('format') == 'json':
        data = {
            'period': f"{year}-{month:02d}",
            'total_budget': float(total_budget),
            'total_actual': float(total_actual),
            'total_variance': float(total_variance),
            'total_utilization_pct': float((total_actual / total_budget * 100) if total_budget > 0 else 0),
            'cost_centers': [
                {
                    'code': r['cost_center'].code,
                    'name': r['cost_center'].name,
                    'budget': float(r['budget']),
                    'actual': float(r['actual']),
                    'variance': float(r['variance']),
                    'variance_pct': float(r['variance_pct']),
                    'utilization_pct': float(r['utilization_pct']),
                    'status': r['status']
                }
                for r in results
            ]
        }
        return JsonResponse(data)
    
    context = {
        'results': results,
        'year': year,
        'month': month,
        'start_date': start_date,
        'end_date': end_date,
        'total_budget': total_budget,
        'total_actual': total_actual,
        'total_variance': total_variance,
        'total_utilization_pct': (total_actual / total_budget * 100) if total_budget > 0 else 0,
        'cost_centers': CostCenter.objects.filter(is_active=True),
        'selected_cost_center': cost_center_id,
        'years': [2024, 2025, 2026, 2027],
        'months': range(1, 13)
    }
    
    return render(request, 'accounting/reports/budget_vs_actual.html', context)


@login_required
def product_profitability_report(request):
    """
    تقرير ربحية المنتجات
    
    يحسب:
    - تكلفة المنتج (مواد + عمالة + مصاريف صناعية)
    - سعر البيع المتوسط
    - هامش الربح
    - إجمالي المبيعات والأرباح
    """
    # الحصول على الفترة
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    product_id = request.GET.get('product')
    
    if not start_date:
        start_date = (timezone.now() - timedelta(days=30)).date()
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    
    if not end_date:
        end_date = timezone.now().date()
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # الحصول على المنتجات
    products = Product.objects.all()
    if product_id:
        products = products.filter(id=product_id)
    
    results = []
    total_revenue = Decimal('0')
    total_cost = Decimal('0')
    total_profit = Decimal('0')
    
    for product in products:
        # الحصول على المبيعات
        sales_data = InvoiceItem.objects.filter(
            product=product,
            invoice__date__gte=start_date,
            invoice__date__lte=end_date,
            invoice__is_deleted=False
        ).aggregate(
            qty=Sum('quantity'),
            revenue=Sum(F('quantity') * F('price'))
        )
        
        quantity_sold = sales_data['qty'] or Decimal('0')
        revenue = sales_data['revenue'] or Decimal('0')
        
        if quantity_sold == 0:
            continue  # تخطي المنتجات التي لم تُباع
        
        # الحصول على التكلفة من BOM أو التكلفة المسجلة
        bom = BillOfMaterials.objects.filter(product=product, is_active=True).first()
        if bom:
            unit_cost = bom.total_cost or product.cost or Decimal('0')
        else:
            unit_cost = product.cost or Decimal('0')
        
        total_cost_for_product = unit_cost * quantity_sold
        profit = revenue - total_cost_for_product
        profit_margin = (profit / revenue * 100) if revenue > 0 else Decimal('0')
        avg_selling_price = revenue / quantity_sold if quantity_sold > 0 else Decimal('0')
        
        results.append({
            'product': product,
            'quantity_sold': quantity_sold,
            'unit_cost': unit_cost,
            'avg_selling_price': avg_selling_price,
            'revenue': revenue,
            'total_cost': total_cost_for_product,
            'profit': profit,
            'profit_margin': profit_margin
        })
        
        total_revenue += revenue
        total_cost += total_cost_for_product
        total_profit += profit
    
    # ترتيب حسب الربحية
    results.sort(key=lambda x: x['profit'], reverse=True)
    
    # JSON response
    if request.GET.get('format') == 'json':
        data = {
            'period': f"{start_date} to {end_date}",
            'total_revenue': float(total_revenue),
            'total_cost': float(total_cost),
            'total_profit': float(total_profit),
            'total_profit_margin': float((total_profit / total_revenue * 100) if total_revenue > 0 else 0),
            'products': [
                {
                    'sku': r['product'].sku,
                    'name': r['product'].name,
                    'quantity_sold': float(r['quantity_sold']),
                    'unit_cost': float(r['unit_cost']),
                    'avg_selling_price': float(r['avg_selling_price']),
                    'revenue': float(r['revenue']),
                    'total_cost': float(r['total_cost']),
                    'profit': float(r['profit']),
                    'profit_margin': float(r['profit_margin'])
                }
                for r in results
            ]
        }
        return JsonResponse(data)
    
    context = {
        'results': results,
        'start_date': start_date,
        'end_date': end_date,
        'total_revenue': total_revenue,
        'total_cost': total_cost,
        'total_profit': total_profit,
        'total_profit_margin': (total_profit / total_revenue * 100) if total_revenue > 0 else 0,
        'products': Product.objects.all(),
        'selected_product': product_id
    }
    
    return render(request, 'accounting/reports/product_profitability.html', context)


@login_required
def customer_profitability_report(request):
    """
    تقرير ربحية العملاء
    
    يحسب لكل عميل:
    - إجمالي المبيعات
    - التكلفة التقديرية
    - هامش الربح
    """
    from partners.models import Customer
    
    # الحصول على الفترة
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if not start_date:
        start_date = (timezone.now() - timedelta(days=90)).date()
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    
    if not end_date:
        end_date = timezone.now().date()
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # الحصول على العملاء الذين لديهم مبيعات في الفترة
    customers = Customer.objects.filter(
        invoices__date__gte=start_date,
        invoices__date__lte=end_date,
        invoices__is_deleted=False
    ).distinct()
    
    results = []
    
    for customer in customers:
        # المبيعات
        invoices = Invoice.objects.filter(
            customer=customer,
            date__gte=start_date,
            date__lte=end_date,
            is_deleted=False
        )
        
        revenue = invoices.aggregate(total=Sum('cached_total'))['total'] or Decimal('0')
        # Subtract discounts
        discount_total = invoices.aggregate(total=Sum('discount'))['total'] or Decimal('0')
        revenue = revenue - discount_total
        
        # حساب التكلفة التقديرية من الأصناف المباعة
        estimated_cost = Decimal('0')
        for invoice in invoices:
            for item in invoice.items.all():
                product_cost = item.product.cost or Decimal('0')
                estimated_cost += product_cost * item.quantity
        
        profit = revenue - estimated_cost
        profit_margin = (profit / revenue * 100) if revenue > 0 else Decimal('0')
        
        results.append({
            'customer': customer,
            'revenue': revenue,
            'estimated_cost': estimated_cost,
            'profit': profit,
            'profit_margin': profit_margin,
            'invoice_count': invoices.count()
        })
    
    # ترتيب حسب الربح
    results.sort(key=lambda x: x['profit'], reverse=True)
    
    total_revenue = sum(r['revenue'] for r in results)
    total_cost = sum(r['estimated_cost'] for r in results)
    total_profit = sum(r['profit'] for r in results)
    total_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else Decimal('0')
    
    if request.GET.get('format') == 'json':
        data = {
            'period': f"{start_date} to {end_date}",
            'total_revenue': float(total_revenue),
            'total_cost': float(total_cost),
            'total_profit': float(total_profit),
            'customers': [
                {
                    'name': r['customer'].name,
                    'revenue': float(r['revenue']),
                    'estimated_cost': float(r['estimated_cost']),
                    'profit': float(r['profit']),
                    'profit_margin': float(r['profit_margin']),
                    'invoice_count': r['invoice_count']
                }
                for r in results
            ]
        }
        return JsonResponse(data)
    
    context = {
        'results': results,
        'start_date': start_date,
        'end_date': end_date,
        'total_revenue': total_revenue,
        'total_cost': total_cost,
        'total_profit': total_profit,
        'total_margin': total_margin
    }
    
    return render(request, 'accounting/reports/customer_profitability.html', context)


@login_required
def variance_analysis_dashboard(request):
    """
    لوحة تحليل الانحرافات
    
    تعرض:
    - انحرافات الموازنة
    - انحرافات التكلفة المعيارية
    - تنبيهات التجاوزات
    """
    # الحصول على الشهر الحالي
    now = timezone.now()
    year = now.year
    month = now.month
    
    # مراكز التكلفة المتجاوزة للموازنة
    over_budget_centers = []
    
    cost_centers = CostCenter.objects.filter(is_active=True)
    for cc in cost_centers:
        budget = CostCenterBudget.objects.filter(
            cost_center=cc,
            fiscal_year__is_active=True,
            period_type='monthly',
            period=month
        ).aggregate(total=Sum('budget_amount'))['total'] or Decimal('0')
        
        if budget == 0:
            continue
        
        actual = JournalEntryItem.objects.filter(
            cost_center=cc,
            journal_entry__is_posted=True,
            journal_entry__date__year=year,
            journal_entry__date__month=month,
            type='debit',
            account__account_type='expense'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        if actual > budget:
            over_budget_centers.append({
                'cost_center': cc,
                'budget': budget,
                'actual': actual,
                'variance': budget - actual,
                'over_pct': ((actual - budget) / budget * 100)
            })
    
    # ترتيب حسب التجاوز
    over_budget_centers.sort(key=lambda x: x['over_pct'], reverse=True)
    
    context = {
        'over_budget_centers': over_budget_centers[:10],  # أعلى 10
        'year': year,
        'month': month
    }
    
    return render(request, 'accounting/reports/variance_dashboard.html', context)
