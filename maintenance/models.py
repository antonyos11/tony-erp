from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from inventory.models import Product, Location
from hr.models import Employee, Department
from accounting.models import Account, JournalEntry, CostCenter
from production.models import ProductionWorkCenter
import uuid


class MachineCategory(models.Model):
    """فئات الماكينات والمعدات"""
    
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    name = models.CharField('اسم الفئة', max_length=200)
    code = models.CharField('كود الفئة', max_length=20, unique=True)
    description = models.TextField('الوصف', blank=True)
    
    # الإعدادات الافتراضية
    default_maintenance_interval_days = models.PositiveIntegerField('فترة الصيانة الافتراضية (أيام)', default=30)
    default_warranty_months = models.PositiveIntegerField('فترة الضمان الافتراضية (شهور)', default=12)
    
    is_active = models.BooleanField('نشط', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'فئة ماكينة'
        verbose_name_plural = 'فئات الماكينات'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class Machine(models.Model):
    """الماكينات والمعدات"""
    
    STATUS_CHOICES = [
        ('operational', 'تعمل'),
        ('maintenance', 'قيد الصيانة'),
        ('breakdown', 'عاطلة'),
        ('retired', 'خارج الخدمة'),
        ('sold', 'مباعة'),
    ]
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    
    CONDITION_CHOICES = [
        ('excellent', 'ممتاز'),
        ('good', 'جيد'),
        ('fair', 'مقبول'),
        ('poor', 'ضعيف'),
        ('critical', 'حرج'),
    ]
    
    # معلومات أساسية
    code = models.CharField('كود الماكينة', max_length=50, unique=True)
    name = models.CharField('اسم الماكينة', max_length=200)
    category = models.ForeignKey(MachineCategory, on_delete=models.CASCADE, verbose_name='الفئة')
    
    # معلومات الشركة المصنعة
    manufacturer = models.CharField('الشركة المصنعة', max_length=200)
    model = models.CharField('الموديل', max_length=100)
    serial_number = models.CharField('الرقم التسلسلي', max_length=100, unique=True)
    year_manufactured = models.PositiveIntegerField('سنة الصنع')
    
    # معلومات الموقع والتشغيل
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='الموقع')
    work_center = models.ForeignKey(ProductionWorkCenter, on_delete=models.SET_NULL, null=True, blank=True, 
                                  verbose_name='مركز العمل')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='القسم')
    
    # الحالة والتشغيل
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='operational')
    condition = models.CharField('حالة الماكينة', max_length=20, choices=CONDITION_CHOICES, default='good')
    operational_hours = models.DecimalField('ساعات التشغيل', max_digits=10, decimal_places=2, default=Decimal('0'))
    
    # معلومات الشراء والضمان
    purchase_date = models.DateField('تاريخ الشراء')
    purchase_price = models.DecimalField('سعر الشراء', max_digits=12, decimal_places=2)
    warranty_start_date = models.DateField('بداية الضمان')
    warranty_end_date = models.DateField('انتهاء الضمان')
    supplier = models.CharField('المورد', max_length=200, blank=True)
    
    # الصيانة
    last_maintenance_date = models.DateField('تاريخ آخر صيانة', null=True, blank=True)
    next_maintenance_date = models.DateField('تاريخ الصيانة القادمة', null=True, blank=True)
    maintenance_interval_days = models.PositiveIntegerField('فترة الصيانة (أيام)', default=30)
    
    # المسؤول عن الماكينة
    responsible_employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True,
                                           verbose_name='المسؤول عن الماكينة')
    
    # ملاحظات وتوثيق
    specifications = models.TextField('المواصفات الفنية', blank=True)
    installation_notes = models.TextField('ملاحظات التركيب', blank=True)
    user_manual_path = models.CharField('مسار دليل المستخدم', max_length=500, blank=True)
    
    # الحسابات المحاسبية
    asset_account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='machine_assets', verbose_name='حساب الأصل')
    depreciation_account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True,
                                           related_name='machine_depreciation', verbose_name='حساب الإهلاك')
    maintenance_expense_account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True,
                                                   related_name='maintenance_expenses', verbose_name='حساب مصروفات الصيانة')
    
    # إعدادات الإهلاك
    depreciation_method = models.CharField('طريقة الإهلاك', max_length=20,
                                         choices=[
                                             ('straight_line', 'القسط الثابت'),
                                             ('declining_balance', 'القسط المتناقص'),
                                             ('units_of_production', 'وحدات الإنتاج')
                                         ], default='straight_line')
    useful_life_years = models.PositiveIntegerField('العمر الافتراضي (سنوات)', default=10)
    salvage_value = models.DecimalField('القيمة التخريدية', max_digits=12, decimal_places=2, default=Decimal('0'))
    
    is_active = models.BooleanField('نشط', default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='أنشئ بواسطة')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'ماكينة'
        verbose_name_plural = 'الماكينات'
        ordering = ['code']
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    @property
    def is_under_warranty(self):
        """هل الماكينة تحت الضمان"""
        return timezone.now().date() <= self.warranty_end_date
    
    @property
    def days_since_last_maintenance(self):
        """عدد الأيام منذ آخر صيانة"""
        if self.last_maintenance_date:
            return (timezone.now().date() - self.last_maintenance_date).days
        return None
    
    @property
    def maintenance_overdue(self):
        """هل الصيانة متأخرة"""
        if self.next_maintenance_date:
            return timezone.now().date() > self.next_maintenance_date
        return False
    
    @property
    def current_book_value(self):
        """القيمة الدفترية الحالية"""
        # حساب مبسط للإهلاك بالقسط الثابت
        years_used = (timezone.now().date() - self.purchase_date).days / 365.25
        if years_used >= self.useful_life_years:
            return self.salvage_value
        
        annual_depreciation = (self.purchase_price - self.salvage_value) / self.useful_life_years
        total_depreciation = min(annual_depreciation * years_used, self.purchase_price - self.salvage_value)
        return self.purchase_price - total_depreciation


