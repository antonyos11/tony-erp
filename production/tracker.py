"""
نظام تتبع الإنتاج المرئي
Visual Production Tracking System
"""

from django.db.models import Count, Sum, Avg, F, Q
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal


class ProductionTracker:
    """متتبع الإنتاج"""
    
    STATUS_COLORS = {
        'pending': '#6c757d',      # رمادي
        'in_progress': '#007bff',  # أزرق
        'completed': '#28a745',    # أخضر
        'delayed': '#dc3545',      # أحمر
        'on_hold': '#ffc107',      # أصفر
    }
    
    @classmethod
    def get_production_status(cls, production_order):
        """الحصول على حالة أمر الإنتاج"""
        from production.models import ProductionOrder
        
        now = timezone.now()
        
        # حساب النسبة المئوية للإنجاز
        progress = cls.calculate_progress(production_order)
        
        # تحديد الحالة
        if production_order.status == 'completed':
            status = 'completed'
            color = cls.STATUS_COLORS['completed']
        elif production_order.expected_completion_date and production_order.expected_completion_date < now.date():
            status = 'delayed'
            color = cls.STATUS_COLORS['delayed']
        elif production_order.status == 'on_hold':
            status = 'on_hold'
            color = cls.STATUS_COLORS['on_hold']
        elif production_order.status == 'in_progress':
            status = 'in_progress'
            color = cls.STATUS_COLORS['in_progress']
        else:
            status = 'pending'
            color = cls.STATUS_COLORS['pending']
        
        return {
            'status': status,
            'color': color,
            'progress': progress,
            'status_label': production_order.get_status_display()
        }
    
    @classmethod
    def calculate_progress(cls, production_order):
        """حساب نسبة الإنجاز"""
        if production_order.status == 'completed':
            return 100
        
        if production_order.status == 'pending':
            return 0
        
        # حساب بناءً على الكمية المنتجة
        if production_order.quantity_produced and production_order.target_quantity:
            progress = (production_order.quantity_produced / production_order.target_quantity) * 100
            return min(100, progress)
        
        # حساب بناءً على الوقت المنقضي
        if production_order.start_date and production_order.expected_completion_date:
            total_days = (production_order.expected_completion_date - production_order.start_date).days
            elapsed_days = (timezone.now().date() - production_order.start_date).days
            
            if total_days > 0:
                time_progress = (elapsed_days / total_days) * 100
                return min(100, max(0, time_progress))
        
        return 0
    
    @classmethod
    def get_timeline_data(cls, production_order):
        """بيانات الخط الزمني"""
        timeline = []
        
        # البداية
        if production_order.created_at:
            timeline.append({
                'date': production_order.created_at,
                'title': 'إنشاء الأمر',
                'status': 'completed',
                'icon': 'file-text'
            })
        
        # الموافقة
        if production_order.approved_at:
            timeline.append({
                'date': production_order.approved_at,
                'title': 'الموافقة على الأمر',
                'status': 'completed',
                'icon': 'check-circle'
            })
        
        # البدء
        if production_order.start_date:
            timeline.append({
                'date': production_order.start_date,
                'title': 'بدء الإنتاج',
                'status': 'completed' if production_order.status != 'pending' else 'pending',
                'icon': 'play'
            })
        
        # نقاط التفتيش (milestones)
        for milestone in production_order.milestones.all():
            timeline.append({
                'date': milestone.date,
                'title': milestone.title,
                'status': 'completed' if milestone.is_completed else 'pending',
                'icon': 'flag'
            })
        
        # الإنجاز المتوقع
        if production_order.expected_completion_date:
            timeline.append({
                'date': production_order.expected_completion_date,
                'title': 'الإنجاز المتوقع',
                'status': 'pending' if production_order.status != 'completed' else 'completed',
                'icon': 'calendar'
            })
        
        # الإنجاز الفعلي
        if production_order.actual_completion_date:
            timeline.append({
                'date': production_order.actual_completion_date,
                'title': 'الإنجاز الفعلي',
                'status': 'completed',
                'icon': 'check-square'
            })
        
        return sorted(timeline, key=lambda x: x['date'])
    
    @classmethod
    def get_delay_warning(cls, production_order):
        """تحذير التأخير"""
        if production_order.status == 'completed':
            return None
        
        now = timezone.now().date()
        expected_date = production_order.expected_completion_date
        
        if not expected_date:
            return None
        
        days_remaining = (expected_date - now).days
        
        if days_remaining < 0:
            return {
                'type': 'danger',
                'message': f'متأخر بـ {abs(days_remaining)} يوم',
                'days': abs(days_remaining),
                'is_delayed': True
            }
        elif days_remaining <= 2:
            return {
                'type': 'warning',
                'message': f'الموعد خلال {days_remaining} يوم',
                'days': days_remaining,
                'is_at_risk': True
            }
        elif days_remaining <= 7:
            return {
                'type': 'info',
                'message': f'متبقي {days_remaining} يوم',
                'days': days_remaining,
                'is_on_track': True
            }
        
        return None
    
    @classmethod
    def get_production_chart_data(cls, start_date=None, end_date=None):
        """بيانات الرسم البياني للإنتاج"""
        from production.models import ProductionOrder
        
        if not start_date:
            start_date = timezone.now().date() - timedelta(days=30)
        if not end_date:
            end_date = timezone.now().date()
        
        orders = ProductionOrder.objects.filter(
            created_at__date__range=[start_date, end_date]
        )
        
        # الإنتاج حسب اليوم
        daily_production = orders.values('created_at__date').annotate(
            count=Count('id'),
            total_quantity=Sum('target_quantity'),
            completed_quantity=Sum('quantity_produced')
        ).order_by('created_at__date')
        
        # الإنتاج حسب الحالة
        by_status = orders.values('status').annotate(
            count=Count('id')
        )
        
        # الإنتاج حسب المنتج
        by_product = orders.values('product__name').annotate(
            count=Count('id'),
            total_quantity=Sum('target_quantity')
        ).order_by('-total_quantity')[:10]
        
        return {
            'daily': list(daily_production),
            'by_status': list(by_status),
            'by_product': list(by_product)
        }
    
    @classmethod
    def get_efficiency_metrics(cls, production_order):
        """مقاييس الكفاءة"""
        metrics = {}
        
        # معدل الإنجاز
        if production_order.start_date and production_order.status == 'in_progress':
            days_elapsed = (timezone.now().date() - production_order.start_date).days
            if days_elapsed > 0 and production_order.quantity_produced:
                metrics['daily_rate'] = production_order.quantity_produced / days_elapsed
            else:
                metrics['daily_rate'] = 0
        
        # الكفاءة (المنتج الفعلي / المستهدف)
        if production_order.target_quantity and production_order.target_quantity > 0:
            metrics['efficiency'] = (production_order.quantity_produced / production_order.target_quantity) * 100
        else:
            metrics['efficiency'] = 0
        
        # الفاقد
        if hasattr(production_order, 'defective_quantity'):
            if production_order.quantity_produced > 0:
                metrics['defect_rate'] = (production_order.defective_quantity / production_order.quantity_produced) * 100
            else:
                metrics['defect_rate'] = 0
        
        # تقدير وقت الإنجاز
        if production_order.status == 'in_progress' and metrics.get('daily_rate', 0) > 0:
            remaining = production_order.target_quantity - production_order.quantity_produced
            days_needed = remaining / metrics['daily_rate']
            estimated_completion = timezone.now().date() + timedelta(days=days_needed)
            metrics['estimated_completion'] = estimated_completion
        
        return metrics


