"""
نظام تحسين نقاط البيع (POS)
POS Optimization System
"""

from django.db import transaction
from django.core.cache import cache
from django.db.models import F, Sum
from decimal import Decimal
import json


class POSOptimizer:
    """محسّن نقاط البيع"""
    
    CACHE_TIMEOUT = 3600  # ساعة واحدة
    
    @classmethod
    def get_frequently_sold_products(cls, limit=20):
        """الحصول على المنتجات الأكثر مبيعاً (مع التخزين المؤقت)"""
        cache_key = f'pos_top_products_{limit}'
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data
        
        from sales.models import InvoiceItem
        from inventory.models import Product
        
        # المنتجات الأكثر مبيعاً في آخر 30 يوم
        top_products = InvoiceItem.objects.filter(
            invoice__invoice_date__gte=timezone.now() - timedelta(days=30),
            invoice__status='approved'
        ).values('product').annotate(
            total_quantity=Sum('quantity'),
            total_sales=Sum('total_price')
        ).order_by('-total_quantity')[:limit]
        
        product_ids = [item['product'] for item in top_products]
        products = Product.objects.filter(id__in=product_ids).select_related('category')
        
        result = []
        for product in products:
            sales_data = next((item for item in top_products if item['product'] == product.id), None)
            result.append({
                'id': product.id,
                'name': product.name,
                'category': product.category.name if product.category else '',
                'price': float(product.price),
                'stock': product.stock_quantity,
                'total_sold': sales_data['total_quantity'] if sales_data else 0,
                'barcode': product.barcode
            })
        
        cache.set(cache_key, result, cls.CACHE_TIMEOUT)
        return result
    
    @classmethod
    def quick_search_products(cls, query, limit=10):
        """بحث سريع عن المنتجات"""
        from inventory.models import Product
        from django.db.models import Q
        
        # البحث بالاسم أو الباركود
        products = Product.objects.filter(
            Q(name__icontains=query) | Q(barcode__icontains=query),
            is_active=True,
            stock_quantity__gt=0
        ).select_related('category')[:limit]
        
        return [{
            'id': p.id,
            'name': p.name,
            'barcode': p.barcode,
            'price': float(p.price),
            'stock': p.stock_quantity,
            'category': p.category.name if p.category else ''
        } for p in products]
    
    @classmethod
    @transaction.atomic
    def create_fast_invoice(cls, customer_id, items, payment_method='cash', user=None):
        """إنشاء فاتورة سريعة (محسّنة للسرعة)"""
        from sales.models import Invoice, InvoiceItem
        from inventory.models import Product
        
        # التحقق من المخزون مرة واحدة
        product_ids = [item['product_id'] for item in items]
        products = Product.objects.filter(id__in=product_ids).select_for_update()
        
        products_dict = {p.id: p for p in products}
        
        # التحقق من توفر المخزون
        for item in items:
            product = products_dict.get(item['product_id'])
            if not product:
                raise ValueError(f"المنتج {item['product_id']} غير موجود")
            
            if product.stock_quantity < item['quantity']:
                raise ValueError(f"المخزون غير كافٍ للمنتج {product.name}")
        
        # إنشاء الفاتورة
        invoice = Invoice.objects.create(
            customer_id=customer_id,
            invoice_date=timezone.now(),
            payment_method=payment_method,
            status='approved',  # موافقة تلقائية للفواتير النقدية
            created_by=user
        )
        
        total_amount = Decimal('0')
        
        # إنشاء بنود الفاتورة وتحديث المخزون
        for item in items:
            product = products_dict[item['product_id']]
            quantity = item['quantity']
            unit_price = item.get('unit_price', product.price)
            discount = item.get('discount', 0)
            
            item_total = (unit_price * quantity) - discount
            total_amount += item_total
            
            # إنشاء بند الفاتورة
            InvoiceItem.objects.create(
                invoice=invoice,
                product=product,
                quantity=quantity,
                unit_price=unit_price,
                discount=discount,
                total_price=item_total
            )
            
            # تحديث المخزون
            product.stock_quantity = F('stock_quantity') - quantity
            product.save(update_fields=['stock_quantity'])
        
        # تحديث إجمالي الفاتورة
        invoice.total_amount = total_amount
        invoice.save(update_fields=['total_amount'])
        
        # إنشاء حركة مخزون
        cls._create_stock_movements(invoice, items, products_dict)
        
        # إلغاء الكاش
        cache.delete('pos_top_products_20')
        
        return invoice
    
    @classmethod
    def _create_stock_movements(cls, invoice, items, products_dict):
        """إنشاء حركات المخزون"""
        from inventory.models import StockMovement
        
        movements = []
        for item in items:
            product = products_dict[item['product_id']]
            movements.append(StockMovement(
                product=product,
                movement_type='out',
                quantity=item['quantity'],
                unit_cost=product.cost_price,
                reference_type='invoice',
                reference_id=invoice.id,
                notes=f'بيع - فاتورة {invoice.invoice_number}'
            ))
        
        StockMovement.objects.bulk_create(movements)
    
    @classmethod
    def get_customer_quick_info(cls, customer_id):
        """معلومات سريعة عن العميل"""
        from sales.models import Customer, Invoice
        
        cache_key = f'pos_customer_{customer_id}'
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data
        
        customer = Customer.objects.get(id=customer_id)
        
        # آخر 5 فواتير
        recent_invoices = Invoice.objects.filter(
            customer=customer,
            status='approved'
        ).order_by('-invoice_date')[:5]
        
        # إحصائيات
        stats = Invoice.objects.filter(
            customer=customer,
            status='approved'
        ).aggregate(
            total_purchases=Sum('total_amount'),
            invoice_count=Count('id'),
            avg_invoice=Avg('total_amount')
        )
        
        info = {
            'id': customer.id,
            'name': customer.name,
            'phone': customer.phone,
            'email': customer.email,
            'total_purchases': float(stats['total_purchases'] or 0),
            'invoice_count': stats['invoice_count'],
            'avg_invoice': float(stats['avg_invoice'] or 0),
            'recent_invoices': [{
                'number': inv.invoice_number,
                'date': inv.invoice_date.isoformat(),
                'amount': float(inv.total_amount)
            } for inv in recent_invoices]
        }
        
        cache.set(cache_key, info, 300)  # 5 دقائق
        return info