class MaintenanceType(models.Model):
    """أنواع الصيانة"""
    
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    name = models.CharField('اسم نوع الصيانة', max_length=200)
    code = models.CharField('الكود', max_length=20, unique=True)
    description = models.TextField('الوصف', blank=True)
    
    # التصنيف
    category = models.CharField('التصنيف', max_length=20,
                              choices=[
                                  ('preventive', 'صيانة وقائية'),
                                  ('corrective', 'صيانة إصلاحية'),
                                  ('emergency', 'صيانة طارئة'),
                                  ('overhaul', 'صيانة شاملة'),
                                  ('calibration', 'معايرة'),
                                  ('inspection', 'فحص'),
                              ], default='preventive')
    
    # التكرار للصيانة الوقائية
    default_interval_days = models.PositiveIntegerField('الفترة الافتراضية (أيام)', default=30)
    
    # التكلفة المتوقعة
    estimated_cost = models.DecimalField('التكلفة المتوقعة', max_digits=10, decimal_places=2, default=Decimal('0'))
    estimated_duration_hours = models.DecimalField('المدة المتوقعة (ساعات)', max_digits=6, decimal_places=2, default=1)
    
    # المهارات المطلوبة
    required_skills = models.TextField('المهارات المطلوبة', blank=True)
    requires_external_service = models.BooleanField('يتطلب خدمة خارجية', default=False)
    
    is_active = models.BooleanField('نشط', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'نوع صيانة'
        verbose_name_plural = 'أنواع الصيانة'
        ordering = ['category', 'name']
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class SparePart(models.Model):
    """قطع الغيار"""
    
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    # معلومات أساسية
    code = models.CharField('كود قطعة الغيار', max_length=50, unique=True)
    name = models.CharField('اسم قطعة الغيار', max_length=200)
    description = models.TextField('الوصف', blank=True)
    
    # ربط بالماكينات
    compatible_machines = models.ManyToManyField(Machine, blank=True, 
                                               verbose_name='الماكينات المتوافقة')
    machine_categories = models.ManyToManyField(MachineCategory, blank=True,
                                              verbose_name='فئات الماكينات المتوافقة')
    
    # معلومات الشركة المصنعة
    manufacturer = models.CharField('الشركة المصنعة', max_length=200, blank=True)
    part_number = models.CharField('رقم القطعة الأصلي', max_length=100, blank=True)
    alternative_part_numbers = models.TextField('أرقام القطع البديلة', blank=True,
                                              help_text='كل رقم في سطر منفصل')
    
    # المخزون
    current_stock = models.DecimalField('المخزون الحالي', max_digits=10, decimal_places=3, default=Decimal('0'))
    minimum_stock = models.DecimalField('الحد الأدنى للمخزون', max_digits=10, decimal_places=3, default=Decimal('1'))
    maximum_stock = models.DecimalField('الحد الأقصى للمخزون', max_digits=10, decimal_places=3, default=Decimal('100'))
    reorder_point = models.DecimalField('نقطة إعادة الطلب', max_digits=10, decimal_places=3, default=Decimal('5'))
    
    # التكلفة والسعر
    unit_cost = models.DecimalField('تكلفة الوحدة', max_digits=10, decimal_places=2, default=Decimal('0'))
    last_purchase_price = models.DecimalField('آخر سعر شراء', max_digits=10, decimal_places=2, default=Decimal('0'))
    average_cost = models.DecimalField('متوسط التكلفة', max_digits=10, decimal_places=2, default=Decimal('0'))
    
    # معلومات الموردين
    primary_supplier = models.CharField('المورد الأساسي', max_length=200, blank=True)
    alternative_suppliers = models.TextField('الموردين البدائل', blank=True,
                                           help_text='كل مورد في سطر منفصل')
    
    # العمر الافتراضي ومعلومات الاستخدام
    expected_life_hours = models.DecimalField('العمر الافتراضي (ساعات)', max_digits=10, decimal_places=2, 
                                            null=True, blank=True)
    shelf_life_months = models.PositiveIntegerField('مدة الصلاحية (شهور)', null=True, blank=True)
    
    # التصنيف
    category = models.CharField('التصنيف', max_length=20,
                              choices=[
                                  ('consumable', 'مستهلكات'),
                                  ('wearing_part', 'قطع تآكل'),
                                  ('component', 'مكونات'),
                                  ('tool', 'أدوات'),
                                  ('filter', 'فلاتر'),
                                  ('lubricant', 'زيوت وشحوم'),
                                  ('electrical', 'قطع كهربائية'),
                                  ('mechanical', 'قطع ميكانيكية'),
                              ], default='component')
    
    # الموقع
    storage_location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True,
                                       verbose_name='موقع التخزين')
    bin_location = models.CharField('موقع الرف', max_length=50, blank=True)
    
    # الحسابات المحاسبية
    inventory_account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True,
                                        related_name='spare_parts_inventory', verbose_name='حساب المخزون')
    expense_account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name='spare_parts_expense', verbose_name='حساب المصروفات')
    
    is_active = models.BooleanField('نشط', default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='أنشئ بواسطة')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'قطعة غيار'
        verbose_name_plural = 'قطع الغيار'
        ordering = ['code']
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    @property
    def needs_reorder(self):
        """هل تحتاج إعادة طلب"""
        return self.current_stock <= self.reorder_point
    
    @property
    def stock_status(self):
        """حالة المخزون"""
        if self.current_stock <= 0:
            return 'out_of_stock'
        elif self.current_stock <= self.minimum_stock:
            return 'low_stock'
        elif self.current_stock <= self.reorder_point:
            return 'reorder_needed'
        elif self.current_stock >= self.maximum_stock:
            return 'overstock'
        else:
            return 'normal'


