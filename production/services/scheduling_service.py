"""
خدمة الجدولة التلقائية للإنتاج
Production Auto-Scheduling Service

يوفر هذا الملف خوارزميات متقدمة لجدولة أوامر الإنتاج تلقائياً بناءً على:
- السعة المتاحة لمراكز العمل
- الأولويات
- التبعيات بين المراحل
- تحسين استخدام الموارد
"""

from django.db import transaction
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Tuple, Optional, Any
import heapq
from collections import defaultdict

from production.models import (
    ProductionOrder, ProductionOrderStage, ProductionWorkCenter,
    ProductionStage, BillOfMaterials, BOMItem
)


class ProductionScheduler:
    """
    محرك الجدولة التلقائية للإنتاج
    
    يستخدم خوارزميات متقدمة لتحسين جدولة الإنتاج:
    - Priority Scheduling: جدولة بناءً على الأولويات
    - Capacity-Based Scheduling: مراعاة سعة مراكز العمل
    - Constraint Programming: حل قيود التبعيات
    - Critical Path Method (CPM): تحديد المسار الحرج
    """
    
    def __init__(self):
        self.work_centers_cache = {}
        self.schedules = []
    
    def schedule_production_orders(
        self,
        orders: List[ProductionOrder],
        start_date: Optional[datetime] = None,
        optimization_goal: str = 'minimize_time'  # minimize_time, balance_load, minimize_cost
    ) -> Dict[str, Any]:
        """
        جدولة مجموعة من أوامر الإنتاج
        
        Args:
            orders: قائمة أوامر الإنتاج المراد جدولتها
            start_date: تاريخ البدء (افتراضياً الآن)
            optimization_goal: هدف التحسين
        
        Returns:
            dict: نتائج الجدولة مع التواريخ المقترحة والتحذيرات
        """
        if not start_date:
            start_date = timezone.now()
        
        # ترتيب الأوامر حسب الأولوية
        sorted_orders = self._sort_orders_by_priority(orders)
        
        # تحميل سعات مراكز العمل
        self._load_work_center_capacities()
        
        # جدولة كل أمر
        results = {
            'scheduled_orders': [],
            'conflicts': [],
            'warnings': [],
            'statistics': {}
        }
        
        current_date = start_date
        
        for order in sorted_orders:
            try:
                schedule_result = self._schedule_single_order(
                    order, current_date, optimization_goal
                )
                results['scheduled_orders'].append(schedule_result)
                
                # تحديث التاريخ الحالي بناءً على هدف التحسين
                if optimization_goal == 'minimize_time':
                    current_date = schedule_result['estimated_end_date']
                
            except Exception as e:
                results['warnings'].append({
                    'order': order.number,
                    'message': f'فشل جدولة الأمر: {str(e)}'
                })
        
        # حساب الإحصائيات
        results['statistics'] = self._calculate_scheduling_statistics(results)
        
        return results
    
    def _schedule_single_order(
        self,
        order: ProductionOrder,
        start_date: datetime,
        optimization_goal: str
    ) -> Dict[str, Any]:
        """
        جدولة أمر إنتاج واحد
        
        Returns:
            dict: معلومات الجدولة (التواريخ، مراكز العمل، المدة)
        """
        # الحصول على قائمة المواد (BOM)
        bom = order.bom
        stages_qs = getattr(bom, 'production_stages', None)
        stages = list(stages_qs.all().order_by('sequence')) if stages_qs is not None else []

        if not stages and hasattr(bom, 'stages'):
            stages = [bs.stage for bs in bom.stages.all().order_by('sequence')]

        if not stages:
            raise ValueError(f'لا توجد مراحل معرفة للمنتج {order.product.name}')
        
        # بناء خطة الجدولة لكل مرحلة
        stage_schedules = []
        current_start = start_date
        
        for stage in stages:
            # اختيار أفضل مركز عمل
            work_center = self._select_best_work_center(
                stage, current_start, optimization_goal
            )
            
            if not work_center:
                raise ValueError(f'لا يوجد مركز عمل متاح للمرحلة {stage.name}')
            
            # حساب المدة المطلوبة
            duration = self._calculate_stage_duration(
                stage, order.planned_quantity, work_center
            )
            
            # حساب تاريخ الانتهاء
            end_date = self._calculate_end_date(
                current_start, duration, work_center
            )
            
            # حجز السعة
            self._reserve_capacity(work_center, current_start, end_date, order)
            
            stage_schedule = {
                'stage': stage,
                'work_center': work_center,
                'start_date': current_start,
                'end_date': end_date,
                'duration_hours': duration,
                'estimated_cost': self._calculate_stage_cost(
                    stage, duration, work_center, order.planned_quantity
                )
            }
            
            stage_schedules.append(stage_schedule)
            
            # المرحلة التالية تبدأ بعد انتهاء الحالية
            current_start = end_date
        
        # إنشاء أو تحديث مراحل أمر الإنتاج
        self._create_order_stages(order, stage_schedules)
        
        # حساب النتائج الإجمالية
        total_duration = sum(s['duration_hours'] for s in stage_schedules)
        total_cost = sum(s['estimated_cost'] for s in stage_schedules)
        
        return {
            'order': order,
            'estimated_start_date': start_date,
            'estimated_end_date': stage_schedules[-1]['end_date'],
            'total_duration_hours': total_duration,
            'total_estimated_cost': total_cost,
            'stage_schedules': stage_schedules
        }
    
    def _sort_orders_by_priority(self, orders: List[ProductionOrder]) -> List[ProductionOrder]:
        """
        ترتيب الأوامر حسب الأولوية والتاريخ
        
        الأولويات: urgent > high > normal > low
        """
        priority_weights = {
            'urgent': 4,
            'high': 3,
            'normal': 2,
            'low': 1
        }
        
        return sorted(
            orders,
            key=lambda o: (
                -priority_weights.get(o.priority, 0),  # أولوية أعلى أولاً
                o.planned_start_date  # ثم التاريخ الأقدم
            )
        )
    
    def _load_work_center_capacities(self):
        """
        تحميل معلومات السعة لجميع مراكز العمل
        """
        work_centers = ProductionWorkCenter.objects.filter(is_active=True)
        
        for wc in work_centers:
            self.work_centers_cache[wc.id] = {
                'object': wc,
                'capacity_per_hour': wc.capacity_per_hour,
                'working_hours_per_day': wc.working_hours_per_day,
                'efficiency_rate': wc.efficiency_rate / 100,
                'hourly_rate': wc.hourly_rate,
                'reserved_slots': []  # قائمة الفترات المحجوزة
            }
    
    def _select_best_work_center(
        self,
        stage: ProductionStage,
        start_date: datetime,
        optimization_goal: str
    ) -> Optional[ProductionWorkCenter]:
        """
        اختيار أفضل مركز عمل للمرحلة
        
        Args:
            stage: مرحلة الإنتاج
            start_date: تاريخ البدء المطلوب
            optimization_goal: هدف التحسين
        
        Returns:
            أفضل مركز عمل أو None
        """
        # الحصول على مراكز العمل المناسبة للمرحلة
        suitable_centers = stage.work_centers.filter(is_active=True)

        if not suitable_centers.exists():
            # Fallback to single work_center if provided
            return stage.work_center if getattr(stage, 'work_center', None) and stage.work_center.is_active else None
        
        best_center = None
        best_score = float('-inf')
        
        for wc in suitable_centers:
            score = self._calculate_work_center_score(
                wc, start_date, optimization_goal
            )
            
            if score > best_score:
                best_score = score
                best_center = wc
        
        return best_center
    
    def _calculate_work_center_score(
        self,
        work_center: ProductionWorkCenter,
        start_date: datetime,
        optimization_goal: str
    ) -> float:
        """
        حساب نقاط مركز العمل بناءً على معايير متعددة
        """
        wc_info = self.work_centers_cache.get(work_center.id, {})
        
        if optimization_goal == 'minimize_cost':
            # تفضيل مراكز العمل الأقل تكلفة
            return -float(wc_info.get('hourly_rate', 1000))
        
        elif optimization_goal == 'balance_load':
            # تفضيل مراكز العمل الأقل حجزاً
            reserved_count = len(wc_info.get('reserved_slots', []))
            return -reserved_count
        
        else:  # minimize_time
            # تفضيل مراكز العمل الأعلى كفاءة
            return float(wc_info.get('efficiency_rate', 1.0))
    
    def _calculate_stage_duration(
        self,
        stage: ProductionStage,
        quantity: Decimal,
        work_center: ProductionWorkCenter
    ) -> float:
        """
        حساب المدة المطلوبة لإنجاز المرحلة (بالساعات)
        
        المدة = (الكمية / السعة_في_الساعة) / معدل_الكفاءة + وقت_الإعداد
        """
        wc_info = self.work_centers_cache.get(getattr(work_center, 'id', None), {}) if work_center else {}
        
        capacity = float(wc_info.get('capacity_per_hour', 0) or 0)
        efficiency = float(wc_info.get('efficiency_rate', 1.0) or 1.0)
        if efficiency <= 0:
            efficiency = 1.0
        setup_time_hours = float(getattr(work_center, 'setup_time', 0) or 0) / 60  # تحويل من دقائق
        
        if work_center and capacity > 0:
            production_hours = (float(quantity) / capacity) / efficiency
            return production_hours + setup_time_hours

        # fallback to standard_time when no capacity/work center
        std_time_hours = float(getattr(stage, 'standard_time', 0) or 0)
        production_hours = std_time_hours * float(quantity)
        return production_hours + setup_time_hours
    
    def _calculate_end_date(
        self,
        start_date: datetime,
        duration_hours: float,
        work_center: ProductionWorkCenter
    ) -> datetime:
        """
        حساب تاريخ الانتهاء بناءً على ساعات العمل اليومية
        
        يأخذ في الاعتبار:
        - ساعات العمل اليومية
        - أيام العطل (يمكن تطويرها لاحقاً)
        """
        wc_info = self.work_centers_cache.get(work_center.id, {})
        working_hours_per_day = float(wc_info.get('working_hours_per_day', 8))
        
        # حساب عدد الأيام المطلوبة
        days_needed = duration_hours / working_hours_per_day
        
        # إضافة الأيام (يمكن تحسينها لتخطي العطل)
        end_date = start_date + timedelta(days=days_needed)
        
        return end_date
    
    def _reserve_capacity(
        self,
        work_center: ProductionWorkCenter,
        start_date: datetime,
        end_date: datetime,
        order: ProductionOrder
    ):
        """
        حجز سعة مركز العمل للفترة المحددة
        """
        if work_center.id in self.work_centers_cache:
            self.work_centers_cache[work_center.id]['reserved_slots'].append({
                'start': start_date,
                'end': end_date,
                'order': order.number
            })
    
    def _calculate_stage_cost(
        self,
        stage: ProductionStage,
        duration_hours: float,
        work_center: ProductionWorkCenter,
        quantity: Decimal
    ) -> Decimal:
        """
        حساب تكلفة المرحلة
        
        التكلفة = (ساعات_العمل × معدل_الساعة) + تكلفة_المواد
        """
        if not work_center:
            return Decimal('0')

        wc_info = self.work_centers_cache.get(work_center.id, {})
        hourly_rate = wc_info.get('hourly_rate', getattr(work_center, 'hourly_rate', Decimal('0')))
        
        labor_cost = Decimal(str(duration_hours)) * hourly_rate
        
        # يمكن إضافة تكلفة المواد هنا من BOMItem
        # material_cost = self._calculate_material_cost(stage, quantity)
        
        return labor_cost
    
    @transaction.atomic
    def _create_order_stages(
        self,
        order: ProductionOrder,
        stage_schedules: List[Dict]
    ):
        """
        إنشاء أو تحديث سجلات مراحل أمر الإنتاج
        """
        # حذف المراحل القديمة
        order.order_stages.all().delete()
        
        # إنشاء المراحل الجديدة
        for schedule in stage_schedules:
            ProductionOrderStage.objects.create(
                production_order=order,
                stage=schedule['stage'],
                status='ready',
                planned_start_date=schedule['start_date'],
                planned_end_date=schedule['end_date'],
                planned_quantity=order.planned_quantity,
                estimated_cost=schedule['estimated_cost']
            )
        
        # تحديث تواريخ أمر الإنتاج
        order.planned_start_date = stage_schedules[0]['start_date'].date()
        order.planned_end_date = stage_schedules[-1]['end_date'].date()
        order.save(update_fields=['planned_start_date', 'planned_end_date'])
    
    def _calculate_scheduling_statistics(self, results: Dict) -> Dict:
        """
        حساب إحصائيات الجدولة
        """
        scheduled = results['scheduled_orders']
        
        if not scheduled:
            return {}
        
        total_orders = len(scheduled)
        total_duration = sum(s['total_duration_hours'] for s in scheduled)
        total_cost = sum(s['total_estimated_cost'] for s in scheduled)
        
        return {
            'total_orders': total_orders,
            'total_duration_hours': total_duration,
            'average_duration_per_order': total_duration / total_orders if total_orders > 0 else 0,
            'total_estimated_cost': total_cost,
            'average_cost_per_order': total_cost / total_orders if total_orders > 0 else 0,
            'conflicts_count': len(results['conflicts']),
            'warnings_count': len(results['warnings'])
        }
    
    def check_capacity_conflicts(
        self,
        start_date: datetime,
        end_date: datetime,
        work_center: Optional[ProductionWorkCenter] = None
    ) -> List[Dict]:
        """
        فحص تعارضات السعة في الفترة المحددة
        
        Returns:
            قائمة بالتعارضات المكتشفة
        """
        conflicts = []
        
        # الحصول على مراكز العمل المراد فحصها
        if work_center:
            centers_to_check = [work_center]
        else:
            centers_to_check = ProductionWorkCenter.objects.filter(is_active=True)
        
        for wc in centers_to_check:
            # الحصول على أوامر الإنتاج المجدولة في هذه الفترة
            overlapping_stages = ProductionOrderStage.objects.filter(
                stage__work_centers=wc,
                planned_start_date__lt=end_date,
                planned_end_date__gt=start_date,
                status__in=['ready', 'in_progress']
            ).select_related('production_order', 'stage')
            
            if overlapping_stages.count() > 1:
                conflicts.append({
                    'work_center': wc.name,
                    'period': f'{start_date} - {end_date}',
                    'overlapping_count': overlapping_stages.count(),
                    'orders': [s.production_order.number for s in overlapping_stages]
                })
        
        return conflicts
    
    def optimize_schedule(
        self,
        orders: List[ProductionOrder],
        optimization_type: str = 'genetic'  # genetic, greedy, critical_path
    ) -> Dict:
        """
        تحسين الجدولة باستخدام خوارزميات متقدمة
        
        Args:
            orders: أوامر الإنتاج
            optimization_type: نوع الخوارزمية
        
        Returns:
            الجدولة المحسنة
        """
        if optimization_type == 'greedy':
            return self._greedy_optimization(orders)
        elif optimization_type == 'critical_path':
            return self._critical_path_optimization(orders)
        else:
            # الطريقة الافتراضية
            return self.schedule_production_orders(orders)
    
    def _greedy_optimization(self, orders: List[ProductionOrder]) -> Dict:
        """
        خوارزمية الجشع: اختيار أفضل قرار محلي في كل خطوة
        """
        # جدولة الأوامر بالأولوية وأقل مدة أولاً
        sorted_orders = sorted(
            orders,
            key=lambda o: (
                -{'urgent': 4, 'high': 3, 'normal': 2, 'low': 1}.get(o.priority, 0),
                float(o.planned_quantity)  # الكميات الأقل أولاً
            )
        )
        
        return self.schedule_production_orders(
            sorted_orders,
            optimization_goal='minimize_time'
        )
    
    def _critical_path_optimization(self, orders: List[ProductionOrder]) -> Dict:
        """
        طريقة المسار الحرج (CPM): تحديد المسار الأطول وتحسينه
        """
        # هذه نسخة مبسطة - يمكن توسيعها
        return self.schedule_production_orders(
            orders,
            optimization_goal='minimize_time'
        )


