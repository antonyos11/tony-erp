from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from inventory.models import Product, Location
from hr.models import Employee, Department
from accounting.models import Account, JournalEntry, CostCenter
import uuid


class ProductionSettings(models.Model):
    """إعدادات نظام الإنتاج"""
    
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    company_name = models.CharField('اسم المصنع', max_length=200, default='مصنع المراتب والمفروشات')
    default_work_center = models.ForeignKey('ProductionWorkCenter', on_delete=models.SET_NULL, 
                                          null=True, blank=True, verbose_name='مركز العمل الافتراضي')
    
    # حسابات محاسبية للإنتاج
    wip_account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='production_wip', verbose_name='حساب الإنتاج تحت التشغيل')
    finished_goods_account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True,
                                             related_name='finished_goods', verbose_name='حساب البضائع التامة')
    raw_materials_account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True,
                                            related_name='raw_materials', verbose_name='حساب المواد الخام')
    labor_cost_account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True,
                                         related_name='labor_costs', verbose_name='حساب تكلفة العمالة')
    overhead_account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name='overhead_costs', verbose_name='حساب التكاليف الإضافية')
    
    # إعدادات التكلفة
    overhead_allocation_method = models.CharField('طريقة توزيع التكاليف الإضافية', max_length=20,
                                                 choices=[
                                                     ('labor_hours', 'ساعات العمل'),
                                                     ('labor_cost', 'تكلفة العمالة'),
                                                     ('material_cost', 'تكلفة المواد'),
                                                     ('machine_hours', 'ساعات التشغيل')
                                                 ], default='labor_hours')
    overhead_rate = models.DecimalField('معدل التكاليف الإضافية', max_digits=8, decimal_places=4, default=1.5)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'إعدادات الإنتاج'
        verbose_name_plural = 'إعدادات الإنتاج'
    
    def __str__(self):
        return self.company_name


class ProductionWorkCenter(models.Model):
    """مراكز العمل في المصنع"""
    
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    WORK_CENTER_TYPES = [
        ('cutting', 'قسم التقطيع'),
        ('sewing', 'قسم الخياطة'),  
        ('filling', 'قسم الحشو'),
        ('assembly', 'قسم التجميع'),
        ('finishing', 'قسم التشطيب'),
        ('quality', 'قسم الجودة'),
        ('packaging', 'قسم التعبئة'),
        ('warehouse', 'المخزن'),
        ('maintenance', 'الصيانة'),
    ]
    
    code = models.CharField('كود المركز', max_length=20, unique=True)
    name = models.CharField('اسم مركز العمل', max_length=200)
    work_center_type = models.CharField('نوع المركز', max_length=20, choices=WORK_CENTER_TYPES)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True,
                                 verbose_name='القسم المرتبط')
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True,
                               verbose_name='الموقع')
    supervisor = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True,
                                 verbose_name='المشرف')
    
    # معدلات التكلفة
    hourly_rate = models.DecimalField('معدل الساعة', max_digits=10, decimal_places=2, default=Decimal('0'))
    setup_time = models.DecimalField('وقت الإعداد (دقيقة)', max_digits=8, decimal_places=2, default=0)
    efficiency_rate = models.DecimalField('معدل الكفاءة %', max_digits=5, decimal_places=2, default=100.00,
                                        validators=[MinValueValidator(1), MaxValueValidator(200)])
    
    # السعة والقدرة
    capacity_per_hour = models.DecimalField('السعة في الساعة', max_digits=10, decimal_places=2, default=Decimal('1'))
    working_hours_per_day = models.DecimalField('ساعات العمل اليومية', max_digits=4, decimal_places=2, default=Decimal('8'))
    
    is_active = models.BooleanField('نشط', default=True)
    cost_center = models.ForeignKey(CostCenter, on_delete=models.SET_NULL, null=True, blank=True,
                                  verbose_name='مركز التكلفة')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'مركز عمل'
        verbose_name_plural = 'مراكز العمل'
        ordering = ['code']
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    @property
    def daily_capacity(self):
        """السعة اليومية"""
        return self.capacity_per_hour * self.working_hours_per_day


class BillOfMaterials(models.Model):
    """قائمة المواد للمنتج - وصفة الإنتاج"""
    
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='bom_list',
                              verbose_name='المنتج')
    version = models.CharField('الإصدار', max_length=10, default='1.0')
    name = models.CharField('اسم الوصفة', max_length=200)
    description = models.TextField('الوصف', blank=True)
    
    # كمية الإنتاج
    base_quantity = models.DecimalField('الكمية الأساسية', max_digits=10, decimal_places=3, default=Decimal('1'))
    
    # التواريخ
    effective_date = models.DateField('تاريخ السريان', default=timezone.localdate)
    expiry_date = models.DateField('تاريخ الانتهاء', null=True, blank=True)
    
    # الحالة
    is_active = models.BooleanField('نشط', default=True)
    is_default = models.BooleanField('افتراضي', default=False)
    
    # التكاليف المحسوبة
    total_material_cost = models.DecimalField('إجمالي تكلفة المواد', max_digits=12, decimal_places=2,
                                            default=Decimal('0'), editable=False)
    total_labor_cost = models.DecimalField('إجمالي تكلفة العمالة', max_digits=12, decimal_places=2,
                                         default=Decimal('0'), editable=False)
    total_overhead_cost = models.DecimalField('إجمالي التكاليف الإضافية', max_digits=12, decimal_places=2,
                                            default=Decimal('0'), editable=False)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='أنشئ بواسطة')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'قائمة مواد'
        verbose_name_plural = 'قوائم المواد'
        unique_together = ['product', 'version']
        ordering = ['product__name', '-version']
    
    def __str__(self):
        return f"{self.product.name} - {self.version}"
    
    @property
    def total_cost_per_unit(self):
        """إجمالي التكلفة لكل وحدة"""
        total = self.total_material_cost + self.total_labor_cost + self.total_overhead_cost
        return total / self.base_quantity if self.base_quantity > 0 else 0
    
    def save(self, *args, **kwargs):
        if self.is_default:
            # إلغاء الافتراضي من الوصفات الأخرى لنفس المنتج
            BillOfMaterials.objects.filter(product=self.product).update(is_default=False)
        super().save(*args, **kwargs)


