"""
نظام التصفية المتقدمة للمدير
Advanced Filtering System for Branch Manager
"""

from django.db.models import Q, Sum, Count, Avg, F
from datetime import datetime, timedelta
from decimal import Decimal


class AdvancedFilterSystem:
    """نظام التصفية المتقدمة"""
    
    def __init__(self, user, model_class):
        self.user = user
        self.model_class = model_class
        self.filters = Q()
    
    def add_date_range_filter(self, start_date=None, end_date=None, field_name='created_at'):
        """تصفية حسب النطاق الزمني"""
        if start_date:
            self.filters &= Q(**{f'{field_name}__gte': start_date})
        if end_date:
            self.filters &= Q(**{f'{field_name}__lte': end_date})
        return self
    
    def add_amount_range_filter(self, min_amount=None, max_amount=None, field_name='total_amount'):
        """تصفية حسب نطاق المبلغ"""
        if min_amount is not None:
            self.filters &= Q(**{f'{field_name}__gte': min_amount})
        if max_amount is not None:
            self.filters &= Q(**{f'{field_name}__lte': max_amount})
        return self
    
    def add_status_filter(self, statuses, field_name='status'):
        """تصفية حسب الحالة"""
        if statuses:
            if isinstance(statuses, list):
                self.filters &= Q(**{f'{field_name}__in': statuses})
            else:
                self.filters &= Q(**{f'{field_name}': statuses})
        return self
    
    def add_customer_filter(self, customer_ids, field_name='customer'):
        """تصفية حسب العميل"""
        if customer_ids:
            if isinstance(customer_ids, list):
                self.filters &= Q(**{f'{field_name}__in': customer_ids})
            else:
                self.filters &= Q(**{f'{field_name}': customer_ids})
        return self
    
    def add_supplier_filter(self, supplier_ids, field_name='supplier'):
        """تصفية حسب المورد"""
        if supplier_ids:
            if isinstance(supplier_ids, list):
                self.filters &= Q(**{f'{field_name}__in': supplier_ids})
            else:
                self.filters &= Q(**{f'{field_name}': supplier_ids})
        return self
    
    def add_branch_filter(self, branch_ids, field_name='branch'):
        """تصفية حسب الفرع"""
        if branch_ids:
            if isinstance(branch_ids, list):
                self.filters &= Q(**{f'{field_name}__in': branch_ids})
            else:
                self.filters &= Q(**{f'{field_name}': branch_ids})
        return self
    
    def add_payment_status_filter(self, payment_statuses, field_name='payment_status'):
        """تصفية حسب حالة الدفع"""
        if payment_statuses:
            if isinstance(payment_statuses, list):
                self.filters &= Q(**{f'{field_name}__in': payment_statuses})
            else:
                self.filters &= Q(**{f'{field_name}': payment_statuses})
        return self
    
    def add_user_filter(self, user_ids, field_name='created_by'):
        """تصفية حسب المستخدم"""
        if user_ids:
            if isinstance(user_ids, list):
                self.filters &= Q(**{f'{field_name}__in': user_ids})
            else:
                self.filters &= Q(**{f'{field_name}': user_ids})
        return self
    
    def add_search_filter(self, search_term, search_fields):
        """بحث في حقول متعددة"""
        if search_term:
            search_query = Q()
            for field in search_fields:
                search_query |= Q(**{f'{field}__icontains': search_term})
            self.filters &= search_query
        return self
    
    def apply(self, queryset=None):
        """تطبيق التصفية"""
        if queryset is None:
            queryset = self.model_class.objects.all()
        return queryset.filter(self.filters)
    
    def get_summary(self, queryset=None):
        """الحصول على ملخص البيانات المصفاة"""
        if queryset is None:
            queryset = self.apply()
        
        summary = {
            'count': queryset.count(),
            'total_amount': queryset.aggregate(total=Sum('total_amount'))['total'] or 0,
            'avg_amount': queryset.aggregate(avg=Avg('total_amount'))['avg'] or 0,
        }
        
        # إضافة تفاصيل حسب الحالة
        if hasattr(self.model_class, 'status'):
            status_summary = queryset.values('status').annotate(
                count=Count('id'),
                total=Sum('total_amount')
            )
            summary['by_status'] = list(status_summary)
        
        # إضافة تفاصيل حسب حالة الدفع
        if hasattr(self.model_class, 'payment_status'):
            payment_summary = queryset.values('payment_status').annotate(
                count=Count('id'),
                total=Sum('total_amount')
            )
            summary['by_payment_status'] = list(payment_summary)
        
        return summary