class MaintenanceRequest(models.Model):
    """طلبات الصيانة"""
    
    STATUS_CHOICES = [
        ('draft', 'مسودة'),
        ('submitted', 'مقدم'),
        ('approved', 'موافق عليه'),
        ('in_progress', 'قيد التنفيذ'),
        ('completed', 'مكتمل'),
        ('cancelled', 'ملغي'),
        ('rejected', 'مرفوض'),
    ]
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    
    PRIORITY_CHOICES = [
        ('low', 'منخفضة'),
        ('normal', 'عادية'),
        ('high', 'عالية'),
        ('urgent', 'عاجل'),
        ('emergency', 'طوارئ'),
    ]
    
    # معلومات الطلب
    request_number = models.CharField('رقم الطلب', max_length=50, unique=True)
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE, verbose_name='الماكينة')
    maintenance_type = models.ForeignKey(MaintenanceType, on_delete=models.CASCADE, verbose_name='نوع الصيانة')
    
    # التفاصيل
    title = models.CharField('عنوان الطلب', max_length=200)
    description = models.TextField('وصف المشكلة/المطلوب')
    problem_symptoms = models.TextField('أعراض المشكلة', blank=True)
    
    # الأولوية والحالة
    priority = models.CharField('الأولوية', max_length=20, choices=PRIORITY_CHOICES, default='normal')
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # التواريخ
    request_date = models.DateTimeField('تاريخ الطلب', default=timezone.now)
    requested_completion_date = models.DateField('التاريخ المطلوب للإنجاز', null=True, blank=True)
    approved_date = models.DateTimeField('تاريخ الموافقة', null=True, blank=True)
    started_date = models.DateTimeField('تاريخ البدء', null=True, blank=True)
    completed_date = models.DateTimeField('تاريخ الإنجاز', null=True, blank=True)
    
    # الأشخاص المعنيين
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='maintenance_requests',
                                   verbose_name='مقدم الطلب')
    assigned_to = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='assigned_maintenance_requests', verbose_name='مسند إلى')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='approved_maintenance_requests', verbose_name='موافق بواسطة')
    
    # التكلفة المتوقعة
    estimated_cost = models.DecimalField('التكلفة المتوقعة', max_digits=10, decimal_places=2, default=Decimal('0'))
    estimated_duration_hours = models.DecimalField('المدة المتوقعة (ساعات)', max_digits=6, decimal_places=2, default=1)
    
    # التكلفة الفعلية (يتم تحديثها من سجل الصيانة)
    actual_cost = models.DecimalField('التكلفة الفعلية', max_digits=10, decimal_places=2, default=Decimal('0'))
    actual_duration_hours = models.DecimalField('المدة الفعلية (ساعات)', max_digits=6, decimal_places=2, default=0)
    
    # ملاحظات
    notes = models.TextField('ملاحظات', blank=True)
    cancellation_reason = models.TextField('سبب الإلغاء', blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'طلب صيانة'
        verbose_name_plural = 'طلبات الصيانة'
        ordering = ['-request_date']
    
    def __str__(self):
        return f"{self.request_number} - {self.title}"
    
    def save(self, *args, **kwargs):
        if not self.request_number:
            # إنشاء رقم تلقائي للطلب
            today = timezone.now().date()
            count = MaintenanceRequest.objects.filter(request_date__date=today).count() + 1
            self.request_number = f"MR{today.strftime('%Y%m%d')}-{count:04d}"
        super().save(*args, **kwargs)


class MaintenanceSchedule(models.Model):
    """جدولة الصيانة الدورية"""
    
    FREQUENCY_CHOICES = [
        ('daily', 'يومي'),
        ('weekly', 'أسبوعي'),
        ('monthly', 'شهري'),
        ('quarterly', 'ربع سنوي'),
        ('semi_annual', 'نصف سنوي'),
        ('annual', 'سنوي'),
        ('custom', 'مخصص'),
    ]
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    
    # معلومات الجدولة
    name = models.CharField('اسم الجدولة', max_length=200)
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE, verbose_name='الماكينة')
    maintenance_type = models.ForeignKey(MaintenanceType, on_delete=models.CASCADE, verbose_name='نوع الصيانة')
    
    # التكرار
    frequency = models.CharField('التكرار', max_length=20, choices=FREQUENCY_CHOICES, default='monthly')
    interval_days = models.PositiveIntegerField('الفترة (أيام)', help_text='للتكرار المخصص')
    
    # التواريخ
    start_date = models.DateField('تاريخ البدء')
    end_date = models.DateField('تاريخ الانتهاء', null=True, blank=True)
    last_generated_date = models.DateField('آخر تاريخ إنشاء', null=True, blank=True)
    next_due_date = models.DateField('التاريخ القادم المستحق')
    
    # الإعدادات
    auto_generate_requests = models.BooleanField('إنشاء طلبات تلقائي', default=True)
    advance_notice_days = models.PositiveIntegerField('إشعار مسبق (أيام)', default=7)
    
    # التكلفة والمدة المتوقعة
    estimated_cost = models.DecimalField('التكلفة المتوقعة', max_digits=10, decimal_places=2, default=Decimal('0'))
    estimated_duration_hours = models.DecimalField('المدة المتوقعة (ساعات)', max_digits=6, decimal_places=2, default=1)
    
    # المسؤول
    assigned_to = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True,
                                  verbose_name='المسند إلى')
    
    # الملاحظات
    description = models.TextField('الوصف', blank=True)
    checklist_template = models.TextField('قائمة الفحص', blank=True,
                                        help_text='كل بند في سطر منفصل')
    
    is_active = models.BooleanField('نشط', default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='أنشئ بواسطة')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'جدولة صيانة'
        verbose_name_plural = 'جدولة الصيانة'
        ordering = ['next_due_date']
    
    def __str__(self):
        return f"{self.name} - {self.machine.name}"
    
    @property
    def is_due(self):
        """هل مستحقة الآن"""
        return timezone.now().date() >= self.next_due_date
    
    @property
    def days_until_due(self):
        """عدد الأيام المتبقية"""
        return (self.next_due_date - timezone.now().date()).days
    
    def calculate_next_due_date(self):
        """حساب التاريخ القادم المستحق"""
        if self.frequency == 'daily':
            return self.next_due_date + timezone.timedelta(days=1)
        elif self.frequency == 'weekly':
            return self.next_due_date + timezone.timedelta(weeks=1)
        elif self.frequency == 'monthly':
            return self.next_due_date + timezone.timedelta(days=30)
        elif self.frequency == 'quarterly':
            return self.next_due_date + timezone.timedelta(days=90)
        elif self.frequency == 'semi_annual':
            return self.next_due_date + timezone.timedelta(days=180)
        elif self.frequency == 'annual':
            return self.next_due_date + timezone.timedelta(days=365)
        elif self.frequency == 'custom':
            return self.next_due_date + timezone.timedelta(days=self.interval_days)
        return self.next_due_date