class BOMItem(models.Model):
    """عنصر في قائمة المواد"""
    
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    ITEM_TYPES = [
        ('material', 'مادة خام'),
        ('component', 'مكون'),
        ('consumable', 'مستهلكات'),
        ('tool', 'أدوات'),
    ]
    
    bom = models.ForeignKey(BillOfMaterials, on_delete=models.CASCADE, related_name='items',
                          verbose_name='قائمة المواد')
    material = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='المادة')
    item_type = models.CharField('نوع العنصر', max_length=20, choices=ITEM_TYPES, default='material')
    
    # الكميات
    quantity = models.DecimalField('الكمية المطلوبة', max_digits=10, decimal_places=3)
    unit_cost = models.DecimalField('تكلفة الوحدة', max_digits=10, decimal_places=2, default=Decimal('0'))
    wastage_percentage = models.DecimalField('نسبة الهدر %', max_digits=5, decimal_places=2, default=Decimal('0'))
    
    # وحدة الاستخدام (للعرض والحسابات)
    usage_unit = models.CharField(
        'وحدة الاستخدام', max_length=10,
        choices=Product.UOM_CHOICES, default='unit', blank=True
    )
    
    # التسلسل
    sequence = models.PositiveIntegerField('الترتيب', default=1)
    
    # ملاحظات
    notes = models.TextField('ملاحظات', blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'عنصر قائمة المواد'
        verbose_name_plural = 'عناصر قوائم المواد'
        ordering = ['sequence']
    
    def __str__(self):
        return f"{self.bom.product.name} - {self.material.name}"
    
    def refresh_cost_from_material(self):
        """تحديث تكلفة الوحدة من سعر المادة الخام الحالي"""
        material = self.material
        if material.product_type == 'raw_material':
            # استخدام تكلفة وحدة الاستخدام (المحسوبة من سعر الشراء)
            self.unit_cost = material.usage_unit_cost or material.cost or material.purchase_price
            self.usage_unit = material.usage_uom or material.purchase_uom
        else:
            self.unit_cost = material.cost or material.price
        return self.unit_cost

    def save(self, *args, **kwargs):
        # إذا لم يتم تحديد تكلفة الوحدة يدوياً - خذها من المادة الخام
        if not self.unit_cost or self.unit_cost == Decimal('0'):
            self.refresh_cost_from_material()
        
        # تحديث وحدة الاستخدام من المادة
        if not self.usage_unit or self.usage_unit == 'unit':
            self.usage_unit = self.material.usage_uom or self.material.purchase_uom or 'unit'
        
        super().save(*args, **kwargs)
    
    @property
    def purchase_unit_display(self):
        """عرض وحدة الشراء للمادة الخام"""
        return self.material.get_purchase_uom_display()

    @property
    def unit_cost_display(self):
        """عرض تكلفة الوحدة مع الوحدة"""
        uom = self.get_usage_unit_display() if self.usage_unit else self.purchase_unit_display
        return f"{self.unit_cost} ج.م/{uom}"

    @property
    def quantity_with_wastage(self):
        """الكمية مع احتساب الهدر"""
        return self.quantity * (1 + self.wastage_percentage / 100)
    
    @property
    def total_cost(self):
        """إجمالي التكلفة للعنصر"""
        return self.quantity_with_wastage * self.unit_cost


class ProductionStage(models.Model):
    """مراحل الإنتاج"""

    STAGE_TYPES = [
        ('cutting', 'تقطيع'),
        ('sewing', 'خياطة'),
        ('assembly', 'تجميع'),
        ('finishing', 'تشطيب'),
        ('quality', 'جودة'),
        ('maintenance', 'صيانة'),
        ('other', 'أخرى'),
    ]

    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    bom = models.ForeignKey(
        BillOfMaterials,
        on_delete=models.CASCADE,
        related_name='production_stages',
        null=True,
        blank=True,
        verbose_name='قائمة المواد'
    )
    name = models.CharField('اسم المرحلة', max_length=200)
    code = models.CharField('كود المرحلة', max_length=20, unique=True, blank=True)
    description = models.TextField('الوصف', blank=True)
    sequence = models.PositiveIntegerField('الترتيب', default=1)

    work_center = models.ForeignKey(
        ProductionWorkCenter,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='مركز العمل'
    )
    work_centers = models.ManyToManyField(
        ProductionWorkCenter,
        blank=True,
        related_name='production_stages',
        verbose_name='مراكز العمل'
    )

    stage_type = models.CharField('نوع المرحلة', max_length=20, choices=STAGE_TYPES, default='other')
    standard_time = models.DecimalField('الوقت القياسي (ساعة/وحدة)', max_digits=8, decimal_places=2, default=Decimal('0'))

    # أوقات العملية
    setup_time = models.DecimalField('وقت الإعداد (دقيقة)', max_digits=8, decimal_places=2, default=Decimal('0'))
    operation_time = models.DecimalField('وقت العملية (دقيقة/وحدة)', max_digits=8, decimal_places=2, default=Decimal('0'))
    teardown_time = models.DecimalField('وقت التفكيك (دقيقة)', max_digits=8, decimal_places=2, default=Decimal('0'))

    # العمالة المطلوبة
    required_workers = models.PositiveIntegerField('عدد العمال المطلوب', default=1)
    skill_level = models.CharField('مستوى المهارة', max_length=20,
                                 choices=[
                                     ('trainee', 'متدرب'),
                                     ('skilled', 'ماهر'),
                                     ('expert', 'خبير'),
                                     ('supervisor', 'مشرف')
                                 ], default='skilled')

    # فحص الجودة
    requires_quality_check = models.BooleanField('يتطلب فحص جودة', default=False)
    quality_check_percentage = models.DecimalField('نسبة فحص الجودة %', max_digits=5, decimal_places=2, default=Decimal('100'))

    is_active = models.BooleanField('نشط', default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'مرحلة إنتاج'
        verbose_name_plural = 'مراحل الإنتاج'
        ordering = ['sequence']

    def __str__(self):
        return f"{self.code or 'STAGE'} - {self.name}"

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = f"STG-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    @property
    def total_time_per_unit(self):
        """إجمالي الوقت لكل وحدة (بالدقائق)"""
        op = self.operation_time or Decimal('0')
        return op + (self.setup_time + self.teardown_time)

    @property
    def labor_cost_per_unit(self):
        """تكلفة العمالة لكل وحدة"""
        if not self.work_center:
            return Decimal('0')
        total_minutes = self.total_time_per_unit
        hourly_cost = self.work_center.hourly_rate * self.required_workers
        return (hourly_cost * total_minutes) / 60


class BOMStage(models.Model):
    """ربط قائمة المواد بمراحل الإنتاج"""
    
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    bom = models.ForeignKey(BillOfMaterials, on_delete=models.CASCADE, related_name='stages',
                          verbose_name='قائمة المواد')
    stage = models.ForeignKey(ProductionStage, on_delete=models.CASCADE, verbose_name='المرحلة')
    sequence = models.PositiveIntegerField('الترتيب', default=1)
    is_required = models.BooleanField('مرحلة إجبارية', default=True)
    
    class Meta:
        verbose_name = 'مرحلة قائمة المواد'
        verbose_name_plural = 'مراحل قوائم المواد'
        unique_together = ['bom', 'stage']
        ordering = ['sequence']
    
    def __str__(self):
        return f"{self.bom.product.name} - {self.stage.name}"


class ProductionOrder(models.Model):
    """أمر الإنتاج"""
    
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    STATUS_CHOICES = [
        ('draft', 'مسودة'),
        ('confirmed', 'مؤكد'),
        ('in_progress', 'قيد الإنتاج'),
        ('quality_check', 'فحص الجودة'),
        ('completed', 'مكتمل'),
        ('cancelled', 'ملغي'),
        ('on_hold', 'معلق'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'منخفضة'),
        ('normal', 'عادية'),
        ('high', 'عالية'),
        ('urgent', 'عاجل'),
    ]
    
    # معلومات الأمر
    number = models.CharField('رقم أمر الإنتاج', max_length=50, unique=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='المنتج')
    bom = models.ForeignKey(BillOfMaterials, on_delete=models.CASCADE, verbose_name='قائمة المواد')
    
    # الكميات
    planned_quantity = models.DecimalField('الكمية المخططة', max_digits=10, decimal_places=3)
    produced_quantity = models.DecimalField('الكمية المنتجة', max_digits=10, decimal_places=3, default=Decimal('0'))
    scrap_quantity = models.DecimalField('كمية التالف', max_digits=10, decimal_places=3, default=Decimal('0'))
    
    # التواريخ
    order_date = models.DateField('تاريخ الأمر', default=timezone.localdate)
    planned_start_date = models.DateField('تاريخ البدء المخطط')
    planned_end_date = models.DateField('تاريخ الانتهاء المخطط')
    actual_start_date = models.DateField('تاريخ البدء الفعلي', null=True, blank=True)
    actual_end_date = models.DateField('تاريخ الانتهاء الفعلي', null=True, blank=True)
    
    # الحالة والأولوية
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='draft')
    priority = models.CharField('الأولوية', max_length=10, choices=PRIORITY_CHOICES, default='normal')
    
    # المسؤوليات
    supervisor = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='supervised_orders', verbose_name='المشرف')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='أنشئ بواسطة')
    
    # التكاليف المحسوبة
    estimated_material_cost = models.DecimalField('تكلفة المواد المقدرة', max_digits=12, decimal_places=2,
                                                 default=Decimal('0'), editable=False)
    estimated_labor_cost = models.DecimalField('تكلفة العمالة المقدرة', max_digits=12, decimal_places=2,
                                             default=Decimal('0'), editable=False)
    estimated_overhead_cost = models.DecimalField('التكاليف الإضافية المقدرة', max_digits=12, decimal_places=2,
                                                default=Decimal('0'), editable=False)
    
    actual_material_cost = models.DecimalField('تكلفة المواد الفعلية', max_digits=12, decimal_places=2,
                                             default=Decimal('0'), editable=False)
    actual_labor_cost = models.DecimalField('تكلفة العمالة الفعلية', max_digits=12, decimal_places=2,
                                          default=Decimal('0'), editable=False)
    actual_overhead_cost = models.DecimalField('التكاليف الإضافية الفعلية', max_digits=12, decimal_places=2,
                                             default=Decimal('0'), editable=False)
    
    # ملاحظات
    notes = models.TextField('ملاحظات', blank=True)
    
    # الربط المحاسبي
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.SET_NULL, null=True, blank=True,
                                    verbose_name='القيد المحاسبي')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'أمر إنتاج'
        verbose_name_plural = 'أوامر الإنتاج'
        ordering = ['-order_date', '-number']
    
    def __str__(self):
        return f"{self.number} - {self.product.name}"
    
    @property
    def completion_percentage(self):
        """نسبة الإنجاز"""
        if self.planned_quantity > 0:
            return min(100, (self.produced_quantity / self.planned_quantity) * 100)
        return 0
    
    @property
    def remaining_quantity(self):
        """الكمية المتبقية"""
        return max(0, self.planned_quantity - self.produced_quantity)
    
    @property
    def estimated_total_cost(self):
        """إجمالي التكلفة المقدرة"""
        return self.estimated_material_cost + self.estimated_labor_cost + self.estimated_overhead_cost
    
    @property
    def actual_total_cost(self):
        """إجمالي التكلفة الفعلية"""
        return self.actual_material_cost + self.actual_labor_cost + self.actual_overhead_cost
    
    @property
    def cost_variance(self):
        """انحراف التكلفة"""
        return self.actual_total_cost - self.estimated_total_cost
    
    @property
    def unit_cost(self):
        """تكلفة الوحدة"""
        if self.produced_quantity > 0:
            return self.actual_total_cost / self.produced_quantity
        return 0
    
    def save(self, *args, **kwargs):
        if not self.number:
            # إنشاء رقم أمر إنتاج تلقائي
            from datetime import datetime
            year = datetime.now().year
            count = ProductionOrder.objects.filter(
                number__startswith=f'PO-{year}'
            ).count() + 1
            self.number = f'PO-{year}-{count:06d}'
        super().save(*args, **kwargs)