class DailySummaryGenerator:
    """مولد الملخص اليومي للمدير"""
    
    def __init__(self, user, branch=None, date=None):
        self.user = user
        self.branch = branch
        self.date = date or datetime.now().date()
    
    def generate_summary(self):
        """إنشاء ملخص يومي شامل"""
        from sales.models import Invoice
        from purchasing.models import PurchaseOrder
        from inventory.models import StockMovement
        from accounting.models import JournalEntry
        
        summary = {
            'date': self.date,
            'branch': self.branch.name if self.branch else 'جميع الفروع',
            'sales': self._get_sales_summary(Invoice),
            'purchases': self._get_purchases_summary(PurchaseOrder),
            'inventory': self._get_inventory_summary(StockMovement),
            'accounting': self._get_accounting_summary(JournalEntry),
            'alerts': self._get_alerts()
        }
        
        return summary
    
    def _get_sales_summary(self, Invoice):
        """ملخص المبيعات"""
        filter_system = AdvancedFilterSystem(self.user, Invoice)
        filter_system.add_date_range_filter(
            start_date=self.date,
            end_date=self.date + timedelta(days=1),
            field_name='invoice_date'
        )
        
        if self.branch:
            filter_system.add_branch_filter(self.branch.id)
        
        queryset = filter_system.apply()
        summary = filter_system.get_summary(queryset)
        
        # إضافة تفاصيل إضافية
        summary['top_customers'] = queryset.values('customer__name').annotate(
            total=Sum('total_amount')
        ).order_by('-total')[:5]
        
        summary['top_products'] = queryset.values('items__product__name').annotate(
            quantity=Sum('items__quantity'),
            total=Sum('items__total_price')
        ).order_by('-total')[:5]
        
        return summary
    
    def _get_purchases_summary(self, PurchaseOrder):
        """ملخص المشتريات"""
        filter_system = AdvancedFilterSystem(self.user, PurchaseOrder)
        filter_system.add_date_range_filter(
            start_date=self.date,
            end_date=self.date + timedelta(days=1),
            field_name='order_date'
        )
        
        if self.branch:
            filter_system.add_branch_filter(self.branch.id)
        
        queryset = filter_system.apply()
        summary = filter_system.get_summary(queryset)
        
        # إضافة الموردين الرئيسيين
        summary['top_suppliers'] = queryset.values('supplier__name').annotate(
            total=Sum('total_amount')
        ).order_by('-total')[:5]
        
        return summary
    
    def _get_inventory_summary(self, StockMovement):
        """ملخص حركة المخزون"""
        movements = StockMovement.objects.filter(
            created_at__date=self.date
        )
        
        if self.branch:
            movements = movements.filter(branch=self.branch)
        
        in_movements = movements.filter(movement_type='in').aggregate(
            count=Count('id'),
            quantity=Sum('quantity')
        )
        
        out_movements = movements.filter(movement_type='out').aggregate(
            count=Count('id'),
            quantity=Sum('quantity')
        )
        
        return {
            'in': in_movements,
            'out': out_movements,
            'net_change': (in_movements['quantity'] or 0) - (out_movements['quantity'] or 0)
        }
    
    def _get_accounting_summary(self, JournalEntry):
        """ملخص المحاسبة"""
        entries = JournalEntry.objects.filter(
            entry_date=self.date,
            status='approved'
        )
        
        if self.branch:
            entries = entries.filter(branch=self.branch)
        
        debits = entries.aggregate(total=Sum('items__debit_amount'))['total'] or 0
        credits = entries.aggregate(total=Sum('items__credit_amount'))['total'] or 0
        
        return {
            'count': entries.count(),
            'total_debits': float(debits),
            'total_credits': float(credits),
            'balance': float(debits - credits)
        }
    
    def _get_alerts(self):
        """التنبيهات المهمة"""
        from inventory.models import Product
        from sales.models import Invoice
        from purchasing.models import PurchaseOrder
        
        alerts = []
        
        # منتجات نافذة أو قليلة
        low_stock = Product.objects.filter(
            Q(stock_quantity=0) | Q(stock_quantity__lte=F('min_stock_level'))
        ).count()
        
        if low_stock > 0:
            alerts.append({
                'type': 'warning',
                'category': 'inventory',
                'message': f'{low_stock} منتج نافذ أو قليل المخزون',
                'count': low_stock
            })
        
        # فواتير معلقة
        pending_invoices = Invoice.objects.filter(
            status='pending'
        ).count()
        
        if pending_invoices > 0:
            alerts.append({
                'type': 'info',
                'category': 'sales',
                'message': f'{pending_invoices} فاتورة معلقة تحتاج موافقة',
                'count': pending_invoices
            })
        
        # طلبات شراء متأخرة
        delayed_orders = PurchaseOrder.objects.filter(
            expected_delivery_date__lt=self.date,
            status__in=['pending', 'approved']
        ).count()
        
        if delayed_orders > 0:
            alerts.append({
                'type': 'danger',
                'category': 'purchasing',
                'message': f'{delayed_orders} طلب شراء متأخر',
                'count': delayed_orders
            })
        
        return alerts
    
    def generate_html_report(self):
        """إنشاء تقرير HTML للملخص اليومي"""
        summary = self.generate_summary()
        
        html = f"""
        <html dir="rtl">
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; direction: rtl; }}
                .header {{ background: #007bff; color: white; padding: 20px; }}
                .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; }}
                .alert {{ padding: 10px; margin: 10px 0; border-radius: 5px; }}
                .alert-warning {{ background: #fff3cd; border: 1px solid #ffc107; }}
                .alert-danger {{ background: #f8d7da; border: 1px solid #dc3545; }}
                .alert-info {{ background: #d1ecf1; border: 1px solid #17a2b8; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: right; }}
                th {{ background: #f8f9fa; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>الملخص اليومي - {summary['date']}</h1>
                <h3>{summary['branch']}</h3>
            </div>
            
            <div class="section">
                <h2>المبيعات</h2>
                <p>عدد الفواتير: {summary['sales']['count']}</p>
                <p>إجمالي المبيعات: {summary['sales']['total_amount']:,.2f} ج.م</p>
                <p>متوسط الفاتورة: {summary['sales']['avg_amount']:,.2f} ج.م</p>
                
                <h3>أفضل العملاء</h3>
                <table>
                    <tr><th>العميل</th><th>المبلغ</th></tr>
                    {''.join([f"<tr><td>{c['customer__name']}</td><td>{c['total']:,.2f}</td></tr>" for c in summary['sales']['top_customers']])}
                </table>
            </div>
            
            <div class="section">
                <h2>المشتريات</h2>
                <p>عدد الطلبات: {summary['purchases']['count']}</p>
                <p>إجمالي المشتريات: {summary['purchases']['total_amount']:,.2f} ج.م</p>
            </div>
            
            <div class="section">
                <h2>التنبيهات</h2>
                {''.join([f"<div class='alert alert-{alert['type']}'>{alert['message']}</div>" for alert in summary['alerts']])}
            </div>
        </body>
        </html>
        """
        
        return html
