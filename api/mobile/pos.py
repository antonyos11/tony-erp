"""
Mobile POS API
API نقطة البيع للموبايل

نظام POS محمول كامل مع عمليات أوفلاين
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from typing import List, Dict


class MobilePOSViewSet(viewsets.ViewSet):
    """نقطة بيع محمولة"""
    
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def products(self, request) -> Response:
        """
        قائمة المنتجات للبيع
        
        GET /api/mobile/pos/products/?branch=1&category=2&search=...
        """
        from inventory.models import Product, Stock
        
        # فلترة
        products = Product.objects.filter(is_active=True, is_sellable=True)
        
        branch_id = request.query_params.get('branch')
        if branch_id:
            products = products.filter(stock__branch_id=branch_id)
        
        category_id = request.query_params.get('category')
        if category_id:
            products = products.filter(category_id=category_id)
        
        search = request.query_params.get('search')
        if search:
            products = products.filter(
                Q(name__icontains=search) |
                Q(barcode__icontains=search) |
                Q(sku__icontains=search)
            )
        
        # جلب بيانات المخزون
        products_data = []
        for product in products[:100]:  # حد أقصى 100
            try:
                stock = Stock.objects.get(
                    product=product,
                    branch_id=branch_id if branch_id else None
                )
                available_qty = stock.quantity
            except Stock.DoesNotExist:
                available_qty = 0
            
            products_data.append({
                'id': product.id,
                'name': product.name,
                'sku': product.sku,
                'barcode': product.barcode,
                'price': float(product.price),
                'cost': float(product.cost),
                'available_qty': available_qty,
                'image': product.image.url if product.image else None,
                'category': product.category.name if product.category else None
            })
        
        return Response({
            'success': True,
            'products': products_data
        })
    
    @action(detail=False, methods=['post'])
    @transaction.atomic
    def create_sale(self, request) -> Response:
        """
        إنشاء فاتورة بيع
        
        POST /api/mobile/pos/create_sale/
        {
            "customer_id": 1,
            "branch_id": 1,
            "items": [
                {"product_id": 1, "quantity": 2, "price": 100},
                {"product_id": 2, "quantity": 1, "price": 50}
            ],
            "payment_method": "cash",
            "discount": 10,
            "notes": "..."
        }
        """
        from sales.models import Invoice, InvoiceItem, Customer
        from inventory.models import Product, Stock
        from branches.models import Branch
        
        try:
            # التحقق من البيانات
            items_data = request.data.get('items', [])
            if not items_data:
                return Response({
                    'success': False,
                    'error': 'يجب إضافة منتج واحد على الأقل'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # العميل
            customer_id = request.data.get('customer_id')
            customer = Customer.objects.get(id=customer_id) if customer_id else None
            
            # الفرع
            branch_id = request.data.get('branch_id')
            branch = Branch.objects.get(id=branch_id) if branch_id else None
            
            # إنشاء الفاتورة
            invoice = Invoice.objects.create(
                customer=customer,
                branch=branch,
                invoice_date=timezone.now().date(),
                due_date=timezone.now().date(),
                created_by=request.user,
                payment_method=request.data.get('payment_method', 'cash'),
                discount=Decimal(request.data.get('discount', 0)),
                notes=request.data.get('notes', ''),
                status='paid'
            )
            
            # إضافة البنود
            subtotal = Decimal('0')
            for item_data in items_data:
                product = Product.objects.get(id=item_data['product_id'])
                quantity = Decimal(item_data['quantity'])
                price = Decimal(item_data.get('price', product.price))
                
                # التحقق من المخزون
                stock = Stock.objects.get(product=product, branch=branch)
                if stock.quantity < quantity:
                    raise ValueError(f'المنتج {product.name} غير متوفر بالكمية المطلوبة')
                
                # إنشاء البند
                item_total = quantity * price
                InvoiceItem.objects.create(
                    invoice=invoice,
                    product=product,
                    quantity=quantity,
                    unit_price=price,
                    total=item_total
                )
                
                # تحديث المخزون
                stock.quantity -= quantity
                stock.save()
                
                subtotal += item_total
            
            # حساب الإجمالي
            invoice.subtotal = subtotal
            invoice.total_amount = subtotal - invoice.discount
            invoice.save()
            
            return Response({
                'success': True,
                'invoice': {
                    'id': invoice.id,
                    'number': invoice.invoice_number,
                    'total': float(invoice.total_amount),
                    'date': invoice.invoice_date.isoformat()
                }
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def check_stock(self, request) -> Response:
        """
        فحص توفر المنتجات
        
        POST /api/mobile/pos/check_stock/
        {
            "branch_id": 1,
            "items": [
                {"product_id": 1, "quantity": 2},
                {"product_id": 2, "quantity": 1}
            ]
        }
        """
        from inventory.models import Product, Stock
        
        branch_id = request.data.get('branch_id')
        items = request.data.get('items', [])
        
        results = []
        all_available = True
        
        for item in items:
            product = Product.objects.get(id=item['product_id'])
            requested_qty = Decimal(item['quantity'])
            
            try:
                stock = Stock.objects.get(product=product, branch_id=branch_id)
                available_qty = stock.quantity
                is_available = available_qty >= requested_qty
            except Stock.DoesNotExist:
                available_qty = 0
                is_available = False
            
            if not is_available:
                all_available = False
            
            results.append({
                'product_id': product.id,
                'product_name': product.name,
                'requested': float(requested_qty),
                'available': float(available_qty),
                'is_available': is_available
            })
        
        return Response({
            'success': True,
            'all_available': all_available,
            'items': results
        })
    
    @action(detail=False, methods=['get'])
    def recent_sales(self, request) -> Response:
        """
        المبيعات الأخيرة
        
        GET /api/mobile/pos/recent_sales/?limit=10
        """
        from sales.models import Invoice
        
        limit = int(request.query_params.get('limit', 10))
        
        invoices = Invoice.objects.filter(
            created_by=request.user
        ).order_by('-created_at')[:limit]
        
        data = []
        for invoice in invoices:
            data.append({
                'id': invoice.id,
                'number': invoice.invoice_number,
                'customer': invoice.customer.name if invoice.customer else 'زبون نقدي',
                'total': float(invoice.total_amount),
                'date': invoice.invoice_date.isoformat(),
                'status': invoice.status
            })
        
        return Response({
            'success': True,
            'invoices': data
        })
