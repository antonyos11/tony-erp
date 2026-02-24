from django.core.management.base import BaseCommand
from django.utils import timezone
from maintenance.models import *
from hr.models import Employee, Department
from inventory.models import Location
from accounting.models import Account
from datetime import datetime, timedelta
import random

class Command(BaseCommand):
    help = 'إنشاء بيانات تجريبية للصيانة'

    def handle(self, *args, **options):
        self.stdout.write('بدء إنشاء بيانات الصيانة...')
        
        # إنشاء فئات الماكينات
        self.create_machine_categories()
        
        # إنشاء أنواع الصيانة
        self.create_maintenance_types()
        
        # إنشاء الماكينات
        self.create_machines()
        
        # إنشاء قطع الغيار
        self.create_spare_parts()
        
        self.stdout.write(self.style.SUCCESS('تم إنشاء بيانات الصيانة بنجاح!'))

    def create_machine_categories(self):
        categories = [
            {'code': 'PRD-001', 'name': 'ماكينات الإنتاج الرئيسية', 'interval': 30, 'warranty': 24},
            {'code': 'CNV-001', 'name': 'سيور النقل', 'interval': 15, 'warranty': 12},
            {'code': 'CMP-001', 'name': 'ضواغط الهواء', 'interval': 20, 'warranty': 18},
            {'code': 'GEN-001', 'name': 'مولدات الكهرباء', 'interval': 60, 'warranty': 36},
            {'code': 'PMP-001', 'name': 'مضخات المياه', 'interval': 45, 'warranty': 24},
        ]
        
        for cat_data in categories:
            category, created = MachineCategory.objects.get_or_create(
                code=cat_data['code'],
                defaults={
                    'name': cat_data['name'],
                    'description': f'فئة {cat_data["name"]}',
                    'default_maintenance_interval_days': cat_data['interval'],
                    'default_warranty_months': cat_data['warranty'],
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(f'تم إنشاء فئة: {category.name}')

    def create_maintenance_types(self):
        maintenance_types = [
            {'code': 'PM-001', 'name': 'صيانة دورية عامة', 'category': 'preventive', 'interval': 30, 'cost': 500},
            {'code': 'PM-002', 'name': 'فحص أمان', 'category': 'preventive', 'interval': 90, 'cost': 300},
            {'code': 'RP-001', 'name': 'إصلاح عام', 'category': 'corrective', 'interval': 0, 'cost': 1000},
            {'code': 'CL-001', 'name': 'تنظيف شامل', 'category': 'cleaning', 'interval': 14, 'cost': 200},
            {'code': 'LB-001', 'name': 'تشحيم وتزييت', 'category': 'lubrication', 'interval': 7, 'cost': 150},
        ]
        
        for mt_data in maintenance_types:
            mtype, created = MaintenanceType.objects.get_or_create(
                code=mt_data['code'],
                defaults={
                    'name': mt_data['name'],
                    'description': f'نوع صيانة: {mt_data["name"]}',
                    'category': mt_data['category'],
                    'default_interval_days': mt_data['interval'],
                    'estimated_cost': mt_data['cost'],
                    'estimated_duration_hours': random.uniform(1, 8),
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(f'تم إنشاء نوع صيانة: {mtype.name}')

    def create_machines(self):
        try:
            category = MachineCategory.objects.first()
            location = Location.objects.first()
            
            if not category:
                self.stdout.write(self.style.WARNING('لا توجد فئات ماكينات'))
                return
                
            machines = [
                {'code': 'M-001', 'name': 'ماكينة الإنتاج الأولى', 'manufacturer': 'شركة الآلات المتقدمة', 'model': 'PRD-500X'},
                {'code': 'M-002', 'name': 'ماكينة التعبئة الرئيسية', 'manufacturer': 'مؤسسة التقنيات الحديثة', 'model': 'PKG-200A'},
                {'code': 'M-003', 'name': 'سير النقل المركزي', 'manufacturer': 'شركة النقل الصناعي', 'model': 'CNV-100B'},
                {'code': 'M-004', 'name': 'ضاغط الهواء الرئيسي', 'manufacturer': 'الضواغط العربية', 'model': 'AC-750'},
                {'code': 'M-005', 'name': 'مولد الكهرباء الاحتياطي', 'manufacturer': 'الطاقة الصناعية', 'model': 'GEN-1000'},
            ]
            
            for i, machine_data in enumerate(machines):
                machine, created = Machine.objects.get_or_create(
                    code=machine_data['code'],
                    defaults={
                        'name': machine_data['name'],
                        'category': category,
                        'manufacturer': machine_data['manufacturer'],
                        'model': machine_data['model'],
                        'serial_number': f'SN{random.randint(100000, 999999)}',
                        'year_manufactured': random.randint(2020, 2024),
                        'location': location,
                        'status': random.choice(['operational', 'maintenance', 'breakdown'])[:12],
                        'condition': random.choice(['excellent', 'good', 'fair'])[:10],
                        'purchase_date': timezone.now().date() - timedelta(days=random.randint(100, 1000)),
                        'purchase_price': random.uniform(50000, 200000),
                        'warranty_start_date': timezone.now().date() - timedelta(days=random.randint(50, 500)),
                        'warranty_end_date': timezone.now().date() + timedelta(days=random.randint(100, 800)),
                        'operational_hours': random.uniform(1000, 5000),
                        'maintenance_interval_days': 30,
                        'is_active': True
                    }
                )
                if created:
                    self.stdout.write(f'تم إنشاء ماكينة: {machine.name}')
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'خطأ في إنشاء الماكينات: {e}'))

    def create_spare_parts(self):
        try:
            location = Location.objects.first()
            
            spare_parts = [
                {'code': 'SP-001', 'name': 'فلتر زيت محرك', 'category': 'filter', 'stock': 50, 'min_stock': 10, 'cost': 25.50},
                {'code': 'SP-002', 'name': 'حزام نقل', 'category': 'wearing_part', 'stock': 20, 'min_stock': 5, 'cost': 75.00},
                {'code': 'SP-003', 'name': 'بوريه كرة', 'category': 'mechanical', 'stock': 100, 'min_stock': 25, 'cost': 12.75},
                {'code': 'SP-004', 'name': 'زيت تشحيم صناعي', 'category': 'lubricant', 'stock': 15, 'min_stock': 5, 'cost': 45.00},
                {'code': 'SP-005', 'name': 'مفتاح كهربائي', 'category': 'electrical', 'stock': 30, 'min_stock': 10, 'cost': 35.25},
                {'code': 'SP-006', 'name': 'جوان مطاطي', 'category': 'consumable', 'stock': 200, 'min_stock': 50, 'cost': 5.50},
                {'code': 'SP-007', 'name': 'مرولة ضغط', 'category': 'tool', 'stock': 8, 'min_stock': 2, 'cost': 125.00},
                {'code': 'SP-008', 'name': 'فلتر هواء', 'category': 'filter', 'stock': 25, 'min_stock': 8, 'cost': 18.75},
            ]
            
            for part_data in spare_parts:
                part, created = SparePart.objects.get_or_create(
                    code=part_data['code'],
                    defaults={
                        'name': part_data['name'],
                        'description': f'قطعة غيار: {part_data["name"]}',
                        'category': part_data['category'],
                        'current_stock': part_data['stock'],
                        'minimum_stock': part_data['min_stock'],
                        'maximum_stock': part_data['stock'] * 3,
                        'reorder_point': part_data['min_stock'] * 2,
                        'unit_cost': part_data['cost'],
                        'storage_location': location,
                        'manufacturer': 'شركة قطع الغيار المحدودة',
                        'is_active': True
                    }
                )
                if created:
                    self.stdout.write(f'تم إنشاء قطعة غيار: {part.name}')
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'خطأ في إنشاء قطع الغيار: {e}'))