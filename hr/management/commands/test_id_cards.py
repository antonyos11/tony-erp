"""
اختبار نظام بطاقات التعريف
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from datetime import date, timedelta
import os

from hr.models import Employee, Department, JobPosition, EmployeeIDCard
from hr.services.id_card_service import IDCardService

User = get_user_model()

class Command(BaseCommand):
    help = 'اختبار نظام بطاقات التعريف'
    
    def handle(self, *args, **options):
        self.stdout.write("="*80)
        self.stdout.write(self.style.SUCCESS("🔍 اختبار نظام بطاقات التعريف"))
        self.stdout.write("="*80)
        
        # 1. التحقق من وجود موظفين
        self.stdout.write("\n✅ 1. التحقق من الموظفين...")
        employees = Employee.objects.filter(status='active')
        self.stdout.write(f"   عدد الموظفين النشطين: {employees.count()}")
        
        if not employees.exists():
            self.stdout.write(self.style.WARNING("   ⚠️  لا يوجد موظفين! إنشاء موظف تجريبي..."))
            dept, _ = Department.objects.get_or_create(
                code='TEST',
                defaults={'name': 'قسم الاختبار'}
            )
            pos, _ = JobPosition.objects.get_or_create(
                code='TEST-EMP',
                defaults={
                    'title': 'موظف اختبار',
                    'department': dept
                }
            )
            
            employee = Employee.objects.create(
                employee_id='TEST001',
                first_name='Test',
                last_name='Employee',
                arabic_name='موظف اختبار',
                department=dept,
                position=pos,
                hire_date=date.today(),
                status='active',
                basic_salary=5000
            )
            self.stdout.write(self.style.SUCCESS(f"   ✅ تم إنشاء موظف: {employee.arabic_name}"))
        else:
            employee = employees.first()
            self.stdout.write(self.style.SUCCESS(f"   ✅ سيتم الاختبار مع: {employee.arabic_name}"))
        
        # 2. إنشاء بطاقة تعريف
        self.stdout.write("\n✅ 2. إنشاء بطاقة تعريف...")
        
        # حذف البطاقات القديمة للاختبار
        old_cards = EmployeeIDCard.objects.filter(employee=employee, card_number__startswith='TEST')
        if old_cards.exists():
            count = old_cards.count()
            old_cards.delete()
            self.stdout.write(f"   🗑️  تم حذف {count} بطاقة قديمة")
        
        year = date.today().year
        count = EmployeeIDCard.objects.filter(issue_date__year=year).count() + 1
        card_number = f"TEST{year}{count:04d}"
        
        card = EmployeeIDCard.objects.create(
            employee=employee,
            card_number=card_number,
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=365),
            status='active',
            qr_data=f'{{"card_number": "{card_number}", "employee_id": "{employee.employee_id}"}}'
        )
        self.stdout.write(self.style.SUCCESS(f"   ✅ تم إنشاء بطاقة: {card.card_number}"))
        self.stdout.write(f"   تاريخ الإصدار: {card.issue_date}")
        self.stdout.write(f"   تاريخ الانتهاء: {card.expiry_date}")
        
        # 3. اختبار صلاحية البطاقة
        self.stdout.write("\n✅ 3. اختبار صلاحية البطاقة...")
        is_valid = card.is_valid()
        self.stdout.write(f"   البطاقة صالحة: {'نعم ✅' if is_valid else 'لا ❌'}")
        
        # 4. اختبار توليد PDF
        self.stdout.write("\n✅ 4. اختبار توليد PDF...")
        try:
            service = IDCardService(employee, card)
            
            # إنشاء مجلد temp
            from django.conf import settings
            temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp', 'test_id_cards')
            os.makedirs(temp_dir, exist_ok=True)
            
            # توليد PDF
            pdf_path = os.path.join(temp_dir, f'test_card_{card.card_number}.pdf')
            service.generate_pdf(pdf_path)
            
            if os.path.exists(pdf_path):
                file_size = os.path.getsize(pdf_path)
                self.stdout.write(self.style.SUCCESS("   ✅ تم توليد PDF بنجاح"))
                self.stdout.write(f"   المسار: {pdf_path}")
                self.stdout.write(f"   الحجم: {file_size:,} بايت")
            else:
                self.stdout.write(self.style.ERROR("   ❌ فشل توليد PDF"))
                return
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ خطأ في توليد PDF: {str(e)}"))
            import traceback
            traceback.print_exc()
            return
        
        # 5. اختبار عداد الطباعة
        self.stdout.write("\n✅ 5. اختبار عداد الطباعة...")
        initial_count = card.print_count
        card.increment_print_count()
        card.refresh_from_db()
        self.stdout.write(f"   العداد قبل: {initial_count}")
        self.stdout.write(f"   العداد بعد: {card.print_count}")
        
        if card.print_count == initial_count + 1:
            self.stdout.write(self.style.SUCCESS("   ✅ العداد يعمل بشكل صحيح"))
        else:
            self.stdout.write(self.style.ERROR("   ❌ خطأ في عداد الطباعة"))
        
        # 6. اختبار عداد المسح
        self.stdout.write("\n✅ 6. اختبار عداد المسح...")
        initial_scan = card.scan_count
        card.increment_scan_count()
        card.refresh_from_db()
        self.stdout.write(f"   عدد المسحات قبل: {initial_scan}")
        self.stdout.write(f"   عدد المسحات بعد: {card.scan_count}")
        
        if card.scan_count == initial_scan + 1:
            self.stdout.write(self.style.SUCCESS("   ✅ عداد المسح يعمل بشكل صحيح"))
        else:
            self.stdout.write(self.style.ERROR("   ❌ خطأ في عداد المسح"))
        
        # 7. إحصائيات
        self.stdout.write("\n✅ 7. إحصائيات عامة...")
        total_cards = EmployeeIDCard.objects.count()
        active_cards = EmployeeIDCard.objects.filter(status='active').count()
        
        self.stdout.write(f"   إجمالي البطاقات: {total_cards}")
        self.stdout.write(f"   البطاقات الفعالة: {active_cards}")
        
        # 8. اختبار URLs
        self.stdout.write("\n✅ 8. التحقق من URLs...")
        from django.urls import reverse
        
        try:
            urls = {
                'قائمة البطاقات': reverse('hr:employee_id_cards_list'),
                'إنشاء بطاقة': reverse('hr:id_card_create', args=[employee.id]),
                'معاينة': reverse('hr:id_card_preview', args=[card.id]),
                'طباعة PDF': reverse('hr:id_card_print_pdf', args=[card.id]),
            }
            
            for name, url in urls.items():
                self.stdout.write(f"   ✅ {name}: {url}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ خطأ في URLs: {str(e)}"))
        
        self.stdout.write("\n" + "="*80)
        self.stdout.write(self.style.SUCCESS("🎉 اكتمل اختبار نظام بطاقات التعريف بنجاح!"))
        self.stdout.write("="*80)

