from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum, Count, Q, Avg, F, Max, Min
from django.db.models.functions import TruncMonth
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from datetime import date, datetime, timedelta
from decimal import Decimal
import json
import os
from functools import wraps

from hr.models import (
    Employee, Department, JobPosition, AttendanceRecord, WorkSchedule,
    LeaveRequest, LeaveType, Payroll, PerformanceReview, TrainingProgram,
    TrainingEnrollment, JobVacancy, JobApplication, HRSettings,
    PerformanceTarget, TargetCategory, TargetProgress, TeamTarget,
    TeamTargetMembership, PerformanceMetric, EmployeeMetricValue,
    WeekendDay, PublicHoliday, EmployeeAbsence,
    AllowanceType, DeductionType, EmployeeAllowance, EmployeeDeduction, PayrollItem
)
from accounting.models import JournalEntry, JournalEntryItem
from hr.forms import (
    ComplaintForm, DisciplinaryActionForm, HSEIncidentForm,
    HSEInspectionForm, HSETrainingForm,
    LeaveRequestForm, PerformanceReviewQuickForm, TrainingProgramForm,
    JobVacancyForm, JobApplicationQuickForm, PerformanceTargetQuickForm,
    TeamTargetQuickForm, AttendanceRecordQuickForm
)

# إدارة الموظفين والأقسام والمناصب

# === إدارة الموظفين ===

@login_required
def employee_list(request):
    """قائمة الموظفين"""
    employees = Employee.objects.select_related('department', 'position').order_by('-hire_date', 'arabic_name')
    
    # فلترة
    department = request.GET.get('department')
    status = request.GET.get('status')
    employment_type = request.GET.get('employment_type')
    search = request.GET.get('search')
    
    if department:
        employees = employees.filter(department_id=department)
    if status:
        employees = employees.filter(status=status)
    if employment_type:
        employees = employees.filter(employment_type=employment_type)
    if search:
        employees = employees.filter(
            Q(arabic_name__icontains=search) |
            Q(employee_id__icontains=search) |
            Q(national_id__icontains=search) |
            Q(email__icontains=search)
        )
    
    # الترقيم
    paginator = Paginator(employees, 12)
    page_number = request.GET.get('page')
    employees = paginator.get_page(page_number)
    
    # إحصائيات
    total_employees = Employee.objects.count()
    active_employees = Employee.objects.filter(status='active').count()
    new_employees = Employee.objects.filter(
        hire_date__gte=date.today().replace(day=1)
    ).count()
    
    context = {
        'employees': employees,
        'departments': Department.objects.filter(is_active=True),
        'total_employees': total_employees,
        'active_employees': active_employees,
        'new_employees': new_employees,
    }
    return render(request, 'hr/employee_list.html', context)

@login_required
def employee_detail(request, pk):
    """تفاصيل الموظف"""
    employee = get_object_or_404(Employee, pk=pk)
    
    # إحصائيات الموظف
    recent_attendance = AttendanceRecord.objects.filter(
        employee=employee
    ).order_by('-date', '-time')[:10]
    
    leave_balance = {}
    for leave_type in LeaveType.objects.all():
        used_days = LeaveRequest.objects.filter(
            employee=employee,
            leave_type=leave_type,
            status='approved',
            start_date__year=date.today().year
        ).aggregate(total=Sum('days_requested'))['total'] or 0
        
        leave_balance[leave_type.name] = {
            'total': leave_type.days_per_year,
            'used': used_days,
            'remaining': leave_type.days_per_year - used_days
        }
    
    recent_payrolls = Payroll.objects.filter(
        employee=employee
    ).order_by('-period_start')[:6]
    
    context = {
        'employee': employee,
        'recent_attendance': recent_attendance,
        'leave_balance': leave_balance,
        'recent_payrolls': recent_payrolls,
    }
    return render(request, 'hr/employee_detail.html', context)

