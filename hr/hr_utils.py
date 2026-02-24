"""
دوال مساعدة للموارد البشرية
معالجة الإجازات، الغياب، وبطاقات الهوية
"""

import jwt
import qrcode
from io import BytesIO
from PIL import Image
from django.conf import settings
from django.utils import timezone
from datetime import timedelta, datetime
from django.contrib.auth.models import User


def generate_employee_qr_login(employee, expiry_days=365):
    """
    توليد QR Code لتسجيل دخول الموظف
    
    Args:
        employee: كائن Employee
        expiry_days: عدد أيام صلاحية التوكن
    
    Returns:
        tuple: (qr_code_data_string, qr_code_image_buffer)
    """
    from .models import EmployeeIDCard
    
    # إنشاء JWT token
    payload = {
        'user_id': employee.user.id if employee.user else None,
        'employee_id': employee.id,
        'username': employee.user.username if employee.user else None,
        'exp': datetime.utcnow() + timedelta(days=expiry_days),
        'iat': datetime.utcnow(),
        'type': 'employee_qr_login'
    }
    
    # توقيع التوكن
    secret = getattr(settings, 'SECRET_KEY', 'default-secret-key')
    token = jwt.encode(payload, secret, algorithm='HS256')
    
    # إنشاء QR Code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(token)
    qr.make(fit=True)
    
    # توليد صورة QR
    img = qr.make_image(fill_color="black", back_color="white")
    
    # حفظ في buffer
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    return token, buffer


def verify_qr_login_token(token):
    """
    التحقق من صحة QR Code token
    
    Args:
        token: JWT token من QR Code
    
    Returns:
        tuple: (success, user_or_error_message)
    """
    try:
        secret = getattr(settings, 'SECRET_KEY', 'default-secret-key')
        payload = jwt.decode(token, secret, algorithms=['HS256'])
        
        # فحص نوع التوكن
        if payload.get('type') != 'employee_qr_login':
            return False, "نوع توكن غير صحيح"
        
        # الحصول على المستخدم
        user_id = payload.get('user_id')
        if not user_id:
            return False, "معرف المستخدم غير موجود"
        
        user = User.objects.get(id=user_id)
        
        if not user.is_active:
            return False, "الحساب غير نشط"
        
        return True, user
    
    except jwt.ExpiredSignatureError:
        return False, "انتهت صلاحية QR Code"
    except jwt.InvalidTokenError:
        return False, "QR Code غير صحيح"
    except User.DoesNotExist:
        return False, "المستخدم غير موجود"
    except Exception as e:
        return False, f"خطأ: {str(e)}"


def process_unauthorized_absence(employee, absence_date, absence_type='unauthorized'):
    """
    معالجة غياب موظف بدون عذر
    
    Args:
        employee: كائن Employee
        absence_date: تاريخ الغياب
        absence_type: نوع الغياب
    
    Returns:
        tuple: (success, absence_record_or_message)
    """
    from .models import EmployeeAbsence, AbsencePolicy, LeaveRequest, LeaveType
    from django.db.models import Q
    
    # فحص إذا كان لديه إجازة معتمدة في هذا اليوم
    approved_leave = LeaveRequest.objects.filter(
        employee=employee,
        status='approved',
        start_date__lte=absence_date,
        end_date__gte=absence_date
    ).first()
    
    if approved_leave:
        return False, "الموظف لديه إجازة معتمدة في هذا اليوم"
    
    # فحص إذا كان الغياب مسجل مسبقاً
    existing = EmployeeAbsence.objects.filter(
        employee=employee,
        absence_date=absence_date
    ).first()
    
    if existing:
        return False, "الغياب مسجل مسبقاً"
    
    # الحصول على سياسة الخصم
    policy = AbsencePolicy.objects.filter(is_default=True, is_active=True).first()
    
    if not policy:
        policy = AbsencePolicy.objects.filter(is_active=True).first()
    
    if not policy:
        return False, "لا توجد سياسة خصم نشطة"
    
    # إنشاء سجل الغياب
    absence = EmployeeAbsence.objects.create(
        employee=employee,
        absence_date=absence_date,
        absence_type=absence_type
    )
    
    # حساب الخصم
    is_authorized = absence_type != 'unauthorized'
    deduction_amount = policy.calculate_deduction(employee, 1, is_authorized)
    
    # محاولة الخصم من الإجازات أولاً
    if policy.deduct_from_leave_first:
        # الحصول على نوع الإجازة السنوية
        annual_leave_type = LeaveType.objects.filter(
            Q(name__icontains='سنوية') | Q(name__icontains='Annual')
        ).first()
        
        if annual_leave_type:
            # حساب رصيد الإجازات المتبقي
            from .leave_utils import calculate_leave_balance
            balance = calculate_leave_balance(employee, annual_leave_type)
            
            if balance >= 1:
                # خصم من الإجازات
                absence.deducted_from_leave = True
                absence.leave_days_deducted = 1
                absence.save(update_fields=['deducted_from_leave', 'leave_days_deducted'])
                
                return True, absence
    
    # إذا لم يتم الخصم من الإجازات، خصم من الراتب
    absence.deducted_from_salary = True
    absence.salary_deduction_amount = deduction_amount
    absence.save(update_fields=['deducted_from_salary', 'salary_deduction_amount'])
    
    return True, absence