class ProductionAnalytics:
    """تحليلات الإنتاج"""
    
    @classmethod
    def get_dashboard_data(cls, branch=None, date_range=None):
        """بيانات لوحة معلومات الإنتاج"""
        from production.models import ProductionOrder
        
        if not date_range:
            date_range = {
                'start': timezone.now().date() - timedelta(days=30),
                'end': timezone.now().date()
            }
        
        orders = ProductionOrder.objects.filter(
            created_at__date__range=[date_range['start'], date_range['end']]
        )
        
        if branch:
            orders = orders.filter(branch=branch)
        
        # الإحصائيات الأساسية
        stats = {
            'total_orders': orders.count(),
            'completed': orders.filter(status='completed').count(),
            'in_progress': orders.filter(status='in_progress').count(),
            'delayed': orders.filter(
                expected_completion_date__lt=timezone.now().date(),
                status__in=['pending', 'in_progress']
            ).count(),
            'total_quantity': orders.aggregate(total=Sum('target_quantity'))['total'] or 0,
            'produced_quantity': orders.aggregate(total=Sum('quantity_produced'))['total'] or 0,
        }
        
        # نسبة الإنجاز
        if stats['total_quantity'] > 0:
            stats['completion_rate'] = (stats['produced_quantity'] / stats['total_quantity']) * 100
        else:
            stats['completion_rate'] = 0
        
        # متوسط وقت الإنجاز
        completed_orders = orders.filter(
            status='completed',
            actual_completion_date__isnull=False,
            start_date__isnull=False
        )
        
        if completed_orders.exists():
            total_days = sum([
                (order.actual_completion_date - order.start_date).days 
                for order in completed_orders
            ])
            stats['avg_completion_days'] = total_days / completed_orders.count()
        else:
            stats['avg_completion_days'] = 0
        
        return stats
    
    @classmethod
    def get_performance_trends(cls, days=30):
        """اتجاهات الأداء"""
        from production.models import ProductionOrder
        from django.db.models.functions import TruncDate
        
        start_date = timezone.now().date() - timedelta(days=days)
        
        daily_stats = ProductionOrder.objects.filter(
            created_at__date__gte=start_date
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            orders=Count('id'),
            quantity=Sum('quantity_produced')
        ).order_by('date')
        
        return list(daily_stats)
    
    @classmethod
    def get_bottlenecks(cls):
        """تحديد الاختناقات في الإنتاج"""
        from production.models import ProductionOrder
        
        # الطلبات المتأخرة
        delayed = ProductionOrder.objects.filter(
            expected_completion_date__lt=timezone.now().date(),
            status__in=['pending', 'in_progress']
        ).select_related('product')
        
        # الطلبات المعلقة لفترة طويلة
        long_pending = ProductionOrder.objects.filter(
            status='pending',
            created_at__lt=timezone.now() - timedelta(days=7)
        ).select_related('product')
        
        # المنتجات ذات معدل الإنجاز المنخفض
        low_completion = ProductionOrder.objects.filter(
            status='in_progress'
        ).annotate(
            completion_rate=F('quantity_produced') / F('target_quantity')
        ).filter(
            completion_rate__lt=0.5,
            start_date__lt=timezone.now().date() - timedelta(days=3)
        ).select_related('product')
        
        return {
            'delayed_orders': list(delayed),
            'long_pending': list(long_pending),
            'low_completion': list(low_completion)
        }
    
    @classmethod
    def generate_production_report(cls, start_date, end_date, branch=None):
        """إنشاء تقرير إنتاج شامل"""
        from production.models import ProductionOrder
        
        orders = ProductionOrder.objects.filter(
            created_at__date__range=[start_date, end_date]
        )
        
        if branch:
            orders = orders.filter(branch=branch)
        
        report = {
            'period': {
                'start': start_date,
                'end': end_date,
                'days': (end_date - start_date).days + 1
            },
            'summary': cls.get_dashboard_data(branch, {'start': start_date, 'end': end_date}),
            'trends': cls.get_performance_trends((end_date - start_date).days),
            'bottlenecks': cls.get_bottlenecks(),
            'top_products': orders.values('product__name').annotate(
                total_quantity=Sum('quantity_produced')
            ).order_by('-total_quantity')[:10],
            'completion_by_product': orders.filter(
                status='completed'
            ).values('product__name').annotate(
                count=Count('id'),
                avg_days=Avg(F('actual_completion_date') - F('start_date'))
            ).order_by('-count')[:10]
        }
        
        return report
