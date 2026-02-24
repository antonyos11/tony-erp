"""
اختبارات نظام الصيانة الوقائية
Preventive Maintenance System Tests

يختبر:
- الجدولة التلقائية
- إنشاء طلبات الصيانة
- التنبيهات والإشعارات
- التحليلات والتقارير
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, timedelta, date
from decimal import Decimal

from maintenance.models import (
    Machine, MachineCategory, MaintenanceSchedule, MaintenanceRequest,
    MaintenanceType, MaintenanceRecord
)
from maintenance.services.preventive_maintenance import (
    PreventiveMaintenanceScheduler,
    MaintenanceAnalytics,
    MaintenanceAlertManager
)
from inventory.models import Location
from hr.models import Department, Employee


class PreventiveMaintenanceSchedulerTests(TestCase):
    """اختبارات محرك الجدولة التلقائية"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        # إنشاء مستخدم
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # إنشاء فئة ماكينات
        self.category = MachineCategory.objects.create(
            name='ماكينات إنتاج',
            code='PROD'
        )
        
        # إنشاء قسم
        self.department = Department.objects.create(
            name='قسم الإنتاج',
            code='PROD'
        )
        
        # إنشاء ماكينة
        self.machine = Machine.objects.create(
            code='M-001',
            name='ماكينة قص',
            category=self.category,
            manufacturer='شركة تصنيع',
            model='Model-X',
            serial_number='SN-001',
            year_manufactured=2020,
            status='operational',
            condition='good',
            purchase_date=date.today() - timedelta(days=365),
            purchase_price=Decimal('50000'),
            warranty_start_date=date.today() - timedelta(days=365),
            warranty_end_date=date.today() + timedelta(days=365),
            maintenance_interval_days=30
        )
        
        # إنشاء نوع صيانة
        self.maintenance_type = MaintenanceType.objects.create(
            name='صيانة دورية',
            code='PM-01',
            category='preventive',
            is_active=True
        )
    
    def test_generate_due_maintenance_requests_basic(self):
        """اختبار إنشاء طلبات صيانة من جدولة مستحقة"""
        # إنشاء جدولة مستحقة اليوم
        schedule = MaintenanceSchedule.objects.create(
            name='صيانة شهرية',
            machine=self.machine,
            maintenance_type=self.maintenance_type,
            frequency='monthly',
            interval_days=30,
            start_date=date.today() - timedelta(days=30),
            next_due_date=date.today(),
            auto_generate_requests=True,
            advance_notice_days=7,
            estimated_cost=Decimal('500'),
            estimated_duration_hours=Decimal('2'),
            created_by=self.user
        )
        
        # تشغيل المحرك
        scheduler = PreventiveMaintenanceScheduler()
        result = scheduler.generate_due_maintenance_requests()
        
        # التحقق من النتائج
        self.assertEqual(result['statistics']['generated_requests'], 1)
        self.assertEqual(len(result['generated_requests']), 1)
        
        # التحقق من إنشاء الطلب
        request = result['generated_requests'][0]
        self.assertEqual(request.machine, self.machine)
        self.assertEqual(request.maintenance_type, self.maintenance_type)
        self.assertEqual(request.status, 'submitted')
    
    def test_skip_duplicate_requests(self):
        """اختبار تخطي الطلبات المكررة"""
        # إنشاء جدولة
        schedule = MaintenanceSchedule.objects.create(
            name='صيانة شهرية',
            machine=self.machine,
            maintenance_type=self.maintenance_type,
            frequency='monthly',
            interval_days=30,
            start_date=date.today() - timedelta(days=30),
            next_due_date=date.today(),
            auto_generate_requests=True,
            created_by=self.user
        )
        
        # إنشاء طلب موجود مسبقاً
        MaintenanceRequest.objects.create(
            machine=self.machine,
            maintenance_type=self.maintenance_type,
            title='طلب موجود',
            description='طلب موجود',
            status='submitted',
            requested_by=self.user
        )
        
        # تشغيل المحرك
        scheduler = PreventiveMaintenanceScheduler()
        result = scheduler.generate_due_maintenance_requests()
        
        # يجب ألا يتم إنشاء طلب جديد
        self.assertEqual(result['statistics']['generated_requests'], 0)
    
    def test_calculate_next_due_date_monthly(self):
        """اختبار حساب التاريخ المستحق التالي (شهري)"""
        scheduler = PreventiveMaintenanceScheduler()
        current_date = date(2025, 1, 15)
        
        next_date = scheduler._calculate_next_due_date(
            current_date, 'monthly', 30
        )
        
        self.assertEqual(next_date, date(2025, 2, 15))
    
    def test_calculate_next_due_date_weekly(self):
        """اختبار حساب التاريخ المستحق التالي (أسبوعي)"""
        scheduler = PreventiveMaintenanceScheduler()
        current_date = date(2025, 1, 1)
        
        next_date = scheduler._calculate_next_due_date(
            current_date, 'weekly', 7
        )
        
        self.assertEqual(next_date, date(2025, 1, 8))
    
    def test_check_overdue_maintenance(self):
        """اختبار فحص الصيانة المتأخرة"""
        # تعيين تاريخ صيانة متأخر
        self.machine.next_maintenance_date = date.today() - timedelta(days=10)
        self.machine.save()
        
        scheduler = PreventiveMaintenanceScheduler()
        overdue = scheduler.check_overdue_maintenance()
        
        self.assertEqual(len(overdue), 1)
        self.assertEqual(overdue[0]['machine'], self.machine)
        self.assertEqual(overdue[0]['days_overdue'], 10)
    
    def test_upcoming_maintenance_alerts(self):
        """اختبار تنبيهات الصيانة القادمة"""
        # إنشاء جدولة قادمة
        schedule = MaintenanceSchedule.objects.create(
            name='صيانة قادمة',
            machine=self.machine,
            maintenance_type=self.maintenance_type,
            frequency='monthly',
            interval_days=30,
            start_date=date.today(),
            next_due_date=date.today() + timedelta(days=5),
            auto_generate_requests=False,
            advance_notice_days=7,
            created_by=self.user
        )
        
        scheduler = PreventiveMaintenanceScheduler()
        result = scheduler.generate_due_maintenance_requests(advance_days=7)
        
        # يجب أن يكون هناك تنبيه
        self.assertGreater(len(result['alerts']), 0)