@login_required
def employee_create(request):
    """إنشاء موظف جديد"""
    User = get_user_model()

    if request.method == 'POST':
        try:
            # الحصول على البيانات الأساسية
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            arabic_name = request.POST.get('arabic_name', '').strip()
            
            # إذا لم يتم إدخال الاسم العربي، استخدم الاسم الإنجليزي
            if not arabic_name:
                arabic_name = f"{first_name} {last_name}".strip()
            
            # إذا لم يتم إدخال الاسم الإنجليزي، استخدم الاسم العربي
            if not first_name and not last_name:
                parts = arabic_name.split()
                first_name = parts[0] if parts else 'موظف'
                last_name = ' '.join(parts[1:]) if len(parts) > 1 else ''

            # إنشاء معرف الموظف
            employee_id = request.POST.get('employee_id', '').strip()
            if not employee_id:
                import random
                employee_id = f"EMP-{random.randint(10000, 99999)}"

            # البريد الإلكتروني
            email = request.POST.get('email', '').strip()
            if not email:
                email = f"{employee_id.lower().replace('-', '')}@company.local"

            # إنشاء حساب مستخدم
            username = email
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    password=__import__('secrets').token_urlsafe(16)  # مؤقتة مولّدة
                )

            # معالجة الجنس
            gender = request.POST.get('gender', '').lower()
            if gender in ['female', 'f', 'أنثى']:
                gender = 'F'
            else:
                gender = 'M'

            # معالجة التواريخ - birth_date مطلوب لذلك نضع تاريخ افتراضي
            birth_date_str = request.POST.get('birth_date', '').strip()
            if birth_date_str:
                birth_date = birth_date_str
            else:
                # تاريخ افتراضي (30 سنة من الآن)
                birth_date = date(date.today().year - 30, 1, 1)
            
            hire_date_str = request.POST.get('hire_date', '').strip()
            if hire_date_str:
                hire_date = hire_date_str
            else:
                hire_date = date.today()

            # معالجة الحالة الاجتماعية
            marital_status = request.POST.get('marital_status') or 'single'

            # معالجة الرواتب والبدلات
            try:
                basic_salary = Decimal(request.POST.get('basic_salary') or '0')
            except:
                basic_salary = Decimal('0')
            
            try:
                housing_allowance = Decimal(request.POST.get('housing_allowance') or '0')
            except:
                housing_allowance = Decimal('0')
            
            try:
                transportation_allowance = Decimal(request.POST.get('transportation_allowance') or '0')
            except:
                transportation_allowance = Decimal('0')

            # معالجة القسم والمنصب - إنشاء افتراضي إذا لم يتم اختياره
            department_id = request.POST.get('department')
            position_id = request.POST.get('position')
            
            # الحصول على قسم افتراضي أو إنشاءه
            if not department_id:
                default_dept, _ = Department.objects.get_or_create(
                    code='GEN001',
                    defaults={'name': 'عام', 'description': 'قسم عام', 'is_active': True}
                )
                department_id = default_dept.id
            
            # الحصول على منصب افتراضي أو إنشاءه
            if not position_id:
                # جلب القسم للمنصب
                dept_for_pos = Department.objects.filter(id=department_id).first()
                default_pos, _ = JobPosition.objects.get_or_create(
                    code='EMP001',
                    defaults={'title': 'موظف', 'description': 'منصب عام', 'is_active': True, 'department': dept_for_pos}
                )
                position_id = default_pos.id

            # إنشاء الموظف - استخدام الحقول الموجودة في النموذج فقط
            employee = Employee.objects.create(
                employee_id=employee_id,
                user=user,
                first_name=first_name,
                last_name=last_name,
                arabic_name=arabic_name,
                national_id=request.POST.get('national_id') or employee_id,
                passport_number=request.POST.get('passport_number', ''),
                gender=gender,
                birth_date=birth_date,
                marital_status=marital_status,
                phone=request.POST.get('phone') or '---',
                email=email,
                address=request.POST.get('address') or '---',
                emergency_contact_name=request.POST.get('emergency_contact_name') or 'غير محدد',
                emergency_contact_phone=request.POST.get('emergency_contact_phone') or '---',
                department_id=department_id,
                position_id=position_id,
                hire_date=hire_date,
                termination_date=None,
                status=request.POST.get('status', 'active'),
                basic_salary=basic_salary,
                housing_allowance=housing_allowance,
                transportation_allowance=transportation_allowance,
                other_allowances=Decimal('0'),
                fingerprint_id=request.POST.get('fingerprint_id') or None,
                rfid_card_number=request.POST.get('rfid_card_number') or None,
                attendance_exempt=bool(request.POST.get('attendance_exempt')),
                bank_name=request.POST.get('bank_name', ''),
                bank_account_number=request.POST.get('bank_account', ''),
                iban=request.POST.get('iban', '')
            )
            
            # رفع الملفات
            if 'photo' in request.FILES:
                employee.photo = request.FILES['photo']
            if 'cv_file' in request.FILES:
                employee.cv_file = request.FILES['cv_file']
            if 'contract_file' in request.FILES:
                employee.contract_file = request.FILES['contract_file']
            
            employee.save()
            
            messages.success(request, f'✓ تم إضافة الموظف {arabic_name} بنجاح')
            return redirect('hr:employee_detail', pk=employee.pk)
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"خطأ في إنشاء الموظف: {error_details}")
            messages.error(request, f'حدث خطأ أثناء إضافة الموظف: {str(e)}')
    
    context = {
        'departments': Department.objects.filter(is_active=True),
        'positions': JobPosition.objects.filter(is_active=True),
        'managers': Employee.objects.filter(status='active'),
    }
    return render(request, 'hr/employee_form.html', context)