class MaintenanceRecord(models.Model):
    """سجل الصيانة المنفذة"""
    
    STATUS_CHOICES = [
        ('in_progress', 'قيد التنفيذ'),
        ('completed', 'مكتمل'),
        ('partially_completed', 'مكتمل جزئياً'),
        ('cancelled', 'ملغي'),
    ]
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    
    RESULT_CHOICES = [
        ('successful', 'ناجح'),
        ('partially_successful', 'ناجح جزئياً'),
        ('unsuccessful', 'غير ناجح'),
        ('requires_followup', 'يحتاج متابعة'),
    ]
    
    # ربط بالطلب (اختياري)
    maintenance_request = models.ForeignKey(MaintenanceRequest, on_delete=models.SET_NULL, null=True, blank=True,
                                          related_name='maintenance_records', verbose_name='طلب الصيانة')
    
    # معلومات أساسية
    record_number = models.CharField('رقم السجل', max_length=50, unique=True)
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE, related_name='maintenance_records',
                              verbose_name='الماكينة')
    maintenance_type = models.ForeignKey(MaintenanceType, on_delete=models.CASCADE, verbose_name='نوع الصيانة')
    
    # التواريخ والأوقات
    start_datetime = models.DateTimeField('تاريخ ووقت البدء')
    end_datetime = models.DateTimeField('تاريخ ووقت الانتهاء', null=True, blank=True)
    
    # الحالة والنتيجة
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='in_progress')
    result = models.CharField('النتيجة', max_length=20, choices=RESULT_CHOICES, null=True, blank=True)
    
    # العمل المنفذ
    work_performed = models.TextField('العمل المنفذ')
    problems_found = models.TextField('المشاكل التي تم اكتشافها', blank=True)
    solutions_applied = models.TextField('الحلول المطبقة', blank=True)
    
    # فريق العمل
    technician = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='maintenance_work',
                                 verbose_name='الفني المسؤول')
    assistant_technicians = models.ManyToManyField(Employee, blank=True, 
                                                 related_name='assisted_maintenance_work',
                                                 verbose_name='الفنيين المساعدين')
    
    # التكاليف
    labor_cost = models.DecimalField('تكلفة العمالة', max_digits=10, decimal_places=2, default=Decimal('0'))
    parts_cost = models.DecimalField('تكلفة قطع الغيار', max_digits=10, decimal_places=2, default=Decimal('0'))
    external_service_cost = models.DecimalField('تكلفة الخدمات الخارجية', max_digits=10, decimal_places=2, default=Decimal('0'))
    other_costs = models.DecimalField('تكاليف أخرى', max_digits=10, decimal_places=2, default=Decimal('0'))
    
    # قطع الغيار المستخدمة (سيتم ربطها بـ SparePartUsage)
    
    # حالة الماكينة قبل وبعد الصيانة
    machine_condition_before = models.CharField('حالة الماكينة قبل الصيانة', max_length=20,
                                              choices=Machine.CONDITION_CHOICES)
    machine_condition_after = models.CharField('حالة الماكينة بعد الصيانة', max_length=20,
                                             choices=Machine.CONDITION_CHOICES)
    
    # ملاحظات
    notes = models.TextField('ملاحظات', blank=True)
    recommendations = models.TextField('التوصيات', blank=True)
    next_maintenance_notes = models.TextField('ملاحظات للصيانة القادمة', blank=True)
    
    # المرفقات (مسارات الملفات)
    photos_before = models.TextField('صور قبل الصيانة', blank=True, 
                                   help_text='مسارات الصور، كل مسار في سطر منفصل')
    photos_after = models.TextField('صور بعد الصيانة', blank=True,
                                  help_text='مسارات الصور، كل مسار في سطر منفصل')
    documents = models.TextField('المستندات', blank=True,
                               help_text='مسارات المستندات، كل مسار في سطر منفصل')
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='أنشئ بواسطة')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'سجل صيانة'
        verbose_name_plural = 'سجلات الصيانة'
        ordering = ['-start_datetime']
    
    def __str__(self):
        return f"{self.record_number} - {self.machine.name}"
    
    @property
    def duration_hours(self):
        """مدة الصيانة بالساعات"""
        if self.end_datetime and self.start_datetime:
            delta = self.end_datetime - self.start_datetime
            return delta.total_seconds() / 3600
        return 0
    
    @property
    def total_cost(self):
        """إجمالي التكلفة"""
        return self.labor_cost + self.parts_cost + self.external_service_cost + self.other_costs
    
    def save(self, *args, **kwargs):
        if not self.record_number:
            # إنشاء رقم تلقائي للسجل
            today = timezone.now().date()
            count = MaintenanceRecord.objects.filter(start_datetime__date=today).count() + 1
            self.record_number = f"MR{today.strftime('%Y%m%d')}-{count:04d}"
        super().save(*args, **kwargs)


