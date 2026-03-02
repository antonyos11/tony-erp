"""
نماذج الموارد البشرية — RITA ERP
"""
from django.db import models
from apps.core.models import AuditMixin


class Department(AuditMixin):
    """الأقسام"""
    name = models.CharField(max_length=255, verbose_name="اسم القسم")
    branch = models.ForeignKey('core.Branch', on_delete=models.PROTECT, verbose_name="الفرع")
    manager = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='managed_departments', verbose_name="المدير")
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True,
                               related_name='children', verbose_name="القسم الأب")
    is_active = models.BooleanField(default=True, verbose_name="نشط")

    class Meta:
        verbose_name = "قسم"
        verbose_name_plural = "الأقسام"

    def __str__(self):
        return self.name


class JobTitle(models.Model):
    """المسميات الوظيفية"""
    name = models.CharField(max_length=255, verbose_name="المسمى الوظيفي")
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='job_titles', verbose_name="القسم")
    min_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="الحد الأدنى للراتب")
    max_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="الحد الأقصى للراتب")
    is_active = models.BooleanField(default=True, verbose_name="نشط")

    class Meta:
        verbose_name = "مسمى وظيفي"
        verbose_name_plural = "المسميات الوظيفية"

    def __str__(self):
        return self.name


class Employee(AuditMixin):
    """الموظف — مرتبط بـ User"""
    EMPLOYMENT_TYPES = [
        ('full_time', 'دوام كامل'),
        ('part_time', 'دوام جزئي'),
        ('contract', 'تعاقد'),
        ('daily', 'يومية'),
        ('production', 'إنتاج بالقطعة'),
    ]
    MARITAL_STATUSES = [
        ('single', 'أعزب'),
        ('married', 'متزوج'),
        ('divorced', 'مطلق'),
        ('widowed', 'أرمل'),
    ]

    user = models.OneToOneField('core.User', on_delete=models.CASCADE, related_name='employee',
                                verbose_name="حساب المستخدم")
    employee_number = models.CharField(max_length=20, unique=True, verbose_name="الرقم الوظيفي")
    full_name_ar = models.CharField(max_length=255, verbose_name="الاسم بالعربي")
    full_name_en = models.CharField(max_length=255, blank=True, verbose_name="الاسم بالإنجليزي")
    national_id = models.CharField(max_length=14, unique=True, verbose_name="الرقم القومي")
    date_of_birth = models.DateField(verbose_name="تاريخ الميلاد")
    gender = models.CharField(max_length=10, choices=[('male', 'ذكر'), ('female', 'أنثى')], verbose_name="الجنس")
    marital_status = models.CharField(max_length=15, choices=MARITAL_STATUSES, default='single', verbose_name="الحالة الاجتماعية")
    phone = models.CharField(max_length=20, verbose_name="الهاتف")
    phone2 = models.CharField(max_length=20, blank=True, verbose_name="هاتف 2")
    address = models.TextField(verbose_name="العنوان")
    governorate = models.CharField(max_length=100, verbose_name="المحافظة")
    emergency_contact = models.CharField(max_length=255, blank=True, verbose_name="شخص للطوارئ")
    emergency_phone = models.CharField(max_length=20, blank=True, verbose_name="هاتف الطوارئ")

    # بيانات وظيفية
    branch = models.ForeignKey('core.Branch', on_delete=models.PROTECT, verbose_name="الفرع")
    department = models.ForeignKey(Department, on_delete=models.PROTECT, verbose_name="القسم")
    job_title = models.ForeignKey(JobTitle, on_delete=models.PROTECT, verbose_name="المسمى الوظيفي")
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPES, default='full_time', verbose_name="نوع التوظيف")
    hire_date = models.DateField(verbose_name="تاريخ التعيين")
    contract_end_date = models.DateField(null=True, blank=True, verbose_name="نهاية التعاقد")
    direct_manager = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name='subordinates', verbose_name="المدير المباشر")

    # بيانات مالية
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="الراتب الأساسي")
    housing_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="بدل سكن")
    transport_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="بدل مواصلات")
    food_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="بدل وجبات")
    other_allowances = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="بدلات أخرى")
    social_insurance_number = models.CharField(max_length=20, blank=True, verbose_name="رقم التأمين الاجتماعي")
    social_insurance_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="خصم التأمين")
    tax_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="خصم الضريبة")
    bank_name = models.CharField(max_length=100, blank=True, verbose_name="البنك")
    bank_account = models.CharField(max_length=50, blank=True, verbose_name="رقم الحساب البنكي")

    # بيانات للعمالة اليومية/الإنتاج
    daily_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="الأجر اليومي")
    piece_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="أجر القطعة")
    production_line = models.ForeignKey('production.ProductionLine', on_delete=models.SET_NULL,
                                        null=True, blank=True, verbose_name="خط الإنتاج")

    is_active = models.BooleanField(default=True, verbose_name="نشط")
    termination_date = models.DateField(null=True, blank=True, verbose_name="تاريخ انتهاء الخدمة")
    termination_reason = models.TextField(blank=True, verbose_name="سبب الإنهاء")
    photo = models.ImageField(upload_to='employees/', null=True, blank=True, verbose_name="الصورة")

    class Meta:
        verbose_name = "موظف"
        verbose_name_plural = "الموظفون"
        ordering = ['employee_number']

    def __str__(self):
        return f"{self.employee_number} - {self.full_name_ar}"

    @property
    def gross_salary(self):
        """إجمالي الراتب"""
        return self.basic_salary + self.housing_allowance + self.transport_allowance + self.food_allowance + self.other_allowances

    @property
    def net_salary(self):
        """صافي الراتب"""
        return self.gross_salary - self.social_insurance_deduction - self.tax_deduction


