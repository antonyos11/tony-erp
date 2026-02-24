from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from hr.models import (
    Employee, Department, TargetCategory, PerformanceTarget, 
    PerformanceMetric, EmployeeMetricValue, TeamTarget
)
from datetime import date, timedelta
from decimal import Decimal
import random


class Command(BaseCommand):
    help = 'إنشاء بيانات تجريبية لنظام الأهداف والتارجت'

    def handle(self, *args, **options):
            self.stdout.write('بدء إنشاء بيانات نظام الأهداف والتارجت...')

            # 1. إنشاء فئات الأهداف
            self.create_target_categories()

            # 2. إنشاء مقاييس الأداء
            self.create_performance_metrics()

            # 3. إنشاء أهداف فردية
            self.create_individual_targets()

            # 4. إنشاء أهداف الفرق
            self.create_team_targets()

            # 5. إضافة قيم مقاييس الأداء
            self.create_metric_values()

            self.stdout.write(self.style.SUCCESS('تم إنشاء بيانات التارجت بنجاح'))

    def create_target_categories(self):
        """إنشاء فئات الأهداف"""
        categories_data = [
            {'name': 'أهداف المبيعات', 'category_type': 'sales', 'description': 'أهداف متعلقة بتحقيق المبيعات والإيرادات'},
            {'name': 'أهداف الإنتاج', 'category_type': 'production', 'description': 'أهداف كمية وجودة الإنتاج'},
            {'name': 'أهداف الجودة', 'category_type': 'quality', 'description': 'أهداف تحسين جودة المنتجات والخدمات'},
            {'name': 'أهداف الحضور', 'category_type': 'attendance', 'description': 'أهداف الالتزام بالحضور والمواعيد'},
            {'name': 'أهداف خدمة العملاء', 'category_type': 'customer_service', 'description': 'أهداف تحسين رضا العملاء'},
            {'name': 'أهداف تقليل التكاليف', 'category_type': 'cost_reduction', 'description': 'أهداف تحسين الكفاءة وتقليل التكاليف'},
            {'name': 'أهداف التدريب والتطوير', 'category_type': 'training', 'description': 'أهداف التطوير المهني والشخصي'},
            {'name': 'أهداف السلامة', 'category_type': 'safety', 'description': 'أهداف السلامة المهنية'},
        ]
        
        for category_data in categories_data:
            category, created = TargetCategory.objects.get_or_create(
                name=category_data['name'],
                defaults=category_data
            )
            if created:
                self.stdout.write(f'- تم إنشاء فئة الأهداف: {category.name}')
    
    def create_performance_metrics(self):
        """إنشاء مقاييس الأداء"""
        metrics_data = [
            {
                'name': 'حجم المبيعات الشهرية',
                'metric_type': 'sales_volume',
                'description': 'عدد القطع المباعة شهرياً',
                'unit': 'قطعة',
                'benchmark_value': 1000,
                'target_value': 1200,
                'is_higher_better': True
            },
            {
                'name': 'قيمة المبيعات الشهرية',
                'metric_type': 'sales_value',
                'description': 'القيمة النقدية للمبيعات شهرياً',
                'unit': '{% currency_symbol %}',
                'benchmark_value': 50000,
                'target_value': 60000,
                'is_higher_better': True
            },
            {
                'name': 'كمية الإنتاج اليومية',
                'metric_type': 'production_quantity',
                'description': 'عدد القطع المنتجة يومياً',
                'unit': 'قطعة',
                'benchmark_value': 100,
                'target_value': 120,
                'is_higher_better': True
            },
            {
                'name': 'معدل الجودة',
                'metric_type': 'quality_rate',
                'description': 'نسبة القطع المقبولة من إجمالي الإنتاج',
                'unit': '%',
                'benchmark_value': 95,
                'target_value': 98,
                'is_higher_better': True
            },
            {
                'name': 'معدل الحضور',
                'metric_type': 'attendance_rate',
                'description': 'نسبة أيام الحضور الفعلي',
                'unit': '%',
                'benchmark_value': 90,
                'target_value': 95,
                'is_higher_better': True
            },
            {
                'name': 'رضا العملاء',
                'metric_type': 'customer_satisfaction',
                'description': 'درجة رضا العملاء من 10',
                'unit': 'درجة',
                'benchmark_value': 8.0,
                'target_value': 9.0,
                'is_higher_better': True
            },
            {
                'name': 'كفاءة التكلفة',
                'metric_type': 'cost_efficiency',
                'description': 'نسبة توفير التكاليف',
                'unit': '%',
                'benchmark_value': 5,
                'target_value': 10,
                'is_higher_better': True
            },
            {
                'name': 'وقت التسليم',
                'metric_type': 'delivery_time',
                'description': 'متوسط وقت التسليم بالأيام',
                'unit': 'يوم',
                'benchmark_value': 7,
                'target_value': 5,
                'is_higher_better': False
            }
        ]
        
        for metric_data in metrics_data:
            metric, created = PerformanceMetric.objects.get_or_create(
                name=metric_data['name'],
                defaults=metric_data
            )
            if created:
                self.stdout.write(f'- تم إنشاء مقياس الأداء: {metric.name}')
    
    def create_individual_targets(self):
        """إنشاء أهداف فردية للموظفين"""
        employees = Employee.objects.filter(status='active')[:10]
        categories = TargetCategory.objects.all()
        
        if not employees.exists():
            self.stdout.write(self.style.WARNING('لا توجد موظفين نشطين لإنشاء أهداف'))
            return
        
        # إنشاء مستخدم admin للإسناد
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            admin_user = User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
        
        targets_data = [
            {
                'title': 'تحقيق مبيعات شهرية {{ 50,000|currency_format }}',
                'description': 'تحقيق إيرادات مبيعات شهرية بقيمة 50 ألف ج.م من المراتب والمفروشات',
                'target_period': 'monthly',
                'target_type': 'amount',
                'target_value': 50000,
                'unit': '{% currency_symbol %}',
                'priority': 'high',
                'min_acceptable': 40000,
                'excellence_threshold': 60000,
                'reward_amount': 2000,
                'category_type': 'sales'
            },
            {
                'title': 'إنتاج 1000 قطعة مراتب شهرياً',
                'description': 'إنتاج 1000 قطعة مراتب مختلفة الأحجام بجودة عالية خلال الشهر',
                'target_period': 'monthly',
                'target_type': 'quantity',
                'target_value': 1000,
                'unit': 'قطعة',
                'priority': 'high',
                'min_acceptable': 800,
                'excellence_threshold': 1200,
                'reward_amount': 1500,
                'category_type': 'production'
            },
            {
                'title': 'تحقيق معدل جودة 98%',
                'description': 'الحفاظ على معدل جودة 98% في فحص المنتجات النهائية',
                'target_period': 'monthly',
                'target_type': 'percentage',
                'target_value': 98,
                'unit': '%',
                'priority': 'critical',
                'min_acceptable': 95,
                'excellence_threshold': 99,
                'reward_amount': 1000,
                'category_type': 'quality'
            },
            {
                'title': 'معدل حضور 95%',
                'description': 'الحفاظ على معدل حضور 95% أو أكثر خلال الشهر',
                'target_period': 'monthly',
                'target_type': 'percentage',
                'target_value': 95,
                'unit': '%',
                'priority': 'medium',
                'min_acceptable': 90,
                'excellence_threshold': 100,
                'reward_amount': 500,
                'category_type': 'attendance'
            },
            {
                'title': 'رضا العملاء 9/10',
                'description': 'تحقيق درجة رضا عملاء 9 من 10 في استطلاعات الرضا الشهرية',
                'target_period': 'monthly',
                'target_type': 'score',
                'target_value': 9,
                'unit': 'درجة',
                'priority': 'high',
                'min_acceptable': 8,
                'excellence_threshold': 9.5,
                'reward_amount': 800,
                'category_type': 'customer_service'
            },
            {
                'title': 'توفير 10% من التكاليف',
                'description': 'تحقيق وفورات بنسبة 10% من التكاليف التشغيلية الشهرية',
                'target_period': 'monthly',
                'target_type': 'percentage',
                'target_value': 10,
                'unit': '%',
                'priority': 'medium',
                'min_acceptable': 5,
                'excellence_threshold': 15,
                'reward_amount': 1200,
                'category_type': 'cost_reduction'
            },
            {
                'title': 'إكمال 40 ساعة تدريب',
                'description': 'إكمال 40 ساعة تدريبية في المهارات المهنية والتطوير الذاتي',
                'target_period': 'quarterly',
                'target_type': 'time',
                'target_value': 40,
                'unit': 'ساعة',
                'priority': 'low',
                'min_acceptable': 30,
                'excellence_threshold': 50,
                'reward_amount': 600,
                'category_type': 'training'
            },
            {
                'title': 'صفر حوادث سلامة',
                'description': 'تحقيق صفر حوادث سلامة مهنية خلال الربع',
                'target_period': 'quarterly',
                'target_type': 'quantity',
                'target_value': 0,
                'unit': 'حادثة',
                'priority': 'critical',
                'min_acceptable': 0,
                'excellence_threshold': 0,
                'reward_amount': 2000,
                'category_type': 'safety'
            }
        ]
        
        for i, employee in enumerate(employees):
            if i < len(targets_data):
                target_data = targets_data[i]
                
                # البحث عن الفئة المناسبة
                category = categories.filter(category_type=target_data['category_type']).first()
                if not category:
                    continue
                
                # تحديد التواريخ
                start_date = date.today()
                if target_data['target_period'] == 'monthly':
                    end_date = start_date + timedelta(days=30)
                elif target_data['target_period'] == 'quarterly':
                    end_date = start_date + timedelta(days=90)
                else:
                    end_date = start_date + timedelta(days=7)
                
                # القيمة الحالية (تقدم عشوائي)
                current_value = target_data['target_value'] * random.uniform(0.1, 0.8)
                
                target = PerformanceTarget.objects.create(
                    employee=employee,
                    category=category,
                    title=target_data['title'],
                    description=target_data['description'],
                    target_period=target_data['target_period'],
                    target_type=target_data['target_type'],
                    target_value=target_data['target_value'],
                    current_value=current_value,
                    unit=target_data['unit'],
                    start_date=start_date,
                    end_date=end_date,
                    priority=target_data['priority'],
                    min_acceptable=target_data.get('min_acceptable'),
                    excellence_threshold=target_data.get('excellence_threshold'),
                    reward_amount=target_data['reward_amount'],
                    status='active',
                    assigned_by=admin_user
                )
                
                self.stdout.write(f'- تم إنشاء هدف: {target.title} للموظف {employee.arabic_name}')
    
    def create_team_targets(self):
        """إنشاء أهداف الفرق"""
        departments = Department.objects.filter(is_active=True)[:3]
        categories = TargetCategory.objects.all()
        
        if not departments.exists():
            self.stdout.write(self.style.WARNING('لا توجد أقسام لإنشاء أهداف الفرق'))
            return
        
        team_targets_data = [
            {
                'team_name': 'فريق الإنتاج الأول',
                'title': 'إنتاج 5000 قطعة مراتب شهرياً',
                'description': 'إنتاج 5000 قطعة مراتب مختلفة الأحجام للفريق كاملاً',
                'target_value': 5000,
                'unit': 'قطعة',
                'category_type': 'production'
            },
            {
                'team_name': 'فريق المبيعات',
                'title': 'تحقيق مبيعات {{ 200,000|currency_format }} شهرياً',
                'description': 'تحقيق إيرادات إجمالية 200 ألف ج.م لفريق المبيعات',
                'target_value': 200000,
                'unit': '{% currency_symbol %}',
                'category_type': 'sales'
            },
            {
                'team_name': 'فريق الجودة',
                'title': 'تحقيق معدل جودة 99%',
                'description': 'الحفاظ على معدل جودة 99% في جميع منتجات القسم',
                'target_value': 99,
                'unit': '%',
                'category_type': 'quality'
            }
        ]
        
        for i, department in enumerate(departments):
            if i < len(team_targets_data):
                team_data = team_targets_data[i]
                
                category = categories.filter(category_type=team_data['category_type']).first()
                if not category:
                    continue
                
                start_date = date.today()
                end_date = start_date + timedelta(days=30)
                current_value = team_data['target_value'] * random.uniform(0.2, 0.7)
                
                team_target = TeamTarget.objects.create(
                    team_name=team_data['team_name'],
                    department=department,
                    category=category,
                    title=team_data['title'],
                    description=team_data['description'],
                    target_value=team_data['target_value'],
                    current_value=current_value,
                    unit=team_data['unit'],
                    start_date=start_date,
                    end_date=end_date,
                    status='active'
                )
                
                self.stdout.write(f'- تم إنشاء هدف فريق: {team_target.title}')
    
    def create_metric_values(self):
        """إضافة قيم مقاييس الأداء للموظفين"""
        employees = Employee.objects.filter(status='active')[:5]
        metrics = PerformanceMetric.objects.all()

        if not employees.exists() or not metrics.exists():
            return

        admin_user = User.objects.filter(is_superuser=True).first()

        for employee in employees:
            for metric in metrics[:4]:  # أول 4 مقاييس فقط
                if metric.is_higher_better:
                    value = float(metric.benchmark_value) * random.uniform(0.8, 1.2)
                else:
                    value = float(metric.benchmark_value) * random.uniform(0.8, 1.2)

                period_start = date.today().replace(day=1)
                period_end = date.today()

                EmployeeMetricValue.objects.get_or_create(
                    employee=employee,
                    metric=metric,
                    period_start=period_start,
                    period_end=period_end,
                    defaults={
                        'value': round(value, 2),
                        'notes': f'قيمة تجريبية لـ {metric.name}',
                        'recorded_by': admin_user
                    }
                )

        self.stdout.write('- تم إضافة قيم مقاييس الأداء للموظفين')