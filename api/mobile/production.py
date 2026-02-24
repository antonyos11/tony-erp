"""
Mobile Production API
API الإنتاج للموبايل

متابعة أوامر الإنتاج وتسجيل التقدم من الورشة
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.utils import timezone
from decimal import Decimal


class MobileProductionViewSet(viewsets.ViewSet):
    """إدارة الإنتاج عبر الموبايل"""
    
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def active_orders(self, request) -> Response:
        """
        أوامر الإنتاج النشطة
        
        GET /api/mobile/production/active_orders/?work_center=1
        """
        from production.models import ProductionOrder
        
        orders = ProductionOrder.objects.filter(
            status__in=['confirmed', 'in_progress']
        ).select_related('product', 'work_center')
        
        # تصفية حسب مركز العمل
        work_center_id = request.query_params.get('work_center')
        if work_center_id:
            orders = orders.filter(work_center_id=work_center_id)
        
        data = []
        for order in orders.order_by('scheduled_start_date'):
            data.append({
                'id': order.id,
                'order_number': order.order_number,
                'product': order.product.name,
                'quantity_planned': float(order.quantity),
                'quantity_produced': float(order.quantity_produced),
                'progress': float((order.quantity_produced / order.quantity) * 100) if order.quantity > 0 else 0,
                'work_center': order.work_center.name if order.work_center else None,
                'scheduled_start': order.scheduled_start_date.isoformat() if order.scheduled_start_date else None,
                'scheduled_end': order.scheduled_end_date.isoformat() if order.scheduled_end_date else None,
                'status': order.status
            })
        
        return Response({
            'success': True,
            'orders': data
        })
    
    @action(detail=False, methods=['get'])
    def order_details(self, request) -> Response:
        """
        تفاصيل أمر إنتاج
        
        GET /api/mobile/production/order_details/?order_id=1
        """
        from production.models import ProductionOrder, BillOfMaterials
        
        order_id = request.query_params.get('order_id')
        
        try:
            order = ProductionOrder.objects.get(id=order_id)
            
            # قائمة المواد
            bom = BillOfMaterials.objects.filter(product=order.product).first()
            materials = []
            
            if bom:
                for item in bom.items.all():
                    materials.append({
                        'material': item.material.name,
                        'quantity_needed': float(item.quantity * order.quantity),
                        'unit': item.material.unit
                    })
            
            return Response({
                'success': True,
                'order': {
                    'id': order.id,
                    'order_number': order.order_number,
                    'product': order.product.name,
                    'quantity_planned': float(order.quantity),
                    'quantity_produced': float(order.quantity_produced),
                    'work_center': order.work_center.name if order.work_center else None,
                    'scheduled_start': order.scheduled_start_date.isoformat() if order.scheduled_start_date else None,
                    'scheduled_end': order.scheduled_end_date.isoformat() if order.scheduled_end_date else None,
                    'actual_start': order.actual_start_date.isoformat() if order.actual_start_date else None,
                    'actual_end': order.actual_end_date.isoformat() if order.actual_end_date else None,
                    'status': order.status,
                    'materials': materials
                }
            })
            
        except ProductionOrder.DoesNotExist:
            return Response({
                'success': False,
                'error': 'أمر الإنتاج غير موجود'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['post'])
    @transaction.atomic
    def start_production(self, request) -> Response:
        """
        بدء الإنتاج
        
        POST /api/mobile/production/start_production/
        {
            "order_id": 1,
            "notes": "..."
        }
        """
        from production.models import ProductionOrder
        
        try:
            order = ProductionOrder.objects.get(id=request.data['order_id'])
            
            if order.status != 'confirmed':
                return Response({
                    'success': False,
                    'error': 'حالة الأمر لا تسمح بالبدء'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            order.status = 'in_progress'
            order.actual_start_date = timezone.now()
            order.save()
            
            return Response({
                'success': True,
                'message': 'تم بدء الإنتاج',
                'order': {
                    'id': order.id,
                    'status': order.status,
                    'actual_start': order.actual_start_date.isoformat()
                }
            })
            
        except ProductionOrder.DoesNotExist:
            return Response({
                'success': False,
                'error': 'أمر الإنتاج غير موجود'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['post'])
    @transaction.atomic
    def record_progress(self, request) -> Response:
        """
        تسجيل التقدم
        
        POST /api/mobile/production/record_progress/
        {
            "order_id": 1,
            "quantity_produced": 10,
            "notes": "...",
            "defects": 2
        }
        """
        from production.models import ProductionOrder, ProductionLog
        
        try:
            order = ProductionOrder.objects.get(id=request.data['order_id'])
            quantity_produced = Decimal(request.data['quantity_produced'])
            defects = Decimal(request.data.get('defects', 0))
            notes = request.data.get('notes', '')
            
            if order.status != 'in_progress':
                return Response({
                    'success': False,
                    'error': 'الأمر ليس قيد التنفيذ'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # تحديث الكمية المنتجة
            order.quantity_produced += quantity_produced
            
            # التحقق من اكتمال الإنتاج
            if order.quantity_produced >= order.quantity:
                order.status = 'completed'
                order.actual_end_date = timezone.now()
            
            order.save()
            
            # تسجيل Log
            ProductionLog.objects.create(
                production_order=order,
                log_type='progress',
                quantity=quantity_produced,
                defects=defects,
                notes=notes,
                created_by=request.user
            )
            
            progress = float((order.quantity_produced / order.quantity) * 100) if order.quantity > 0 else 0
            
            return Response({
                'success': True,
                'message': 'تم تسجيل التقدم',
                'order': {
                    'id': order.id,
                    'quantity_produced': float(order.quantity_produced),
                    'quantity_planned': float(order.quantity),
                    'progress': progress,
                    'status': order.status
                }
            })
            
        except ProductionOrder.DoesNotExist:
            return Response({
                'success': False,
                'error': 'أمر الإنتاج غير موجود'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    @transaction.atomic
    def report_issue(self, request) -> Response:
        """
        الإبلاغ عن مشكلة
        
        POST /api/mobile/production/report_issue/
        {
            "order_id": 1,
            "issue_type": "machine_breakdown",
            "description": "...",
            "severity": "high"
        }
        """
        from production.models import ProductionOrder, ProductionIssue
        
        try:
            order = ProductionOrder.objects.get(id=request.data['order_id'])
            
            issue = ProductionIssue.objects.create(
                production_order=order,
                issue_type=request.data.get('issue_type', 'other'),
                description=request.data.get('description', ''),
                severity=request.data.get('severity', 'medium'),
                reported_by=request.user,
                status='open'
            )
            
            return Response({
                'success': True,
                'message': 'تم تسجيل المشكلة',
                'issue': {
                    'id': issue.id,
                    'type': issue.issue_type,
                    'severity': issue.severity,
                    'status': issue.status
                }
            })
            
        except ProductionOrder.DoesNotExist:
            return Response({
                'success': False,
                'error': 'أمر الإنتاج غير موجود'
            }, status=status.HTTP_404_NOT_FOUND)