class Attendance(AuditMixin):
    """الحضور والانصراف"""
    ATTENDANCE_STATUSES = [
        ('present', 'حاضر'),
        ('absent', 'غائب'),
        ('late', 'متأخر'),
        ('early_leave', 'انصراف مبكر'),
        ('sick_leave', 'إجازة مرضية'),
        ('annual_leave', 'إجازة سنوية'),
        ('unpaid_leave', 'إجازة بدون راتب'),
        ('official_holiday', 'عطلة رسمية'),
        ('friday', 'جمعة'),
        ('mission', 'مأمورية'),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='attendances', verbose_name="الموظف")
    date = models.DateField(verbose_name="التاريخ")
    status = models.CharField(max_length=20, choices=ATTENDANCE_STATUSES, default='present', verbose_name="الحالة")
    check_in = models.TimeField(null=True, blank=True, verbose_name="وقت الحضور")
    check_out = models.TimeField(null=True, blank=True, verbose_name="وقت الانصراف")
    overtime_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="ساعات إضافية")
    late_minutes = models.IntegerField(default=0, verbose_name="دقائق تأخير")
    notes = models.TextField(blank=True, verbose_name="ملاحظات")

    class Meta:
        verbose_name = "حضور"
        verbose_name_plural = "سجل الحضور والانصراف"
        unique_together = ['employee', 'date']
        ordering = ['-date']

    def __str__(self):
        return f"{self.employee} - {self.date} - {self.get_status_display()}"