class ProductionOrderStage(models.Model):
    """مراحل أمر الإنتاج"""
    
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    STATUS_CHOICES = [
        ('pending', 'في الانتظار'),
        ('ready', 'جاهز للبدء'),
        ('in_progress', 'قيد التنفيذ'),
        ('quality_check', 'فحص الجودة'),
        ('completed', 'مكتمل'),
        ('on_hold', 'معلق'),
        ('cancelled', 'ملغي'),
    ]
    
    production_order = models.ForeignKey(ProductionOrder, on_delete=models.CASCADE,
                                       related_name='order_stages', verbose_name='أمر الإنتاج')
    stage = models.ForeignKey(ProductionStage, on_delete=models.CASCADE, verbose_name='المرحلة')
    
    # الحالة والتواريخ
    status = models.CharField('حالة المرحلة', max_length=20, choices=STATUS_CHOICES, default='pending')
    planned_start_date = models.DateTimeField('تاريخ البدء المخطط', null=True, blank=True)
    planned_end_date = models.DateTimeField('تاريخ الانتهاء المخطط', null=True, blank=True)
    actual_start_date = models.DateTimeField('تاريخ البدء الفعلي', null=True, blank=True)
    actual_end_date = models.DateTimeField('تاريخ الانتهاء الفعلي', null=True, blank=True)
    
    # الكميات
    planned_quantity = models.DecimalField('الكمية المخططة', max_digits=10, decimal_places=3)
    completed_quantity = models.DecimalField('الكمية المنجزة', max_digits=10, decimal_places=3, default=Decimal('0'))
    scrap_quantity = models.DecimalField('الكمية التالفة', max_digits=10, decimal_places=3, default=Decimal('0'))
    
    # التكاليف
    estimated_cost = models.DecimalField('التكلفة المقدرة', max_digits=10, decimal_places=2, default=Decimal('0'))
    actual_cost = models.DecimalField('التكلفة الفعلية', max_digits=10, decimal_places=2, default=Decimal('0'))
    
    # العمالة
    assigned_workers = models.ManyToManyField(Employee, blank=True, verbose_name='العمال المكلفون')
    
    # الجودة
    quality_approved = models.BooleanField('موافقة الجودة', default=False)
    quality_notes = models.TextField('ملاحظات الجودة', blank=True)
    
    # ملاحظات
    notes = models.TextField('ملاحظات', blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'مرحلة أمر الإنتاج'
        verbose_name_plural = 'مراحل أوامر الإنتاج'
        unique_together = ['production_order', 'stage']
        ordering = ['stage__sequence']
    
    def __str__(self):
        return f"{self.production_order.number} - {self.stage.name}"
    
    @property
    def completion_percentage(self):
        """نسبة إنجاز المرحلة"""
        if self.planned_quantity > 0:
            return min(100, (self.completed_quantity / self.planned_quantity) * 100)
        return 0
    
    @property
    def duration_planned_hours(self):
        """المدة المخططة بالساعات"""
        if self.planned_start_date and self.planned_end_date:
            delta = self.planned_end_date - self.planned_start_date
            return delta.total_seconds() / 3600
        return 0
    
    @property
    def duration_actual_hours(self):
        """المدة الفعلية بالساعات"""
        if self.actual_start_date and self.actual_end_date:
            delta = self.actual_end_date - self.actual_start_date
            return delta.total_seconds() / 3600
        return 0


class MaterialConsumption(models.Model):
    """استهلاك المواد في الإنتاج"""
    
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    production_order = models.ForeignKey(ProductionOrder, on_delete=models.CASCADE,
                                       related_name='material_consumptions', verbose_name='أمر الإنتاج')
    stage = models.ForeignKey(ProductionOrderStage, on_delete=models.SET_NULL, null=True, blank=True,
                            verbose_name='مرحلة الإنتاج')
    material = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='المادة')
    
    # الكميات
    planned_quantity = models.DecimalField('الكمية المخططة', max_digits=10, decimal_places=3)
    consumed_quantity = models.DecimalField('الكمية المستهلكة', max_digits=10, decimal_places=3, default=Decimal('0'))
    wastage_quantity = models.DecimalField('كمية الهدر', max_digits=10, decimal_places=3, default=Decimal('0'))
    
    # التكلفة
    unit_cost = models.DecimalField('تكلفة الوحدة', max_digits=10, decimal_places=2)
    total_cost = models.DecimalField('إجمالي التكلفة', max_digits=12, decimal_places=2, default=Decimal('0'))
    
    # التواريخ
    consumption_date = models.DateField('تاريخ الاستهلاك', default=timezone.localdate)
    issued_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='صرفت بواسطة')
    
    # المخزن
    location = models.ForeignKey(Location, on_delete=models.CASCADE, verbose_name='المخزن')
    
    # ملاحظات
    notes = models.TextField('ملاحظات', blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'استهلاك مادة'
        verbose_name_plural = 'استهلاك المواد'
        ordering = ['-consumption_date']
    
    def __str__(self):
        return f"{self.production_order.number} - {self.material.name}"
    
    @property
    def variance_quantity(self):
        """انحراف الكمية"""
        return self.consumed_quantity - self.planned_quantity
    
    @property
    def variance_percentage(self):
        """نسبة الانحراف"""
        if self.planned_quantity > 0:
            return (self.variance_quantity / self.planned_quantity) * 100
        return 0
    
    def save(self, *args, **kwargs):
        # حساب إجمالي التكلفة
        self.total_cost = (self.consumed_quantity + self.wastage_quantity) * self.unit_cost
        super().save(*args, **kwargs)


class ProductionTimeLog(models.Model):
    """سجل أوقات العمل في الإنتاج"""
    
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    ACTIVITY_TYPES = [
        ('setup', 'إعداد'),
        ('operation', 'تشغيل'),
        ('quality_check', 'فحص جودة'),
        ('maintenance', 'صيانة'),
        ('cleanup', 'تنظيف'),
        ('waiting', 'انتظار'),
        ('break', 'استراحة'),
    ]
    
    production_order = models.ForeignKey(ProductionOrder, on_delete=models.CASCADE,
                                       related_name='time_logs', verbose_name='أمر الإنتاج')
    stage = models.ForeignKey(ProductionOrderStage, on_delete=models.CASCADE,
                            verbose_name='مرحلة الإنتاج')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name='الموظف')
    work_center = models.ForeignKey(ProductionWorkCenter, on_delete=models.CASCADE,
                                  verbose_name='مركز العمل')
    
    # النشاط والوقت
    activity_type = models.CharField('نوع النشاط', max_length=20, choices=ACTIVITY_TYPES)
    start_time = models.DateTimeField('وقت البداية')
    end_time = models.DateTimeField('وقت النهاية', null=True, blank=True)
    break_time_minutes = models.DecimalField('وقت الاستراحة (دقيقة)', max_digits=6, decimal_places=2, default=0)
    
    # الكمية المنتجة
    quantity_produced = models.DecimalField('الكمية المنتجة', max_digits=10, decimal_places=3, default=Decimal('0'))
    quantity_scrapped = models.DecimalField('الكمية التالفة', max_digits=10, decimal_places=3, default=Decimal('0'))
    
    # التكلفة
    hourly_rate = models.DecimalField('معدل الساعة', max_digits=8, decimal_places=2)
    total_cost = models.DecimalField('إجمالي التكلفة', max_digits=10, decimal_places=2, default=Decimal('0'))
    
    # التقييم
    efficiency_percentage = models.DecimalField('نسبة الكفاءة %', max_digits=5, decimal_places=2, default=Decimal('100'))
    quality_rating = models.IntegerField('تقييم الجودة (1-10)', 
                                       validators=[MinValueValidator(1), MaxValueValidator(10)],
                                       null=True, blank=True)
    
    # ملاحظات
    notes = models.TextField('ملاحظات', blank=True)
    
    # التسجيل
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='سجل بواسطة')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'سجل وقت العمل'
        verbose_name_plural = 'سجلات أوقات العمل'
        ordering = ['-start_time']
    
    def __str__(self):
        return f"{self.employee.arabic_name} - {self.production_order.number} - {self.get_activity_type_display()}"
    
    @property
    def duration_hours(self):
        """مدة العمل بالساعات"""
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            total_minutes = delta.total_seconds() / 60 - float(self.break_time_minutes)
            return max(0, total_minutes / 60)
        return 0
    
    @property
    def productivity_rate(self):
        """معدل الإنتاجية (قطعة/ساعة)"""
        duration = self.duration_hours
        if duration > 0 and self.quantity_produced > 0:
            return float(self.quantity_produced) / duration
        return 0
    
    def save(self, *args, **kwargs):
        # حساب التكلفة
        if self.end_time:
            self.total_cost = self.duration_hours * float(self.hourly_rate)
        super().save(*args, **kwargs)