@login_required
def employee_edit(request, pk):
    """تعديل الموظف"""
    employee = get_object_or_404(Employee, pk=pk)
    
    if request.method == 'POST':
        try:
            # تحديث البيانات الأساسية
            employee.first_name = request.POST.get('first_name', employee.first_name)
            employee.last_name = request.POST.get('last_name', employee.last_name)
            employee.arabic_name = request.POST.get('arabic_name', employee.arabic_name)
            employee.employee_id = request.POST.get('employee_id', employee.employee_id)
            employee.national_id = request.POST.get('national_id', employee.national_id)
            employee.passport_number = request.POST.get('passport_number', employee.passport_number)
            employee.email = request.POST.get('email', employee.email)
            employee.phone = request.POST.get('phone', employee.phone)
            employee.address = request.POST.get('address', employee.address)
            
            # تحديث الجنس
            gender = request.POST.get('gender', '').lower()
            if gender in ['female', 'f', 'أنثى']:
                employee.gender = 'F'
            elif gender:
                employee.gender = 'M'
            
            # تحديث الحالة الاجتماعية
            if request.POST.get('marital_status'):
                employee.marital_status = request.POST.get('marital_status')
            
            # تحديث التواريخ
            if request.POST.get('birth_date'):
                employee.birth_date = request.POST.get('birth_date')
            if request.POST.get('hire_date'):
                employee.hire_date = request.POST.get('hire_date')
            
            # تحديث القسم والمنصب
            if request.POST.get('department'):
                employee.department_id = request.POST.get('department')
            if request.POST.get('position'):
                employee.position_id = request.POST.get('position')
            
            # تحديث الحالة الوظيفية
            if request.POST.get('status'):
                employee.status = request.POST.get('status')
            
            # تحديث الرواتب والبدلات
            if request.POST.get('basic_salary'):
                try:
                    employee.basic_salary = Decimal(request.POST.get('basic_salary'))
                except:
                    pass
            
            if request.POST.get('housing_allowance'):
                try:
                    employee.housing_allowance = Decimal(request.POST.get('housing_allowance'))
                except:
                    pass
            
            if request.POST.get('transportation_allowance'):
                try:
                    employee.transportation_allowance = Decimal(request.POST.get('transportation_allowance'))
                except:
                    pass
            
            # تحديث المعلومات البنكية
            employee.bank_name = request.POST.get('bank_name', employee.bank_name)
            employee.bank_account_number = request.POST.get('bank_account', employee.bank_account_number)
            employee.iban = request.POST.get('iban', employee.iban)
            
            # تحديث معلومات الحضور
            employee.fingerprint_id = request.POST.get('fingerprint_id', employee.fingerprint_id)
            employee.rfid_card_number = request.POST.get('rfid_card_number', employee.rfid_card_number)
            employee.attendance_exempt = bool(request.POST.get('attendance_exempt'))
            
            # تحديث معلومات الطوارئ
            employee.emergency_contact_name = request.POST.get('emergency_contact_name', employee.emergency_contact_name)
            employee.emergency_contact_phone = request.POST.get('emergency_contact_phone', employee.emergency_contact_phone)
            
            # تحديث الملفات
            if 'photo' in request.FILES:
                employee.photo = request.FILES['photo']
            if 'cv_file' in request.FILES:
                employee.cv_file = request.FILES['cv_file']
            if 'contract_file' in request.FILES:
                employee.contract_file = request.FILES['contract_file']
            
            employee.save()
            messages.success(request, f'✓ تم تحديث بيانات الموظف {employee.arabic_name} بنجاح')
            return redirect('hr:employee_detail', pk=employee.pk)
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"خطأ في تحديث الموظف: {error_details}")
            messages.error(request, f'حدث خطأ أثناء تحديث البيانات: {str(e)}')
    
    context = {
        'employee': employee,
        'form': {'first_name': {'value': employee.first_name},
                 'last_name': {'value': employee.last_name},
                 'arabic_name': {'value': employee.arabic_name},
                 'employee_id': {'value': employee.employee_id},
                 'national_id': {'value': employee.national_id},
                 'passport_number': {'value': employee.passport_number},
                 'gender': {'value': employee.gender},
                 'birth_date': {'value': employee.birth_date},
                 'marital_status': {'value': employee.marital_status},
                 'phone': {'value': employee.phone},
                 'email': {'value': employee.email},
                 'address': {'value': employee.address},
                 'hire_date': {'value': employee.hire_date},
                 'department': {'value': employee.department_id},
                 'position': {'value': employee.position_id},
                 'status': {'value': employee.status},
                 'basic_salary': {'value': employee.basic_salary},
                 'housing_allowance': {'value': employee.housing_allowance},
                 'transportation_allowance': {'value': employee.transportation_allowance},
                 'bank_name': {'value': employee.bank_name},
                 'bank_account': {'value': employee.bank_account_number},
                 'iban': {'value': employee.iban},
                 'fingerprint_id': {'value': employee.fingerprint_id},
                 'rfid_card_number': {'value': employee.rfid_card_number},
                 'attendance_exempt': {'value': employee.attendance_exempt},
                 'emergency_contact_name': {'value': employee.emergency_contact_name},
                 'emergency_contact_phone': {'value': employee.emergency_contact_phone},
                 'is_active': {'value': employee.status == 'active'}},
        'departments': Department.objects.filter(is_active=True),
        'positions': JobPosition.objects.filter(is_active=True),
        'managers': Employee.objects.filter(status='active').exclude(pk=employee.pk),
    }
    return render(request, 'hr/employee_form.html', context)

