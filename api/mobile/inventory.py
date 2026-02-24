"""
Mobile Inventory API
API المخزون للموبايل

عمليات الجرد وإدارة المخزون عبر الموبايل
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.utils import timezone
from decimal import Decimal


class MobileInventoryViewSet(viewsets.ViewSet):
    """إدارة المخزون عبر الموبايل"""
    
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def stock_levels(self, request) -> Response:
        """
        مستويات المخزون
        
        GET /api/mobile/inventory/stock_levels/?branch=1&search=...
        """
        from inventory.models import Stock
        from django.db.models import F
        
        stocks = Stock.objects.select_related('product', 'branch')
        
        # تصفية
        branch_id = request.query_params.get('branch')
        if branch_id:
            stocks = stocks.filter(branch_id=branch_id)
        
        search = request.query_params.get('search')
        if search:
            stocks = stocks.filter(
                Q(product__name__icontains=search) |
                Q(product__sku__icontains=search)
            )
        
        # حالة المخزون
        stock_status = request.query_params.get('status')
        if stock_status == 'low':
            stocks = stocks.filter(quantity__lt=F('product__min_stock'), quantity__gt=0)
        elif stock_status == 'out':
            stocks = stocks.filter(quantity=0)
        
        data = []
        for stock in stocks[:100]:
            data.append({
                'product_id': stock.product.id,
                'product_name': stock.product.name,
                'sku': stock.product.sku,
                'quantity': float(stock.quantity),
                'min_stock': float(stock.product.min_stock),
                'branch': stock.branch.name if stock.branch else 'المستودع الرئيسي',
                'status': self._get_stock_status(stock)
            })
        
        return Response({
            'success': True,
            'stocks': data
        })
    
    @action(detail=False, methods=['post'])
    @transaction.atomic
    def adjust_stock(self, request) -> Response:
        """
        تعديل المخزون
        
        POST /api/mobile/inventory/adjust_stock/
        {
            "product_id": 1,
            "branch_id": 1,
            "quantity_change": 10,
            "reason": "جرد مخزون",
            "notes": "..."
        }
        """
        from inventory.models import Stock, StockMovement
        from inventory.models import Product
        from branches.models import Branch
        
        try:
            product = Product.objects.get(id=request.data['product_id'])
            branch_id = request.data.get('branch_id')
            branch = Branch.objects.get(id=branch_id) if branch_id else None
            
            quantity_change = Decimal(request.data['quantity_change'])
            reason = request.data.get('reason', 'تعديل يدوي')
            notes = request.data.get('notes', '')
            
            # الحصول على أو إنشاء المخزون
            stock, created = Stock.objects.get_or_create(
                product=product,
                branch=branch,
                defaults={'quantity': Decimal('0')}
            )
            
            old_quantity = stock.quantity
            stock.quantity += quantity_change
            
            if stock.quantity < 0:
                return Response({
                    'success': False,
                    'error': 'لا يمكن أن تكون الكمية سالبة'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            stock.save()
            
            # تسجيل الحركة
            StockMovement.objects.create(
                product=product,
                branch=branch,
                movement_type='adjustment',
                quantity=abs(quantity_change),
                direction='in' if quantity_change > 0 else 'out',
                reference=reason,
                notes=notes,
                created_by=request.user
            )
            
            return Response({
                'success': True,
                'stock': {
                    'product': product.name,
                    'old_quantity': float(old_quantity),
                    'new_quantity': float(stock.quantity),
                    'change': float(quantity_change)
                }
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    @transaction.atomic
    def physical_count(self, request) -> Response:
        """
        جرد مادي
        
        POST /api/mobile/inventory/physical_count/
        {
            "branch_id": 1,
            "counts": [
                {"product_id": 1, "counted_quantity": 50},
                {"product_id": 2, "counted_quantity": 30}
            ],
            "notes": "جرد نصف سنوي"
        }
        """
        from inventory.models import Stock, StockMovement, PhysicalCount
        from inventory.models import Product
        from branches.models import Branch
        
        try:
            branch_id = request.data.get('branch_id')
            branch = Branch.objects.get(id=branch_id) if branch_id else None
            counts = request.data.get('counts', [])
            notes = request.data.get('notes', '')
            
            # إنشاء سجل الجرد
            physical_count = PhysicalCount.objects.create(
                branch=branch,
                count_date=timezone.now(),
                counted_by=request.user,
                notes=notes,
                status='draft'
            )
            
            differences = []
            
            for count_data in counts:
                product = Product.objects.get(id=count_data['product_id'])
                counted_qty = Decimal(count_data['counted_quantity'])
                
                # الحصول على المخزون الحالي
                stock, _ = Stock.objects.get_or_create(
                    product=product,
                    branch=branch,
                    defaults={'quantity': Decimal('0')}
                )
                
                system_qty = stock.quantity
                difference = counted_qty - system_qty
                
                if difference != 0:
                    # تحديث المخزون
                    stock.quantity = counted_qty
                    stock.save()
                    
                    # تسجيل الحركة
                    StockMovement.objects.create(
                        product=product,
                        branch=branch,
                        movement_type='count_adjustment',
                        quantity=abs(difference),
                        direction='in' if difference > 0 else 'out',
                        reference=f'جرد رقم {physical_count.id}',
                        notes=f'فرق الجرد: {difference}',
                        created_by=request.user
                    )
                    
                    differences.append({
                        'product': product.name,
                        'system_qty': float(system_qty),
                        'counted_qty': float(counted_qty),
                        'difference': float(difference)
                    })
            
            physical_count.status = 'completed'
            physical_count.save()
            
            return Response({
                'success': True,
                'count_id': physical_count.id,
                'differences': differences,
                'total_items': len(counts),
                'items_with_differences': len(differences)
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def barcode_scan(self, request) -> Response:
        """
        مسح الباركود
        
        POST /api/mobile/inventory/barcode_scan/
        {
            "barcode": "1234567890"
        }
        """
        from inventory.models import Product, Stock
        
        barcode = request.data.get('barcode')
        
        try:
            product = Product.objects.get(barcode=barcode)
            
            # الحصول على المخزون
            branch_id = request.query_params.get('branch')
            if branch_id:
                stock = Stock.objects.filter(
                    product=product,
                    branch_id=branch_id
                ).first()
            else:
                stock = Stock.objects.filter(product=product).first()
            
            return Response({
                'success': True,
                'product': {
                    'id': product.id,
                    'name': product.name,
                    'sku': product.sku,
                    'barcode': product.barcode,
                    'price': float(product.price),
                    'cost': float(product.cost),
                    'quantity': float(stock.quantity) if stock else 0,
                    'image': product.image.url if product.image else None
                }
            })
            
        except Product.DoesNotExist:
            return Response({
                'success': False,
                'error': 'المنتج غير موجود'
            }, status=status.HTTP_404_NOT_FOUND)
    
    def _get_stock_status(self, stock) -> str:
        """تحديد حالة المخزون"""
        if stock.quantity == 0:
            return 'out_of_stock'
        elif stock.quantity < stock.product.min_stock:
            return 'low_stock'
        else:
            return 'in_stock'
