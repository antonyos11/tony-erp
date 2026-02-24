from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, F, Q, Avg, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce, TruncDay, TruncMonth
from datetime import date, timedelta, datetime
from decimal import Decimal
from inventory.models import Product, Location, Stock
from sales.models import Invoice, InvoiceItem, InvoicePayment
from purchases.models import PurchaseBill, PurchaseItem
from partners.models import Customer, Supplier
from accounting.models import Expense


@login_required
def reports_dashboard(request):
    """Reports dashboard with basic analytics"""
    
    # Date ranges
    today = date.today()
    last_30_days = today - timedelta(days=30)
    last_7_days = today - timedelta(days=7)
    
    # Basic stats
    stats = {
        'total_products': Product.objects.count(),
        'total_customers': Customer.objects.count(),
        'total_suppliers': Supplier.objects.count(),
        'total_locations': Location.objects.count(),
        
        'invoices_30_days': Invoice.objects.filter(date__gte=last_30_days).count(),
        'purchases_30_days': PurchaseBill.objects.filter(date__gte=last_30_days).count(),
        
        # Rewritten to use item-level aggregations to avoid fragile 'items__' joins
        'sales_total_30_days': InvoiceItem.objects.filter(invoice__date__gte=last_30_days).aggregate(
            total=Sum(ExpressionWrapper(F('quantity') * F('price'), output_field=DecimalField(max_digits=18, decimal_places=2)))
        )['total'] or 0,
        'purchases_total_30_days': PurchaseItem.objects.filter(bill__date__gte=last_30_days).aggregate(
            total=Sum(ExpressionWrapper(F('quantity') * F('cost'), output_field=DecimalField(max_digits=18, decimal_places=2)))
        )['total'] or 0,
        
        'low_stock_count': Product.objects.annotate(
            total_qty=Coalesce(Sum('stocks__quantity'), 0)
        ).filter(total_qty__lt=F('min_stock')).count(),
    }
    
    # Top products by sales
    top_products = InvoiceItem.objects.values('product__name').annotate(
        total_sold=Sum('quantity'),
        total_revenue=Sum(ExpressionWrapper(F('quantity') * F('price'), output_field=DecimalField(max_digits=18, decimal_places=2)))
    ).order_by('-total_sold')[:5]
    
    # Recent activity
    recent_invoices = Invoice.objects.select_related('customer').order_by('-date')[:5]
    recent_purchases = PurchaseBill.objects.select_related('supplier').order_by('-date')[:5]
    
    context = {
        'stats': stats,
        'top_products': top_products,
        'recent_invoices': recent_invoices,
        'recent_purchases': recent_purchases,
    }
    return render(request, 'reports/dashboard.html', context)


@login_required
def sales_report(request):
    """Advanced sales reports"""
    
    # Get date filters
    date_from = request.GET.get('date_from', (date.today() - timedelta(days=30)).strftime('%Y-%m-%d'))
    date_to = request.GET.get('date_to', date.today().strftime('%Y-%m-%d'))
    
    # Parse dates
    from datetime import datetime
    date_from_parsed = datetime.strptime(date_from, '%Y-%m-%d').date()
    date_to_parsed = datetime.strptime(date_to, '%Y-%m-%d').date()
    
    # Sales summary
    invoices = Invoice.objects.filter(date__range=[date_from_parsed, date_to_parsed])
    
    items_qs = InvoiceItem.objects.filter(invoice__date__range=[date_from_parsed, date_to_parsed])
    item_total_expr = ExpressionWrapper(F('quantity') * F('price'), output_field=DecimalField(max_digits=18, decimal_places=2))
    total_revenue = items_qs.aggregate(total=Sum(item_total_expr))['total'] or 0
    if invoices.exists():
        per_invoice = items_qs.values('invoice_id').annotate(total=Sum(item_total_expr))
        totals = [r['total'] or 0 for r in per_invoice]
        avg_invoice = (sum(totals) / len(totals)) if totals else 0
    else:
        avg_invoice = 0
    sales_summary = {
        'total_invoices': invoices.count(),
        'total_revenue': total_revenue,
        'total_discount': invoices.aggregate(total=Sum('discount'))['total'] or 0,
        'total_paid': invoices.aggregate(total=Sum('paid'))['total'] or 0,
        'average_invoice': avg_invoice,
    }
    
    # Top customers
    top_customers = items_qs.values('invoice__customer__name').annotate(
        invoice_count=Count('invoice', distinct=True),
        total_amount=Sum(item_total_expr)
    ).order_by('-total_amount')[:10]
    
    # Top selling products
    top_products = InvoiceItem.objects.filter(
        invoice__date__range=[date_from_parsed, date_to_parsed]
    ).values('product__name').annotate(
        quantity_sold=Sum('quantity'),
        total_revenue=Sum(F('quantity') * F('price'))
    ).order_by('-quantity_sold')[:10]
    
    # Daily sales trend
    daily_sales = items_qs.values('invoice__date').annotate(
        revenue=Sum(item_total_expr),
        invoice_count=Count('invoice', distinct=True)
    ).order_by('invoice__date')
    
    context = {
        'date_from': date_from,
        'date_to': date_to,
        'sales_summary': sales_summary,
        'top_customers': top_customers,
        'top_products': top_products,
        'daily_sales': daily_sales,
    }
    return render(request, 'reports/sales_report.html', context)


