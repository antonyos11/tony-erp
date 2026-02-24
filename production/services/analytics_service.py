"""
خدمة التحليلات الذكية للإنتاج
Production Analytics & AI Service

يوفر هذا الملف تحليلات متقدمة للإنتاج تشمل:
- توقع الطلب
- تحسين الإنتاج
- اكتشاف الأنماط
- التنبؤ بالمشاكل
"""

from django.db.models import Sum, Avg, Count, F, Q, ExpressionWrapper, DecimalField, DurationField
from django.db.models.functions import TruncMonth, TruncWeek, TruncDate, Extract
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Tuple, Optional, Any
from collections import defaultdict
import statistics

from production.models import (
    ProductionOrder, ProductionOrderStage, ProductionWorkCenter,
    WorkerProductionEntry, MaterialConsumption
)


class ProductionAnalyticsService:
    """
    خدمة التحليلات المتقدمة للإنتاج
    
    تقدم:
    - تحليل الإنتاجية
    - توقع الطلب
    - تحسين الموارد
    - KPIs ذكية
    """
    
    @staticmethod
    def get_production_kpis(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        الحصول على مؤشرات الأداء الرئيسية للإنتاج
        
        Returns:
            dict: مؤشرات شاملة للإنتاج
        """
        if not start_date:
            start_date = timezone.now() - timedelta(days=30)
        if not end_date:
            end_date = timezone.now()
        
        orders = ProductionOrder.objects.filter(
            created_at__range=[start_date, end_date]
        )
        
        completed_orders = orders.filter(status='completed')
        
        # حساب المؤشرات
        total_orders = orders.count()
        completed_count = completed_orders.count()
        
        # OEE (Overall Equipment Effectiveness)
        oee = ProductionAnalyticsService._calculate_oee(start_date, end_date)
        
        # إنتاجية العمال
        worker_productivity = ProductionAnalyticsService._calculate_worker_productivity(
            start_date, end_date
        )
        
        # كفاءة المواد
        material_efficiency = ProductionAnalyticsService._calculate_material_efficiency(
            start_date, end_date
        )
        
        # متوسط وقت الإنتاج
        avg_production_time = ProductionAnalyticsService._calculate_avg_production_time(
            completed_orders
        )
        
        # انحراف التكلفة
        cost_variance = ProductionAnalyticsService._calculate_cost_variance(
            completed_orders
        )
        
        # نسبة الجودة
        quality_rate = ProductionAnalyticsService._calculate_quality_rate(
            completed_orders
        )
        
        return {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
            },
            'orders': {
                'total': total_orders,
                'completed': completed_count,
                'in_progress': orders.filter(status='in_progress').count(),
                'pending': orders.filter(status__in=['draft', 'confirmed']).count(),
                'completion_rate': (completed_count / total_orders * 100) if total_orders > 0 else 0,
            },
            'oee': oee,
            'worker_productivity': worker_productivity,
            'material_efficiency': material_efficiency,
            'avg_production_time_hours': avg_production_time,
            'cost_variance': cost_variance,
            'quality_rate': quality_rate,
            'trends': ProductionAnalyticsService._get_production_trends(start_date, end_date),
        }
    
    @staticmethod
    def _calculate_oee(start_date: datetime, end_date: datetime) -> Dict[str, float]:
        """
        حساب كفاءة المعدات الشاملة (OEE)
        OEE = Availability × Performance × Quality
        """
        work_centers = ProductionWorkCenter.objects.filter(is_active=True)
        
        total_availability = Decimal('0')
        total_performance = Decimal('0')
        total_quality = Decimal('0')
        center_count = 0
        
        for wc in work_centers:
            # حساب الإتاحة (Availability)
            # الوقت الفعلي / الوقت المخطط
            planned_hours = (end_date - start_date).total_seconds() / 3600 * float(wc.working_hours_per_day) / 24
            
            # استخدام ProductionOrderStage بدلاً من TimeLog
            stage_qs = ProductionOrderStage.objects.filter(
                stage__work_center=wc,
                actual_start_date__range=[start_date, end_date],
                actual_end_date__isnull=False
            )
            # حساب الساعات الفعلية من تواريخ البداية والنهاية
            actual_hours = Decimal('0')
            for s in stage_qs:
                if s.actual_start_date and s.actual_end_date:
                    duration = (s.actual_end_date - s.actual_start_date).total_seconds() / 3600
                    actual_hours += Decimal(str(duration))
            
            availability = min(Decimal('100'), (actual_hours / Decimal(str(planned_hours)) * 100)) if planned_hours > 0 else Decimal('0')
            
            # حساب الأداء (Performance)
            # الوحدات الفعلية / الوحدات النظرية
            stages = ProductionOrderStage.objects.filter(
                stage__work_center=wc,
                actual_start_date__range=[start_date, end_date]
            )
            
            theoretical_output = stages.aggregate(
                total=Sum(F('production_order__planned_quantity'))
            )['total'] or Decimal('0')
            
            actual_output = stages.aggregate(
                total=Sum(F('completed_quantity'))
            )['total'] or Decimal('0')
            
            performance = min(Decimal('100'), (actual_output / theoretical_output * 100)) if theoretical_output > 0 else Decimal('0')
            
            # حساب الجودة
            scrap = stages.aggregate(
                total=Sum(F('scrap_quantity'))
            )['total'] or Decimal('0')
            
            good_output = actual_output - scrap
            quality = (good_output / actual_output * 100) if actual_output > 0 else Decimal('100')
            
            total_availability += availability
            total_performance += performance
            total_quality += quality
            center_count += 1
        
        if center_count == 0:
            return {'availability': 0, 'performance': 0, 'quality': 0, 'oee': 0}
        
        avg_availability = float(total_availability / center_count)
        avg_performance = float(total_performance / center_count)
        avg_quality = float(total_quality / center_count)
        oee = (avg_availability * avg_performance * avg_quality) / 10000
        
        return {
            'availability': round(avg_availability, 2),
            'performance': round(avg_performance, 2),
            'quality': round(avg_quality, 2),
            'oee': round(oee, 2),
        }
    
    @staticmethod
    def _calculate_worker_productivity(
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        حساب إنتاجية العمال
        """
        entries = WorkerProductionEntry.objects.filter(
            date__range=[start_date.date(), end_date.date()],
            status='approved'
        )
        
        worker_stats = entries.values('employee').annotate(
            total_quantity=Sum('quantity'),
            total_entries=Count('id'),
            avg_quantity=Avg('quantity'),
        ).order_by('-total_quantity')
        
        total_workers = worker_stats.count()
        total_produced = entries.aggregate(Sum('quantity'))['quantity__sum'] or 0
        
        # أفضل 5 عمال
        top_workers = list(worker_stats[:5])
        
        # متوسط الإنتاجية
        if total_workers > 0:
            avg_per_worker = total_produced / total_workers
        else:
            avg_per_worker = 0
        
        return {
            'total_workers': total_workers,
            'total_produced': float(total_produced),
            'avg_per_worker': round(float(avg_per_worker), 2),
            'top_workers': top_workers,
        }
    
    @staticmethod
    def _calculate_material_efficiency(
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        حساب كفاءة استخدام المواد
        """
        consumptions = MaterialConsumption.objects.filter(
            created_at__range=[start_date, end_date]
        )
        
        total_planned = consumptions.aggregate(Sum('planned_quantity'))['planned_quantity__sum'] or Decimal('0')
        total_actual = consumptions.aggregate(Sum('consumed_quantity'))['consumed_quantity__sum'] or Decimal('0')
        total_wasted = consumptions.aggregate(Sum('wastage_quantity'))['wastage_quantity__sum'] or Decimal('0')
        
        efficiency = ((total_planned - total_wasted) / total_planned * 100) if total_planned > 0 else Decimal('100')
        waste_rate = (total_wasted / total_actual * 100) if total_actual > 0 else Decimal('0')
        
        return {
            'planned_quantity': float(total_planned),
            'actual_quantity': float(total_actual),
            'wasted_quantity': float(total_wasted),
            'efficiency_percentage': round(float(efficiency), 2),
            'waste_rate': round(float(waste_rate), 2),
        }
    
    @staticmethod
    def _calculate_avg_production_time(orders) -> float:
        """
        حساب متوسط وقت الإنتاج
        """
        times = []
        for order in orders.filter(
            actual_start_date__isnull=False,
            actual_end_date__isnull=False
        ):
            duration = (order.actual_end_date - order.actual_start_date).total_seconds() / 3600
            times.append(duration)
        
        return round(statistics.mean(times), 2) if times else 0
    
    @staticmethod
    def _calculate_cost_variance(orders) -> Dict[str, Any]:
        """
        حساب انحراف التكلفة
        """
        total_estimated = orders.aggregate(
            materials=Sum('estimated_material_cost'),
            labor=Sum('estimated_labor_cost'),
            overhead=Sum('estimated_overhead_cost'),
        )
        
        total_actual = orders.aggregate(
            materials=Sum('actual_material_cost'),
            labor=Sum('actual_labor_cost'),
            overhead=Sum('actual_overhead_cost'),
        )
        
        estimated_total = sum(v or 0 for v in total_estimated.values())
        actual_total = sum(v or 0 for v in total_actual.values())
        
        variance = actual_total - estimated_total
        variance_percentage = (variance / estimated_total * 100) if estimated_total > 0 else 0
        
        return {
            'estimated_total': float(estimated_total),
            'actual_total': float(actual_total),
            'variance': float(variance),
            'variance_percentage': round(float(variance_percentage), 2),
            'status': 'favorable' if variance < 0 else ('unfavorable' if variance > 0 else 'on_target'),
        }
    
    @staticmethod
    def _calculate_quality_rate(orders) -> Dict[str, Any]:
        """
        حساب نسبة الجودة
        """
        total_produced = orders.aggregate(Sum('produced_quantity'))['produced_quantity__sum'] or Decimal('0')
        total_scrap = orders.aggregate(Sum('scrap_quantity'))['scrap_quantity__sum'] or Decimal('0')
        
        good_quantity = total_produced - total_scrap
        quality_rate = (good_quantity / total_produced * 100) if total_produced > 0 else Decimal('100')
        
        return {
            'total_produced': float(total_produced),
            'good_quantity': float(good_quantity),
            'scrap_quantity': float(total_scrap),
            'quality_rate': round(float(quality_rate), 2),
        }
    
    @staticmethod
    def _get_production_trends(
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, List]:
        """
        الحصول على اتجاهات الإنتاج
        """
        orders = ProductionOrder.objects.filter(
            created_at__range=[start_date, end_date]
        )
        
        # اتجاه أسبوعي
        weekly_trend = orders.annotate(
            week=TruncWeek('created_at')
        ).values('week').annotate(
            count=Count('id'),
            total_quantity=Sum('planned_quantity'),
            completed=Count('id', filter=Q(status='completed')),
        ).order_by('week')
        
        # اتجاه حسب المنتج
        product_trend = orders.values(
            'product__name'
        ).annotate(
            count=Count('id'),
            total_quantity=Sum('planned_quantity'),
        ).order_by('-total_quantity')[:10]
        
        return {
            'weekly': list(weekly_trend),
            'by_product': list(product_trend),
        }
    
    @staticmethod
    def predict_demand(
        product_id: int,
        periods: int = 4,
        period_type: str = 'week'
    ) -> Dict[str, Any]:
        """
        توقع الطلب باستخدام Moving Average
        
        Args:
            product_id: معرف المنتج
            periods: عدد الفترات للتوقع
            period_type: نوع الفترة (week, month)
        
        Returns:
            dict: التوقعات مع فترات الثقة
        """
        from inventory.models import Product
        
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return {'error': 'المنتج غير موجود'}
        
        # جمع البيانات التاريخية
        if period_type == 'week':
            lookback = timedelta(weeks=12)
            trunc_func = TruncWeek
        else:
            lookback = timedelta(days=365)
            trunc_func = TruncMonth
        
        historical_data = ProductionOrder.objects.filter(
            product_id=product_id,
            status='completed',
            created_at__gte=timezone.now() - lookback
        ).annotate(
            period=trunc_func('created_at')
        ).values('period').annotate(
            quantity=Sum('produced_quantity')
        ).order_by('period')
        
        quantities = [float(d['quantity']) for d in historical_data]
        
        if len(quantities) < 3:
            return {
                'error': 'بيانات تاريخية غير كافية',
                'min_required': 3,
                'available': len(quantities),
            }
        
        # حساب Moving Average
        window = min(4, len(quantities))
        ma = statistics.mean(quantities[-window:])
        
        # حساب الانحراف المعياري
        std_dev = statistics.stdev(quantities) if len(quantities) > 1 else 0
        
        # توقعات الفترات القادمة
        predictions = []
        for i in range(periods):
            prediction = {
                'period': i + 1,
                'predicted_quantity': round(ma, 2),
                'lower_bound': round(max(0, ma - 1.96 * std_dev), 2),
                'upper_bound': round(ma + 1.96 * std_dev, 2),
                'confidence': 0.95,
            }
            predictions.append(prediction)
        
        return {
            'product': {
                'id': product.id,
                'name': product.name,
            },
            'historical_periods': len(quantities),
            'moving_average': round(ma, 2),
            'standard_deviation': round(std_dev, 2),
            'predictions': predictions,
        }
    
    @staticmethod
    def identify_bottlenecks(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        تحديد الاختناقات في الإنتاج
        """
        if not start_date:
            start_date = timezone.now() - timedelta(days=30)
        if not end_date:
            end_date = timezone.now()
        
        work_centers = ProductionWorkCenter.objects.filter(is_active=True)
        
        bottlenecks = []
        
        for wc in work_centers:
            # حساب الاستغلال
            stages = ProductionOrderStage.objects.filter(
                stage__work_center=wc,
                actual_start_date__range=[start_date, end_date]
            )
            
            # حساب الساعات الفعلية من تواريخ البداية والنهاية
            total_hours = Decimal('0')
            for s in stages.filter(actual_end_date__isnull=False):
                if s.actual_start_date and s.actual_end_date:
                    duration = (s.actual_end_date - s.actual_start_date).total_seconds() / 3600
                    total_hours += Decimal(str(duration))
            
            # السعة المتاحة
            days = (end_date - start_date).days
            available_hours = days * float(wc.working_hours_per_day)
            
            utilization = (float(total_hours) / available_hours * 100) if available_hours > 0 else 0
            
            # حساب متوسط وقت الانتظار
            wait_times = []
            ordered_stages = stages.order_by('actual_start_date')
            
            prev_end = None
            for stage in ordered_stages:
                if prev_end and stage.actual_start_date:
                    wait = (stage.actual_start_date - prev_end).total_seconds() / 3600
                    if wait > 0:
                        wait_times.append(wait)
                if stage.actual_end_date:
                    prev_end = stage.actual_end_date
            
            avg_wait = statistics.mean(wait_times) if wait_times else 0
            
            # تصنيف الاختناق
            if utilization >= 90 or avg_wait > 4:
                severity = 'critical'
            elif utilization >= 75 or avg_wait > 2:
                severity = 'warning'
            else:
                severity = 'normal'
            
            if severity != 'normal':
                bottlenecks.append({
                    'work_center': {
                        'id': wc.id,
                        'name': wc.name,
                        'code': wc.code,
                    },
                    'utilization': round(utilization, 2),
                    'avg_wait_hours': round(avg_wait, 2),
                    'severity': severity,
                    'recommendation': ProductionAnalyticsService._get_bottleneck_recommendation(
                        utilization, avg_wait
                    ),
                })
        
        return sorted(bottlenecks, key=lambda x: x['utilization'], reverse=True)
    
    @staticmethod
    def _get_bottleneck_recommendation(utilization: float, avg_wait: float) -> str:
        """
        الحصول على توصية لحل الاختناق
        """
        if utilization >= 95:
            return 'يُنصح بشدة بإضافة مركز عمل موازٍ أو زيادة ساعات العمل'
        elif utilization >= 85:
            return 'يُنصح بتوزيع الحمل على مراكز عمل أخرى أو جدولة العمل الإضافي'
        elif avg_wait > 4:
            return 'يُنصح بتحسين تدفق العمل وتقليل أوقات الإعداد'
        else:
            return 'مراقبة الوضع وتحسين الصيانة الوقائية'
    
    @staticmethod
    def get_optimization_suggestions(
        order_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        الحصول على اقتراحات لتحسين الإنتاج
        """
        suggestions = []
        
        if order_id:
            try:
                order = ProductionOrder.objects.get(id=order_id)
                suggestions.extend(
                    ProductionAnalyticsService._get_order_suggestions(order)
                )
            except ProductionOrder.DoesNotExist:
                return [{'error': 'أمر الإنتاج غير موجود'}]
        else:
            # اقتراحات عامة
            suggestions.extend(
                ProductionAnalyticsService._get_general_suggestions()
            )
        
        return suggestions
    
    @staticmethod
    def _get_order_suggestions(order: ProductionOrder) -> List[Dict[str, Any]]:
        """
        اقتراحات لأمر إنتاج محدد
        """
        suggestions = []
        
        # تحليل انحراف التكلفة
        if order.actual_total_cost > 0:
            variance_pct = (order.cost_variance / order.estimated_total_cost * 100) if order.estimated_total_cost > 0 else 0
            
            if variance_pct > 10:
                suggestions.append({
                    'type': 'cost',
                    'priority': 'high',
                    'title': 'انحراف تكلفة كبير',
                    'description': f'انحراف التكلفة {variance_pct:.1f}% فوق المخطط',
                    'action': 'مراجعة أسعار المواد وساعات العمل الفعلية',
                })
        
        # تحليل نسبة التالف
        if order.produced_quantity > 0:
            scrap_rate = (order.scrap_quantity / order.produced_quantity * 100)
            if scrap_rate > 5:
                suggestions.append({
                    'type': 'quality',
                    'priority': 'high',
                    'title': 'نسبة تالف مرتفعة',
                    'description': f'نسبة التالف {scrap_rate:.1f}%',
                    'action': 'فحص جودة المواد الخام ومراجعة إجراءات العمل',
                })
        
        # تحليل التأخير
        if order.actual_end_date and order.planned_end_date:
            delay_days = (order.actual_end_date - order.planned_end_date).days
            if delay_days > 0:
                suggestions.append({
                    'type': 'schedule',
                    'priority': 'medium',
                    'title': 'تأخير في التسليم',
                    'description': f'تأخير {delay_days} يوم عن الموعد المخطط',
                    'action': 'مراجعة تقديرات الوقت وتحسين الجدولة',
                })
        
        return suggestions
    
    @staticmethod
    def _get_general_suggestions() -> List[Dict[str, Any]]:
        """
        اقتراحات عامة للإنتاج
        """
        suggestions = []
        
        # فحص المخزون المنخفض
        from inventory.models import Product, Stock
        from django.db.models import Subquery, OuterRef
        low_stock = Product.objects.filter(
            product_type='raw',
        ).annotate(
            total_stock=Sum('stocks__quantity')
        ).filter(
            total_stock__lt=F('min_stock')
        ).count()
        
        if low_stock > 0:
            suggestions.append({
                'type': 'inventory',
                'priority': 'high',
                'title': 'مواد خام منخفضة المخزون',
                'description': f'{low_stock} مادة تحتاج إعادة طلب',
                'action': 'إنشاء أوامر شراء عاجلة',
            })
        
        # أوامر متأخرة
        overdue_orders = ProductionOrder.objects.filter(
            status__in=['confirmed', 'in_progress'],
            planned_end_date__lt=timezone.now().date()
        ).count()
        
        if overdue_orders > 0:
            suggestions.append({
                'type': 'schedule',
                'priority': 'high',
                'title': 'أوامر إنتاج متأخرة',
                'description': f'{overdue_orders} أمر متأخر عن الموعد',
                'action': 'مراجعة الأولويات وتخصيص موارد إضافية',
            })
        
        # صيانة المعدات
        from maintenance.models import MaintenanceSchedule
        pending_maintenance = MaintenanceSchedule.objects.filter(
            next_due_date__lte=timezone.now().date(),
            is_active=True
        ).count()
        
        if pending_maintenance > 0:
            suggestions.append({
                'type': 'maintenance',
                'priority': 'medium',
                'title': 'صيانة مستحقة',
                'description': f'{pending_maintenance} جدول صيانة بحاجة تنفيذ',
                'action': 'جدولة أعمال الصيانة الوقائية',
            })
        
        return suggestions