class ProductionQualityCheck(models.Model):
    """فحص الجودة في الإنتاج"""
    
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    CHECK_RESULTS = [
        ('passed', 'مقبول'),
        ('failed', 'مرفوض'),
        ('rework', 'إعادة عمل'),
        ('pending', 'في الانتظار'),
    ]
    
    production_order = models.ForeignKey(ProductionOrder, on_delete=models.CASCADE,
                                       related_name='quality_checks', verbose_name='أمر الإنتاج')
    stage = models.ForeignKey(ProductionOrderStage, on_delete=models.CASCADE,
                            verbose_name='مرحلة الإنتاج')
    
    # معلومات الفحص
    check_date = models.DateTimeField('تاريخ الفحص', default=timezone.now)
    inspector = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name='المفتش')
    
    # الكميات
    quantity_checked = models.DecimalField('الكمية المفحوصة', max_digits=10, decimal_places=3)
    quantity_passed = models.DecimalField('الكمية المقبولة', max_digits=10, decimal_places=3, default=Decimal('0'))
    quantity_failed = models.DecimalField('الكمية المرفوضة', max_digits=10, decimal_places=3, default=Decimal('0'))
    quantity_rework = models.DecimalField('كمية إعادة العمل', max_digits=10, decimal_places=3, default=Decimal('0'))
    
    # النتيجة
    overall_result = models.CharField('النتيجة العامة', max_length=10, choices=CHECK_RESULTS, default='pending')
    quality_score = models.DecimalField('درجة الجودة %', max_digits=5, decimal_places=2, null=True, blank=True,
                                      validators=[MinValueValidator(0), MaxValueValidator(100)])
    
    # التفاصيل
    defect_types = models.TextField('أنواع العيوب', blank=True)
    corrective_actions = models.TextField('الإجراءات التصحيحية', blank=True)
    notes = models.TextField('ملاحظات', blank=True)
    
    # المتطلبات
    standards_reference = models.CharField('مرجع المعايير', max_length=200, blank=True)
    test_conditions = models.TextField('ظروف الاختبار', blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'فحص جودة'
        verbose_name_plural = 'فحوصات الجودة'
        ordering = ['-check_date']
    
    def __str__(self):
        return f"{self.production_order.number} - {self.stage.stage.name} - {self.get_overall_result_display()}"
    
    @property
    def pass_rate_percentage(self):
        """نسبة النجاح"""
        if self.quantity_checked > 0:
            return (self.quantity_passed / self.quantity_checked) * 100
        return 0
    
    @property
    def reject_rate_percentage(self):
        """نسبة الرفض"""
        if self.quantity_checked > 0:
            return (self.quantity_failed / self.quantity_checked) * 100
        return 0


class ProductionCostAnalysis(models.Model):
    """تحليل تكاليف الإنتاج التفصيلي"""
    
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    COST_CATEGORIES = [
        ('material', 'مواد خام'),
        ('labor', 'عمالة مباشرة'),
        ('overhead', 'تكاليف إضافية'),
        ('quality', 'تكاليف الجودة'),
        ('setup', 'تكاليف الإعداد'),
        ('scrap', 'تكاليف التالف'),
        ('rework', 'تكاليف إعادة العمل'),
    ]
    
    production_order = models.ForeignKey(ProductionOrder, on_delete=models.CASCADE,
                                       related_name='cost_analysis', verbose_name='أمر الإنتاج')
    cost_category = models.CharField('فئة التكلفة', max_length=20, choices=COST_CATEGORIES)
    cost_center = models.ForeignKey(CostCenter, on_delete=models.SET_NULL, null=True, blank=True,
                                  verbose_name='مركز التكلفة')
    
    # التفاصيل
    description = models.CharField('الوصف', max_length=200)
    reference_document = models.CharField('وثيقة مرجعية', max_length=100, blank=True)
    
    # المبالغ
    budgeted_amount = models.DecimalField('المبلغ المدرج في الموازنة', max_digits=12, decimal_places=2, default=Decimal('0'))
    actual_amount = models.DecimalField('المبلغ الفعلي', max_digits=12, decimal_places=2)
    
    # التواريخ
    cost_date = models.DateField('تاريخ التكلفة', default=timezone.localdate)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='سجل بواسطة')
    
    # الربط المحاسبي
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.SET_NULL, null=True, blank=True,
                                    verbose_name='القيد المحاسبي')
    
    # ملاحظات
    notes = models.TextField('ملاحظات', blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'تحليل تكاليف الإنتاج'
        verbose_name_plural = 'تحليلات تكاليف الإنتاج'
        ordering = ['-cost_date']
    
    def __str__(self):
        return f"{self.production_order.number} - {self.get_cost_category_display()} - {self.actual_amount}"
    
    @property
    def variance(self):
        """الانحراف"""
        return self.actual_amount - self.budgeted_amount
    
    @property
    def variance_percentage(self):
        """نسبة الانحراف"""
        if self.budgeted_amount > 0:
            return (self.variance / self.budgeted_amount) * 100
        return 0


class ProductionReport(models.Model):
    """تقارير الإنتاج"""
    
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    REPORT_TYPES = [
        ('daily', 'يومي'),
        ('weekly', 'أسبوعي'),
        ('monthly', 'شهري'),
        ('order_summary', 'ملخص أمر الإنتاج'),
        ('cost_analysis', 'تحليل التكاليف'),
        ('quality_report', 'تقرير الجودة'),
        ('efficiency_report', 'تقرير الكفاءة'),
    ]
    
    REPORT_STATUS = [
        ('draft', 'مسودة'),
        ('final', 'نهائي'),
        ('archived', 'مؤرشف'),
    ]
    
    title = models.CharField('عنوان التقرير', max_length=200)
    report_type = models.CharField('نوع التقرير', max_length=20, choices=REPORT_TYPES)
    
    # الفترة
    period_start = models.DateField('بداية الفترة')
    period_end = models.DateField('نهاية الفترة')
    
    # الفلاتر
    work_center = models.ForeignKey(ProductionWorkCenter, on_delete=models.SET_NULL, null=True, blank=True,
                                  verbose_name='مركز العمل')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True,
                              verbose_name='المنتج')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True,
                                 verbose_name='القسم')
    
    # المحتوى
    summary = models.TextField('الملخص', blank=True)
    details = models.JSONField('التفاصيل', default=dict, blank=True)
    
    # الحالة
    status = models.CharField('حالة التقرير', max_length=10, choices=REPORT_STATUS, default='draft')
    
    # المسؤوليات
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='أنشئ بواسطة')
    approved_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True,
                                  verbose_name='اعتمد بواسطة')
    
    # ملف التقرير
    report_file = models.FileField('ملف التقرير', upload_to='production/reports/', null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'تقرير الإنتاج'
        verbose_name_plural = 'تقارير الإنتاج'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.period_start} إلى {self.period_end}"


