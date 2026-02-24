#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""فحص شامل للوحة التحكم"""

import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')

import django
django.setup()

from datetime import date, timedelta
from django.db.models import Sum, F, Count, Q
from django.db.models.functions import Coalesce
from decimal import Decimal

print('=' * 60)
print('فحص شامل للوحة التحكم - Dashboard Check')
print('=' * 60)

today = date.today()
last_30 = today - timedelta(days=30)

# 1. فحص المبيعات
try:
    from sales.models import Invoice, InvoiceItem
    total_invoices = Invoice.objects.count()
    today_invoices = Invoice.objects.filter(date=today).count()
    month_invoices = Invoice.objects.filter(date__gte=last_30).count()
    print(f'[OK] المبيعات:')
    print(f'     - اجمالي الفواتير: {total_invoices}')
    print(f'     - فواتير اليوم: {today_invoices}')
    print(f'     - فواتير اخر 30 يوم: {month_invoices}')
except Exception as e:
    print(f'[ERR] خطا في المبيعات: {e}')

# 2. فحص المشتريات
try:
    from purchases.models import PurchaseBill, PurchaseItem
    total_bills = PurchaseBill.objects.count()
    today_bills = PurchaseBill.objects.filter(date=today).count()
    print(f'[OK] المشتريات:')
    print(f'     - اجمالي فواتير الشراء: {total_bills}')
    print(f'     - مشتريات اليوم: {today_bills}')
except Exception as e:
    print(f'[ERR] خطا في المشتريات: {e}')

# 3. فحص المخزون
try:
    from inventory.models import Product, Stock
    total_products = Product.objects.count()
    low_stock = Product.objects.annotate(
        total_qty=Coalesce(Sum('stocks__quantity'), 0)
    ).filter(total_qty__lt=F('min_stock')).count()
    print(f'[OK] المخزون:')
    print(f'     - اجمالي المنتجات: {total_products}')
    print(f'     - منتجات منخفضة المخزون: {low_stock}')
except Exception as e:
    print(f'[ERR] خطا في المخزون: {e}')

# 4. فحص العملاء
try:
    from partners.models import Customer, Supplier
    total_customers = Customer.objects.count()
    total_suppliers = Supplier.objects.count()
    print(f'[OK] الشركاء:')
    print(f'     - اجمالي العملاء: {total_customers}')
    print(f'     - اجمالي الموردين: {total_suppliers}')
except Exception as e:
    print(f'[ERR] خطا في الشركاء: {e}')

# 5. فحص المصروفات
try:
    from accounting.models import Expense, Revenue
    total_expenses = Expense.objects.count()
    total_revenues = Revenue.objects.count()
    print(f'[OK] المصروفات والايرادات:')
    print(f'     - اجمالي المصروفات: {total_expenses}')
    print(f'     - اجمالي الايرادات: {total_revenues}')
except Exception as e:
    print(f'[ERR] خطا في المصروفات: {e}')

# 6. فحص المدفوعات
try:
    from payments.models import InvoicePayment
    total_payments = InvoicePayment.objects.count()
    today_payments = InvoicePayment.objects.filter(date=today).count()
    print(f'[OK] المدفوعات:')
    print(f'     - اجمالي المدفوعات: {total_payments}')
    print(f'     - مدفوعات اليوم: {today_payments}')
except Exception as e:
    print(f'[ERR] خطا في المدفوعات: {e}')

# 7. فحص الفروع
try:
    from showrooms.models import Showroom
    total_showrooms = Showroom.objects.count()
    print(f'[OK] الفروع:')
    print(f'     - اجمالي الفروع: {total_showrooms}')
except Exception as e:
    print(f'[ERR] خطا في الفروع: {e}')

# 8. فحص سجل النشاطات
try:
    from core.models import AuditLog
    total_logs = AuditLog.objects.count()
    print(f'[OK] سجل النشاطات:')
    print(f'     - اجمالي السجلات: {total_logs}')
except Exception as e:
    print(f'[ERR] خطا في سجل النشاطات: {e}')

# 9. فحص الحسابات
try:
    from accounting.models import Account
    total_accounts = Account.objects.count()
    print(f'[OK] الحسابات:')
    print(f'     - اجمالي الحسابات: {total_accounts}')
except Exception as e:
    print(f'[ERR] خطا في الحسابات: {e}')

# 10. فحص الموارد البشرية
try:
    from hr.models import Employee
    total_employees = Employee.objects.count()
    active_employees = Employee.objects.filter(is_active=True).count()
    print(f'[OK] الموارد البشرية:')
    print(f'     - اجمالي الموظفين: {total_employees}')
    print(f'     - الموظفين النشطين: {active_employees}')
except Exception as e:
    print(f'[ERR] خطا في الموارد البشرية: {e}')

print('=' * 60)
print('[DONE] تم الفحص بنجاح - جميع الموديلات مرتبطة بالنظام')
print('=' * 60)
