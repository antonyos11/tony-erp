"""
نظام الصيانة الوقائية المتقدم
Advanced Preventive Maintenance System

يوفر:
- جدولة تلقائية للصيانة الدورية
- تنبيهات وإشعارات مسبقة
- تتبع تاريخ الصيانة وتحليل الأداء
- تكامل مع نظام التكاليف
"""

from django.db import transaction
from django.utils import timezone
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import List, Dict, Optional, Tuple, Any
from dateutil.relativedelta import relativedelta

from maintenance.models import (
    Machine, MaintenanceSchedule, MaintenanceRequest,
    MaintenanceType, MaintenanceRecord
)
from hr.models import Employee
from django.contrib.auth.models import User


class PreventiveMaintenanceScheduler:
    """
    محرك الجدولة التلقائية للصيانة الوقائية
    
    المسؤوليات:
    - إنشاء طلبات صيانة تلقائية من الجداول
    - حساب التواريخ المستحقة التالية
    - إرسال تنبيهات مسبقة
    - تحديث حالة الماكينات
    """
    
    def __init__(self):
        self.generated_requests = []
        self.alerts = []
    
    def generate_due_maintenance_requests(
        self,
        check_date: Optional[date] = None,
        advance_days: int = 7
    ) -> Dict[str, Any]:
        """
        إنشاء طلبات صيانة للجداول المستحقة
        
        Args:
            check_date: التاريخ المراد الفحص له (افتراضياً اليوم)
            advance_days: عدد الأيام المستقبلية للفحص
        
        Returns:
            {
                'generated_requests': [...],  # الطلبات المنشأة
                'upcoming_schedules': [...],  # الجداول القادمة
                'alerts': [...],              # التنبيهات
                'statistics': {...}
            }
        """
        if not check_date:
            check_date = timezone.now().date()
        
        future_date = check_date + timedelta(days=advance_days)
        
        # الحصول على الجداول النشطة المستحقة
        due_schedules = MaintenanceSchedule.objects.filter(
            is_active=True,
            next_due_date__lte=future_date,
            machine__status='operational'
        ).select_related('machine', 'maintenance_type', 'assigned_to')
        
        generated_count = 0
        upcoming_count = 0
        
        for schedule in due_schedules:
            # التحقق من عدم وجود طلب مفتوح بالفعل
            existing_request = MaintenanceRequest.objects.filter(
                machine=schedule.machine,
                maintenance_type=schedule.maintenance_type,
                status__in=['draft', 'submitted', 'approved', 'in_progress']
            ).first()
            
            if existing_request:
                continue  # تخطي إذا كان هناك طلب مفتوح
            
            # فحص إذا كانت مستحقة الآن
            if schedule.next_due_date <= check_date:
                if schedule.auto_generate_requests:
                    # إنشاء طلب صيانة تلقائياً
                    request = self._create_maintenance_request_from_schedule(schedule)
                    self.generated_requests.append(request)
                    generated_count += 1
                    
                    # تحديث تاريخ آخر إنشاء
                    schedule.last_generated_date = check_date
                    schedule.save(update_fields=['last_generated_date'])
            else:
                # صيانة قادمة - إضافة للتنبيهات
                upcoming_count += 1
                days_until = (schedule.next_due_date - check_date).days
                
                if days_until <= schedule.advance_notice_days:
                    self.alerts.append({
                        'type': 'upcoming_maintenance',
                        'schedule': schedule,
                        'machine': schedule.machine,
                        'days_until': days_until,
                        'severity': 'warning' if days_until <= 3 else 'info'
                    })
        
        # إحصائيات
        statistics = {
            'total_schedules_checked': due_schedules.count(),
            'generated_requests': generated_count,
            'upcoming_maintenance': upcoming_count,
            'alerts_count': len(self.alerts)
        }
        
        return {
            'generated_requests': self.generated_requests,
            'upcoming_schedules': list(due_schedules.filter(
                next_due_date__gt=check_date
            )),
            'alerts': self.alerts,
            'statistics': statistics
        }
    
    def _create_maintenance_request_from_schedule(
        self,
        schedule: MaintenanceSchedule
    ) -> MaintenanceRequest:
        """
        إنشاء طلب صيانة من جدولة
        """
        # البحث عن مستخدم نظام للإنشاء التلقائي، وإن لم يوجد ننشئ مستخدماً تقنياً بسيطاً
        system_user = User.objects.filter(is_staff=True).first()
        if system_user is None:
            system_user, _ = User.objects.get_or_create(username='system', defaults={'is_staff': True, 'is_active': True})
        
        request = MaintenanceRequest.objects.create(
            machine=schedule.machine,
            maintenance_type=schedule.maintenance_type,
            title=f"صيانة دورية - {schedule.name}",
            description=schedule.description or f"صيانة وقائية مجدولة للماكينة {schedule.machine.name}",
            priority='normal',
            status='submitted',  # مباشرة للمراجعة
            requested_by=system_user,
            assigned_to=schedule.assigned_to,
            estimated_cost=schedule.estimated_cost,
            estimated_duration_hours=schedule.estimated_duration_hours,
            requested_completion_date=schedule.next_due_date,
            notes=f"تم الإنشاء تلقائياً من الجدولة: {schedule.name}"
        )
        
        # تحديث تاريخ الصيانة القادمة في الجدولة
        schedule.next_due_date = self._calculate_next_due_date(
            schedule.next_due_date,
            schedule.frequency,
            schedule.interval_days
        )
        schedule.save(update_fields=['next_due_date'])
        
        return request
    
    def _calculate_next_due_date(
        self,
        current_due_date: date,
        frequency: str,
        interval_days: int
    ) -> date:
        """
        حساب التاريخ المستحق التالي بناءً على التكرار
        
        Args:
            current_due_date: التاريخ المستحق الحالي
            frequency: التكرار (daily, weekly, monthly, etc.)
            interval_days: الفترة بالأيام (للتكرار المخصص)
        
        Returns:
            التاريخ المستحق التالي
        """
        if frequency == 'daily':
            return current_due_date + timedelta(days=1)
        
        elif frequency == 'weekly':
            return current_due_date + timedelta(weeks=1)
        
        elif frequency == 'monthly':
            return current_due_date + relativedelta(months=1)
        
        elif frequency == 'quarterly':
            return current_due_date + relativedelta(months=3)
        
        elif frequency == 'semi_annual':
            return current_due_date + relativedelta(months=6)
        
        elif frequency == 'annual':
            return current_due_date + relativedelta(years=1)
        
        elif frequency == 'custom':
            return current_due_date + timedelta(days=interval_days)
        
        else:
            # افتراضي: شهري
            return current_due_date + relativedelta(months=1)
    
    def update_machine_maintenance_dates(self, machine: Machine):
        """
        تحديث تواريخ الصيانة للماكينة بناءً على آخر سجل صيانة
        """
        # الحصول على آخر سجل صيانة مكتمل
        last_maintenance = MaintenanceRecord.objects.filter(
            machine=machine,
            status='completed'
        ).order_by('-completion_date').first()
        
        if last_maintenance:
            machine.last_maintenance_date = last_maintenance.completion_date
            machine.next_maintenance_date = (
                last_maintenance.completion_date + 
                timedelta(days=machine.maintenance_interval_days)
            )
            machine.save(update_fields=['last_maintenance_date', 'next_maintenance_date'])
    
    def check_overdue_maintenance(self) -> List[Dict]:
        """
        فحص الماكينات التي تأخرت عن موعد الصيانة
        
        Returns:
            قائمة بالماكينات المتأخرة مع تفاصيل التأخير
        """
        today = timezone.now().date()
        overdue_machines = []
        
        machines = Machine.objects.filter(
            status='operational',
            next_maintenance_date__lt=today
        )
        
        for machine in machines:
            days_overdue = (today - machine.next_maintenance_date).days if machine.next_maintenance_date else 0
            
            # تحديد مستوى الخطورة
            if days_overdue > 30:
                severity = 'critical'
            elif days_overdue > 14:
                severity = 'high'
            elif days_overdue > 7:
                severity = 'medium'
            else:
                severity = 'low'
            
            overdue_machines.append({
                'machine': machine,
                'next_maintenance_date': machine.next_maintenance_date,
                'days_overdue': days_overdue,
                'severity': severity
            })
        
        # ترتيب حسب الخطورة وعدد الأيام
        overdue_machines.sort(
            key=lambda m: (
                {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}[m['severity']],
                -m['days_overdue']
            ),
            reverse=True
        )
        
        return overdue_machines