class ProductManufacturingProfile(models.Model):
    """إعدادات تصنيع المنتج: صلاحية افتراضية ومقاس افتراضي للطباعة"""
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='mfg_profile', verbose_name='المنتج')
    shelf_life_days = models.PositiveIntegerField(default=0, verbose_name='مدة الصلاحية (أيام)')
    default_size_text = models.CharField(max_length=100, blank=True, verbose_name='المقاس الافتراضي (مثال: 10x10 سم)')
    
    class Meta:
        verbose_name = 'إعداد تصنيع المنتج'
        verbose_name_plural = 'إعدادات تصنيع المنتجات'
    
    def __str__(self):
        return f"{self.product.name} - صلاحية: {self.shelf_life_days} يوم - مقاس: {self.default_size_text or '-'}"


class FinishedGoodUnit(models.Model):
    """وحدة منتج نهائي (قطعة) مع باركود فردي ومعلومات صلاحية ومقاس للطباعة والضمان"""
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    
    # المنتج وأمر الإنتاج
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='finished_units', verbose_name='المنتج')
    production_order = models.ForeignKey(ProductionOrder, on_delete=models.CASCADE, related_name='finished_units', verbose_name='أمر الإنتاج')
    
    # الأكواد الفريدة
    unit_serial = models.CharField('رقم تسلسلي', max_length=50, unique=True)
    barcode = models.CharField('باركود القطعة', max_length=30, unique=True)
    qr_code_data = models.CharField('بيانات QR Code', max_length=500, blank=True)
    qr_code_image = models.ImageField(upload_to='finished_units/qr/', blank=True, null=True, verbose_name='صورة QR Code')
    
    # التواريخ
    manufacture_date = models.DateField('تاريخ التصنيع', default=timezone.localdate)
    expiry_date = models.DateField('تاريخ الانتهاء', null=True, blank=True)
    
    # المواصفات
    size_text = models.CharField('المقاس', max_length=100, blank=True, help_text='مثال: 10x10 سم أو 10x5 سم؛ قابل للتعديل يدويًا')
    
    # الحالة
    STATUS_CHOICES = [
        ('produced', 'تم الإنتاج'),
        ('in_stock', 'في المخزن'),
        ('sold_to_dealer', 'مباع لتاجر'),
        ('sold_to_customer', 'مباع لعميل'),
        ('warranty_registered', 'ضمان مسجل'),
        ('warranty_claimed', 'مطالبة ضمان'),
        ('returned', 'مرتجع'),
        ('defective', 'معيب'),
        ('scrapped', 'خردة'),
    ]
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='produced')
    
    # معلومات البيع للتاجر
    dealer = models.ForeignKey('partners.Partner', on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='purchased_finished_units', verbose_name='التاجر/الموزع')
    dealer_invoice = models.ForeignKey('sales.Invoice', on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name='dealer_finished_units', verbose_name='فاتورة التاجر')
    dealer_sale_date = models.DateField('تاريخ البيع للتاجر', null=True, blank=True)
    dealer_sale_price = models.DecimalField('سعر البيع للتاجر', max_digits=12, decimal_places=2, null=True, blank=True)
    
    # معلومات البيع للعميل النهائي
    customer_name = models.CharField('اسم العميل', max_length=200, blank=True)
    customer_phone = models.CharField('هاتف العميل', max_length=20, blank=True)
    customer_email = models.EmailField('بريد العميل', blank=True)
    customer_address = models.TextField('عنوان العميل', blank=True)
    customer_national_id = models.CharField('رقم الهوية', max_length=20, blank=True)
    customer_sale_date = models.DateField('تاريخ البيع للعميل', null=True, blank=True)
    customer_sale_price = models.DecimalField('سعر البيع للعميل', max_digits=12, decimal_places=2, null=True, blank=True)
    customer_invoice_image = models.ImageField(upload_to='finished_units/invoices/', blank=True, null=True, verbose_name='صورة فاتورة العميل')
    
    # معلومات الضمان
    warranty_policy = models.ForeignKey('ecommerce.ProductWarranty', on_delete=models.SET_NULL, null=True, blank=True,
                                       verbose_name='سياسة الضمان')
    warranty_start_date = models.DateField('تاريخ بداية الضمان', null=True, blank=True)
    warranty_end_date = models.DateField('تاريخ نهاية الضمان', null=True, blank=True)
    warranty_registered = models.BooleanField('تم تسجيل الضمان', default=False)
    warranty_registration_date = models.DateTimeField('تاريخ تسجيل الضمان', null=True, blank=True)
    
    # ملاحظات
    notes = models.TextField('ملاحظات', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'وحدة منتج نهائي'
        verbose_name_plural = 'وحدات منتجات نهائية'
        indexes = [
            models.Index(fields=['barcode']),
            models.Index(fields=['unit_serial']),
            models.Index(fields=['status']),
            models.Index(fields=['customer_phone']),
            models.Index(fields=['product', 'production_order']),
        ]
        ordering = ['-id']

    def __str__(self):
        return f"{self.product.name} - {self.unit_serial}"
    
    def save(self, *args, **kwargs):
        # توليد/ترقية QR Code data تلقائياً
        if not self.qr_code_data:
            self.generate_qr_data()
        else:
            # ترقية البيانات القديمة (JSON أو مسار verify غير موجود) إلى رابط التفعيل الصحيح
            old = (self.qr_code_data or '').strip()
            if old.startswith('{') or '/store/warranty/verify/' in old:
                self.generate_qr_data()
                # إذا كان لدينا صورة قديمة، أعد توليدها لتطابق البيانات الجديدة
                if self.qr_code_image:
                    self.qr_code_image = None
        # توليد صورة QR Code
        if self.qr_code_data and not self.qr_code_image:
            self.generate_qr_image()
        super().save(*args, **kwargs)
    
    def generate_qr_data(self):
        """توليد بيانات QR Code.

        الهدف: QR يفتح صفحة تفعيل/تسجيل الضمان على الموقع مع تمرير الكود تلقائياً.
        """
        from urllib.parse import urlencode
        from django.urls import reverse
        from django.conf import settings

        code = f"WARRANTY:{self.unit_serial}"
        path = reverse('ecommerce:warranty_register')
        query = urlencode({'code': code})

        public_base = (getattr(settings, 'PUBLIC_SITE_URL', '') or '').rstrip('/')
        if public_base:
            self.qr_code_data = f"{public_base}{path}?{query}"
        else:
            # رابط نسبي (مفيد داخل النظام/البيئات المحلية)
            self.qr_code_data = f"{path}?{query}"
    
    def generate_qr_image(self):
        """توليد صورة QR Code"""
        try:
            import qrcode
            from io import BytesIO
            from django.core.files.base import ContentFile
            
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=10,
                border=4,
            )
            qr.add_data(self.qr_code_data)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            
            filename = f"qr_{self.unit_serial}.png"
            self.qr_code_image.save(filename, ContentFile(buffer.read()), save=False)
        except Exception as e:
            print(f"Error generating QR image: {e}")
    
    def activate_warranty(self, customer_data=None):
        """تفعيل الضمان للعميل وإنشاء/ربط العميل في CRM"""
        from dateutil.relativedelta import relativedelta
        
        if customer_data:
            self.customer_name = customer_data.get('name', '')
            self.customer_phone = customer_data.get('phone', '')
            self.customer_email = customer_data.get('email', '')
            self.customer_address = customer_data.get('address', '')
            self.customer_national_id = customer_data.get('national_id', '')
            
            # إنشاء أو ربط العميل في CRM
            self._link_to_crm_customer(customer_data)
        
        # تحديد فترة الضمان باستخدام ProductWarranty.get_expiry_date
        today = timezone.now().date()
        
        # تاريخ بداية الضمان من تاريخ البيع أو اليوم
        if self.customer_sale_date:
            self.warranty_start_date = self.customer_sale_date
        else:
            self.warranty_start_date = today
            self.customer_sale_date = today
        
        # حساب تاريخ انتهاء الضمان
        if self.warranty_policy:
            self.warranty_end_date = self.warranty_policy.get_expiry_date(self.warranty_start_date)
        else:
            # افتراضي سنة واحدة
            self.warranty_end_date = self.warranty_start_date + relativedelta(months=12)
        
        self.warranty_registered = True
        self.warranty_registration_date = timezone.now()
        self.status = 'warranty_registered'
        
        self.save()
        return True
    
    def _link_to_crm_customer(self, customer_data):
        """إنشاء أو ربط العميل في نظام CRM"""
        try:
            from crm.models import Customer, CustomerSource
            
            phone = customer_data.get('phone', '')
            email = customer_data.get('email', '')
            name = customer_data.get('name', '')
            
            if not phone and not email:
                return None
            
            # البحث عن العميل بالهاتف أو البريد الإلكتروني
            customer = None
            if phone:
                customer = Customer.objects.filter(
                    models.Q(phone=phone) | models.Q(mobile=phone)
                ).first()
            
            if not customer and email:
                customer = Customer.objects.filter(email=email).first()
            
            # إذا لم يُوجد، إنشاء عميل جديد
            if not customer:
                # تقسيم الاسم
                name_parts = name.split() if name else ['عميل']
                first_name = name_parts[0]
                last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
                
                # توليد كود فريد للعميل
                import random
                customer_code = f"WRN{timezone.now().strftime('%Y%m%d')}{random.randint(1000, 9999)}"
                
                # البحث عن مصدر "ضمان المنتج" أو إنشاؤه
                source, _ = CustomerSource.objects.get_or_create(
                    name="ضمان المنتج",
                    defaults={'description': 'عملاء تم تسجيلهم من خلال تفعيل ضمان المنتج'}
                )
                
                customer = Customer.objects.create(
                    customer_code=customer_code,
                    first_name=first_name,
                    last_name=last_name,
                    phone=phone,
                    email=email or '',
                    address_line1=customer_data.get('address', ''),
                    national_id=customer_data.get('national_id', ''),
                    source=source,
                    notes=f"تم إنشاؤه تلقائياً من تفعيل ضمان الوحدة: {self.unit_serial}"
                )
            
            return customer
            
        except Exception as e:
            # لا نريد أن يفشل تفعيل الضمان بسبب خطأ في CRM
            print(f"Error linking to CRM: {e}")
            return None
    
    @property
    def is_warranty_valid(self):
        """هل الضمان ساري؟"""
        if not self.warranty_registered or not self.warranty_end_date:
            return False
        return timezone.now().date() <= self.warranty_end_date
    
    @property
    def warranty_remaining_days(self):
        """الأيام المتبقية من الضمان"""
        if not self.warranty_end_date:
            return 0
        remaining = (self.warranty_end_date - timezone.now().date()).days
        return max(0, remaining)