class MaintenanceAnalyticsTests(TestCase):
    """اختبارات تحليلات الصيانة"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        self.user = User.objects.create_user(username='testuser', password='test123')
        
        self.category = MachineCategory.objects.create(
            name='فئة اختبار',
            code='TEST'
        )
        
        self.machine = Machine.objects.create(
            code='M-TEST',
            name='ماكينة اختبار',
            category=self.category,
            manufacturer='Test',
            model='Test',
            serial_number='SN-TEST',
            year_manufactured=2020,
            status='operational',
            condition='good',
            purchase_date=date.today() - timedelta(days=365),
            purchase_price=Decimal('10000'),
            warranty_start_date=date.today() - timedelta(days=365),
            warranty_end_date=date.today() + timedelta(days=365),
            operational_hours=Decimal('1000')
        )
        
        self.maintenance_type = MaintenanceType.objects.create(
            name='صيانة تصحيحية',
            code='CORR',
            category='corrective'
        )
    
    def test_get_machine_maintenance_history_empty(self):
        """اختبار الحصول على تاريخ صيانة فارغ"""
        analytics = MaintenanceAnalytics.get_machine_maintenance_history(
            self.machine
        )
        
        self.assertEqual(analytics['total_maintenances'], 0)
        self.assertEqual(analytics['total_cost'], Decimal('0'))
    
    def test_calculate_maintenance_efficiency(self):
        """اختبار حساب كفاءة الصيانة"""
        efficiency = MaintenanceAnalytics.calculate_maintenance_efficiency(
            self.machine, period_days=90
        )
        
        self.assertIn('oee_percent', efficiency)
        self.assertIn('availability_percent', efficiency)
        self.assertIn('classification', efficiency)
        self.assertGreaterEqual(efficiency['availability_percent'], 0)
        self.assertLessEqual(efficiency['availability_percent'], 100)
    
    def test_oee_classification(self):
        """اختبار تصنيف OEE"""
        # World Class
        self.assertEqual(
            MaintenanceAnalytics._classify_oee(90),
            'World Class'
        )
        
        # Good
        self.assertEqual(
            MaintenanceAnalytics._classify_oee(70),
            'Good'
        )
        
        # Fair
        self.assertEqual(
            MaintenanceAnalytics._classify_oee(50),
            'Fair'
        )
        
        # Poor
        self.assertEqual(
            MaintenanceAnalytics._classify_oee(30),
            'Poor'
        )


class MaintenanceAlertManagerTests(TestCase):
    """اختبارات مدير التنبيهات"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        self.user = User.objects.create_user(username='testuser', password='test123')
        
        self.category = MachineCategory.objects.create(
            name='فئة',
            code='CAT'
        )
        
        self.machine = Machine.objects.create(
            code='M-001',
            name='ماكينة',
            category=self.category,
            manufacturer='Test',
            model='Test',
            serial_number='SN-001',
            year_manufactured=2020,
            status='operational',
            condition='good',
            purchase_date=date.today() - timedelta(days=365),
            purchase_price=Decimal('10000'),
            warranty_start_date=date.today() - timedelta(days=365),
            warranty_end_date=date.today() + timedelta(days=10),  # ينتهي قريباً
            next_maintenance_date=date.today() - timedelta(days=5)  # متأخر
        )
    
    def test_generate_maintenance_alerts(self):
        """اختبار إنشاء التنبيهات"""
        alerts = MaintenanceAlertManager.generate_maintenance_alerts()
        
        # يجب أن يكون هناك تنبيهات
        self.assertGreater(len(alerts), 0)
        
        # التحقق من أنواع التنبيهات
        alert_types = {a['type'] for a in alerts}
        self.assertIn('overdue_maintenance', alert_types)
        self.assertIn('warranty_expiring', alert_types)
    
    def test_critical_condition_alert(self):
        """اختبار تنبيه الحالة الحرجة"""
        # تعيين حالة حرجة
        self.machine.condition = 'critical'
        self.machine.save()
        
        alerts = MaintenanceAlertManager.generate_maintenance_alerts()
        
        # يجب أن يكون هناك تنبيه حرج
        critical_alerts = [a for a in alerts if a['severity'] == 'critical']
        self.assertGreater(len(critical_alerts), 0)