@login_required
def inventory_report(request):
    """Advanced inventory reports"""
    
    # Stock status analysis
    products_with_stock = Product.objects.annotate(
        total_stock=Coalesce(
            Sum('stocks__quantity', output_field=DecimalField(max_digits=18, decimal_places=2)),
            0,
            output_field=DecimalField(max_digits=18, decimal_places=2)
        ),
        stock_value=Sum(
            ExpressionWrapper(F('stocks__quantity') * F('cost'), output_field=DecimalField(max_digits=18, decimal_places=2))
        ),
        locations_count=Count('stocks__location', distinct=True)
    )
    
    # Stock levels categorization
    stock_analysis = {
        'total_products': products_with_stock.count(),
        'out_of_stock': products_with_stock.filter(total_stock=0).count(),
        'low_stock': products_with_stock.filter(
            total_stock__gt=0, total_stock__lt=F('min_stock')
        ).count(),
        'good_stock': products_with_stock.filter(
            total_stock__gte=F('min_stock')
        ).count(),
        'total_value': products_with_stock.aggregate(
            total=Sum('stock_value')
        )['total'] or 0,
    }
    
    # Products by category/status
    out_of_stock_products = products_with_stock.filter(total_stock=0)[:10]
    low_stock_products = products_with_stock.filter(
        total_stock__gt=0, total_stock__lt=F('min_stock')
    )[:10]
    high_value_products = products_with_stock.filter(
        stock_value__gt=0
    ).order_by('-stock_value')[:10]
    
    # Stock by location (use values to avoid assigning annotated names onto model instances)
    locations_stock = (
        Location.objects.annotate(
            products_count=Count('stocks__product', distinct=True),
            total_items=Sum('stocks__quantity', output_field=DecimalField(max_digits=18, decimal_places=2)),
            stock_value_total=Sum(
                ExpressionWrapper(
                    F('stocks__quantity') * F('stocks__product__cost'),
                    output_field=DecimalField(max_digits=18, decimal_places=2),
                )
            ),
        )
        .order_by('-stock_value_total')
        .values('code', 'name', 'products_count', 'total_items', 'stock_value_total')
    )
    
    # Recent stock movements (from purchase items)
    recent_movements = PurchaseItem.objects.select_related(
        'product', 'location', 'bill'
    ).order_by('-bill__date')[:20]

    # Optional: export locations stock as CSV
    export = request.GET.get('export')
    if export == 'locations_csv':
        import csv
        # Ensure we have a concrete iterable of dicts
        rows = list(locations_stock)
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="locations_stock.csv"'
        # UTF-8 BOM for Excel compatibility
        response.write('\ufeff')
        writer = csv.writer(response)
        writer.writerow(['الكود', 'الاسم', 'عدد الأصناف', 'إجمالي الكمية', 'إجمالي القيمة'])
        for r in rows:
            writer.writerow([
                r.get('code') or '',
                r.get('name') or '',
                r.get('products_count') or 0,
                r.get('total_items') or 0,
                f"{float(r.get('stock_value_total') or 0):.2f}",
            ])
        return response
    elif export == 'csv':
        # Export critical products (out of stock, low stock, high value)
        import csv
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="critical_products.csv"'
        response.write('\ufeff')  # UTF-8 BOM for Excel
        writer = csv.writer(response)
        writer.writerow(['النوع', 'الاسم', 'الكمية', 'الحد الأدنى', 'قيمة المخزون'])

        # Prepare safe accessors
        def _flt(v):
            try:
                return float(v or 0)
            except Exception:
                return 0.0

        # Out of stock
        for p in out_of_stock_products.values('name', 'total_stock', 'min_stock', 'stock_value'):
            writer.writerow(['منعدم', p.get('name') or '', _flt(p.get('total_stock')), p.get('min_stock') or 0, f"{_flt(p.get('stock_value')):.2f}"])

        # Low stock
        for p in low_stock_products.values('name', 'total_stock', 'min_stock', 'stock_value'):
            writer.writerow(['منخفض', p.get('name') or '', _flt(p.get('total_stock')), p.get('min_stock') or 0, f"{_flt(p.get('stock_value')):.2f}"])

        # High value
        for p in high_value_products.values('name', 'total_stock', 'min_stock', 'stock_value'):
            writer.writerow(['عالي القيمة', p.get('name') or '', _flt(p.get('total_stock')), p.get('min_stock') or 0, f"{_flt(p.get('stock_value')):.2f}"])

        return response
    
    context = {
        'stock_analysis': stock_analysis,
        'out_of_stock_products': out_of_stock_products,
        'low_stock_products': low_stock_products,
        'high_value_products': high_value_products,
        'locations_stock': locations_stock,
        'recent_movements': recent_movements,
    }
    return render(request, 'reports/inventory_report.html', context)