class POSKeyboardHandler:
    """معالج اختصارات لوحة المفاتيح لنقاط البيع"""
    
    SHORTCUTS = {
        'F5': 'new_invoice',
        'F6': 'add_product',
        'F7': 'search_customer',
        'F8': 'apply_discount',
        'F9': 'cash_payment',
        'F10': 'card_payment',
        'F11': 'print_invoice',
        'F12': 'save_draft',
        'ESC': 'cancel',
        'ENTER': 'confirm',
        'TAB': 'next_field',
        'SHIFT+TAB': 'prev_field',
        'CTRL+F': 'search_product',
        'CTRL+D': 'delete_item',
        'CTRL+S': 'save',
        'CTRL+P': 'print',
    }
    
    @classmethod
    def get_shortcuts_config(cls):
        """الحصول على إعدادات الاختصارات"""
        return cls.SHORTCUTS
    
    @classmethod
    def get_shortcuts_help(cls):
        """الحصول على مساعدة الاختصارات"""
        help_text = {
            'general': [
                {'key': 'F5', 'action': 'فاتورة جديدة'},
                {'key': 'F6', 'action': 'إضافة منتج'},
                {'key': 'F7', 'action': 'بحث عن عميل'},
                {'key': 'Ctrl+S', 'action': 'حفظ'},
                {'key': 'Esc', 'action': 'إلغاء'},
            ],
            'payment': [
                {'key': 'F9', 'action': 'دفع نقدي'},
                {'key': 'F10', 'action': 'دفع ببطاقة'},
                {'key': 'F8', 'action': 'تطبيق خصم'},
            ],
            'items': [
                {'key': 'Ctrl+F', 'action': 'بحث عن منتج'},
                {'key': 'Ctrl+D', 'action': 'حذف بند'},
                {'key': 'Tab', 'action': 'الحقل التالي'},
            ]
        }
        return help_text


from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Avg


class POSAnalytics:
    """تحليلات نقاط البيع"""
    
    @classmethod
    def get_hourly_sales(cls, date=None):
        """مبيعات حسب الساعة"""
        from sales.models import Invoice
        from django.db.models.functions import TruncHour
        
        if not date:
            date = timezone.now().date()
        
        sales = Invoice.objects.filter(
            invoice_date__date=date,
            status='approved'
        ).annotate(
            hour=TruncHour('invoice_date')
        ).values('hour').annotate(
            count=Count('id'),
            total=Sum('total_amount')
        ).order_by('hour')
        
        return list(sales)
    
    @classmethod
    def get_peak_hours(cls, days=7):
        """ساعات الذروة"""
        from sales.models import Invoice
        from django.db.models.functions import ExtractHour
        
        start_date = timezone.now() - timedelta(days=days)
        
        peak_hours = Invoice.objects.filter(
            invoice_date__gte=start_date,
            status='approved'
        ).annotate(
            hour=ExtractHour('invoice_date')
        ).values('hour').annotate(
            count=Count('id'),
            avg_amount=Avg('total_amount')
        ).order_by('-count')[:3]
        
        return list(peak_hours)
    
    @classmethod
    def get_cashier_performance(cls, date=None):
        """أداء الكاشير"""
        from sales.models import Invoice
        
        if not date:
            date = timezone.now().date()
        
        performance = Invoice.objects.filter(
            invoice_date__date=date,
            status='approved'
        ).values('created_by__username').annotate(
            invoice_count=Count('id'),
            total_sales=Sum('total_amount'),
            avg_invoice=Avg('total_amount')
        ).order_by('-total_sales')
        
        return list(performance)