class ProductionAlert(models.Model):
    """تنبيهات الإنتاج"""
    
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    ALERT_TYPES = [
        ('delay', 'تأخير في الإنتاج'),
        ('quality', 'مشكلة في الجودة'),
        ('cost_overrun', 'تجاوز في التكلفة'),
        ('material_shortage', 'نقص في المواد'),
        ('machine_breakdown', 'عطل في الماكينة'),
        ('safety', 'تنبيه أمان'),
        ('maintenance', 'تنبيه صيانة'),
    ]
    
    PRIORITY_LEVELS = [
        ('low', 'منخفض'),
        ('medium', 'متوسط'),
        ('high', 'عالي'),
        ('critical', 'حرج'),
    ]
    
    ALERT_STATUS = [
        ('new', 'جديد'),
        ('acknowledged', 'تم الاطلاع'),
        ('in_progress', 'قيد المعالجة'),
        ('resolved', 'تم الحل'),
        ('closed', 'مغلق'),
    ]
    
    # معلومات التنبيه
    title = models.CharField('عنوان التنبيه', max_length=200)
    alert_type = models.CharField('نوع التنبيه', max_length=20, choices=ALERT_TYPES)
    priority = models.CharField('الأولوية', max_length=10, choices=PRIORITY_LEVELS, default='medium')
    status = models.CharField('الحالة', max_length=15, choices=ALERT_STATUS, default='new')
    
    # المصدر
    production_order = models.ForeignKey(ProductionOrder, on_delete=models.SET_NULL, null=True, blank=True,
                                       verbose_name='أمر الإنتاج')
    work_center = models.ForeignKey(ProductionWorkCenter, on_delete=models.SET_NULL, null=True, blank=True,
                                  verbose_name='مركز العمل')
    
    # التفاصيل
    description = models.TextField('الوصف')
    suggested_action = models.TextField('الإجراء المقترح', blank=True)
    
    # المسؤوليات
    assigned_to = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True,
                                  verbose_name='مكلف إلى')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='أنشئ بواسطة')
    
    # التواريخ
    alert_date = models.DateTimeField('تاريخ التنبيه', default=timezone.now)
    due_date = models.DateTimeField('تاريخ الاستحقاق', null=True, blank=True)
    resolved_date = models.DateTimeField('تاريخ الحل', null=True, blank=True)
    
    # الإقرار والحل
    acknowledged_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name='acknowledged_alerts', verbose_name='أقر بواسطة')
    acknowledged_date = models.DateTimeField('تاريخ الإقرار', null=True, blank=True)
    
    resolution_notes = models.TextField('ملاحظات الحل', blank=True)
    resolved_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='resolved_alerts', verbose_name='تم حله بواسطة')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'تنبيه الإنتاج'
        verbose_name_plural = 'تنبيهات الإنتاج'
        ordering = ['-priority', '-alert_date']
    
    def __str__(self):
        return f"{self.title} - {self.get_priority_display()}"
    
    @property
    def is_overdue(self):
        """هل التنبيه متأخر"""
        if self.due_date and self.status not in ['resolved', 'closed']:
            return timezone.now() > self.due_date
        return False