@login_required
def purchases_report(request):
    """Purchases analysis report"""
    
    # Get date filters
    date_from = request.GET.get('date_from', (date.today() - timedelta(days=30)).strftime('%Y-%m-%d'))
    date_to = request.GET.get('date_to', date.today().strftime('%Y-%m-%d'))
    
    from datetime import datetime
    date_from_parsed = datetime.strptime(date_from, '%Y-%m-%d').date()
    date_to_parsed = datetime.strptime(date_to, '%Y-%m-%d').date()
    
    # Purchases summary
    bills = PurchaseBill.objects.filter(date__range=[date_from_parsed, date_to_parsed])
    
    purchase_items = PurchaseItem.objects.filter(bill__date__range=[date_from_parsed, date_to_parsed])
    item_cost_expr = ExpressionWrapper(F('quantity') * F('cost'), output_field=DecimalField(max_digits=18, decimal_places=2))
    total_cost = purchase_items.aggregate(total=Sum(item_cost_expr))['total'] or 0
    if bills.exists():
        per_bill = purchase_items.values('bill_id').annotate(total=Sum(item_cost_expr))
        bill_totals = [r['total'] or 0 for r in per_bill]
        avg_bill = (sum(bill_totals) / len(bill_totals)) if bill_totals else 0
    else:
        avg_bill = 0
    purchases_summary = {
        'total_bills': bills.count(),
        'total_amount': total_cost,
        'total_discount': bills.aggregate(total=Sum('discount'))['total'] or 0,
        'total_paid': bills.aggregate(total=Sum('paid'))['total'] or 0,
        'average_bill': avg_bill,
    }
    
    # Top suppliers
    top_suppliers = purchase_items.values('bill__supplier__name').annotate(
        bill_count=Count('bill', distinct=True),
        total_amount=Sum(item_cost_expr)
    ).order_by('-total_amount')[:10]
    
    # Most purchased products
    top_purchased = PurchaseItem.objects.filter(
        bill__date__range=[date_from_parsed, date_to_parsed]
    ).values('product__name').annotate(
        quantity_purchased=Sum('quantity'),
        total_cost=Sum(F('quantity') * F('cost'))
    ).order_by('-quantity_purchased')[:10]
    
    context = {
        'date_from': date_from,
        'date_to': date_to,
        'purchases_summary': purchases_summary,
        'top_suppliers': top_suppliers,
        'top_purchased': top_purchased,
    }
    return render(request, 'reports/purchases_report.html', context)