class CapacityAnalyzer:
    """
    محلل سعة مراكز العمل
    """
    
    @staticmethod
    def get_work_center_utilization(
        work_center: ProductionWorkCenter,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        حساب معدل استخدام مركز العمل في فترة معينة
        
        Returns:
            dict: معدل الاستخدام، الساعات المحجوزة، الساعات المتاحة
        """
        # حساب إجمالي الساعات المتاحة
        days = (end_date.date() - start_date.date()).days
        total_available_hours = float(work_center.working_hours_per_day) * days
        
        # حساب الساعات المحجوزة
        stages = ProductionOrderStage.objects.filter(
            stage__work_center=work_center,
            planned_start_date__gte=start_date,
            planned_end_date__lte=end_date,
            status__in=['ready', 'in_progress', 'completed']
        )
        
        reserved_hours = 0
        for stage in stages:
            if stage.planned_start_date and stage.planned_end_date:
                duration = (stage.planned_end_date - stage.planned_start_date).total_seconds() / 3600
                reserved_hours += duration
        
        # حساب معدل الاستخدام
        utilization_rate = (reserved_hours / total_available_hours * 100) if total_available_hours > 0 else 0
        
        return {
            'work_center': work_center.name,
            'period': f'{start_date.date()} to {end_date.date()}',
            'total_available_hours': total_available_hours,
            'reserved_hours': reserved_hours,
            'available_hours': total_available_hours - reserved_hours,
            'utilization_rate': round(utilization_rate, 2),
            'status': 'overbooked' if utilization_rate > 100 else 'normal'
        }
    
    @staticmethod
    def identify_bottlenecks(
        start_date: datetime,
        end_date: datetime,
        threshold: float = 80.0
    ) -> List[Dict]:
        """
        تحديد الاختناقات (مراكز العمل المحملة بشكل زائد)
        
        Args:
            start_date: بداية الفترة
            end_date: نهاية الفترة
            threshold: نسبة الاستخدام التي تعتبر اختناق (افتراضياً 80%)
        
        Returns:
            قائمة بمراكز العمل التي تشكل اختناقات
        """
        bottlenecks = []
        
        work_centers = ProductionWorkCenter.objects.filter(is_active=True)
        
        for wc in work_centers:
            utilization = CapacityAnalyzer.get_work_center_utilization(
                wc, start_date, end_date
            )
            
            if utilization['utilization_rate'] >= threshold:
                bottlenecks.append({
                    'work_center': wc,
                    'utilization_data': utilization,
                    'severity': 'critical' if utilization['utilization_rate'] > 100 else 'high'
                })
        
        # ترتيب حسب معدل الاستخدام (الأعلى أولاً)
        bottlenecks.sort(
            key=lambda b: b['utilization_data']['utilization_rate'],
            reverse=True
        )
        
        return bottlenecks
