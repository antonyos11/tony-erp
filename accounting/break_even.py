"""
Break-Even Analysis System
نظام تحليل نقطة التعادل

يحسب نقطة التعادل للمنتجات ومراكز التكلفة والشركة ككل
"""

from decimal import Decimal
from typing import Dict, List, Optional
from django.db.models import Sum, Q, F, Count
from django.utils import timezone
from datetime import datetime, timedelta


class BreakEvenAnalyzer:
    """محلل نقطة التعادل"""
    
    def __init__(self):
        self.default_period_days = 30
    
    def calculate_product_breakeven(
        self,
        product,
        period_days: int = None
    ) -> Dict:
        """
        حساب نقطة التعادل لمنتج محدد
        
        Returns:
            Dict يحتوي على:
            - breakeven_units: عدد الوحدات اللازمة للتعادل
            - breakeven_revenue: الإيرادات اللازمة للتعادل
            - current_units_sold: الوحدات المباعة فعلياً
            - profit_margin: هامش الربح
            - status: فوق/تحت التعادل
        """
        from sales.models import Invoice, InvoiceItem
        from production.models import ProductionOrder
        from accounting.models import JournalEntry
        
        period_days = period_days or self.default_period_days
        start_date = timezone.now().date() - timedelta(days=period_days)
        
        # حساب سعر البيع المتوسط
        sales_data = InvoiceItem.objects.filter(
            invoice__invoice_date__gte=start_date,
            product=product,
            invoice__status='paid'
        ).aggregate(
            total_revenue=Sum(F('quantity') * F('price')),
            total_quantity=Sum('quantity')
        )
        
        avg_selling_price = Decimal('0')
        if sales_data['total_quantity'] and sales_data['total_quantity'] > 0:
            avg_selling_price = Decimal(str(sales_data['total_revenue'] or 0)) / Decimal(str(sales_data['total_quantity']))
        else:
            # استخدام السعر الحالي
            avg_selling_price = product.price
        
        # حساب التكلفة المتغيرة (Variable Cost per Unit)
        variable_cost = self._calculate_variable_cost(product)
        
        # حساب التكاليف الثابتة المخصصة لهذا المنتج
        fixed_costs = self._calculate_allocated_fixed_costs(product, period_days)
        
        # حساب هامش المساهمة
        contribution_margin = avg_selling_price - variable_cost
        
        # حساب نقطة التعادل (بالوحدات)
        breakeven_units = Decimal('0')
        if contribution_margin > 0:
            breakeven_units = fixed_costs / contribution_margin
        
        # حساب نقطة التعادل (بالإيرادات)
        breakeven_revenue = breakeven_units * avg_selling_price
        
        # الوحدات المباعة فعلياً
        current_units_sold = sales_data['total_quantity'] or 0
        
        # حساب الحالة
        if current_units_sold >= breakeven_units:
            status = 'profitable'
            units_above_breakeven = current_units_sold - float(breakeven_units)
        else:
            status = 'below_breakeven'
            units_above_breakeven = current_units_sold - float(breakeven_units)  # سيكون سالب
        
        # حساب هامش الأمان
        safety_margin = Decimal('0')
        if current_units_sold > 0:
            safety_margin = ((Decimal(str(current_units_sold)) - breakeven_units) / Decimal(str(current_units_sold))) * 100
        
        return {
            'product': {
                'id': product.id,
                'name': product.name,
                'sku': product.sku
            },
            'pricing': {
                'avg_selling_price': float(avg_selling_price),
                'variable_cost': float(variable_cost),
                'contribution_margin': float(contribution_margin),
                'contribution_margin_ratio': float((contribution_margin / avg_selling_price * 100)) if avg_selling_price > 0 else 0
            },
            'costs': {
                'fixed_costs': float(fixed_costs),
                'variable_cost_per_unit': float(variable_cost)
            },
            'breakeven': {
                'units': float(breakeven_units),
                'revenue': float(breakeven_revenue)
            },
            'actual': {
                'units_sold': current_units_sold,
                'revenue': float(sales_data['total_revenue'] or 0)
            },
            'performance': {
                'status': status,
                'units_above_breakeven': float(units_above_breakeven),
                'safety_margin_percent': float(safety_margin)
            },
            'period_days': period_days
        }
    
    def calculate_cost_center_breakeven(
        self,
        cost_center,
        period_days: int = None
    ) -> Dict:
        """حساب نقطة التعادل لمركز تكلفة"""
        from accounting.models import JournalEntry, JournalEntryLine
        
        period_days = period_days or self.default_period_days
        start_date = timezone.now().date() - timedelta(days=period_days)
        
        # حساب إجمالي التكاليف
        expenses = JournalEntryLine.objects.filter(
            journal__date__gte=start_date,
            journal__is_posted=True,
            cost_center=cost_center,
            account__type='expense'
        ).aggregate(
            total=Sum('debit')
        )['total'] or Decimal('0')
        
        # حساب إجمالي الإيرادات
        revenues = JournalEntryLine.objects.filter(
            journal__date__gte=start_date,
            journal__is_posted=True,
            cost_center=cost_center,
            account__type='revenue'
        ).aggregate(
            total=Sum('credit')
        )['total'] or Decimal('0')
        
        # حساب هامش المساهمة الإجمالي
        contribution_margin = revenues - expenses
        
        # حساب معدل هامش المساهمة
        contribution_margin_ratio = Decimal('0')
        if revenues > 0:
            contribution_margin_ratio = (contribution_margin / revenues) * 100
        
        # حساب نقطة التعادل (بالإيرادات)
        breakeven_revenue = Decimal('0')
        if contribution_margin_ratio > 0:
            breakeven_revenue = (expenses * 100) / contribution_margin_ratio
        
        return {
            'cost_center': {
                'id': cost_center.id,
                'code': cost_center.code,
                'name': cost_center.name
            },
            'financials': {
                'total_revenue': float(revenues),
                'total_expenses': float(expenses),
                'contribution_margin': float(contribution_margin),
                'contribution_margin_ratio': float(contribution_margin_ratio)
            },
            'breakeven': {
                'revenue_required': float(breakeven_revenue)
            },
            'performance': {
                'status': 'profitable' if revenues >= breakeven_revenue else 'below_breakeven',
                'revenue_above_breakeven': float(revenues - breakeven_revenue)
            },
            'period_days': period_days
        }
    
    def calculate_company_breakeven(
        self,
        period_days: int = None
    ) -> Dict:
        """حساب نقطة التعادل للشركة ككل"""
        from accounting.models import Account, JournalEntryLine
        from sales.models import Invoice
        
        period_days = period_days or self.default_period_days
        start_date = timezone.now().date() - timedelta(days=period_days)
        
        # حساب إجمالي الإيرادات
        revenue_accounts = Account.objects.filter(type='revenue')
        total_revenue = JournalEntryLine.objects.filter(
            journal__date__gte=start_date,
            journal__is_posted=True,
            account__in=revenue_accounts
        ).aggregate(
            total=Sum('credit')
        )['total'] or Decimal('0')
        
        # حساب التكاليف المتغيرة (COGS)
        cogs_accounts = Account.objects.filter(
            Q(code__startswith='5.1') | Q(name__icontains='تكلفة المبيعات')
        )
        variable_costs = JournalEntryLine.objects.filter(
            journal__date__gte=start_date,
            journal__is_posted=True,
            account__in=cogs_accounts
        ).aggregate(
            total=Sum('debit')
        )['total'] or Decimal('0')
        
        # حساب التكاليف الثابتة (Operating Expenses)
        fixed_cost_accounts = Account.objects.filter(
            Q(code__startswith='5.2') | Q(code__startswith='5.3') | Q(name__icontains='مصروف')
        ).exclude(id__in=cogs_accounts)
        
        fixed_costs = JournalEntryLine.objects.filter(
            journal__date__gte=start_date,
            journal__is_posted=True,
            account__in=fixed_cost_accounts
        ).aggregate(
            total=Sum('debit')
        )['total'] or Decimal('0')
        
        # حساب هامش المساهمة
        contribution_margin = total_revenue - variable_costs
        
        # حساب معدل هامش المساهمة
        contribution_margin_ratio = Decimal('0')
        if total_revenue > 0:
            contribution_margin_ratio = (contribution_margin / total_revenue) * 100
        
        # حساب نقطة التعادل
        breakeven_revenue = Decimal('0')
        if contribution_margin_ratio > 0:
            breakeven_revenue = (fixed_costs * 100) / contribution_margin_ratio
        
        # حساب الربح الفعلي
        actual_profit = contribution_margin - fixed_costs
        
        # حساب هامش الأمان
        safety_margin = Decimal('0')
        if total_revenue > 0:
            safety_margin = ((total_revenue - breakeven_revenue) / total_revenue) * 100
        
        return {
            'company_wide': True,
            'financials': {
                'total_revenue': float(total_revenue),
                'variable_costs': float(variable_costs),
                'fixed_costs': float(fixed_costs),
                'contribution_margin': float(contribution_margin),
                'contribution_margin_ratio': float(contribution_margin_ratio),
                'actual_profit': float(actual_profit)
            },
            'breakeven': {
                'revenue_required': float(breakeven_revenue)
            },
            'performance': {
                'status': 'profitable' if total_revenue >= breakeven_revenue else 'below_breakeven',
                'revenue_above_breakeven': float(total_revenue - breakeven_revenue),
                'safety_margin_percent': float(safety_margin),
                'profit_margin_percent': float((actual_profit / total_revenue * 100)) if total_revenue > 0 else 0
            },
            'period_days': period_days
        }
    
    def _calculate_variable_cost(self, product) -> Decimal:
        """حساب التكلفة المتغيرة للوحدة"""
        from production.models import BillOfMaterials, BOMItem
        
        # استخدام BOM لحساب تكلفة المواد
        bom = BillOfMaterials.objects.filter(
            product=product,
            is_active=True,
            is_default=True
        ).first()
        
        if bom:
            # حساب تكلفة المواد من BOM
            material_cost = bom.total_material_cost
            labor_cost = bom.total_labor_cost
            
            # التكلفة المتغيرة = مواد + عمالة مباشرة
            return material_cost + labor_cost
        else:
            # استخدام تكلفة المنتج المخزنة
            return product.cost
    
    def _calculate_allocated_fixed_costs(
        self,
        product,
        period_days: int
    ) -> Decimal:
        """حساب التكاليف الثابتة المخصصة للمنتج"""
        from accounting.models import Account, JournalEntryLine
        from sales.models import InvoiceItem
        
        start_date = timezone.now().date() - timedelta(days=period_days)
        
        # حساب نسبة مبيعات هذا المنتج من إجمالي المبيعات
        product_sales = InvoiceItem.objects.filter(
            invoice__invoice_date__gte=start_date,
            product=product
        ).aggregate(
            total=Sum(F('quantity') * F('price'))
        )['total'] or Decimal('0')
        
        total_sales = InvoiceItem.objects.filter(
            invoice__invoice_date__gte=start_date
        ).aggregate(
            total=Sum(F('quantity') * F('price'))
        )['total'] or Decimal('1')  # تجنب القسمة على صفر
        
        allocation_ratio = product_sales / total_sales if total_sales > 0 else Decimal('0')
        
        # حساب إجمالي التكاليف الثابتة
        fixed_cost_accounts = Account.objects.filter(
            Q(code__startswith='5.2') | Q(code__startswith='5.3')
        )
        
        total_fixed_costs = JournalEntryLine.objects.filter(
            journal__date__gte=start_date,
            journal__is_posted=True,
            account__in=fixed_cost_accounts
        ).aggregate(
            total=Sum('debit')
        )['total'] or Decimal('0')
        
        # تخصيص جزء من التكاليف الثابتة لهذا المنتج
        allocated_fixed_costs = total_fixed_costs * allocation_ratio
        
        return allocated_fixed_costs
    
    def multi_product_breakeven(
        self,
        products: List,
        period_days: int = None
    ) -> Dict:
        """تحليل نقطة التعادل لعدة منتجات"""
        results = []
        
        for product in products:
            analysis = self.calculate_product_breakeven(product, period_days)
            results.append(analysis)
        
        # ترتيب حسب الأداء
        results.sort(key=lambda x: x['performance']['units_above_breakeven'], reverse=True)
        
        # حساب الإحصائيات الإجمالية
        total_breakeven_revenue = sum(r['breakeven']['revenue'] for r in results)
        total_actual_revenue = sum(r['actual']['revenue'] for r in results)
        products_profitable = sum(1 for r in results if r['performance']['status'] == 'profitable')
        
        return {
            'products': results,
            'summary': {
                'total_products': len(products),
                'products_profitable': products_profitable,
                'products_below_breakeven': len(products) - products_profitable,
                'total_breakeven_revenue': float(total_breakeven_revenue),
                'total_actual_revenue': float(total_actual_revenue),
                'overall_performance': 'profitable' if total_actual_revenue >= total_breakeven_revenue else 'below_breakeven'
            }
        }


# Singleton instance
breakeven_analyzer = BreakEvenAnalyzer()