# ==================== تقارير عامة ====================

@login_required
def account_statement_report(request):
    """تقرير كشف حساب العملاء والموردين"""
    partner_type = request.GET.get('type', 'customer')
    partner_id = request.GET.get('id')
    date_from = request.GET.get('date_from', (date.today() - timedelta(days=90)).strftime('%Y-%m-%d'))
    date_to = request.GET.get('date_to', date.today().strftime('%Y-%m-%d'))
    
    customers = Customer.objects.all()[:50]
    suppliers = Supplier.objects.all()[:50]
    
    transactions = []
    partner = None
    opening_balance = Decimal('0')
    
    if partner_id:
        date_from_parsed = datetime.strptime(date_from, '%Y-%m-%d').date()
        date_to_parsed = datetime.strptime(date_to, '%Y-%m-%d').date()
        
        if partner_type == 'customer':
            try:
                partner = Customer.objects.get(pk=partner_id)
                invoices = Invoice.objects.filter(
                    customer=partner,
                    date__range=[date_from_parsed, date_to_parsed]
                ).order_by('date')
                
                running_balance = opening_balance
                for inv in invoices:
                    running_balance += inv.total - inv.paid
                    transactions.append({
                        'date': inv.date,
                        'type': 'فاتورة بيع',
                        'reference': inv.number,
                        'debit': inv.total,
                        'credit': inv.paid,
                        'balance': running_balance,
                        'notes': f'فاتورة للعميل'
                    })
            except Customer.DoesNotExist:
                pass
        else:
            try:
                partner = Supplier.objects.get(pk=partner_id)
                bills = PurchaseBill.objects.filter(
                    supplier=partner,
                    date__range=[date_from_parsed, date_to_parsed]
                ).order_by('date')
                
                running_balance = opening_balance
                for bill in bills:
                    running_balance += bill.total - bill.paid
                    transactions.append({
                        'date': bill.date,
                        'type': 'فاتورة شراء',
                        'reference': bill.number,
                        'debit': bill.paid,
                        'credit': bill.total,
                        'balance': running_balance,
                        'notes': f'فاتورة من المورد'
                    })
            except Supplier.DoesNotExist:
                pass
    
    context = {
        'partner_type': partner_type,
        'partner': partner,
        'customers': customers,
        'suppliers': suppliers,
        'transactions': transactions,
        'opening_balance': opening_balance,
        'date_from': date_from,
        'date_to': date_to,
        'report_title': 'كشف حساب عملاء/موردين',
    }
    return render(request, 'reports/account_statement.html', context)


@login_required
def customer_debts_report(request):
    """تقرير مديونية العملاء"""
    customers = Customer.objects.annotate(
        total_sales=Coalesce(Sum('invoices__total'), Decimal('0')),
        total_paid=Coalesce(Sum('invoices__paid'), Decimal('0')),
    ).annotate(
        balance=F('total_sales') - F('total_paid')
    ).filter(balance__gt=0).order_by('-balance')
    
    total_debt = customers.aggregate(total=Sum('balance'))['total'] or 0
    
    context = {
        'customers': customers,
        'total_debt': total_debt,
        'report_title': 'مديونية العملاء',
    }
    return render(request, 'reports/customer_debts.html', context)


@login_required
def supplier_debts_report(request):
    """تقرير مديونية الموردين"""
    suppliers = Supplier.objects.annotate(
        total_purchases=Coalesce(Sum('bills__total'), Decimal('0')),
        total_paid=Coalesce(Sum('bills__paid'), Decimal('0')),
    ).annotate(
        balance=F('total_purchases') - F('total_paid')
    ).filter(balance__gt=0).order_by('-balance')
    
    total_debt = suppliers.aggregate(total=Sum('balance'))['total'] or 0
    
    context = {
        'suppliers': suppliers,
        'total_debt': total_debt,
        'report_title': 'مديونية الموردين',
    }
    return render(request, 'reports/supplier_debts.html', context)