class LeaveRequest(AuditMixin):
    """طلبات الإجازات"""
    LEAVE_TYPES = [
        ('annual', 'سنوية'),
        ('sick', 'مرضية'),
        ('unpaid', 'بدون راتب'),
        ('emergency', 'طارئة'),
        ('maternity', 'أمومة'),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_requests', verbose_name="الموظف")
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPES, verbose_name="نوع الإجازة")
    start_date = models.DateField(verbose_name="من تاريخ")
    end_date = models.DateField(verbose_name="إلى تاريخ")
    days_count = models.IntegerField(verbose_name="عدد الأيام")
    reason = models.TextField(verbose_name="السبب")
    status = models.CharField(max_length=20, choices=[
        ('pending', 'في الانتظار'),
        ('approved', 'موافق'),
        ('rejected', 'مرفوض'),
        ('cancelled', 'ملغي'),
    ], default='pending', verbose_name="الحالة")
    approved_by = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='approved_leaves', verbose_name="اعتمده")
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الاعتماد")
    rejection_reason = models.TextField(blank=True, verbose_name="سبب الرفض")

    class Meta:
        verbose_name = "طلب إجازة"
        verbose_name_plural = "طلبات الإجازات"
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.employee} - {self.get_leave_type_display()} ({self.days_count} يوم)"


class LeaveBalance(models.Model):
    """أرصدة الإجازات"""
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_balances', verbose_name="الموظف")
    year = models.IntegerField(verbose_name="السنة")
    annual_balance = models.IntegerField(default=21, verbose_name="رصيد سنوي")
    sick_balance = models.IntegerField(default=7, verbose_name="رصيد مرضي")
    used_annual = models.IntegerField(default=0, verbose_name="مستخدم سنوي")
    used_sick = models.IntegerField(default=0, verbose_name="مستخدم مرضي")
    carried_over = models.IntegerField(default=0, verbose_name="مرحّل من العام السابق")

    class Meta:
        verbose_name = "رصيد إجازات"
        verbose_name_plural = "أرصدة الإجازات"
        unique_together = ['employee', 'year']

    def __str__(self):
        return f"{self.employee} - {self.year}"

    @property
    def remaining_annual(self):
        return self.annual_balance + self.carried_over - self.used_annual

    @property
    def remaining_sick(self):
        return self.sick_balance - self.used_sick


class Penalty(AuditMixin):
    """الجزاءات والمكافآت"""
    PENALTY_TYPES = [
        ('warning', 'إنذار'),
        ('deduction', 'خصم'),
        ('suspension', 'إيقاف'),
        ('bonus', 'مكافأة'),
        ('incentive', 'حافز'),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='penalties', verbose_name="الموظف")
    penalty_type = models.CharField(max_length=20, choices=PENALTY_TYPES, verbose_name="النوع")
    date = models.DateField(verbose_name="التاريخ")
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="المبلغ")
    days = models.IntegerField(default=0, verbose_name="عدد الأيام (للإيقاف)")
    reason = models.TextField(verbose_name="السبب")
    approved_by = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="اعتمده")

    class Meta:
        verbose_name = "جزاء / مكافأة"
        verbose_name_plural = "الجزاءات والمكافآت"
        ordering = ['-date']

    def __str__(self):
        return f"{self.employee} - {self.get_penalty_type_display()} - {self.date}"


class SalaryAdvance(AuditMixin):
    """السلف"""
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='advances', verbose_name="الموظف")
    date = models.DateField(verbose_name="التاريخ")
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="المبلغ")
    reason = models.TextField(verbose_name="السبب")
    deduction_months = models.IntegerField(default=1, verbose_name="عدد أشهر الخصم")
    monthly_deduction = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="القسط الشهري")
    remaining_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="المتبقي")
    status = models.CharField(max_length=20, choices=[
        ('pending', 'في الانتظار'),
        ('approved', 'موافق'),
        ('rejected', 'مرفوض'),
        ('fully_paid', 'مسدد بالكامل'),
    ], default='pending', verbose_name="الحالة")
    approved_by = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="اعتمده")
    journal_entry = models.ForeignKey('accounts.JournalEntry', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="القيد")

    class Meta:
        verbose_name = "سلفة"
        verbose_name_plural = "السلف"
        ordering = ['-date']

    def __str__(self):
        return f"{self.employee} - {self.amount} - {self.date}"