@login_required
def employee_delete(request, pk):
    """حذف الموظف"""
    employee = get_object_or_404(Employee, pk=pk)
    
    if request.method == 'POST':
        employee_name = employee.arabic_name
        employee.delete()
        messages.success(request, f'تم حذف الموظف {employee_name} بنجاح')
        return redirect('hr:employee_list')
    
    return redirect('hr:employee_detail', pk=pk)

@login_required
def get_positions_by_department(request):
    """API للحصول على المناصب حسب القسم"""
    department_id = request.GET.get('department')
    if department_id:
        positions = JobPosition.objects.filter(
            department_id=department_id,
            is_active=True
        ).values('id', 'title')
        return JsonResponse(list(positions), safe=False)
    return JsonResponse([], safe=False)

# === إدارة الأقسام والمناصب ===

@login_required
def department_list(request):
    """قائمة الأقسام - توجيه للـ Admin"""
    from django.shortcuts import redirect
    messages.info(request, 'يمكنك إدارة الأقسام من لوحة الإدارة')
    return redirect('/admin/hr/department/')

@login_required
def department_create(request):
    """إنشاء قسم جديد - توجيه للـ Admin"""
    from django.shortcuts import redirect
    return redirect('/admin/hr/department/add/')

@login_required
def position_list(request):
    """قائمة المناصب - توجيه للـ Admin"""
    from django.shortcuts import redirect
    messages.info(request, 'يمكنك إدارة المناصب من لوحة الإدارة')
    return redirect('/admin/hr/jobposition/')