@login_required
def sales_representatives_report(request):
    """تقرير تحصيلات المناديب - يعتمد على من أنشأ الدفعات"""
    date_from = request.GET.get('date_from', (date.today() - timedelta(days=30)).strftime('%Y-%m-%d'))
    date_to = request.GET.get('date_to', date.today().strftime('%Y-%m-%d'))
    
    date_from_parsed = datetime.strptime(date_from, '%Y-%m-%d').date()
    date_to_parsed = datetime.strptime(date_to, '%Y-%m-%d').date()
    
    # تحصيلات حسب المندوب (من أنشأ الدفعات)
    sales_by_rep = InvoicePayment.objects.filter(
        date__date__range=[date_from_parsed, date_to_parsed],
        created_by__isnull=False
    ).values('created_by__username', 'created_by__first_name', 'created_by__last_name').annotate(
        payment_count=Count('id'),
        total_collected=Sum('amount'),
        customer_count=Count('customer', distinct=True),
    ).order_by('-total_collected')
    
    # تحصيلات حسب المندوب والعميل
    sales_by_rep_customer = InvoicePayment.objects.filter(
        date__date__range=[date_from_parsed, date_to_parsed],
        created_by__isnull=False
    ).values(
        'created_by__username', 'customer__name'
    ).annotate(
        payment_count=Count('id'),
        total_collected=Sum('amount'),
    ).order_by('created_by__username', '-total_collected')[:50]
    
    context = {
        'sales_by_rep': sales_by_rep,
        'sales_by_rep_customer': sales_by_rep_customer,
        'date_from': date_from,
        'date_to': date_to,
        'report_title': 'تحصيلات المناديب والعملاء',
    }
    return render(request, 'reports/sales_representatives.html', context)


@login_required
def top_selling_report(request):
    """تقرير الأصناف الأكثر مبيعاً"""
    date_from = request.GET.get('date_from', (date.today() - timedelta(days=30)).strftime('%Y-%m-%d'))
    date_to = request.GET.get('date_to', date.today().strftime('%Y-%m-%d'))
    limit = int(request.GET.get('limit', 20))
    
    date_from_parsed = datetime.strptime(date_from, '%Y-%m-%d').date()
    date_to_parsed = datetime.strptime(date_to, '%Y-%m-%d').date()
    
    top_products = InvoiceItem.objects.filter(
        invoice__date__range=[date_from_parsed, date_to_parsed]
    ).values('product__name', 'product__sku').annotate(
        quantity_sold=Sum('quantity'),
        total_revenue=Sum(F('quantity') * F('price')),
        invoice_count=Count('invoice', distinct=True),
    ).order_by('-quantity_sold')[:limit]
    
    context = {
        'products': top_products,
        'date_from': date_from,
        'date_to': date_to,
        'limit': limit,
        'report_title': 'الأصناف الأكثر مبيعاً',
    }
    return render(request, 'reports/top_selling.html', context)


@login_required
def least_selling_report(request):
    """تقرير الأصناف الأقل مبيعاً"""
    date_from = request.GET.get('date_from', (date.today() - timedelta(days=90)).strftime('%Y-%m-%d'))
    date_to = request.GET.get('date_to', date.today().strftime('%Y-%m-%d'))
    limit = int(request.GET.get('limit', 20))
    
    date_from_parsed = datetime.strptime(date_from, '%Y-%m-%d').date()
    date_to_parsed = datetime.strptime(date_to, '%Y-%m-%d').date()
    
    # المنتجات التي لها مبيعات قليلة
    sold_products = InvoiceItem.objects.filter(
        invoice__date__range=[date_from_parsed, date_to_parsed]
    ).values('product_id').annotate(
        quantity_sold=Sum('quantity')
    )
    
    # المنتجات الراكدة (لم تباع أو بيعت قليلاً)
    slow_moving = Product.objects.annotate(
        total_stock=Coalesce(Sum('stocks__quantity'), Decimal('0')),
        sold_qty=Coalesce(
            Sum('invoiceitem__quantity', filter=Q(
                invoiceitem__invoice__date__range=[date_from_parsed, date_to_parsed]
            )), Decimal('0')
        )
    ).filter(total_stock__gt=0).order_by('sold_qty')[:limit]
    
    context = {
        'products': slow_moving,
        'date_from': date_from,
        'date_to': date_to,
        'limit': limit,
        'report_title': 'الأصناف الأقل مبيعاً / الراكدة',
    }
    return render(request, 'reports/least_selling.html', context)