class MaintenanceAnalytics:
    """
    تحليل أداء الصيانة والإحصائيات
    """
    
    @staticmethod
    def get_machine_maintenance_history(
        machine: Machine,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        الحصول على تاريخ صيانة الماكينة مع تحليل شامل
        
        Returns:
            {
                'total_maintenances': int,
                'total_cost': Decimal,
                'total_downtime_hours': Decimal,
                'average_cost_per_maintenance': Decimal,
                'mtbf': float,  # Mean Time Between Failures
                'mttr': float,  # Mean Time To Repair
                'maintenance_types_breakdown': {...},
                'recent_records': [...]
            }
        """
        # بناء الاستعلام
        query = MaintenanceRecord.objects.filter(machine=machine)

        if start_date:
            query = query.filter(start_datetime__date__gte=start_date)
        if end_date:
            query = query.filter(start_datetime__date__lte=end_date)

        records = query.select_related('maintenance_type').order_by('-start_datetime')
        
        # الإحصائيات الأساسية
        total_maintenances = records.count()
        total_cost = sum(r.actual_cost or Decimal('0') for r in records)
        total_downtime = sum(r.actual_duration_hours or Decimal('0') for r in records)
        
        # المتوسطات
        avg_cost = total_cost / total_maintenances if total_maintenances > 0 else Decimal('0')
        
        # MTBF - متوسط الوقت بين الأعطال (للصيانة التصحيحية فقط)
        corrective_records = [r for r in records if r.maintenance_type.category == 'corrective']
        mtbf = MaintenanceAnalytics._calculate_mtbf(corrective_records, machine)
        
        # MTTR - متوسط وقت الإصلاح
        mttr = float(total_downtime / total_maintenances) if total_maintenances > 0 else 0.0
        
        # تحليل حسب نوع الصيانة
        maintenance_types_breakdown = {}
        for record in records:
            type_name = record.maintenance_type.name
            if type_name not in maintenance_types_breakdown:
                maintenance_types_breakdown[type_name] = {
                    'count': 0,
                    'cost': Decimal('0'),
                    'downtime': Decimal('0')
                }
            
            maintenance_types_breakdown[type_name]['count'] += 1
            maintenance_types_breakdown[type_name]['cost'] += record.actual_cost or Decimal('0')
            maintenance_types_breakdown[type_name]['downtime'] += record.actual_duration_hours or Decimal('0')
        
        return {
            'machine': machine,
            'period': f'{start_date or "البداية"} إلى {end_date or "الآن"}',
            'total_maintenances': total_maintenances,
            'total_cost': total_cost,
            'total_downtime_hours': total_downtime,
            'average_cost_per_maintenance': avg_cost,
            'mtbf_hours': mtbf,
            'mttr_hours': mttr,
            'maintenance_types_breakdown': maintenance_types_breakdown,
            'recent_records': list(records[:10])  # آخر 10 سجلات
        }
    
    @staticmethod
    def _calculate_mtbf(corrective_records: List, machine: Machine) -> float:
        """
        حساب متوسط الوقت بين الأعطال (MTBF)
        
        MTBF = إجمالي ساعات التشغيل / عدد الأعطال
        """
        if not corrective_records:
            return 0.0
        
        failures_count = len(corrective_records)
        total_operational_hours = float(machine.operational_hours)
        
        mtbf = total_operational_hours / failures_count if failures_count > 0 else 0.0
        
        return mtbf
    
    @staticmethod
    def get_maintenance_cost_analysis(
        start_date: date,
        end_date: date,
        group_by: str = 'machine'  # machine, type, department, month
    ) -> Dict[str, Any]:
        """
        تحليل تكاليف الصيانة
        
        Args:
            start_date: تاريخ البدء
            end_date: تاريخ الانتهاء
            group_by: طريقة التجميع
        
        Returns:
            تحليل شامل للتكاليف
        """
        from django.db.models import Sum, Count, Avg
        
        records = MaintenanceRecord.objects.filter(
            start_date__gte=start_date,
            start_date__lte=end_date,
            status='completed'
        )
        
        # الإحصائيات العامة
        total_records = records.count()
        total_cost = records.aggregate(Sum('actual_cost'))['actual_cost__sum'] or Decimal('0')
        avg_cost = records.aggregate(Avg('actual_cost'))['actual_cost__avg'] or Decimal('0')
        
        # التجميع حسب المعيار المحدد
        grouped_data = {}
        
        if group_by == 'machine':
            for record in records:
                machine_name = record.machine.name
                if machine_name not in grouped_data:
                    grouped_data[machine_name] = {
                        'count': 0,
                        'total_cost': Decimal('0'),
                        'total_downtime': Decimal('0')
                    }
                
                grouped_data[machine_name]['count'] += 1
                grouped_data[machine_name]['total_cost'] += record.actual_cost or Decimal('0')
                grouped_data[machine_name]['total_downtime'] += record.actual_duration_hours or Decimal('0')
        
        elif group_by == 'type':
            for record in records:
                type_name = record.maintenance_type.name
                if type_name not in grouped_data:
                    grouped_data[type_name] = {
                        'count': 0,
                        'total_cost': Decimal('0')
                    }
                
                grouped_data[type_name]['count'] += 1
                grouped_data[type_name]['total_cost'] += record.actual_cost or Decimal('0')
        
        elif group_by == 'month':
            for record in records:
                month_key = record.start_date.strftime('%Y-%m')
                if month_key not in grouped_data:
                    grouped_data[month_key] = {
                        'count': 0,
                        'total_cost': Decimal('0')
                    }
                
                grouped_data[month_key]['count'] += 1
                grouped_data[month_key]['total_cost'] += record.actual_cost or Decimal('0')
        
        return {
            'period': f'{start_date} إلى {end_date}',
            'total_records': total_records,
            'total_cost': total_cost,
            'average_cost': avg_cost,
            'grouped_data': grouped_data
        }
    
    @staticmethod
    def calculate_maintenance_efficiency(
        machine: Machine,
        period_days: int = 90
    ) -> Dict[str, Any]:
        """
        حساب كفاءة الصيانة للماكينة
        
        المؤشرات:
        - Availability (التوفر)
        - Performance (الأداء)
        - Quality (الجودة)
        - OEE (Overall Equipment Effectiveness)
        """
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=period_days)
        
        # حساب وقت التوقف
        records = MaintenanceRecord.objects.filter(
            machine=machine,
            start_datetime__date__gte=start_date,
            start_datetime__date__lte=end_date,
            status='completed'
        )
        
        total_downtime_hours = sum(
            float(r.actual_duration_hours or 0) for r in records
        )
        
        # إجمالي الوقت المتاح (أيام × 24 ساعة)
        total_available_hours = period_days * 24
        
        # وقت التشغيل الفعلي
        operating_hours = total_available_hours - total_downtime_hours
        
        # نسبة التوفر
        availability = (operating_hours / total_available_hours * 100) if total_available_hours > 0 else 0
        
        # نسبة الأداء (يمكن حسابها من معدل الإنتاج - افتراضياً 100%)
        performance = 100.0  # يمكن تحسينها بالتكامل مع الإنتاج
        
        # نسبة الجودة (يمكن حسابها من معدل الإنتاج الجيد - افتراضياً 100%)
        quality = 100.0  # يمكن تحسينها بالتكامل مع الجودة
        
        # OEE
        oee = (availability * performance * quality) / 10000
        
        return {
            'machine': machine.name,
            'period_days': period_days,
            'total_available_hours': total_available_hours,
            'total_downtime_hours': total_downtime_hours,
            'operating_hours': operating_hours,
            'availability_percent': round(availability, 2),
            'performance_percent': round(performance, 2),
            'quality_percent': round(quality, 2),
            'oee_percent': round(oee, 2),
            'classification': MaintenanceAnalytics._classify_oee(oee)
        }
    
    @staticmethod
    def _classify_oee(oee: float) -> str:
        """
        تصنيف OEE
        
        World Class: >= 85%
        Good: 60-85%
        Fair: 40-60%
        Poor: < 40%
        """
        if oee >= 85:
            return 'World Class'
        elif oee >= 60:
            return 'Good'
        elif oee >= 40:
            return 'Fair'
        else:
            return 'Poor'


class MaintenanceAlertManager:
    """
    إدارة التنبيهات والإشعارات
    """
    
    @staticmethod
    def generate_maintenance_alerts() -> List[Dict]:
        """
        إنشاء جميع التنبيهات المطلوبة
        
        Returns:
            قائمة بالتنبيهات مع مستويات الخطورة
        """
        alerts = []
        today = timezone.now().date()
        
        # 1. تنبيهات الصيانة المتأخرة
        scheduler = PreventiveMaintenanceScheduler()
        overdue = scheduler.check_overdue_maintenance()
        
        for item in overdue:
            alerts.append({
                'type': 'overdue_maintenance',
                'severity': item['severity'],
                'machine': item['machine'],
                'message': f"الصيانة متأخرة {item['days_overdue']} يوم",
                'days_overdue': item['days_overdue']
            })
        
        # 2. تنبيهات انتهاء الضمان
        machines_warranty_expiring = Machine.objects.filter(
            status='operational',
            warranty_end_date__lte=today + timedelta(days=30),
            warranty_end_date__gte=today
        )
        
        for machine in machines_warranty_expiring:
            days_until = (machine.warranty_end_date - today).days
            alerts.append({
                'type': 'warranty_expiring',
                'severity': 'warning',
                'machine': machine,
                'message': f"الضمان سينتهي خلال {days_until} يوم",
                'days_until': days_until
            })
        
        # 3. تنبيهات الحالة الحرجة
        critical_machines = Machine.objects.filter(
            condition='critical',
            status='operational'
        )
        
        for machine in critical_machines:
            alerts.append({
                'type': 'critical_condition',
                'severity': 'critical',
                'machine': machine,
                'message': f"حالة الماكينة حرجة - تحتاج صيانة فورية"
            })
        
        # 4. تنبيهات الطلبات المتأخرة
        overdue_requests = MaintenanceRequest.objects.filter(
            status__in=['submitted', 'approved', 'in_progress'],
            requested_completion_date__lt=today
        )
        
        for request in overdue_requests:
            days_overdue = (today - request.requested_completion_date).days if request.requested_completion_date else 0
            alerts.append({
                'type': 'request_overdue',
                'severity': 'high' if days_overdue > 7 else 'medium',
                'request': request,
                'machine': request.machine,
                'message': f"طلب الصيانة متأخر {days_overdue} يوم",
                'days_overdue': days_overdue
            })
        
        # ترتيب حسب الخطورة
        severity_order = {'critical': 4, 'high': 3, 'warning': 2, 'medium': 2, 'info': 1, 'low': 1}
        alerts.sort(key=lambda a: -severity_order.get(a['severity'], 0))
        
        return alerts
    
    @staticmethod
    def send_scheduled_notifications():
        """
        إرسال الإشعارات المجدولة
        
        يتم استدعاؤها عبر Cron Job يومياً
        """
        # الحصول على التنبيهات
        alerts = MaintenanceAlertManager.generate_maintenance_alerts()
        
        # تجميع حسب الخطورة
        critical_alerts = [a for a in alerts if a['severity'] == 'critical']
        high_alerts = [a for a in alerts if a['severity'] == 'high']
        
        # إرسال إشعارات (يمكن التكامل مع Email/SMS)
        # هذا مثال - يمكن توسيعه
        
        if critical_alerts:
            # إرسال إشعار فوري للإدارة
            pass
        
        if high_alerts:
            # إرسال إشعار للمسؤولين
            pass
        
        return {
            'total_alerts': len(alerts),
            'critical': len(critical_alerts),
            'high': len(high_alerts),
            'sent': True
        }