@login_required
def position_create(request):
    """إنشاء منصب جديد - توجيه للـ Admin"""
    from django.shortcuts import redirect
    return redirect('/admin/hr/jobposition/add/')


# === استيراد وتصدير الموظفين ===

@login_required
@permission_required('hr.add_employee', raise_exception=True)
def employee_import(request):
    """استيراد الموظفين من ملف CSV/Excel"""
    if request.method == 'POST':
        file = request.FILES.get('file')
        if not file:
            messages.error(request, 'الرجاء اختيار ملف')
            return redirect('hr:employee_import')

        file_ext = file.name.split('.')[-1].lower()

        try:
            if file_ext == 'csv':
                imported = _import_employees_csv(file)
            elif file_ext in ('xlsx', 'xls'):
                imported = _import_employees_excel(file)
            else:
                messages.error(request, 'صيغة الملف غير مدعومة. استخدم CSV أو Excel.')
                return redirect('hr:employee_import')

            messages.success(request, f'تم استيراد {imported} موظف بنجاح')
            return redirect('hr:employee_list')

        except Exception as e:
            messages.error(request, f'خطأ في الاستيراد: {str(e)}')
            return redirect('hr:employee_import')

    context = {
        'title': 'استيراد الموظفين',
        'sample_headers': [
            'رقم الموظف', 'الاسم الأول', 'اسم العائلة', 'الاسم بالعربية',
            'رقم الهوية', 'الهاتف', 'البريد الإلكتروني', 'القسم',
            'المنصب', 'تاريخ التعيين', 'الراتب الأساسي',
        ],
    }
    return render(request, 'hr/employee_import.html', context)


@transaction.atomic
def _import_employees_csv(file):
    """استيراد الموظفين من CSV"""
    import csv
    import io
    from hr.models import Employee, Department, JobPosition

    decoded_file = file.read().decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(decoded_file))
    count = 0
    User = get_user_model()

    for row in reader:
        # البحث عن أو إنشاء القسم
        dept = None
        dept_name = row.get('القسم', '').strip()
        if dept_name:
            dept, _ = Department.objects.get_or_create(name=dept_name)

        # البحث عن أو إنشاء المنصب
        position = None
        position_name = row.get('المنصب', '').strip()
        if position_name:
            position, _ = JobPosition.objects.get_or_create(
                title=position_name,
                defaults={'department': dept} if dept else {},
            )

        # إنشاء حساب مستخدم
        email = row.get('البريد الإلكتروني', '').strip()
        emp_id = row.get('رقم الموظف', f'EMP{count+1:04d}').strip()
        username = email.split('@')[0] if email else emp_id.lower()

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'first_name': row.get('الاسم الأول', '').strip(),
                'last_name': row.get('اسم العائلة', '').strip(),
            }
        )
        if created:
            user.set_password('changeme123')
            user.save()

        employee_data = {
            'employee_id': emp_id,
            'user': user,
            'first_name': row.get('الاسم الأول', '').strip() or 'غير محدد',
            'last_name': row.get('اسم العائلة', '').strip() or 'غير محدد',
            'arabic_name': row.get('الاسم بالعربية', '').strip() or f"{row.get('الاسم الأول', '')} {row.get('اسم العائلة', '')}".strip() or 'غير محدد',
            'national_id': row.get('رقم الهوية', f'ID{count+1:08d}').strip(),
            'gender': row.get('الجنس', 'M').strip()[:1] or 'M',
            'birth_date': row.get('تاريخ الميلاد') or '1990-01-01',
            'marital_status': 'single',
            'phone': row.get('الهاتف', '').strip() or '0000000000',
            'email': email or f'{username}@company.com',
            'address': row.get('العنوان', '').strip() or 'غير محدد',
            'emergency_contact_name': row.get('جهة اتصال الطوارئ', '').strip() or 'غير محدد',
            'emergency_contact_phone': row.get('هاتف الطوارئ', '').strip() or '0000000000',
            'hire_date': row.get('تاريخ التعيين') or date.today().isoformat(),
            'basic_salary': Decimal(row.get('الراتب الأساسي', '0').strip() or '0'),
        }

        if dept:
            employee_data['department'] = dept
        if position:
            employee_data['position'] = position

        Employee.objects.create(**employee_data)
        count += 1

    return count