class Payroll(AuditMixin):
    """مسيّر الرواتب الشهري"""
    PAYROLL_STATUSES = [
        ('draft', 'مسودة'),
        ('calculated', 'محسوب'),
        ('approved', 'معتمد'),
        ('paid', 'مدفوع'),
        ('cancelled', 'ملغي'),
    ]

    month = models.IntegerField(verbose_name="الشهر")
    year = models.IntegerField(verbose_name="السنة")
    branch = models.ForeignKey('core.Branch', on_delete=models.PROTECT, verbose_name="الفرع")
    status = models.CharField(max_length=20, choices=PAYROLL_STATUSES, default='draft', verbose_name="الحالة")
    total_gross = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="إجمالي الرواتب")
    total_deductions = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="إجمالي الخصومات")
    total_net = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="صافي الرواتب")
    total_bonuses = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="إجمالي المكافآت")
    total_overtime = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="إجمالي الإضافي")
    journal_entry = models.ForeignKey('accounts.JournalEntry', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="القيد")
    paid_date = models.DateField(null=True, blank=True, verbose_name="تاريخ الصرف")
    notes = models.TextField(blank=True, verbose_name="ملاحظات")

    class Meta:
        verbose_name = "مسيّر رواتب"
        verbose_name_plural = "مسيّرات الرواتب"
        unique_together = ['month', 'year', 'branch']
        ordering = ['-year', '-month']

    def __str__(self):
        return f"رواتب {self.month}/{self.year} - {self.branch}"


class PayrollLine(models.Model):
    """سطر مسيّر الرواتب — راتب موظف واحد"""
    payroll = models.ForeignKey(Payroll, on_delete=models.CASCADE, related_name='lines', verbose_name="المسيّر")
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, verbose_name="الموظف")

    # الراتب
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="الأساسي")
    housing_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="بدل سكن")
    transport_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="بدل مواصلات")
    food_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="بدل وجبات")
    other_allowances = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="بدلات أخرى")

    # الإضافات
    overtime_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="ساعات إضافية")
    overtime_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="مبلغ الإضافي")
    bonus = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="مكافأة")
    incentive = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="حافز")
    commission = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="عمولة")

    # الخصومات
    absence_days = models.IntegerField(default=0, verbose_name="أيام غياب")
    absence_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="خصم غياب")
    late_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="خصم تأخير")
    penalty_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="خصم جزاءات")
    advance_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="خصم سلفة")
    social_insurance = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="تأمين اجتماعي")
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="ضريبة")
    other_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="خصومات أخرى")

    # الإجماليات
    gross_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="الإجمالي")
    total_additions = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="إجمالي الإضافات")
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="إجمالي الخصومات")
    net_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="الصافي")

    # أيام العمل
    working_days = models.IntegerField(default=26, verbose_name="أيام العمل")
    actual_days = models.IntegerField(default=0, verbose_name="أيام الحضور الفعلي")

    class Meta:
        verbose_name = "سطر مسيّر"
        verbose_name_plural = "سطور المسيّر"
        unique_together = ['payroll', 'employee']

    def __str__(self):
        return f"{self.payroll} - {self.employee}"


class ProductionPieceWork(AuditMixin):
    """عمل بالقطعة — لعمال الإنتاج"""
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='piece_works', verbose_name="الموظف")
    date = models.DateField(verbose_name="التاريخ")
    production_order = models.ForeignKey('production.ProductionOrder', on_delete=models.SET_NULL,
                                         null=True, blank=True, verbose_name="أمر الإنتاج")
    product = models.ForeignKey('inventory.Product', on_delete=models.PROTECT, verbose_name="المنتج")
    quantity = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="الكمية")
    rate = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="سعر القطعة")
    total = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="الإجمالي")
    is_approved = models.BooleanField(default=False, verbose_name="معتمد")

    class Meta:
        verbose_name = "عمل بالقطعة"
        verbose_name_plural = "أعمال بالقطعة"
        ordering = ['-date']

    def __str__(self):
        return f"{self.employee} - {self.product} - {self.date}"
