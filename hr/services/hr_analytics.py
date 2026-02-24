"""
خدمة تحليلات الموارد البشرية المتقدمة
HR Analytics Service

يوفر هذا الملف تحليلات متقدمة للموارد البشرية تشمل:
- تحليل الدوران الوظيفي
- توقع المغادرة
- تحليل الأداء
- KPIs للموارد البشرية
"""

from django.db.models import Sum, Avg, Count, F, Q, ExpressionWrapper, DecimalField
from django.db.models.functions import TruncMonth, TruncWeek, ExtractYear, ExtractMonth
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Tuple, Optional, Any
from collections import defaultdict
import statistics

from hr.models import (
    Employee, Department, JobPosition, AttendanceRecord,
    LeaveRequest, Payroll, PerformanceReview,
    PerformanceTarget
)


class HRAnalyticsService:
    """
    خدمة التحليلات المتقدمة للموارد البشرية
    """
    
    @staticmethod
    def get_hr_kpis(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        الحصول على مؤشرات الأداء الرئيسية للموارد البشرية
        """
        if not start_date:
            start_date = timezone.now() - timedelta(days=30)
        if not end_date:
            end_date = timezone.now()
        
        # إحصائيات الموظفين
        employee_stats = HRAnalyticsService._get_employee_stats()
        
        # معدل الحضور
        attendance_rate = HRAnalyticsService._calculate_attendance_rate(start_date, end_date)
        
        # معدل الدوران
        turnover_rate = HRAnalyticsService._calculate_turnover_rate(start_date, end_date)
        
        # تكلفة الموظفين
        labor_cost = HRAnalyticsService._calculate_labor_cost(start_date, end_date)
        
        # الإجازات
        leave_stats = HRAnalyticsService._get_leave_stats(start_date, end_date)
        
        # الأداء
        performance_stats = HRAnalyticsService._get_performance_stats()
        
        return {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
            },
            'employees': employee_stats,
            'attendance_rate': attendance_rate,
            'turnover_rate': turnover_rate,
            'labor_cost': labor_cost,
            'leaves': leave_stats,
            'performance': performance_stats,
            'recommendations': HRAnalyticsService._generate_recommendations(
                employee_stats, attendance_rate, turnover_rate
            ),
        }
    
    @staticmethod
    def _get_employee_stats() -> Dict[str, Any]:
        """
        إحصائيات الموظفين
        """
        total = Employee.objects.count()
        active = Employee.objects.filter(status='active').count()
        
        # توزيع حسب الأقسام
        by_department = Employee.objects.filter(
            status='active'
        ).values(
            'department__name'
        ).annotate(
            count=Count('id')
        ).order_by('-count')
        
        # توزيع حسب النوع
        by_gender = Employee.objects.filter(
            status='active'
        ).values('gender').annotate(count=Count('id'))
        
        # توزيع حسب نوع العقد
        by_contract = Employee.objects.filter(
            status='active'
        ).values('contract_type').annotate(count=Count('id'))
        
        # متوسط سنوات الخدمة
        avg_tenure = HRAnalyticsService._calculate_avg_tenure()
        
        return {
            'total': total,
            'active': active,
            'inactive': total - active,
            'active_percentage': round((active / total * 100) if total > 0 else 0, 1),
            'by_department': list(by_department[:10]),
            'by_gender': list(by_gender),
            'by_contract': list(by_contract),
            'avg_tenure_years': avg_tenure,
        }
    
    @staticmethod
    def _calculate_avg_tenure() -> float:
        """
        حساب متوسط سنوات الخدمة
        """
        employees = Employee.objects.filter(
            status='active',
            hire_date__isnull=False
        )
        
        today = timezone.now().date()
        tenures = []
        
        for emp in employees:
            tenure_days = (today - emp.hire_date).days
            tenure_years = tenure_days / 365.25
            tenures.append(tenure_years)
        
        return round(statistics.mean(tenures), 1) if tenures else 0
    
    @staticmethod
    def _calculate_attendance_rate(
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        حساب معدل الحضور
        """
        records = AttendanceRecord.objects.filter(
            date__range=[start_date.date(), end_date.date()]
        )
        
        total_records = records.count()
        present = records.filter(status='present').count()
        late = records.filter(status='late').count()
        absent = records.filter(status='absent').count()
        
        attendance_rate = ((present + late) / total_records * 100) if total_records > 0 else 0
        
        # الحضور حسب القسم
        by_department = records.values(
            'employee__department__name'
        ).annotate(
            total=Count('id'),
            present=Count('id', filter=Q(status__in=['present', 'late'])),
        ).annotate(
            rate=ExpressionWrapper(
                F('present') * 100.0 / F('total'),
                output_field=DecimalField()
            )
        ).order_by('-rate')
        
        return {
            'total_records': total_records,
            'present': present,
            'late': late,
            'absent': absent,
            'attendance_rate': round(attendance_rate, 1),
            'punctuality_rate': round((present / total_records * 100) if total_records > 0 else 0, 1),
            'by_department': list(by_department[:10]),
        }
    
    @staticmethod
    def _calculate_turnover_rate(
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        حساب معدل الدوران الوظيفي
        """
        # الموظفون في بداية الفترة
        start_count = Employee.objects.filter(
            hire_date__lt=start_date,
            status='active'
        ).count() + Employee.objects.filter(
            hire_date__lt=start_date,
            termination_date__gte=start_date
        ).count()
        
        # الموظفون في نهاية الفترة
        end_count = Employee.objects.filter(
            status='active',
            hire_date__lte=end_date
        ).exclude(
            termination_date__lt=end_date
        ).count()
        
        # المغادرون خلال الفترة
        departed = Employee.objects.filter(
            termination_date__range=[start_date.date(), end_date.date()]
        ).count()
        
        # التوظيف الجديد
        hired = Employee.objects.filter(
            hire_date__range=[start_date.date(), end_date.date()]
        ).count()
        
        # حساب معدل الدوران
        avg_count = (start_count + end_count) / 2
        turnover_rate = (departed / avg_count * 100) if avg_count > 0 else 0
        
        # أسباب المغادرة
        departure_reasons = Employee.objects.filter(
            termination_date__range=[start_date.date(), end_date.date()]
        ).values('termination_reason').annotate(count=Count('id'))
        
        return {
            'start_count': start_count,
            'end_count': end_count,
            'hired': hired,
            'departed': departed,
            'net_change': hired - departed,
            'turnover_rate': round(turnover_rate, 1),
            'retention_rate': round(100 - turnover_rate, 1),
            'departure_reasons': list(departure_reasons),
        }
    
    @staticmethod
    def _calculate_labor_cost(
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        حساب تكلفة العمالة
        """
        payrolls = Payroll.objects.filter(
            pay_period_start__range=[start_date.date(), end_date.date()]
        )
        
        total_salary = payrolls.aggregate(Sum('basic_salary'))['basic_salary__sum'] or Decimal('0')
        total_allowances = payrolls.aggregate(Sum('total_allowances'))['total_allowances__sum'] or Decimal('0')
        total_deductions = payrolls.aggregate(Sum('total_deductions'))['total_deductions__sum'] or Decimal('0')
        total_net = payrolls.aggregate(Sum('net_salary'))['net_salary__sum'] or Decimal('0')
        
        # توزيع حسب القسم
        by_department = payrolls.values(
            'employee__department__name'
        ).annotate(
            total=Sum('net_salary'),
            count=Count('id'),
        ).order_by('-total')
        
        return {
            'total_basic': float(total_salary),
            'total_allowances': float(total_allowances),
            'total_deductions': float(total_deductions),
            'total_net': float(total_net),
            'avg_salary': float(total_net / payrolls.count()) if payrolls.count() > 0 else 0,
            'by_department': list(by_department[:10]),
        }
    
    @staticmethod
    def _get_leave_stats(
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        إحصائيات الإجازات
        """
        leaves = LeaveRequest.objects.filter(
            start_date__range=[start_date.date(), end_date.date()]
        )
        
        total = leaves.count()
        approved = leaves.filter(status='approved').count()
        pending = leaves.filter(status='pending').count()
        rejected = leaves.filter(status='rejected').count()
        
        # حسب النوع
        by_type = leaves.values('leave_type').annotate(
            count=Count('id'),
            days=Sum('days_requested')
        ).order_by('-count')
        
        return {
            'total_requests': total,
            'approved': approved,
            'pending': pending,
            'rejected': rejected,
            'approval_rate': round((approved / total * 100) if total > 0 else 0, 1),
            'by_type': list(by_type),
        }
    
    @staticmethod
    def _get_performance_stats() -> Dict[str, Any]:
        """
        إحصائيات الأداء
        """
        reviews = PerformanceReview.objects.filter(
            review_date__gte=timezone.now().date() - timedelta(days=365)
        )
        
        total = reviews.count()
        avg_score = reviews.aggregate(Avg('overall_score'))['overall_score__avg'] or 0
        
        # توزيع التقييمات
        score_distribution = {
            'excellent': reviews.filter(overall_score__gte=90).count(),
            'good': reviews.filter(overall_score__gte=75, overall_score__lt=90).count(),
            'average': reviews.filter(overall_score__gte=60, overall_score__lt=75).count(),
            'below_average': reviews.filter(overall_score__lt=60).count(),
        }
        
        # أفضل 5 موظفين
        top_performers = reviews.order_by('-overall_score')[:5].values(
            'employee__first_name',
            'employee__last_name',
            'overall_score'
        )
        
        # الأهداف
        targets = PerformanceTarget.objects.filter(
            target_date__gte=timezone.now().date() - timedelta(days=90)
        )
        
        target_stats = {
            'total': targets.count(),
            'achieved': targets.filter(status='achieved').count(),
            'in_progress': targets.filter(status='in_progress').count(),
            'not_started': targets.filter(status='not_started').count(),
        }
        
        return {
            'total_reviews': total,
            'avg_score': round(float(avg_score), 1),
            'score_distribution': score_distribution,
            'top_performers': list(top_performers),
            'targets': target_stats,
        }
    
    @staticmethod
    def _generate_recommendations(
        employee_stats: Dict,
        attendance_rate: Dict,
        turnover_rate: Dict
    ) -> List[Dict[str, Any]]:
        """
        توليد توصيات ذكية
        """
        recommendations = []
        
        # توصية الحضور
        if attendance_rate['attendance_rate'] < 90:
            recommendations.append({
                'type': 'attendance',
                'priority': 'high',
                'title': 'تحسين معدل الحضور',
                'description': f"معدل الحضور الحالي {attendance_rate['attendance_rate']}% أقل من المستهدف",
                'action': 'مراجعة سياسات الحضور وتطبيق حوافز الانتظام',
            })
        
        # توصية الدوران
        if turnover_rate['turnover_rate'] > 15:
            recommendations.append({
                'type': 'retention',
                'priority': 'high',
                'title': 'معالجة ارتفاع معدل الدوران',
                'description': f"معدل الدوران {turnover_rate['turnover_rate']}% مرتفع",
                'action': 'إجراء مقابلات خروج وتحسين بيئة العمل',
            })
        
        # توصية التوظيف
        if turnover_rate['departed'] > turnover_rate['hired']:
            recommendations.append({
                'type': 'hiring',
                'priority': 'medium',
                'title': 'تسريع التوظيف',
                'description': 'عدد المغادرين أكثر من الموظفين الجدد',
                'action': 'تسريع عمليات التوظيف لسد الفجوة',
            })
        
        # توصية التنوع
        if employee_stats.get('by_gender'):
            gender_data = {g['gender']: g['count'] for g in employee_stats['by_gender']}
            total = sum(gender_data.values())
            if total > 0:
                female_pct = (gender_data.get('female', 0) / total * 100)
                if female_pct < 20:
                    recommendations.append({
                        'type': 'diversity',
                        'priority': 'low',
                        'title': 'تحسين التنوع الجنسي',
                        'description': f'نسبة الإناث {female_pct:.0f}% فقط',
                        'action': 'مراجعة سياسات التوظيف لتعزيز التنوع',
                    })
        
        return recommendations
    
    @staticmethod
    def predict_attrition_risk() -> List[Dict[str, Any]]:
        """
        توقع خطر المغادرة للموظفين
        بناءً على عوامل متعددة
        """
        high_risk = []
        
        employees = Employee.objects.filter(status='active')
        
        for emp in employees:
            risk_score = 0
            risk_factors = []
            
            # عامل 1: سنوات الخدمة (2-5 سنوات = أعلى خطر)
            tenure = (timezone.now().date() - emp.hire_date).days / 365.25 if emp.hire_date else 0
            if 2 <= tenure <= 5:
                risk_score += 20
                risk_factors.append('فترة خطرة من سنوات الخدمة (2-5 سنوات)')
            
            # عامل 2: الحضور
            recent_attendance = AttendanceRecord.objects.filter(
                employee=emp,
                date__gte=timezone.now().date() - timedelta(days=90)
            )
            absent_count = recent_attendance.filter(status='absent').count()
            if absent_count > 5:
                risk_score += 25
                risk_factors.append(f'غياب متكرر ({absent_count} أيام)')
            
            # عامل 3: الأداء
            recent_review = PerformanceReview.objects.filter(
                employee=emp
            ).order_by('-review_date').first()
            
            if recent_review and recent_review.overall_score < 60:
                risk_score += 30
                risk_factors.append('أداء منخفض')
            
            # عامل 4: عدم الترقية
            if emp.last_promotion_date:
                years_since_promotion = (timezone.now().date() - emp.last_promotion_date).days / 365.25
                if years_since_promotion > 3:
                    risk_score += 15
                    risk_factors.append('لم تتم ترقيته منذ أكثر من 3 سنوات')
            
            # تصنيف المخاطر
            if risk_score >= 50:
                high_risk.append({
                    'employee': {
                        'id': emp.id,
                        'name': emp.get_full_name(),
                        'department': emp.department.name if emp.department else 'غير محدد',
                    },
                    'risk_score': risk_score,
                    'risk_level': 'high' if risk_score >= 70 else 'medium',
                    'factors': risk_factors,
                })
        
        return sorted(high_risk, key=lambda x: x['risk_score'], reverse=True)[:10]
    
    @staticmethod
    def get_workforce_planning(
        months_ahead: int = 12
    ) -> Dict[str, Any]:
        """
        تخطيط القوى العاملة
        """
        current_headcount = Employee.objects.filter(status='active').count()
        
        # توقع التقاعد
        retirement_age = 60
        retiring_soon = Employee.objects.filter(
            status='active',
            birth_date__isnull=False,
        ).annotate(
            age=ExtractYear(timezone.now().date()) - ExtractYear(F('birth_date'))
        ).filter(age__gte=retirement_age - 2).count()
        
        # توقع المغادرة بناءً على الاتجاه التاريخي
        historical_turnover = HRAnalyticsService._calculate_turnover_rate(
            timezone.now() - timedelta(days=365),
            timezone.now()
        )
        
        expected_departures = int(current_headcount * historical_turnover['turnover_rate'] / 100 * months_ahead / 12)
        
        # الاحتياج المتوقع
        projected_need = expected_departures + retiring_soon
        
        # توزيع الاحتياج حسب القسم
        departments = Employee.objects.filter(
            status='active'
        ).values('department__name').annotate(
            current=Count('id')
        )
        
        department_needs = []
        for dept in departments:
            dept_turnover = int(dept['current'] * historical_turnover['turnover_rate'] / 100 * months_ahead / 12)
            department_needs.append({
                'department': dept['department__name'],
                'current': dept['current'],
                'projected_need': dept_turnover,
            })
        
        return {
            'current_headcount': current_headcount,
            'retiring_soon': retiring_soon,
            'expected_departures': expected_departures,
            'total_projected_need': projected_need,
            'by_department': department_needs,
            'months_ahead': months_ahead,
        }