@login_required
def customer_details_report(request):
    """تقرير تفصيلي للعملاء"""
    # استخدام cached_total بدلاً من total (لأن total هو property وليس حقل في قاعدة البيانات)
    customers = Customer.objects.annotate(
        invoice_count=Count('invoices'),
        total_sales=Coalesce(Sum('invoices__cached_total') - Sum('invoices__discount'), Decimal('0')),
        total_paid=Coalesce(Sum('invoices__paid'), Decimal('0')),
    ).order_by('-total_sales')
    
    # إحصائيات عامة
    stats = {
        'total_customers': customers.count(),
        'active_customers': customers.filter(invoice_count__gt=0).count(),
        'total_sales': customers.aggregate(total=Sum('total_sales'))['total'] or 0,
        'total_debt': customers.aggregate(
            total=Sum(F('total_sales') - F('total_paid'))
        )['total'] or 0,
    }
    
    context = {
        'customers': customers[:100],
        'stats': stats,
        'report_title': 'تقرير العملاء التفصيلي',
    }
    return render(request, 'reports/customer_details.html', context)


@login_required
def supplier_details_report(request):
    """تقرير تفصيلي للموردين"""
    # حساب إجمالي المشتريات عن طريق جمع قيم بنود الفواتير (لأن total هو property)
    # PurchaseItem يستخدم cost بدلاً من price
    suppliers = Supplier.objects.annotate(
        bill_count=Count('bills', distinct=True),
        total_purchases=Coalesce(
            Sum(F('bills__items__quantity') * F('bills__items__cost')) - Sum('bills__discount'),
            Decimal('0')
        ),
        total_paid=Coalesce(Sum('bills__paid'), Decimal('0')),
    ).order_by('-total_purchases')
    
    # إحصائيات عامة
    stats = {
        'total_suppliers': Supplier.objects.count(),
        'active_suppliers': suppliers.filter(bill_count__gt=0).count(),
        'total_purchases': suppliers.aggregate(total=Sum('total_purchases'))['total'] or 0,
        'total_debt': suppliers.aggregate(
            total=Sum(F('total_purchases') - F('total_paid'))
        )['total'] or 0,
    }
    
    context = {
        'suppliers': suppliers[:100],
        'stats': stats,
        'report_title': 'تقرير الموردين التفصيلي',
    }
    return render(request, 'reports/supplier_details.html', context)