class WorkerProductionEntry(models.Model):
    """
    تسجيل إنتاج العامل اليومي
    يستخدم لتسجيل كمية الإنتاج التي أنجزها العامل في وردية معينة
    """
    id = models.AutoField(primary_key=True)
    
    STATUS_CHOICES = [
        ('draft', 'مسودة'),
        ('submitted', 'مقدم'),
        ('approved', 'موافق عليه'),
        ('rejected', 'مرفوض'),
    ]
    
    # بيانات أساسية
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, 
                                related_name='production_entries', verbose_name='العامل')
    date = models.DateField('تاريخ الإنتاج', default=timezone.localdate)
    shift = models.CharField('الوردية', max_length=50, blank=True)
    
    # بيانات الإنتاج
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='المنتج/القماشة')
    quantity = models.DecimalField('الكمية المنتجة', max_digits=12, decimal_places=3)
    unit_of_measure = models.CharField('وحدة القياس', max_length=20, default='متر')
    size_description = models.CharField('المقاس', max_length=50, blank=True)
    
    # مركز العمل والماكينة
    work_center = models.ForeignKey(ProductionWorkCenter, on_delete=models.SET_NULL, 
                                   null=True, blank=True, verbose_name='مركز العمل')
    machine_code = models.CharField('كود الماكينة', max_length=50, blank=True)
    
    # الوقت
    start_time = models.TimeField('وقت البدء', null=True, blank=True)
    end_time = models.TimeField('وقت الانتهاء', null=True, blank=True)
    hours_worked = models.DecimalField('ساعات العمل', max_digits=5, decimal_places=2, 
                                       default=Decimal('0'))
    
    # ربط بأمر الإنتاج (اختياري)
    production_order = models.ForeignKey(ProductionOrder, on_delete=models.SET_NULL, 
                                        null=True, blank=True, verbose_name='أمر الإنتاج')
    
    # الحالة والموافقات
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='draft')
    notes = models.TextField('ملاحظات', blank=True)
    
    # الموافقات
    supervisor = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='supervised_production_entries', 
                                  verbose_name='المشرف')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   verbose_name='تمت الموافقة بواسطة')
    approved_at = models.DateTimeField('تاريخ الموافقة', null=True, blank=True)
    rejection_reason = models.TextField('سبب الرفض', blank=True)
    
    # ربط بالمخزون
    inventory_transaction_created = models.BooleanField('تم إنشاء حركة مخزون', default=False)
    inventory_transaction_id = models.IntegerField('رقم حركة المخزون', null=True, blank=True)
    
    # التكلفة
    labor_cost_calculated = models.DecimalField('تكلفة العمالة المحسوبة', max_digits=12, 
                                               decimal_places=2, default=Decimal('0'))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'تسجيل إنتاج عامل'
        verbose_name_plural = 'تسجيلات إنتاج العمال'
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['employee', 'date']),
            models.Index(fields=['product', 'date']),
            models.Index(fields=['status']),
            models.Index(fields=['date', 'status']),
        ]
    
    def __str__(self):
        return f"{self.employee.arabic_name} - {self.product.name} - {self.quantity} {self.unit_of_measure} - {self.date}"
    
    def calculate_labor_cost(self):
        """حساب تكلفة العمالة لهذا الإدخال"""
        if self.hours_worked > 0:
            # حساب معدل الساعة للعامل
            hourly_rate = self.employee.basic_salary / Decimal('160')  # 160 ساعة شهرياً
            self.labor_cost_calculated = self.hours_worked * hourly_rate
        elif self.quantity > 0:
            # إذا كان هناك أجر بالقطعة (يمكن إضافة حقل piece_rate لاحقاً)
            # self.labor_cost_calculated = self.quantity * piece_rate
            pass
        return self.labor_cost_calculated
    
    def approve(self, user):
        """الموافقة على التسجيل"""
        self.status = 'approved'
        self.approved_by = user
        self.approved_at = timezone.now()
        self.save()
        
        # إنشاء حركة مخزون تلقائياً
        self.create_inventory_transaction()
    
    def reject(self, user, reason):
        """رفض التسجيل"""
        self.status = 'rejected'
        self.rejection_reason = reason
        self.approved_by = user
        self.approved_at = timezone.now()
        self.save()
    
    def create_inventory_transaction(self):
        """
        إنشاء حركة مخزون تلقائية:
        1. خصم المواد الخام من مخزن الخامات
        2. إضافة المنتج المصنع إلى مخزن WIP أو التام
        """
        if self.inventory_transaction_created:
            return False, "تم إنشاء حركة المخزون مسبقاً"
        
        try:
            from inventory.models import Location, Issue, IssueItem
            from production.services.costing_service import ProductCostingService
            
            # 1. حساب المواد المطلوبة حسب BOM
            material_cost_data = ProductCostingService.calculate_material_cost(
                self.product, 
                self.quantity
            )
            
            if 'error' in material_cost_data:
                return False, material_cost_data['error']
            
            # 2. إنشاء سند صرف للمواد الخام
            raw_materials_location = Location.objects.filter(
                type='raw_material'
            ).first()
            
            wip_location = Location.objects.filter(
                type='wip'
            ).first()
            
            if not raw_materials_location or not wip_location:
                return False, "لم يتم العثور على مستودعات الخامات أو WIP"
            
            # إنشاء سند صرف
            issue = Issue.objects.create(
                date=self.date,
                from_location=raw_materials_location,
                to_location=wip_location,
                reference_type='worker_production',
                reference_id=self.id,
                notes=f"صرف مواد لإنتاج {self.product.name} بواسطة {self.employee.arabic_name}",
                status='draft'
            )
            
            # إضافة بنود الصرف
            for material_item in material_cost_data.get('materials', []):
                IssueItem.objects.create(
                    issue=issue,
                    product=material_item['material'],
                    quantity=material_item['quantity'],
                    unit_cost=material_item['unit_cost'],
                    notes=f"للإنتاج: {self.product.name}"
                )
            
            # ترحيل سند الصرف
            # issue.status = 'posted'
            # issue.save()
            
            self.inventory_transaction_created = True
            self.inventory_transaction_id = issue.id
            self.save(update_fields=['inventory_transaction_created', 'inventory_transaction_id'])
            
            return True, f"تم إنشاء سند صرف رقم {issue.id}"
            
        except Exception as e:
            return False, f"خطأ في إنشاء حركة المخزون: {str(e)}"


# ==================== استيراد الموديلات من الملفات الإضافية ====================
# هذه الموديلات موجودة في ملفات منفصلة للتنظيم
# يتم استيرادها هنا لضمان تسجيلها في Django

try:
    from .mrp import MRPPlanningModel, MaterialReorderPoint
    from .costing import StandardCost, CostVarianceRecord, OverheadAllocation
    from .factory_showroom_integration import ProductionShowroomLink, DemandForecast, IntegrationLog
except ImportError:
    # الملفات لم تُنشأ بعد أو هناك مشكلة في الاستيراد
    pass

# Pipeline models
try:
    from .models_pipeline import (
        PipelineBoard, PipelineStageEntry, PipelinePrintJob,
        PipelineStageStatus
    )
except ImportError:
    pass