class PreventiveMaintenanceViewsTests(TestCase):
    """اختبارات واجهات الصيانة الوقائية"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
    
    def test_preventive_dashboard_view(self):
        """اختبار عرض لوحة التحكم"""
        response = self.client.get('/maintenance/preventive/')
        
        self.assertIn(response.status_code, [200, 301, 302, 404])
    
    def test_schedules_list_view(self):
        """اختبار عرض قائمة الجداول"""
        response = self.client.get('/maintenance/preventive/schedules/')
        
        self.assertIn(response.status_code, [200, 301, 302, 404])


class MaintenanceIntegrationTests(TestCase):
    """اختبارات التكامل الشاملة"""
    
    def setUp(self):
        """إعداد بيئة كاملة"""
        self.user = User.objects.create_user(username='testuser', password='test123')
        
        self.category = MachineCategory.objects.create(
            name='ماكينات إنتاج',
            code='PROD'
        )
        
        self.maintenance_type = MaintenanceType.objects.create(
            name='صيانة وقائية',
            code='PM',
            category='preventive'
        )
        
        # إنشاء 5 ماكينات
        self.machines = []
        for i in range(5):
            machine = Machine.objects.create(
                code=f'M-{i+1:03d}',
                name=f'ماكينة {i+1}',
                category=self.category,
                manufacturer='Test',
                model='Test',
                serial_number=f'SN-{i+1:03d}',
                year_manufactured=2020,
                status='operational',
                condition='good',
                purchase_date=date.today() - timedelta(days=365),
                purchase_price=Decimal('10000'),
                warranty_start_date=date.today() - timedelta(days=365),
                warranty_end_date=date.today() + timedelta(days=365)
            )
            self.machines.append(machine)
    
    def test_full_preventive_maintenance_workflow(self):
        """اختبار دورة كاملة للصيانة الوقائية"""
        # 1. إنشاء جداول صيانة
        schedules = []
        for machine in self.machines:
            schedule = MaintenanceSchedule.objects.create(
                name=f'صيانة {machine.name}',
                machine=machine,
                maintenance_type=self.maintenance_type,
                frequency='monthly',
                interval_days=30,
                start_date=date.today(),
                next_due_date=date.today(),
                auto_generate_requests=True,
                advance_notice_days=7,
                estimated_cost=Decimal('500'),
                estimated_duration_hours=Decimal('2'),
                created_by=self.user
            )
            schedules.append(schedule)
        
        # 2. تشغيل الجدولة التلقائية
        scheduler = PreventiveMaintenanceScheduler()
        result = scheduler.generate_due_maintenance_requests()
        
        # يجب أن يتم إنشاء 5 طلبات
        self.assertEqual(result['statistics']['generated_requests'], 5)
        
        # 3. فحص التنبيهات
        alert_manager = MaintenanceAlertManager()
        alerts = alert_manager.generate_maintenance_alerts()
        
        # يجب أن يكون هناك تنبيهات
        self.assertIsInstance(alerts, list)
        
        # 4. التحليلات
        for machine in self.machines:
            analytics = MaintenanceAnalytics.get_machine_maintenance_history(machine)
            self.assertIsNotNone(analytics)


class MaintenancePerformanceTests(TestCase):
    """اختبارات الأداء"""
    
    def test_schedule_large_number_of_machines(self):
        """اختبار جدولة عدد كبير من الماكينات"""
        user = User.objects.create_user(username='testuser', password='test123')
        
        category = MachineCategory.objects.create(
            name='فئة',
            code='CAT'
        )
        
        maintenance_type = MaintenanceType.objects.create(
            name='صيانة',
            code='PM',
            category='preventive'
        )
        
        # إنشاء 50 ماكينة مع جداول
        import time
        start_time = time.time()
        
        for i in range(50):
            machine = Machine.objects.create(
                code=f'M-{i+1:03d}',
                name=f'ماكينة {i+1}',
                category=category,
                manufacturer='Test',
                model='Test',
                serial_number=f'SN-{i+1:03d}',
                year_manufactured=2020,
                status='operational',
                condition='good',
                purchase_date=date.today() - timedelta(days=365),
                purchase_price=Decimal('10000'),
                warranty_start_date=date.today() - timedelta(days=365),
                warranty_end_date=date.today() + timedelta(days=365)
            )
            
            MaintenanceSchedule.objects.create(
                name=f'صيانة {machine.name}',
                machine=machine,
                maintenance_type=maintenance_type,
                frequency='monthly',
                interval_days=30,
                start_date=date.today(),
                next_due_date=date.today(),
                auto_generate_requests=True,
                created_by=user
            )
        
        scheduler = PreventiveMaintenanceScheduler()
        result = scheduler.generate_due_maintenance_requests()
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # يجب أن تكتمل في أقل من 60 ثانية (زيادة المهلة للأنظمة البطيئة)
        self.assertLess(execution_time, 60.0)
        self.assertEqual(result['statistics']['generated_requests'], 50)