class SparePartUsage(models.Model):
    """استخدام قطع الغيار في الصيانة"""
    
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    maintenance_record = models.ForeignKey(MaintenanceRecord, on_delete=models.CASCADE, 
                                         related_name='spare_parts_used',
                                         verbose_name='سجل الصيانة')
    spare_part = models.ForeignKey(SparePart, on_delete=models.CASCADE, verbose_name='قطعة الغيار')
    
    # الكمية والتكلفة
    quantity_used = models.DecimalField('الكمية المستخدمة', max_digits=10, decimal_places=3)
    unit_cost = models.DecimalField('تكلفة الوحدة', max_digits=10, decimal_places=2)
    total_cost = models.DecimalField('إجمالي التكلفة', max_digits=10, decimal_places=2, editable=False)
    
    # سبب الاستخدام
    reason = models.CharField('السبب', max_length=20,
                            choices=[
                                ('replacement', 'استبدال'),
                                ('repair', 'إصلاح'),
                                ('upgrade', 'ترقية'),
                                ('preventive', 'وقائية'),
                                ('consumable', 'مستهلكات'),
                            ], default='replacement')
    
    # ملاحظات
    notes = models.TextField('ملاحظات', blank=True)
    
    # قطعة الغيار المستبدلة (إن وجدت)
    replaced_part_condition = models.CharField('حالة القطعة المستبدلة', max_length=20,
                                             choices=[
                                                 ('scrap', 'تالف'),
                                                 ('repairable', 'قابل للإصلاح'),
                                                 ('reusable', 'قابل للاستخدام'),
                                                 ('returned', 'مرتجع للمورد'),
                                             ], blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'استخدام قطعة غيار'
        verbose_name_plural = 'استخدام قطع الغيار'
    
    def __str__(self):
        return f"{self.spare_part.name} - {self.maintenance_record.record_number}"
    
    def save(self, *args, **kwargs):
        self.total_cost = self.quantity_used * self.unit_cost
        super().save(*args, **kwargs)


class MaintenanceChecklist(models.Model):
    """قوائم فحص الصيانة"""
    
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    name = models.CharField('اسم قائمة الفحص', max_length=200)
    maintenance_type = models.ForeignKey(MaintenanceType, on_delete=models.CASCADE, verbose_name='نوع الصيانة')
    machine_category = models.ForeignKey(MachineCategory, on_delete=models.SET_NULL, null=True, blank=True,
                                       verbose_name='فئة الماكينة')
    
    # قائمة الفحص
    checklist_items = models.TextField('عناصر قائمة الفحص',
                                     help_text='كل عنصر في سطر منفصل')
    
    # ملاحظات
    instructions = models.TextField('تعليمات', blank=True)
    safety_notes = models.TextField('ملاحظات السلامة', blank=True)
    
    is_active = models.BooleanField('نشط', default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='أنشئ بواسطة')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'قائمة فحص صيانة'
        verbose_name_plural = 'قوائم فحص الصيانة'
    
    def __str__(self):
        return self.name


class ChecklistExecution(models.Model):
    """تنفيذ قائمة الفحص"""
    
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    maintenance_record = models.ForeignKey(MaintenanceRecord, on_delete=models.CASCADE,
                                         related_name='checklist_executions',
                                         verbose_name='سجل الصيانة')
    checklist = models.ForeignKey(MaintenanceChecklist, on_delete=models.CASCADE, verbose_name='قائمة الفحص')
    
    # النتائج
    results = models.TextField('النتائج', 
                             help_text='نتيجة كل عنصر في سطر منفصل (OK/NOK/N/A)')
    
    # الملاحظات
    notes = models.TextField('ملاحظات', blank=True)
    issues_found = models.TextField('المشاكل المكتشفة', blank=True)
    
    # التوقيع
    executed_by = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name='منفذ بواسطة')
    execution_datetime = models.DateTimeField('تاريخ ووقت التنفيذ')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'تنفيذ قائمة فحص'
        verbose_name_plural = 'تنفيذ قوائم الفحص'
    
    def __str__(self):
        return f"{self.checklist.name} - {self.maintenance_record.record_number}"