def calculate_employee_leave_balance(employee, leave_type):
    """
    حساب رصيد إجازات الموظف
    
    Args:
        employee: كائن Employee
        leave_type: نوع الإجازة
    
    Returns:
        dict: معلومات الرصيد
    """
    from .models import LeaveRequest, EmployeeAbsence
    from django.db.models import Sum
    from datetime import date
    
    # عدد الأيام السنوية
    annual_days = leave_type.days_per_year
    
    # حساب عدد الأيام المستخدمة هذا العام
    current_year = date.today().year
    used_days = LeaveRequest.objects.filter(
        employee=employee,
        leave_type=leave_type,
        status='approved',
        start_date__year=current_year
    ).aggregate(total=Sum('days_requested'))['total'] or 0
    
    # إضافة الأيام المخصومة من الغياب
    deducted_from_absence = EmployeeAbsence.objects.filter(
        employee=employee,
        deducted_from_leave=True,
        absence_date__year=current_year
    ).aggregate(total=Sum('leave_days_deducted'))['total'] or 0
    
    used_days += deducted_from_absence
    
    # الرصيد المتبقي
    remaining = annual_days - used_days
    
    # رصيد مرحل من السنة الماضية (إذا كان النوع يسمح)
    carried_forward = 0
    if leave_type.carry_forward:
        # يمكن تطوير هذا لحساب الرصيد المرحل
        pass
    
    return {
        'annual_days': annual_days,
        'used_days': used_days,
        'remaining_days': remaining + carried_forward,
        'carried_forward': carried_forward,
        'deducted_from_absence': deducted_from_absence
    }


def check_and_process_daily_absences():
    """
    فحص ومعالجة الغياب اليومي لجميع الموظفين
    يتم تشغيلها كمهمة يومية (Cron Job أو Celery Task)
    
    Returns:
        dict: إحصائيات المعالجة
    """
    from .models import Employee, AttendanceRecord, WeekendDay
    from datetime import date, timedelta
    
    yesterday = date.today() - timedelta(days=1)
    
    # فحص إذا كان يوم عمل (is_active=True يعني عطلة)
    weekday = yesterday.weekday()
    is_weekend = WeekendDay.objects.filter(day_of_week=weekday, is_active=True).exists()
    
    if is_weekend:
        return {'message': 'ليس يوم عمل', 'processed': 0}
    
    # الحصول على الموظفين النشطين
    active_employees = Employee.objects.filter(status='active')
    
    stats = {
        'total_employees': active_employees.count(),
        'absent_count': 0,
        'processed': 0,
        'errors': []
    }
    
    for employee in active_employees:
        # فحص إذا كان لديه سجل حضور
        attendance = AttendanceRecord.objects.filter(
            employee=employee,
            clock_in__date=yesterday
        ).first()
        
        if not attendance:
            # موظف غائب
            stats['absent_count'] += 1
            
            try:
                success, result = process_unauthorized_absence(
                    employee, 
                    yesterday, 
                    'unauthorized'
                )
                
                if success:
                    stats['processed'] += 1
            except Exception as e:
                stats['errors'].append(f"{employee}: {str(e)}")
    
    return stats


def create_employee_id_card(employee, expiry_months=12):
    """
    إنشاء بطاقة هوية جديدة للموظف
    
    Args:
        employee: كائن Employee
        expiry_months: عدد شهور الصلاحية
    
    Returns:
        EmployeeIDCard: كائن البطاقة
    """
    from .models import EmployeeIDCard
    from datetime import date
    from django.core.files.base import ContentFile
    import uuid
    
    # إنهاء صلاحية البطاقات القديمة
    EmployeeIDCard.objects.filter(
        employee=employee,
        status='active'
    ).update(status='replaced')
    
    # توليد QR Code
    qr_data, qr_image_buffer = generate_employee_qr_login(employee, expiry_days=expiry_months * 30)
    
    # رقم بطاقة فريد
    card_number = f"EMP-{employee.id:05d}-{uuid.uuid4().hex[:8].upper()}"
    
    # تواريخ الصلاحية
    issue_date = date.today()
    expiry_date = issue_date + timedelta(days=expiry_months * 30)
    
    # إنشاء البطاقة
    card = EmployeeIDCard.objects.create(
        employee=employee,
        card_number=card_number,
        qr_code_data=qr_data,
        issue_date=issue_date,
        expiry_date=expiry_date,
        status='active'
    )
    
    # حفظ صورة QR Code
    card.qr_code_image.save(
        f'qr_{card_number}.png',
        ContentFile(qr_image_buffer.getvalue()),
        save=True
    )
    
    return card