@login_required
def daily_expenses_report(request):
    """تقرير المصاريف اليومية"""
    date_from = request.GET.get('date_from', (date.today() - timedelta(days=30)).strftime('%Y-%m-%d'))
    date_to = request.GET.get('date_to', date.today().strftime('%Y-%m-%d'))
    
    date_from_parsed = datetime.strptime(date_from, '%Y-%m-%d').date()
    date_to_parsed = datetime.strptime(date_to, '%Y-%m-%d').date()
    
    # المصاريف حسب اليوم
    daily_expenses = Expense.objects.filter(
        date__range=[date_from_parsed, date_to_parsed]
    ).values('date').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-date')
    
    # قائمة المصاريف مع الوصف (بدلاً من الفئة لأن نموذج Expense لا يحتوي على حقل category)
    expense_list = Expense.objects.filter(
        date__range=[date_from_parsed, date_to_parsed]
    ).order_by('-date', '-id')[:100]
    
    # إجمالي المصاريف
    total = Expense.objects.filter(
        date__range=[date_from_parsed, date_to_parsed]
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    context = {
        'daily_expenses': daily_expenses,
        'expense_list': expense_list,
        'total': total,
        'date_from': date_from,
        'date_to': date_to,
        'report_title': 'تقرير المصاريف اليومية',
    }
    return render(request, 'reports/daily_expenses.html', context)


@login_required
def comprehensive_report(request):
    """تقرير شامل للعملاء والموردين"""
    today = date.today()
    last_30_days = today - timedelta(days=30)
    
    # إحصائيات العملاء - استخدام cached_total بدلاً من total (property)
    customer_stats = {
        'total': Customer.objects.count(),
        'with_debt': Customer.objects.annotate(
            debt=Coalesce(Sum('invoices__cached_total') - Sum('invoices__discount'), Decimal('0')) - Coalesce(Sum('invoices__paid'), Decimal('0'))
        ).filter(debt__gt=0).count(),
        'total_sales': Invoice.objects.filter(date__gte=last_30_days).aggregate(
            total=Coalesce(Sum('cached_total') - Sum('discount'), Decimal('0'))
        )['total'] or 0,
    }
    
    # إحصائيات الموردين - استخدام items لحساب الإجمالي (لأن total هو property)
    supplier_stats = {
        'total': Supplier.objects.count(),
        'with_debt': Supplier.objects.annotate(
            total_purchases=Coalesce(Sum(F('bills__items__quantity') * F('bills__items__cost')) - Sum('bills__discount'), Decimal('0')),
            total_paid=Coalesce(Sum('bills__paid'), Decimal('0'))
        ).annotate(
            debt=F('total_purchases') - F('total_paid')
        ).filter(debt__gt=0).count(),
        'total_purchases': PurchaseItem.objects.filter(bill__date__gte=last_30_days).aggregate(
            total=Coalesce(Sum(F('quantity') * F('cost')), Decimal('0'))
        )['total'] or 0,
    }
    
    # أعلى 5 عملاء
    top_customers = Customer.objects.annotate(
        total=Coalesce(Sum('invoices__cached_total') - Sum('invoices__discount'), Decimal('0'))
    ).order_by('-total')[:5]
    
    # أعلى 5 موردين
    top_suppliers = Supplier.objects.annotate(
        total=Coalesce(Sum(F('bills__items__quantity') * F('bills__items__cost')) - Sum('bills__discount'), Decimal('0'))
    ).order_by('-total')[:5]
    
    context = {
        'customer_stats': customer_stats,
        'supplier_stats': supplier_stats,
        'top_customers': top_customers,
        'top_suppliers': top_suppliers,
        'report_title': 'تقرير شامل للعملاء والموردين',
    }
    return render(request, 'reports/comprehensive.html', context)


@login_required
def price_comparison_report(request):
    """تقرير مقارنة أسعار الأصناف"""
    products = Product.objects.annotate(
        avg_purchase_price=Avg('purchaseitem__cost'),
        last_purchase_price=Coalesce(
            Avg('purchaseitem__cost'),
            F('cost')
        ),
        avg_sale_price=Avg('invoiceitem__price'),
        margin=F('price') - F('cost'),
    ).order_by('name')[:100]
    
    context = {
        'products': products,
        'report_title': 'مقارنة أسعار الأصناف',
    }
    return render(request, 'reports/price_comparison.html', context)


@login_required
def monthly_sales_comparison_report(request):
    """تقرير مقارنة المبيعات الشهرية"""
    # آخر 12 شهر
    monthly_sales = Invoice.objects.annotate(
        month=TruncMonth('date')
    ).values('month').annotate(
        invoice_count=Count('id'),
        total_sales=Sum(F('cached_total') - F('discount')),
        total_paid=Sum('paid'),
        total_discount=Sum('discount'),
    ).order_by('-month')[:12]
    
    context = {
        'monthly_sales': monthly_sales,
        'report_title': 'مقارنة المبيعات الشهرية',
    }
    return render(request, 'reports/monthly_comparison.html', context)


@login_required
def sales_rep_summary_report(request):
    """تقرير ملخص تحصيلات المناديب"""
    date_from = request.GET.get('date_from', (date.today() - timedelta(days=30)).strftime('%Y-%m-%d'))
    date_to = request.GET.get('date_to', date.today().strftime('%Y-%m-%d'))
    
    date_from_parsed = datetime.strptime(date_from, '%Y-%m-%d').date()
    date_to_parsed = datetime.strptime(date_to, '%Y-%m-%d').date()
    
    reps = InvoicePayment.objects.filter(
        date__date__range=[date_from_parsed, date_to_parsed],
        created_by__isnull=False
    ).values('created_by__username', 'created_by__first_name').annotate(
        payment_count=Count('id'),
        total_collected=Sum('amount'),
        customer_count=Count('customer', distinct=True),
    ).order_by('-total_collected')
    
    context = {
        'reps': reps,
        'date_from': date_from,
        'date_to': date_to,
        'report_title': 'ملخص تحصيلات المناديب',
    }
    return render(request, 'reports/sales_rep_summary.html', context)


@login_required
def sales_and_cost_report(request):
    """تقرير المبيعات والتكلفة"""
    date_from = request.GET.get('date_from', (date.today() - timedelta(days=30)).strftime('%Y-%m-%d'))
    date_to = request.GET.get('date_to', date.today().strftime('%Y-%m-%d'))
    
    date_from_parsed = datetime.strptime(date_from, '%Y-%m-%d').date()
    date_to_parsed = datetime.strptime(date_to, '%Y-%m-%d').date()
    
    # تحليل الربحية حسب المنتج
    products = InvoiceItem.objects.filter(
        invoice__date__range=[date_from_parsed, date_to_parsed]
    ).values('product__name', 'product__sku').annotate(
        quantity_sold=Sum('quantity'),
        total_revenue=Sum(F('quantity') * F('price')),
        total_cost=Sum(F('quantity') * F('product__cost')),
    ).annotate(
        profit=F('total_revenue') - F('total_cost'),
        margin_percent=ExpressionWrapper(
            (F('total_revenue') - F('total_cost')) * 100 / F('total_revenue'),
            output_field=DecimalField(max_digits=10, decimal_places=2)
        )
    ).order_by('-profit')[:50]
    
    # إجمالي
    totals = InvoiceItem.objects.filter(
        invoice__date__range=[date_from_parsed, date_to_parsed]
    ).aggregate(
        total_revenue=Sum(F('quantity') * F('price')),
        total_cost=Sum(F('quantity') * F('product__cost')),
    )
    totals['profit'] = (totals['total_revenue'] or 0) - (totals['total_cost'] or 0)
    
    context = {
        'products': products,
        'totals': totals,
        'date_from': date_from,
        'date_to': date_to,
        'report_title': 'تقرير المبيعات والتكلفة',
    }
    return render(request, 'reports/sales_and_cost.html', context)


@login_required
def equipment_usage_report(request):
    """تقرير استخدام المعدات"""
    try:
        from fixed_assets.models import Asset
        assets = Asset.objects.all()[:50]
    except:
        assets = []
    
    context = {
        'assets': assets,
        'report_title': 'تقرير استخدام المعدات',
    }
    return render(request, 'reports/equipment_usage.html', context)


@login_required
def equipment_maintenance_report(request):
    """تقرير صيانة المعدات"""
    try:
        from fixed_assets.models import Maintenance
        maintenances = Maintenance.objects.order_by('-date')[:50]
    except:
        maintenances = []
    
    context = {
        'maintenances': maintenances,
        'report_title': 'تقرير صيانة المعدات',
    }
    return render(request, 'reports/equipment_maintenance.html', context)


@login_required
def material_consumption_report(request):
    """تقرير استهلاك المواد"""
    date_from = request.GET.get('date_from', (date.today() - timedelta(days=30)).strftime('%Y-%m-%d'))
    date_to = request.GET.get('date_to', date.today().strftime('%Y-%m-%d'))
    
    date_from_parsed = datetime.strptime(date_from, '%Y-%m-%d').date()
    date_to_parsed = datetime.strptime(date_to, '%Y-%m-%d').date()
    
    # استهلاك المواد من المشتريات
    consumption = PurchaseItem.objects.filter(
        bill__date__range=[date_from_parsed, date_to_parsed]
    ).values('product__name', 'product__sku').annotate(
        total_quantity=Sum('quantity'),
        total_cost=Sum(F('quantity') * F('cost')),
    ).order_by('-total_cost')[:50]
    
    context = {
        'consumption': consumption,
        'date_from': date_from,
        'date_to': date_to,
        'report_title': 'تقرير استهلاك المواد',
    }
    return render(request, 'reports/material_consumption.html', context)