def _import_employees_excel(file):
    """استيراد الموظفين من Excel"""
    try:
        import openpyxl
    except ImportError:
        raise Exception('مكتبة openpyxl غير مثبتة. شغّل: pip install openpyxl')

    wb = openpyxl.load_workbook(file)
    ws = wb.active

    headers = [cell.value for cell in ws[1] if cell.value]
    if not headers:
        raise Exception('الملف فارغ أو لا يحتوي على عناوين أعمدة')

    count = 0
    import io
    import csv

    # تحويل Excel -> CSV ثم استخدام نفس المنطق
    csv_buffer = io.StringIO()
    writer = csv.DictWriter(csv_buffer, fieldnames=headers)
    writer.writeheader()

    for row in ws.iter_rows(min_row=2, values_only=True):
        if not any(row):
            continue
        row_data = dict(zip(headers, row))
        # تحويل القيم None إلى string فارغ
        row_data = {k: str(v) if v is not None else '' for k, v in row_data.items()}
        writer.writerow(row_data)

    csv_buffer.seek(0)
    # إنشاء ملف وهمي
    from io import BytesIO
    fake_file = BytesIO(csv_buffer.getvalue().encode('utf-8-sig'))
    return _import_employees_csv(fake_file)


@login_required
def employee_export(request, format='csv'):
    """تصدير الموظفين"""
    from hr.models import Employee
    import csv

    employees = Employee.objects.select_related('department', 'position').filter(status='active')

    export_format = request.GET.get('format', format)

    if export_format == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = 'attachment; filename="employees.csv"'
        response.write('\ufeff')  # BOM for Excel Arabic support

        writer = csv.writer(response)
        writer.writerow([
            'رقم الموظف', 'الاسم الأول', 'اسم العائلة', 'الاسم بالعربية',
            'رقم الهوية', 'الهاتف', 'البريد الإلكتروني', 'القسم',
            'المنصب', 'تاريخ التعيين', 'الراتب الأساسي', 'الحالة',
        ])

        for emp in employees:
            writer.writerow([
                emp.employee_id,
                emp.first_name,
                emp.last_name,
                emp.arabic_name,
                emp.national_id,
                emp.phone,
                emp.email,
                emp.department.name if emp.department else '',
                emp.position.title if emp.position else '',
                emp.hire_date,
                emp.basic_salary,
                emp.get_status_display(),
            ])

        return response

    elif export_format == 'json':
        data = [{
            'employee_id': emp.employee_id,
            'first_name': emp.first_name,
            'last_name': emp.last_name,
            'arabic_name': emp.arabic_name,
            'phone': emp.phone,
            'email': emp.email,
            'department': emp.department.name if emp.department else None,
            'position': emp.position.title if emp.position else None,
            'hire_date': str(emp.hire_date) if emp.hire_date else None,
            'basic_salary': str(emp.basic_salary),
        } for emp in employees]
        return JsonResponse({'employees': data, 'count': len(data)})

    return HttpResponse('صيغة غير مدعومة', status=400)


# === نظام الحضور والانصراف ===
