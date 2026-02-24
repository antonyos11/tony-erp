from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
from accounting.models import Account, JournalEntry
import uuid

# --- إعدادات النظام ---
class HRSettings(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    company_name = models.CharField(max_length=200, verbose_name=_("اسم الشركة"))
    company_address = models.TextField(blank=True, default='', verbose_name=_("عنوان الشركة"))
    company_phone = models.CharField(max_length=50, blank=True, default='', verbose_name=_("هاتف الشركة"))
    company_vat_number = models.CharField(max_length=50, blank=True, default='', verbose_name=_("الرقم الضريبي"))
    working_hours_per_day = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('8'), verbose_name=_("ساعات العمل اليومية"))
    working_days_per_week = models.IntegerField(default=5, verbose_name=_("أيام العمل الأسبوعية"))
    overtime_rate = models.DecimalField(max_digits=5, decimal_places=2, default=1.5, verbose_name=_("معدل الساعات الإضافية"))
    late_penalty_per_minute = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'), verbose_name=_("غرامة التأخير لكل دقيقة"))

    # حسابات محاسبية للموارد البشرية
    salary_expense_account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, related_name='salary_expenses', verbose_name=_("حساب مصاريف الرواتب"))
    salary_payable_account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, related_name='salary_payables', verbose_name=_("حساب رواتب مستحقة"))
    overtime_expense_account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, related_name='overtime_expenses', verbose_name=_("حساب مصاريف الساعات الإضافية"))
    bonus_expense_account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, related_name='bonus_expenses', verbose_name=_("حساب مصاريف المكافآت"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("إعدادات الموارد البشرية")
        verbose_name_plural = _("إعدادات الموارد البشرية")

# --- الأقسام والإدارات ---
class Department(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    name = models.CharField(max_length=100, verbose_name=_("اسم القسم"))
    code = models.CharField(max_length=20, unique=True, verbose_name=_("كود القسم"))
    description = models.TextField(blank=True, verbose_name=_("الوصف"))
    head = models.ForeignKey('Employee', on_delete=models.SET_NULL, null=True, blank=True, related_name='headed_departments', verbose_name=_("رئيس القسم"))
    budget = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'), verbose_name=_("الميزانية"))
    cost_center = models.ForeignKey('accounting.CostCenter', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("مركز التكلفة"))
    is_active = models.BooleanField(default=True, verbose_name=_("نشط"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("قسم")
        verbose_name_plural = _("الأقسام")
        
    def __str__(self):
        return self.name

# --- المناصب والوظائف ---
class JobPosition(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    title = models.CharField(max_length=100, verbose_name=_("المسمى الوظيفي"))
    code = models.CharField(max_length=20, unique=True, verbose_name=_("كود الوظيفة"))
    department = models.ForeignKey(Department, on_delete=models.CASCADE, verbose_name=_("القسم"))
    description = models.TextField(verbose_name=_("الوصف الوظيفي"))
    requirements = models.TextField(verbose_name=_("المتطلبات"))
    min_salary = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'), blank=True, verbose_name=_("الحد الأدنى للراتب"))
    max_salary = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'), blank=True, verbose_name=_("الحد الأقصى للراتب"))
    is_active = models.BooleanField(default=True, verbose_name=_("نشط"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("منصب وظيفي")
        verbose_name_plural = _("المناصب الوظيفية")
        
    def __str__(self):
        return f"{self.title} - {self.department.name}"


# توافق مع الاستيراد القديم
Position = JobPosition

# --- الموظفين ---
class Employee(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    GENDER_CHOICES = [
        ('M', _('ذكر')),
        ('F', _('أنثى')),
    ]

    MARITAL_STATUS_CHOICES = [
        ('single', _('أعزب')),
        ('married', _('متزوج')),
        ('divorced', _('مطلق')),
        ('widowed', _('أرمل')),
    ]

    STATUS_CHOICES = [
        ('active', _('نشط')),
        ('inactive', _('غير نشط')),
        ('terminated', _('منتهي الخدمة')),
        ('suspended', _('موقوف')),
    ]
    
    # البيانات الأساسية
    employee_id = models.CharField(max_length=20, unique=True, verbose_name=_("رقم الموظف"))
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee_profile', verbose_name=_("حساب المستخدم"))
    
    # البيانات الشخصية
    first_name = models.CharField(max_length=50, verbose_name=_("الاسم الأول"))
    last_name = models.CharField(max_length=50, verbose_name=_("اسم العائلة"))
    arabic_name = models.CharField(max_length=100, verbose_name=_("الاسم بالعربية"))
    national_id = models.CharField(max_length=20, unique=True, verbose_name=_("رقم الهوية"))
    passport_number = models.CharField(max_length=20, blank=True, verbose_name=_("رقم الجواز"))
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, verbose_name=_("الجنس"))
    birth_date = models.DateField(verbose_name=_("تاريخ الميلاد"))
    marital_status = models.CharField(max_length=10, choices=MARITAL_STATUS_CHOICES, verbose_name=_("الحالة الاجتماعية"))
    
    # معلومات الاتصال
    phone = models.CharField(max_length=15, verbose_name=_("الهاتف"))
    email = models.EmailField(verbose_name=_("البريد الإلكتروني"))
    address = models.TextField(verbose_name=_("العنوان"))
    emergency_contact_name = models.CharField(max_length=100, verbose_name=_("اسم جهة الاتصال للطوارئ"))
    emergency_contact_phone = models.CharField(max_length=15, verbose_name=_("هاتف جهة الاتصال للطوارئ"))
    
    # معلومات العمل
    department = models.ForeignKey(Department, on_delete=models.CASCADE, verbose_name=_("القسم"))
    position = models.ForeignKey(JobPosition, on_delete=models.CASCADE, verbose_name=_("المنصب"))
    hire_date = models.DateField(verbose_name=_("تاريخ التعيين"))
    termination_date = models.DateField(null=True, blank=True, verbose_name=_("تاريخ انتهاء الخدمة"))
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='active', verbose_name=_("الحالة"))
    
    # معلومات الراتب
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("الراتب الأساسي"))
    housing_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'), verbose_name=_("بدل السكن"))
    transportation_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'), verbose_name=_("بدل المواصلات"))
    other_allowances = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'), verbose_name=_("بدلات أخرى"))
    
    # إعدادات الحضور
    fingerprint_id = models.CharField(max_length=50, unique=True, null=True, blank=True, verbose_name=_("معرف البصمة"))
    rfid_card_number = models.CharField(max_length=20, unique=True, null=True, blank=True, verbose_name=_("رقم بطاقة RFID"))
    attendance_exempt = models.BooleanField(default=False, verbose_name=_("مستثنى من إلزام الحضور"))
    
    # معلومات البنك
    bank_name = models.CharField(max_length=100, blank=True, verbose_name=_("اسم البنك"))
    bank_account_number = models.CharField(max_length=30, blank=True, verbose_name=_("رقم الحساب البنكي"))
    iban = models.CharField(max_length=34, blank=True, verbose_name="IBAN")
    
    # ملفات
    photo = models.ImageField(upload_to='employees/photos/', null=True, blank=True, verbose_name=_("الصورة"))
    cv_file = models.FileField(upload_to='employees/cvs/', null=True, blank=True, verbose_name=_("ملف السيرة الذاتية"))
    contract_file = models.FileField(upload_to='employees/contracts/', null=True, blank=True, verbose_name=_("ملف العقد"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("موظف")
        verbose_name_plural = _("الموظفون")
        
    def __str__(self):
        return f"{self.employee_id} - {self.arabic_name}"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def total_salary(self):
        return self.basic_salary + self.housing_allowance + self.transportation_allowance + self.other_allowances
    
    @property
    def years_of_service(self):
        from datetime import date
        if self.termination_date:
            end_date = self.termination_date
        else:
            end_date = date.today()
        return (end_date - self.hire_date).days / 365.25

# --- الحضور والانصراف ---
class AttendanceRecord(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    RECORD_TYPE_CHOICES = [
        ('check_in', _('حضور')),
        ('check_out', _('انصراف')),
        ('break_start', _('بداية استراحة')),
        ('break_end', _('نهاية استراحة')),
    ]

    SOURCE_CHOICES = [
        ('manual', _('يدوي')),
        ('fingerprint', _('بصمة')),
        ('rfid', 'RFID'),
        ('mobile', _('تطبيق الموبايل')),
        ('web', _('موقع الويب')),
    ]
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='attendance_records', verbose_name=_("الموظف"))
    date = models.DateField(verbose_name=_("التاريخ"))
    time = models.TimeField(verbose_name=_("الوقت"))
    record_type = models.CharField(max_length=15, choices=RECORD_TYPE_CHOICES, verbose_name=_("نوع التسجيل"))
    source = models.CharField(max_length=15, choices=SOURCE_CHOICES, verbose_name=_("المصدر"))
    device_info = models.CharField(max_length=100, blank=True, verbose_name=_("معلومات الجهاز"))
    notes = models.TextField(blank=True, verbose_name=_("ملاحظات"))
    
    # معلومات الموقع (للتطبيقات المتنقلة)
    latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True, verbose_name=_("خط العرض"))
    longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True, verbose_name=_("خط الطول"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name=_("أنشأه"))
    
    class Meta:
        verbose_name = _("سجل حضور")
        verbose_name_plural = _("سجلات الحضور")
        ordering = ['-date', '-time']
        
    def __str__(self):
        return f"{self.employee.arabic_name} - {self.date} {self.time} - {self.get_record_type_display()}"

# --- جدولة المناوبات ---
class WorkSchedule(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    name = models.CharField(max_length=100, verbose_name=_("اسم الجدولة"))
    is_default = models.BooleanField(default=False, verbose_name=_("جدولة افتراضية"))
    
    # أيام العمل
    sunday_start = models.TimeField(null=True, blank=True, verbose_name=_("بداية الأحد"))
    sunday_end = models.TimeField(null=True, blank=True, verbose_name=_("نهاية الأحد"))
    monday_start = models.TimeField(null=True, blank=True, verbose_name=_("بداية الاثنين"))
    monday_end = models.TimeField(null=True, blank=True, verbose_name=_("نهاية الاثنين"))
    tuesday_start = models.TimeField(null=True, blank=True, verbose_name=_("بداية الثلاثاء"))
    tuesday_end = models.TimeField(null=True, blank=True, verbose_name=_("نهاية الثلاثاء"))
    wednesday_start = models.TimeField(null=True, blank=True, verbose_name=_("بداية الأربعاء"))
    wednesday_end = models.TimeField(null=True, blank=True, verbose_name=_("نهاية الأربعاء"))
    thursday_start = models.TimeField(null=True, blank=True, verbose_name=_("بداية الخميس"))
    thursday_end = models.TimeField(null=True, blank=True, verbose_name=_("نهاية الخميس"))
    friday_start = models.TimeField(null=True, blank=True, verbose_name=_("بداية الجمعة"))
    friday_end = models.TimeField(null=True, blank=True, verbose_name=_("نهاية الجمعة"))
    saturday_start = models.TimeField(null=True, blank=True, verbose_name=_("بداية السبت"))
    saturday_end = models.TimeField(null=True, blank=True, verbose_name=_("نهاية السبت"))
    
    # إعدادات المرونة
    grace_period_minutes = models.IntegerField(default=15, verbose_name=_("فترة السماح بالدقائق"))
    break_duration_minutes = models.IntegerField(default=60, verbose_name=_("مدة الاستراحة بالدقائق"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("جدولة العمل")
        verbose_name_plural = _("جدولة الأعمال")
        
    def __str__(self):
        return self.name

# --- ربط الموظفين بجدولة العمل ---
class EmployeeSchedule(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='schedules', verbose_name=_("الموظف"))
    schedule = models.ForeignKey(WorkSchedule, on_delete=models.CASCADE, verbose_name=_("الجدولة"))
    start_date = models.DateField(verbose_name=_("تاريخ البداية"))
    end_date = models.DateField(null=True, blank=True, verbose_name=_("تاريخ النهاية"))
    is_active = models.BooleanField(default=True, verbose_name=_("نشط"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _("جدولة موظف")
        verbose_name_plural = _("جدولة الموظفين")
        
    def __str__(self):
        return f"{self.employee.arabic_name} - {self.schedule.name}"

# --- الإجازات والعطل ---
class LeaveType(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    name = models.CharField(max_length=100, verbose_name=_("نوع الإجازة"))
    days_per_year = models.IntegerField(verbose_name=_("الأيام المسموحة سنوياً"))
    is_paid = models.BooleanField(default=True, verbose_name=_("مدفوعة الأجر"))
    carry_forward = models.BooleanField(default=False, verbose_name=_("يمكن ترحيلها"))
    max_carry_forward_days = models.IntegerField(default=0, verbose_name=_("حد الأيام المرحلة"))
    requires_approval = models.BooleanField(default=True, verbose_name=_("تحتاج موافقة"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _("نوع إجازة")
        verbose_name_plural = _("أنواع الإجازات")
        
    def __str__(self):
        return self.name

class LeaveRequest(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    STATUS_CHOICES = [
        ('pending', _('في انتظار الموافقة')),
        ('approved', _('موافق عليها')),
        ('rejected', _('مرفوضة')),
        ('cancelled', _('ملغية')),
    ]
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_requests', verbose_name=_("الموظف"))
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE, verbose_name=_("نوع الإجازة"))
    start_date = models.DateField(verbose_name=_("تاريخ البداية"))
    end_date = models.DateField(verbose_name=_("تاريخ النهاية"))
    days_requested = models.IntegerField(verbose_name=_("عدد الأيام المطلوبة"))
    reason = models.TextField(verbose_name=_("السبب"))
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending', verbose_name=_("الحالة"))

    # الموظف البديل أثناء الإجازة
    replacement_employee = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replacement_leave_requests',
        verbose_name=_("الموظف البديل أثناء الإجازة"),
    )
    
    # معلومات الموافقة
    approved_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_leaves', verbose_name=_("وافق عليها"))
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name=_("تاريخ الموافقة"))
    rejection_reason = models.TextField(blank=True, verbose_name=_("سبب الرفض"))
    
    # ملفات داعمة
    supporting_documents = models.FileField(upload_to='leaves/documents/', null=True, blank=True, verbose_name=_("المستندات الداعمة"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("طلب إجازة")
        verbose_name_plural = _("طلبات الإجازات")
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.employee.arabic_name} - {self.leave_type.name} - {self.start_date}"

# --- العطلات الرسمية وأيام العطل الأسبوعية ---
class WeekendDay(models.Model):
    """تحديد أيام العطلة الأسبوعية يدوياً من داخل النظام"""
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    DAY_CHOICES = [
        (0, _('الاثنين')),
        (1, _('الثلاثاء')),
        (2, _('الأربعاء')),
        (3, _('الخميس')),
        (4, _('الجمعة')),
        (5, _('السبت')),
        (6, _('الأحد')),
    ]
    day_of_week = models.IntegerField(choices=DAY_CHOICES, unique=True, verbose_name=_('اليوم'))
    is_active = models.BooleanField(default=True, verbose_name=_('نشط'))

    class Meta:
        verbose_name = _('يوم عطلة أسبوعية')
        verbose_name_plural = _('أيام العطلة الأسبوعية')
        ordering = ['day_of_week']

    def __str__(self):
        day_name = dict(self.DAY_CHOICES).get(self.day_of_week)
        # تحويل lazy translation إلى string
        return str(day_name) if day_name else str(self.day_of_week)


class PublicHoliday(models.Model):
    """عطل رسمية يتم إدارتها من لوحة الإدارة"""
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    name = models.CharField(max_length=200, verbose_name=_('اسم العطلة'))
    date = models.DateField(verbose_name=_('التاريخ'))
    is_recurring = models.BooleanField(default=False, verbose_name=_('تُكرر سنوياً (حسب اليوم والشهر)'))
    notes = models.TextField(blank=True, verbose_name=_('ملاحظات'))

    class Meta:
        verbose_name = _('عطلة رسمية')
        verbose_name_plural = _('عطل رسمية')
        unique_together = [('name', 'date')]
        ordering = ['date']

    def __str__(self):
        return f"{self.name} - {self.date}"

# --- رواتب الموظفين ---
class Payroll(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    STATUS_CHOICES = [
        ('draft', _('مسودة')),
        ('calculated', _('محسوبة')),
        ('approved', _('معتمدة')),
        ('paid', _('مدفوعة')),
    ]
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='payrolls', verbose_name=_("الموظف"))
    period_start = models.DateField(verbose_name=_("بداية الفترة"))
    period_end = models.DateField(verbose_name=_("نهاية الفترة"))
    
    # الراتب والبدلات
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("الراتب الأساسي"))
    housing_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'), verbose_name=_("بدل السكن"))
    transportation_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'), verbose_name=_("بدل المواصلات"))
    other_allowances = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'), verbose_name=_("بدلات أخرى"))
    
    # الساعات الإضافية والمكافآت
    overtime_hours = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0'), verbose_name=_("ساعات إضافية"))
    overtime_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'), verbose_name=_("مبلغ الساعات الإضافية"))
    bonus_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'), verbose_name=_("المكافآت"))
    
    # الخصومات
    late_penalty = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'), verbose_name=_("غرامة التأخير"))
    absence_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'), verbose_name=_("خصم الغياب"))
    other_deductions = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'), verbose_name=_("خصومات أخرى"))
    
    # المجاميع
    gross_salary = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_("إجمالي الراتب"))
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_("إجمالي الخصومات"))
    net_salary = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_("صافي الراتب"))
    
    # معلومات المعالجة
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='draft', verbose_name=_("الحالة"))
    calculated_at = models.DateTimeField(null=True, blank=True, verbose_name=_("تاريخ الحساب"))
    approved_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_payrolls', verbose_name=_("اعتمده"))
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name=_("تاريخ الاعتماد"))
    
    # ربط بالقيد المحاسبي
    journal_entry = models.OneToOneField(JournalEntry, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("القيد المحاسبي"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("راتب")
        verbose_name_plural = _("الرواتب")
        unique_together = ['employee', 'period_start', 'period_end']
        ordering = ['-period_start']
        
    def __str__(self):
        return f"{self.employee.arabic_name} - {self.period_start} إلى {self.period_end}"
    
    def calculate_totals(self):
        """حساب إجمالي الراتب والخصومات والصافي"""
        self.gross_salary = (
            self.basic_salary + self.housing_allowance + 
            self.transportation_allowance + self.other_allowances + 
            self.overtime_amount + self.bonus_amount
        )
        
        self.total_deductions = (
            self.late_penalty + self.absence_deduction + self.other_deductions
        )
        
        self.net_salary = self.gross_salary - self.total_deductions
        
    def save(self, *args, **kwargs):
        self.calculate_totals()
        super().save(*args, **kwargs)


# --- أنواع البدلات والخصومات ---
class AllowanceType(models.Model):
    """أنواع البدلات المختلفة"""
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, verbose_name=_("اسم البدل"))
    code = models.CharField(max_length=20, unique=True, verbose_name=_("كود البدل"))
    description = models.TextField(blank=True, verbose_name=_("الوصف"))
    is_taxable = models.BooleanField(default=False, verbose_name=_("خاضع للضريبة"))
    is_fixed = models.BooleanField(default=True, verbose_name=_("مبلغ ثابت"))
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0'), 
                                     verbose_name=_("النسبة المئوية"), 
                                     help_text=_("تستخدم إذا كان البدل نسبة من الراتب"))
    default_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'), 
                                         verbose_name=_("المبلغ الافتراضي"))
    is_active = models.BooleanField(default=True, verbose_name=_("نشط"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("نوع بدل")
        verbose_name_plural = _("أنواع البدلات")
        ordering = ['name']
        
    def __str__(self):
        return self.name


class DeductionType(models.Model):
    """أنواع الخصومات المختلفة"""
    CALCULATION_CHOICES = [
        ('fixed', _('مبلغ ثابت')),
        ('percentage', _('نسبة من الراتب')),
        ('days', _('أيام غياب')),
        ('hours', _('ساعات')),
    ]
    
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, verbose_name=_("اسم الخصم"))
    code = models.CharField(max_length=20, unique=True, verbose_name=_("كود الخصم"))
    description = models.TextField(blank=True, verbose_name=_("الوصف"))
    calculation_type = models.CharField(max_length=15, choices=CALCULATION_CHOICES, default='fixed', 
                                        verbose_name=_("طريقة الحساب"))
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0'), 
                                     verbose_name=_("النسبة المئوية"))
    default_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'), 
                                         verbose_name=_("المبلغ الافتراضي"))
    is_mandatory = models.BooleanField(default=False, verbose_name=_("إجباري"))
    is_active = models.BooleanField(default=True, verbose_name=_("نشط"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("نوع خصم")
        verbose_name_plural = _("أنواع الخصومات")
        ordering = ['name']
        
    def __str__(self):
        return self.name


class EmployeeAllowance(models.Model):
    """بدلات مخصصة للموظف"""
    id = models.AutoField(primary_key=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='custom_allowances', 
                                 verbose_name=_("الموظف"))
    allowance_type = models.ForeignKey(AllowanceType, on_delete=models.CASCADE, verbose_name=_("نوع البدل"))
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("المبلغ"))
    start_date = models.DateField(verbose_name=_("تاريخ البداية"))
    end_date = models.DateField(null=True, blank=True, verbose_name=_("تاريخ النهاية"))
    is_active = models.BooleanField(default=True, verbose_name=_("نشط"))
    notes = models.TextField(blank=True, verbose_name=_("ملاحظات"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("بدل موظف")
        verbose_name_plural = _("بدلات الموظفين")
        ordering = ['-start_date']
        
    def __str__(self):
        return f"{self.employee.arabic_name} - {self.allowance_type.name}: {self.amount}"


class EmployeeDeduction(models.Model):
    """خصومات مخصصة للموظف"""
    id = models.AutoField(primary_key=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='custom_deductions', 
                                 verbose_name=_("الموظف"))
    deduction_type = models.ForeignKey(DeductionType, on_delete=models.CASCADE, verbose_name=_("نوع الخصم"))
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("المبلغ"))
    start_date = models.DateField(verbose_name=_("تاريخ البداية"))
    end_date = models.DateField(null=True, blank=True, verbose_name=_("تاريخ النهاية"))
    is_active = models.BooleanField(default=True, verbose_name=_("نشط"))
    notes = models.TextField(blank=True, verbose_name=_("ملاحظات"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("خصم موظف")
        verbose_name_plural = _("خصومات الموظفين")
        ordering = ['-start_date']
        
    def __str__(self):
        return f"{self.employee.arabic_name} - {self.deduction_type.name}: {self.amount}"


class PayrollItem(models.Model):
    """بنود الراتب التفصيلية (بدلات وخصومات لكل راتب)"""
    ITEM_TYPE_CHOICES = [
        ('allowance', _('بدل')),
        ('deduction', _('خصم')),
    ]
    
    id = models.AutoField(primary_key=True)
    payroll = models.ForeignKey(Payroll, on_delete=models.CASCADE, related_name='items', verbose_name=_("الراتب"))
    item_type = models.CharField(max_length=15, choices=ITEM_TYPE_CHOICES, verbose_name=_("النوع"))
    name = models.CharField(max_length=100, verbose_name=_("اسم البند"))
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("المبلغ"))
    notes = models.TextField(blank=True, verbose_name=_("ملاحظات"))
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _("بند راتب")
        verbose_name_plural = _("بنود الراتب")
        ordering = ['item_type', 'name']
        
    def __str__(self):
        return f"{self.payroll.employee.arabic_name} - {self.name}: {self.amount}"


# --- تقييم الأداء ---
class PerformanceReview(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    STATUS_CHOICES = [
        ('draft', _('مسودة')),
        ('submitted', _('مرسل')),
        ('approved', _('معتمد')),
    ]
    
    RATING_CHOICES = [
        (1, _('ضعيف')),
        (2, _('أقل من المتوقع')),
        (3, _('يلبي التوقعات')),
        (4, _('يفوق التوقعات')),
        (5, _('ممتاز')),
    ]
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='performance_reviews', verbose_name=_("الموظف"))
    reviewer = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='conducted_reviews', verbose_name=_("المقيم"))
    review_period_start = models.DateField(verbose_name=_("بداية فترة التقييم"))
    review_period_end = models.DateField(verbose_name=_("نهاية فترة التقييم"))
    
    # التقييمات
    quality_of_work = models.IntegerField(choices=RATING_CHOICES, verbose_name=_("جودة العمل"))
    productivity = models.IntegerField(choices=RATING_CHOICES, verbose_name=_("الإنتاجية"))
    communication = models.IntegerField(choices=RATING_CHOICES, verbose_name=_("التواصل"))
    teamwork = models.IntegerField(choices=RATING_CHOICES, verbose_name=_("العمل الجماعي"))
    punctuality = models.IntegerField(choices=RATING_CHOICES, verbose_name=_("الالتزام بالمواعيد"))
    initiative = models.IntegerField(choices=RATING_CHOICES, verbose_name=_("المبادرة"))
    
    # التقييم الإجمالي
    overall_rating = models.DecimalField(max_digits=3, decimal_places=1, verbose_name=_("التقييم الإجمالي"))
    
    # التعليقات
    strengths = models.TextField(verbose_name=_("نقاط القوة"))
    areas_for_improvement = models.TextField(verbose_name=_("مجالات التحسين"))
    goals_for_next_period = models.TextField(verbose_name=_("أهداف الفترة القادمة"))
    reviewer_comments = models.TextField(verbose_name=_("تعليقات المقيم"))
    employee_comments = models.TextField(blank=True, verbose_name=_("تعليقات الموظف"))
    
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='draft', verbose_name=_("الحالة"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("تقييم أداء")
        verbose_name_plural = _("تقييمات الأداء")
        ordering = ['-review_period_end']
        
    def __str__(self):
        return f"{self.employee.arabic_name} - {self.review_period_start} إلى {self.review_period_end}"
    
    def calculate_overall_rating(self):
        """حساب التقييم الإجمالي"""
        ratings = [
            self.quality_of_work,
            self.productivity,
            self.communication,
            self.teamwork,
            self.punctuality,
            self.initiative,
        ]
        # تصفية القيم غير الفارغة لتجنب TypeError
        valid_ratings = [r for r in ratings if r is not None]
        if valid_ratings:
            self.overall_rating = round(sum(valid_ratings) / len(valid_ratings), 2)
        else:
            self.overall_rating = None
        
    def save(self, *args, **kwargs):
        self.calculate_overall_rating()
        super().save(*args, **kwargs)

# --- نظام الأهداف والتارجت المتطور ---
class TargetCategory(models.Model):
    """فئات الأهداف"""
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    CATEGORY_TYPES = [
        ('sales', _('مبيعات')),
        ('production', _('إنتاج')),
        ('quality', _('جودة')),
        ('attendance', _('حضور')),
        ('customer_service', _('خدمة العملاء')),
        ('cost_reduction', _('تقليل التكاليف')),
        ('training', _('تدريب')),
        ('safety', _('سلامة')),
        ('other', _('أخرى')),
    ]

    name = models.CharField(_('اسم الفئة'), max_length=100)
    category_type = models.CharField(_('نوع الفئة'), max_length=20, choices=CATEGORY_TYPES)
    description = models.TextField(_('الوصف'), blank=True)
    is_active = models.BooleanField(_('نشط'), default=True)

    class Meta:
        verbose_name = _('فئة الأهداف')
        verbose_name_plural = _('فئات الأهداف')
    
    def __str__(self):
        return self.name


class PerformanceTarget(models.Model):
    """الأهداف والتارجت للموظفين"""
    
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    TARGET_PERIODS = [
        ('daily', _('يومي')),
        ('weekly', _('أسبوعي')),
        ('monthly', _('شهري')),
        ('quarterly', _('ربع سنوي')),
        ('yearly', _('سنوي')),
        ('custom', _('فترة مخصصة')),
    ]
    
    TARGET_TYPES = [
        ('quantity', _('كمية')),
        ('percentage', _('نسبة مئوية')),
        ('amount', _('مبلغ مالي')),
        ('time', _('وقت')),
        ('score', _('نقاط')),
        ('boolean', _('تحقق/عدم تحقق')),
    ]
    
    STATUS_CHOICES = [
        ('draft', _('مسودة')),
        ('active', _('نشط')),
        ('completed', _('مكتمل')),
        ('cancelled', _('ملغي')),
        ('expired', _('منتهي')),
    ]
    
    # معلومات الهدف
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, 
                               related_name='targets', verbose_name=_('الموظف'))
    category = models.ForeignKey(TargetCategory, on_delete=models.CASCADE,
                               verbose_name=_('فئة الهدف'))
    title = models.CharField(_('عنوان الهدف'), max_length=200)
    description = models.TextField(_('وصف الهدف'))
    
    # نوع ومدة الهدف
    target_period = models.CharField(_('فترة الهدف'), max_length=20, choices=TARGET_PERIODS)
    target_type = models.CharField(_('نوع الهدف'), max_length=20, choices=TARGET_TYPES)
    
    # القيم المستهدفة والمحققة
    target_value = models.DecimalField(_('القيمة المستهدفة'), max_digits=15, decimal_places=2)
    current_value = models.DecimalField(_('القيمة الحالية'), max_digits=15, decimal_places=2, default=0)
    unit = models.CharField(_('الوحدة'), max_length=50, default='عدد')
    
    # التواريخ
    start_date = models.DateField(_('تاريخ البدء'))
    end_date = models.DateField(_('تاريخ الانتهاء'))
    
    # الأوزان والأهمية
    weight = models.DecimalField(_('الوزن النسبي %'), max_digits=5, decimal_places=2, default=100,
                   help_text=_('الوزن النسبي لهذا الهدف من إجمالي أهداف الموظف'))
    priority = models.CharField(_('الأولوية'), max_length=10,
                  choices=[('low', _('منخفضة')), ('medium', _('متوسطة')), 
                      ('high', _('عالية')), ('critical', _('حرجة'))],
                  default='medium')
    
    # المعايير والمكافآت
    min_acceptable = models.DecimalField(_('الحد الأدنى المقبول'), max_digits=15, decimal_places=2,
                                       null=True, blank=True)
    excellence_threshold = models.DecimalField(_('حد التميز'), max_digits=15, decimal_places=2,
                                             null=True, blank=True)
    reward_amount = models.DecimalField(_('مبلغ المكافأة'), max_digits=10, decimal_places=2, 
                                      default=0, help_text=_('مكافأة عند تحقيق الهدف'))
    
    # الحالة والمتابعة
    status = models.CharField(_('الحالة'), max_length=15, choices=STATUS_CHOICES, default='draft')
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                   related_name='assigned_targets', verbose_name=_('محدد الهدف'))
    
    # التقييم التلقائي
    auto_calculate = models.BooleanField(_('حساب تلقائي'), default=False,
                                       help_text=_('هل يتم حساب التقدم تلقائياً من النظام؟'))
    calculation_query = models.TextField(_('استعلام الحساب'), blank=True,
                                       help_text=_('استعلام SQL لحساب التقدم تلقائياً'))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('هدف أداء')
        verbose_name_plural = _('أهداف الأداء')
        ordering = ['-start_date', 'priority']
    
    def __str__(self):
        return f"{self.employee.arabic_name} - {self.title}"
    
    @property
    def achievement_percentage(self):
        """نسبة الإنجاز"""
        if self.target_value > 0:
            return min((self.current_value / self.target_value) * 100, 100)
        return 0
    
    @property
    def remaining_days(self):
        """الأيام المتبقية"""
        if self.end_date:
            delta = self.end_date - timezone.now().date()
            return delta.days if delta.days > 0 else 0
        return 0
    
    @property
    def is_overdue(self):
        """هل تجاوز الموعد المحدد؟"""
        return timezone.now().date() > self.end_date and self.status != 'completed'
    
    @property
    def performance_level(self):
        """مستوى الأداء"""
        percentage = self.achievement_percentage
        if percentage >= (self.excellence_threshold or 120):
            return 'excellence'
        elif percentage >= 100:
            return 'achieved' 
        elif percentage >= (self.min_acceptable or 80):
            return 'acceptable'
        else:
            return 'below_target'
    
    def update_progress(self, value, notes="", updated_by=None):
        """تحديث التقدم"""
        old_value = self.current_value
        self.current_value = value
        self.save()
        
        # تسجيل التحديث
        TargetProgress.objects.create(
            target=self,
            previous_value=old_value,
            new_value=value,
            notes=notes,
            updated_by=updated_by
        )
        
        # تحقق من إكمال الهدف
        if self.achievement_percentage >= 100 and self.status != 'completed':
            self.status = 'completed'
            self.save()


class TargetProgress(models.Model):
    """تتبع التقدم في الأهداف"""
    
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    target = models.ForeignKey(PerformanceTarget, on_delete=models.CASCADE,
                             related_name='progress_records', verbose_name=_('الهدف'))
    previous_value = models.DecimalField(_('القيمة السابقة'), max_digits=15, decimal_places=2)
    new_value = models.DecimalField(_('القيمة الجديدة'), max_digits=15, decimal_places=2)
    change_amount = models.DecimalField(_('مقدار التغيير'), max_digits=15, decimal_places=2,
                                      editable=False)
    notes = models.TextField(_('ملاحظات'), blank=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                 verbose_name=_('محدث بواسطة'))

    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_('وقت التحديث'))

    class Meta:
        verbose_name = _('تقدم الهدف')
        verbose_name_plural = _('تقدم الأهداف')
        ordering = ['-timestamp']
    
    def save(self, *args, **kwargs):
        self.change_amount = self.new_value - self.previous_value
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.target.title} - {self.timestamp.strftime('%Y-%m-%d')}"


class TeamTarget(models.Model):
    """أهداف الفريق/القسم"""
    
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    team_name = models.CharField(_('اسم الفريق'), max_length=200)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, verbose_name=_('القسم'))
    category = models.ForeignKey(TargetCategory, on_delete=models.CASCADE, verbose_name=_('فئة الهدف'))

    title = models.CharField(_('عنوان الهدف'), max_length=200)
    description = models.TextField(_('وصف الهدف'))

    target_value = models.DecimalField(_('القيمة المستهدفة'), max_digits=15, decimal_places=2)
    current_value = models.DecimalField(_('القيمة الحالية'), max_digits=15, decimal_places=2, default=0)
    unit = models.CharField(_('الوحدة'), max_length=50)

    start_date = models.DateField(_('تاريخ البدء'))
    end_date = models.DateField(_('تاريخ الانتهاء'))

    team_members = models.ManyToManyField(Employee, through='TeamTargetMembership',
                                        verbose_name=_('أعضاء الفريق'))

    status = models.CharField(_('الحالة'), max_length=15,
                            choices=PerformanceTarget.STATUS_CHOICES, default='active')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('هدف فريق')
        verbose_name_plural = _('أهداف الفرق')
    
    def __str__(self):
        return f"{self.team_name} - {self.title}"
    
    @property
    def achievement_percentage(self):
        """نسبة إنجاز الفريق"""
        if self.target_value > 0:
            return min((self.current_value / self.target_value) * 100, 100)
        return 0


class TeamTargetMembership(models.Model):
    """عضوية الفريق في الأهداف"""
    
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    team_target = models.ForeignKey(TeamTarget, on_delete=models.CASCADE)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    contribution_weight = models.DecimalField(_('وزن المساهمة %'), max_digits=5, 
                                            decimal_places=2, default=100)
    individual_target = models.DecimalField(_('الهدف الفردي'), max_digits=15, 
                                          decimal_places=2, null=True, blank=True)
    
    class Meta:
        unique_together = ['team_target', 'employee']


# --- مقاييس الأداء الذكية ---
class PerformanceMetric(models.Model):
    """مقاييس الأداء القابلة للتخصيص"""
    
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    METRIC_TYPES = [
        ('sales_volume', _('حجم المبيعات')),
        ('sales_value', _('قيمة المبيعات')),
        ('production_quantity', _('كمية الإنتاج')),
        ('quality_rate', _('معدل الجودة')),
        ('attendance_rate', _('معدل الحضور')),
        ('customer_satisfaction', _('رضا العملاء')),
        ('cost_efficiency', _('كفاءة التكلفة')),
        ('delivery_time', _('وقت التسليم')),
        ('training_completion', _('إكمال التدريب')),
        ('safety_incidents', _('حوادث السلامة')),
        ('custom', _('مخصص')),
    ]

    name = models.CharField(_('اسم المقياس'), max_length=200)
    metric_type = models.CharField(_('نوع المقياس'), max_length=30, choices=METRIC_TYPES)
    description = models.TextField(_('الوصف'))
    unit = models.CharField(_('الوحدة'), max_length=50)

    # معادلة الحساب
    calculation_formula = models.TextField(_('معادلة الحساب'), blank=True,
                                         help_text=_('معادلة لحساب المقياس تلقائياً'))
    data_source = models.CharField(_('مصدر البيانات'), max_length=100, blank=True)

    # القيم المرجعية
    benchmark_value = models.DecimalField(_('القيمة المرجعية'), max_digits=15, 
                                        decimal_places=2, null=True, blank=True)
    target_value = models.DecimalField(_('القيمة المستهدفة'), max_digits=15, 
                                     decimal_places=2, null=True, blank=True)

    is_higher_better = models.BooleanField(_('الأعلى أفضل'), default=True,
                                         help_text=_('هل القيمة الأعلى أفضل أم الأقل؟'))
    is_active = models.BooleanField(_('نشط'), default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('مقياس أداء')
        verbose_name_plural = _('مقاييس الأداء')
    
    def __str__(self):
        return self.name


class EmployeeMetricValue(models.Model):
    """قيم مقاييس الأداء للموظفين"""
    
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name=_('الموظف'))
    metric = models.ForeignKey(PerformanceMetric, on_delete=models.CASCADE, verbose_name=_('المقياس'))

    value = models.DecimalField(_('القيمة'), max_digits=15, decimal_places=2)
    period_start = models.DateField(_('بداية الفترة'))
    period_end = models.DateField(_('نهاية الفترة'))

    notes = models.TextField(_('ملاحظات'), blank=True)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                  verbose_name=_('مسجل بواسطة'))

    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('قيمة مقياس الأداء')
        verbose_name_plural = _('قيم مقاييس الأداء')
        unique_together = ['employee', 'metric', 'period_start', 'period_end']
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.employee.arabic_name} - {self.metric.name}: {self.value}"


# --- العلاقات العمالية ---
class Complaint(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    STATUS_CHOICES = [
        ('open', _('مفتوحة')),
        ('in_progress', _('قيد المعالجة')),
        ('resolved', _('محلولة')),
        ('closed', _('مغلقة')),
    ]
    employee = models.ForeignKey('Employee', on_delete=models.CASCADE, related_name='complaints', verbose_name=_('الموظف'))
    subject = models.CharField(_('الموضوع'), max_length=200)
    description = models.TextField(_('الوصف'))
    status = models.CharField(_('الحالة'), max_length=20, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('شكوى/ملاحظة')
        verbose_name_plural = _('شكاوى وملاحظات')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.employee.arabic_name} - {self.subject}"

class DisciplinaryAction(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    ACTION_TYPES = [
        ('warning', _('إنذار')),
        ('deduction', _('خصم')),
        ('suspension', _('إيقاف')),
        ('termination', _('إنهاء خدمة')),
    ]
    employee = models.ForeignKey('Employee', on_delete=models.CASCADE, related_name='disciplinary_actions', verbose_name=_('الموظف'))
    action_type = models.CharField(_('نوع الجزاء'), max_length=20, choices=ACTION_TYPES)
    description = models.TextField(_('الوصف'))
    date = models.DateField(_('التاريخ'))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('جزاء/مخالفة')
        verbose_name_plural = _('جزاءات ومخالفات')
        ordering = ['-date']

    def __str__(self):
        return f"{self.employee.arabic_name} - {self.get_action_type_display()} - {self.date}"

# --- السلامة والصحة المهنية HSE ---
class HSEIncident(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    STATUS_CHOICES = [
        ('open', _('مفتوح')),
        ('investigating', _('قيد التحقيق')),
        ('closed', _('مغلق')),
    ]
    date = models.DateField(_('تاريخ الحادث'))
    description = models.TextField(_('الوصف'))
    employee = models.ForeignKey('Employee', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('الموظف'))
    department = models.ForeignKey('Department', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('القسم'))
    status = models.CharField(_('الحالة'), max_length=20, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('حادث سلامة')
        verbose_name_plural = _('حوادث السلامة')
        ordering = ['-date']

    def __str__(self):
        return f"{self.date} - {self.status}"

class HSEInspection(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    date = models.DateField(_('تاريخ التفتيش'))
    location = models.CharField(_('الموقع'), max_length=200)
    findings = models.TextField(_('الملاحظات'))
    actions = models.TextField(_('الإجراءات التصحيحية'), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('تفتيش سلامة')
        verbose_name_plural = _('تفتيشات السلامة')
        ordering = ['-date']

    def __str__(self):
        return f"{self.date} - {self.location}"

class HSETraining(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    title = models.CharField(_('عنوان تدريب السلامة'), max_length=200)
    date = models.DateField(_('التاريخ'))
    participants = models.ManyToManyField('Employee', blank=True, verbose_name=_('المشاركون'))
    status = models.CharField(_('الحالة'), max_length=20, choices=[('planned',_('مخطط')),('done',_('منفذ'))], default='planned')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('تدريب سلامة')
        verbose_name_plural = _('تدريبات السلامة')
        ordering = ['-date']

    def __str__(self):
        return self.title

# --- التدريب والتطوير ---
class TrainingProgram(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    title = models.CharField(max_length=200, verbose_name=_("عنوان البرنامج"))
    description = models.TextField(verbose_name=_("الوصف"))
    provider = models.CharField(max_length=100, verbose_name=_("مقدم التدريب"))
    start_date = models.DateField(verbose_name=_("تاريخ البداية"))
    end_date = models.DateField(verbose_name=_("تاريخ النهاية"))
    duration_hours = models.IntegerField(verbose_name=_("مدة التدريب بالساعات"))
    location = models.CharField(max_length=200, verbose_name=_("المكان"))
    cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("التكلفة"))
    max_participants = models.IntegerField(verbose_name=_("الحد الأقصى للمشاركين"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("برنامج تدريبي")
        verbose_name_plural = _("البرامج التدريبية")
        
    def __str__(self):
        return self.title

class TrainingEnrollment(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    STATUS_CHOICES = [
        ('enrolled', _('مسجل')),
        ('completed', _('مكتمل')),
        ('cancelled', _('ملغي')),
        ('failed', _('راسب')),
    ]
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='training_enrollments', verbose_name=_("الموظف"))
    training_program = models.ForeignKey(TrainingProgram, on_delete=models.CASCADE, related_name='enrollments', verbose_name=_("البرنامج التدريبي"))
    enrollment_date = models.DateField(auto_now_add=True, verbose_name=_("تاريخ التسجيل"))
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='enrolled', verbose_name=_("الحالة"))
    completion_date = models.DateField(null=True, blank=True, verbose_name=_("تاريخ الإكمال"))
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name=_("الدرجة"))
    certificate_file = models.FileField(upload_to='training/certificates/', null=True, blank=True, verbose_name=_("ملف الشهادة"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("تسجيل تدريبي")
        verbose_name_plural = _("التسجيلات التدريبية")
        unique_together = ['employee', 'training_program']
        
    def __str__(self):
        return f"{self.employee.arabic_name} - {self.training_program.title}"

# --- التوظيف وإدارة المتقدمين ---
class JobVacancy(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    STATUS_CHOICES = [
        ('open', _('مفتوحة')),
        ('closed', _('مغلقة')),
        ('on_hold', _('معلقة')),
    ]
    
    position = models.ForeignKey(JobPosition, on_delete=models.CASCADE, verbose_name=_("المنصب"))
    title = models.CharField(max_length=200, verbose_name=_("عنوان الوظيفة"))
    description = models.TextField(verbose_name=_("وصف الوظيفة"))
    requirements = models.TextField(verbose_name=_("المتطلبات"))
    number_of_positions = models.IntegerField(default=1, verbose_name=_("عدد المناصب المطلوبة"))
    salary_range_min = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("الحد الأدنى للراتب"))
    salary_range_max = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("الحد الأقصى للراتب"))
    
    posting_date = models.DateField(verbose_name=_("تاريخ النشر"))
    closing_date = models.DateField(verbose_name=_("تاريخ الإغلاق"))
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='open', verbose_name=_("الحالة"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("وظيفة شاغرة")
        verbose_name_plural = _("الوظائف الشاغرة")
        ordering = ['-posting_date']
        
    def __str__(self):
        return f"{self.title} - {self.position.department.name}"

class JobApplication(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    STATUS_CHOICES = [
        ('submitted', _('مرسل')),
        ('under_review', _('قيد المراجعة')),
        ('interview_scheduled', _('مقابلة محددة')),
        ('interviewed', _('تمت المقابلة')),
        ('accepted', _('مقبول')),
        ('rejected', _('مرفوض')),
        ('withdrawn', _('منسحب')),
    ]
    
    vacancy = models.ForeignKey(JobVacancy, on_delete=models.CASCADE, related_name='applications', verbose_name=_("الوظيفة الشاغرة"))
    
    # بيانات المتقدم
    first_name = models.CharField(max_length=50, verbose_name=_("الاسم الأول"))
    last_name = models.CharField(max_length=50, verbose_name=_("اسم العائلة"))
    email = models.EmailField(verbose_name=_("البريد الإلكتروني"))
    phone = models.CharField(max_length=15, verbose_name=_("الهاتف"))
    address = models.TextField(verbose_name=_("العنوان"))
    
    # ملفات التقديم
    cv_file = models.FileField(upload_to='applications/cvs/', verbose_name=_("ملف السيرة الذاتية"))
    cover_letter = models.TextField(blank=True, verbose_name=_("خطاب التقديم"))
    other_documents = models.FileField(upload_to='applications/documents/', null=True, blank=True, verbose_name=_("مستندات أخرى"))
    
    # معلومات الحالة
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='submitted', verbose_name=_("الحالة"))
    application_date = models.DateTimeField(auto_now_add=True, verbose_name=_("تاريخ التقديم"))
    interview_date = models.DateTimeField(null=True, blank=True, verbose_name=_("تاريخ المقابلة"))
    interview_notes = models.TextField(blank=True, verbose_name=_("ملاحظات المقابلة"))
    rejection_reason = models.TextField(blank=True, verbose_name=_("سبب الرفض"))
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("طلب توظيف")
        verbose_name_plural = _("طلبات التوظيف")
        ordering = ['-application_date']
        
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.vacancy.title}"


# =====================
# سياسات الخصم على الغياب
# =====================
class AbsencePolicy(models.Model):
    """
    سياسات خصم الراتب والإجازات عند الغياب
    """
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, verbose_name=_("اسم السياسة"))
    description = models.TextField(blank=True, verbose_name=_("الوصف"))
    
    # خصم من الإجازات أولاً
    deduct_from_leave_first = models.BooleanField(default=True, verbose_name=_("خصم من الإجازات أولاً"))
    
    # خصم من الراتب
    salary_deduction_per_day = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0'),
        verbose_name=_("خصم يومي من الراتب")
    )
    salary_deduction_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('0'),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name=_("نسبة الخصم من الراتب اليومي %")
    )
    
    # عدد أيام التحذير قبل الخصم
    warning_days = models.PositiveIntegerField(default=0, verbose_name=_("أيام التحذير"))
    
    # غياب بدون عذر - عقوبة مضاعفة
    unauthorized_absence_multiplier = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('2.0'),
        verbose_name=_("مضاعف الخصم للغياب بدون عذر")
    )
    
    is_active = models.BooleanField(default=True, verbose_name=_("نشطة"))
    is_default = models.BooleanField(default=False, verbose_name=_("افتراضية"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("سياسة غياب")
        verbose_name_plural = _("سياسات الغياب")
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if self.is_default:
            AbsencePolicy.objects.filter(is_default=True).exclude(id=self.id).update(is_default=False)
        super().save(*args, **kwargs)
    
    def calculate_deduction(self, employee, days, is_authorized=True):
        """
        حساب قيمة الخصم
        """
        daily_salary = employee.basic_salary / 30  # افتراض 30 يوم
        
        if self.salary_deduction_percentage > 0:
            deduction_per_day = daily_salary * (self.salary_deduction_percentage / 100)
        else:
            deduction_per_day = self.salary_deduction_per_day
        
        total_deduction = deduction_per_day * days
        
        # مضاعفة الخصم للغياب بدون عذر
        if not is_authorized:
            total_deduction *= self.unauthorized_absence_multiplier
        
        return total_deduction


# =====================
# سجل غياب الموظفين
# =====================
class EmployeeAbsence(models.Model):
    """
    سجل الغياب اليومي مع تتبع الخصومات
    """
    ABSENCE_TYPES = [
        ('unauthorized', _('غياب بدون عذر')),
        ('late', _('تأخر')),
        ('leave_exhausted', _('إجازة منتهية')),
        ('sick_no_certificate', _('مرضي بدون شهادة')),
    ]
    
    id = models.AutoField(primary_key=True)
    employee = models.ForeignKey('Employee', on_delete=models.CASCADE, related_name='absences', verbose_name=_("الموظف"))
    absence_date = models.DateField(verbose_name=_("تاريخ الغياب"))
    absence_type = models.CharField(max_length=30, choices=ABSENCE_TYPES, verbose_name=_("نوع الغياب"))
    
    # معلومات الخصم
    deducted_from_leave = models.BooleanField(default=False, verbose_name=_("خُصم من الإجازات"))
    leave_days_deducted = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0'), verbose_name=_("أيام الإجازة المخصومة"))
    
    deducted_from_salary = models.BooleanField(default=False, verbose_name=_("خُصم من الراتب"))
    salary_deduction_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'), verbose_name=_("قيمة الخصم"))
    
    # معالجة الغياب
    is_processed = models.BooleanField(default=False, verbose_name=_("تمت المعالجة"))
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("تاريخ المعالجة"))
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("تمت المعالجة بواسطة"))
    
    notes = models.TextField(blank=True, verbose_name=_("ملاحظات"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("غياب موظف")
        verbose_name_plural = _("سجل الغياب")
        unique_together = [['employee', 'absence_date']]
        ordering = ['-absence_date']
        indexes = [
            models.Index(fields=['employee', 'absence_date']),
            models.Index(fields=['is_processed']),
        ]
    
    def __str__(self):
        return f"{self.employee} - {self.absence_date}"


# =====================
# بطاقات الهوية للموظفين
# =====================
class EmployeeIDCard(models.Model):
    """
    بطاقات هوية الموظفين مع QR Code للدخول
    """
    STATUS_CHOICES = [
        ('active', _('فعالة')),
        ('expired', _('منتهية')),
        ('lost', _('مفقودة')),
        ('replaced', _('تم استبدالها')),
    ]
    
    id = models.AutoField(primary_key=True)
    employee = models.ForeignKey('Employee', on_delete=models.CASCADE, related_name='id_cards', verbose_name=_("الموظف"))
    
    # معلومات البطاقة
    card_number = models.CharField(max_length=50, unique=True, verbose_name=_("رقم البطاقة"))
    qr_code_data = models.TextField(verbose_name=_("بيانات QR Code"), blank=True, default='')  # JWT token
    qr_code_image = models.ImageField(upload_to='id_cards/qr/', null=True, blank=True, verbose_name=_("صورة QR Code"))
    
    # تواريخ الصلاحية
    issue_date = models.DateField(default=timezone.localdate, verbose_name=_("تاريخ الإصدار"))
    expiry_date = models.DateField(verbose_name=_("تاريخ الانتهاء"))
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name=_("الحالة"))
    
    # الطباعة
    printed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("تاريخ الطباعة"))
    printed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='printed_cards', verbose_name=_("طبعت بواسطة"))
    print_count = models.PositiveIntegerField(default=0, verbose_name=_("عدد مرات الطباعة"))
    
    # استخدام QR Code
    last_scan_at = models.DateTimeField(null=True, blank=True, verbose_name=_("آخر مسح"))
    scan_count = models.PositiveIntegerField(default=0, verbose_name=_("عدد المسحات"))
    
    notes = models.TextField(blank=True, verbose_name=_("ملاحظات"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("بطاقة هوية")
        verbose_name_plural = _("بطاقات الهوية")
        ordering = ['-issue_date']
        indexes = [
            models.Index(fields=['card_number']),
            models.Index(fields=['employee', 'status']),
        ]
    
    def __str__(self):
        return f"{self.employee} - {self.card_number}"
    
    def is_valid(self):
        """فحص صلاحية البطاقة"""
        from django.utils import timezone
        return (
            self.status == 'active' and 
            self.expiry_date >= timezone.now().date()
        )
    
    def increment_scan_count(self):
        """زيادة عداد المسحات"""
        from django.utils import timezone
        self.scan_count += 1
        self.last_scan_at = timezone.now()
        self.save(update_fields=['scan_count', 'last_scan_at'])
    
    def increment_print_count(self):
        """زيادة عداد الطباعة"""
        from django.utils import timezone
        self.print_count += 1
        if self.print_count == 1:
            self.printed_at = timezone.now()
        self.save(update_fields=['print_count', 'printed_at'])


class IDCardTemplate(models.Model):
    """
    قوالب تصميم بطاقات التعريف
    """
    ORIENTATION_CHOICES = [
        ('horizontal', _('أفقي')),
        ('vertical', _('عمودي')),
    ]
    
    SIZE_CHOICES = [
        ('pvc', _('PVC قياسي (85.6 × 53.98 مم)')),
        ('a4', _('A4 للطباعة العادية')),
        ('a6', _('A6')),
        ('custom', _('مخصص')),
    ]
    
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, verbose_name=_("اسم القالب"))
    description = models.TextField(blank=True, verbose_name=_("الوصف"))
    is_default = models.BooleanField(default=False, verbose_name=_("افتراضي"))
    is_active = models.BooleanField(default=True, verbose_name=_("نشط"))
    
    # التصميم
    orientation = models.CharField(max_length=20, choices=ORIENTATION_CHOICES, default='horizontal', verbose_name=_("الاتجاه"))
    size = models.CharField(max_length=20, choices=SIZE_CHOICES, default='pvc', verbose_name=_("الحجم"))
    
    # الأبعاد المخصصة (بالمليمتر)
    custom_width = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("العرض (مم)"))
    custom_height = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("الارتفاع (مم)"))
    
    # الألوان
    primary_color = models.CharField(max_length=7, default='#0f172a', verbose_name=_("اللون الأساسي"))
    secondary_color = models.CharField(max_length=7, default='#0ea5e9', verbose_name=_("اللون الثانوي"))
    text_color = models.CharField(max_length=7, default='#ffffff', verbose_name=_("لون النص"))
    background_color = models.CharField(max_length=7, default='#f8fafc', verbose_name=_("لون الخلفية"))
    
    # الشعار والصور
    company_logo = models.ImageField(upload_to='id_cards/logos/', null=True, blank=True, verbose_name=_("شعار الشركة"))
    background_image = models.ImageField(upload_to='id_cards/backgrounds/', null=True, blank=True, verbose_name=_("صورة الخلفية"))
    
    # إعدادات المحتوى
    show_qr_code = models.BooleanField(default=True, verbose_name=_("إظهار QR Code"))
    show_barcode = models.BooleanField(default=True, verbose_name=_("إظهار الباركود"))
    show_photo = models.BooleanField(default=True, verbose_name=_("إظهار الصورة"))
    show_department = models.BooleanField(default=True, verbose_name=_("إظهار القسم"))
    show_position = models.BooleanField(default=True, verbose_name=_("إظهار الوظيفة"))
    show_employee_id = models.BooleanField(default=True, verbose_name=_("إظهار رقم الموظف"))
    show_national_id = models.BooleanField(default=False, verbose_name=_("إظهار الرقم القومي"))
    show_issue_date = models.BooleanField(default=True, verbose_name=_("إظهار تاريخ الإصدار"))
    show_expiry_date = models.BooleanField(default=True, verbose_name=_("إظهار تاريخ الانتهاء"))
    
    # الخطوط
    font_family = models.CharField(max_length=100, default='Arial', verbose_name=_("نوع الخط"))
    name_font_size = models.PositiveIntegerField(default=14, verbose_name=_("حجم خط الاسم"))
    info_font_size = models.PositiveIntegerField(default=10, verbose_name=_("حجم خط المعلومات"))
    
    # تعليمات الظهر
    back_instructions = models.TextField(blank=True, default='''• هذه البطاقة ملك للشركة ويجب إرجاعها عند انتهاء الخدمة
• يجب حمل البطاقة في جميع الأوقات داخل المنشأة
• في حالة الفقد يرجى الإبلاغ فوراً لقسم الموارد البشرية
• عدم إساءة استخدام البطاقة أو إعارتها للغير''', verbose_name=_("تعليمات الظهر"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("أنشئ بواسطة"))
    
    class Meta:
        verbose_name = _("قالب بطاقة هوية")
        verbose_name_plural = _("قوالب بطاقات الهوية")
        ordering = ['-is_default', '-created_at']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        # تأكد من وجود قالب افتراضي واحد فقط
        if self.is_default:
            IDCardTemplate.objects.exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class IDCardBatchPrint(models.Model):
    """
    سجل طباعة دفعات البطاقات
    """
    STATUS_CHOICES = [
        ('pending', _('في الانتظار')),
        ('processing', _('قيد المعالجة')),
        ('completed', _('مكتمل')),
        ('failed', _('فشل')),
    ]
    
    id = models.AutoField(primary_key=True)
    batch_number = models.CharField(max_length=50, unique=True, verbose_name=_("رقم الدفعة"))
    template = models.ForeignKey(IDCardTemplate, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("القالب"))
    
    # البطاقات المطبوعة
    cards = models.ManyToManyField(EmployeeIDCard, related_name='batch_prints', verbose_name=_("البطاقات"))
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name=_("الحالة"))
    total_cards = models.PositiveIntegerField(default=0, verbose_name=_("إجمالي البطاقات"))
    printed_cards = models.PositiveIntegerField(default=0, verbose_name=_("البطاقات المطبوعة"))
    
    # ملف PDF الناتج
    pdf_file = models.FileField(upload_to='id_cards/batches/', null=True, blank=True, verbose_name=_("ملف PDF"))
    
    notes = models.TextField(blank=True, verbose_name=_("ملاحظات"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("تاريخ الإكمال"))
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("أنشئ بواسطة"))
    
    class Meta:
        verbose_name = _("طباعة دفعة بطاقات")
        verbose_name_plural = _("طباعات الدفعات")
        ordering = ['-created_at']
    
    def __str__(self):
        return f"دفعة {self.batch_number} - {self.total_cards} بطاقة"


# === سلف الموظفين ===
class EmployeeLoan(models.Model):
    """
    سلف الموظفين - نظام إدارة السلف والخصم من الراتب
    """
    STATUS_CHOICES = [
        ('pending', _('في الانتظار')),
        ('approved', _('معتمدة')),
        ('rejected', _('مرفوضة')),
        ('active', _('نشطة')),
        ('completed', _('مسددة بالكامل')),
        ('cancelled', _('ملغاة')),
    ]
    
    id = models.AutoField(primary_key=True)
    loan_number = models.CharField(max_length=50, unique=True, verbose_name=_("رقم السلفة"), 
                                    help_text=_("يتم توليده تلقائياً"))
    
    # الموظف
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='loans', 
                                 verbose_name=_("الموظف"))
    
    # تفاصيل السلفة
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_("مبلغ السلفة"))
    reason = models.TextField(verbose_name=_("سبب طلب السلفة"))
    request_date = models.DateField(auto_now_add=True, verbose_name=_("تاريخ الطلب"))
    
    # خطة السداد
    installments_count = models.PositiveIntegerField(default=1, verbose_name=_("عدد الأقساط"),
                                                      help_text=_("عدد الأشهر لتسديد السلفة"))
    monthly_installment = models.DecimalField(max_digits=12, decimal_places=2, 
                                               verbose_name=_("قسط شهري"))
    start_deduction_date = models.DateField(verbose_name=_("تاريخ بدء الخصم"),
                                            help_text=_("الشهر الذي سيبدأ فيه الخصم من الراتب"))
    
    # المبالغ
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'),
                                      verbose_name=_("المبلغ المدفوع"))
    remaining_amount = models.DecimalField(max_digits=12, decimal_places=2, 
                                           verbose_name=_("المبلغ المتبقي"))
    
    # الحالة والموافقات
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending',
                              verbose_name=_("حالة السلفة"))
    approved_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='approved_loans', verbose_name=_("اعتمدها"))
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name=_("تاريخ الاعتماد"))
    rejection_reason = models.TextField(blank=True, verbose_name=_("سبب الرفض"))
    
    # ربط بالقيد المحاسبي
    journal_entry = models.OneToOneField(JournalEntry, on_delete=models.SET_NULL, 
                                         null=True, blank=True, 
                                         verbose_name=_("القيد المحاسبي"))
    
    # معلومات إضافية
    notes = models.TextField(blank=True, verbose_name=_("ملاحظات"))
    is_emergency = models.BooleanField(default=False, verbose_name=_("سلفة طارئة"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   verbose_name=_("أنشئ بواسطة"))
    
    class Meta:
        verbose_name = _("سلفة موظف")
        verbose_name_plural = _("سلف الموظفين")
        ordering = ['-request_date', '-created_at']
        indexes = [
            models.Index(fields=['employee', 'status']),
            models.Index(fields=['loan_number']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.loan_number} - {self.employee.arabic_name} - {self.amount}"
    
    def save(self, *args, **kwargs):
        # توليد رقم السلفة تلقائياً
        if not self.loan_number:
            from django.utils import timezone
            year = timezone.now().year
            month = timezone.now().month
            # الحصول على آخر رقم في الشهر الحالي
            last_loan = EmployeeLoan.objects.filter(
                loan_number__startswith=f'LOAN-{year}{month:02d}'
            ).order_by('-loan_number').first()
            
            if last_loan:
                last_num = int(last_loan.loan_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.loan_number = f'LOAN-{year}{month:02d}-{new_num:04d}'
        
        # حساب القسط الشهري
        if self.installments_count > 0:
            self.monthly_installment = self.amount / Decimal(self.installments_count)
        
        # حساب المبلغ المتبقي
        self.remaining_amount = self.amount - self.paid_amount
        
        super().save(*args, **kwargs)
    
    @property
    def progress_percentage(self):
        """نسبة السداد المئوية"""
        if self.amount > 0:
            return (self.paid_amount / self.amount * 100).quantize(Decimal('0.01'))
        return Decimal('0')
    
    @property
    def is_fully_paid(self):
        """هل تم سداد السلفة بالكامل؟"""
        return self.remaining_amount <= 0


class LoanInstallment(models.Model):
    """
    أقساط السلفة - تسجيل كل قسط يتم خصمه من الراتب
    """
    STATUS_CHOICES = [
        ('pending', _('معلق')),
        ('deducted', _('مخصوم')),
        ('deferred', _('مؤجل')),
        ('waived', _('معفى منه')),
    ]
    
    id = models.AutoField(primary_key=True)
    loan = models.ForeignKey(EmployeeLoan, on_delete=models.CASCADE, related_name='installments',
                             verbose_name=_("السلفة"))
    
    # تفاصيل القسط
    installment_number = models.PositiveIntegerField(verbose_name=_("رقم القسط"))
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_("مبلغ القسط"))
    due_date = models.DateField(verbose_name=_("تاريخ الاستحقاق"))
    
    # حالة السداد
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending',
                              verbose_name=_("الحالة"))
    deduction_date = models.DateField(null=True, blank=True, verbose_name=_("تاريخ الخصم"))
    
    # ربط بالراتب
    payroll = models.ForeignKey(Payroll, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='loan_deductions', verbose_name=_("كشف الراتب"))
    
    # في حالة التأجيل
    deferred_to_date = models.DateField(null=True, blank=True, 
                                        verbose_name=_("مؤجل إلى تاريخ"))
    deferment_reason = models.TextField(blank=True, verbose_name=_("سبب التأجيل"))
    
    notes = models.TextField(blank=True, verbose_name=_("ملاحظات"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("قسط سلفة")
        verbose_name_plural = _("أقساط السلف")
        ordering = ['loan', 'installment_number']
        unique_together = ['loan', 'installment_number']
        indexes = [
            models.Index(fields=['loan', 'status']),
            models.Index(fields=['due_date']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.loan.loan_number} - قسط {self.installment_number}"
    
    @property
    def is_overdue(self):
        """هل القسط متأخر؟"""
        from django.utils import timezone
        return (self.status == 'pending' and 
                self.due_date < timezone.now().date())
    
    def mark_as_deducted(self, payroll_instance):
        """تسجيل خصم القسط من الراتب"""
        from django.utils import timezone
        self.status = 'deducted'
        self.deduction_date = timezone.now().date()
        self.payroll = payroll_instance
        self.save()
        
        # تحديث المبلغ المدفوع في السلفة
        self.loan.paid_amount += self.amount
        self.loan.remaining_amount = self.loan.amount - self.loan.paid_amount
        
        # إذا تم سداد كل الأقساط، تحديث حالة السلفة
        if self.loan.remaining_amount <= 0:
            self.loan.status = 'completed'
        
        self.loan.save()
    
    def defer_installment(self, new_due_date, reason):
        """تأجيل القسط لشهر قادم"""
        self.status = 'deferred'
        self.deferred_to_date = new_due_date
        self.deferment_reason = reason
        self.save()