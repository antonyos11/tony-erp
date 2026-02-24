"""
نماذج المخزون المتقدمة
========================
تنبيهات المخزون الذكية، تتبع اللوتات/الأرقام التسلسلية، الجرد الدوري
"""

from django.db import models
from django.conf import settings
from django.utils import timezone


class StockAlert(models.Model):
    """تنبيهات المخزون الذكية"""
    ALERT_TYPE_CHOICES = [
        ('low_stock', 'مخزون منخفض'),
        ('overstock', 'مخزون زائد'),
        ('out_of_stock', 'نفد المخزون'),
        ('expiring', 'قرب انتهاء الصلاحية'),
        ('no_movement', 'بدون حركة'),
        ('reorder_point', 'نقطة إعادة الطلب'),
    ]

    SEVERITY_CHOICES = [
        ('info', 'معلومة'),
        ('warning', 'تحذير'),
        ('critical', 'حرج'),
    ]

    product = models.ForeignKey(
        'inventory.Product',
        on_delete=models.CASCADE,
        related_name='stock_alerts',
        verbose_name='المنتج'
    )
    location = models.ForeignKey(
        'inventory.Location',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='stock_alerts',
        verbose_name='الموقع'
    )
    alert_type = models.CharField(
        max_length=20,
        choices=ALERT_TYPE_CHOICES,
        verbose_name='نوع التنبيه'
    )
    severity = models.CharField(
        max_length=10,
        choices=SEVERITY_CHOICES,
        default='warning',
        verbose_name='مستوى الخطورة'
    )
    threshold = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='الحد',
        help_text='الحد الأدنى/الأقصى للكمية حسب نوع التنبيه'
    )
    current_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='الكمية الحالية'
    )
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    is_acknowledged = models.BooleanField(default=False, verbose_name='تم الاطلاع')
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acknowledged_stock_alerts',
        verbose_name='اطلع عليه'
    )
    last_triggered = models.DateTimeField(null=True, blank=True, verbose_name='آخر تشغيل')
    trigger_count = models.PositiveIntegerField(default=0, verbose_name='عدد مرات التشغيل')
    no_movement_days = models.PositiveIntegerField(
        default=30,
        verbose_name='أيام بدون حركة',
        help_text='لنوع "بدون حركة" فقط'
    )
    notify_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='subscribed_stock_alerts',
        verbose_name='إشعار المستخدمين'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')

    class Meta:
        verbose_name = 'تنبيه مخزون'
        verbose_name_plural = 'تنبيهات المخزون'
        unique_together = ['product', 'location', 'alert_type']
        ordering = ['-last_triggered', '-severity']

    def __str__(self):
        return f"{self.get_alert_type_display()} - {self.product}"

    def check_and_trigger(self):
        """فحص حالة التنبيه وتشغيله إن لزم"""
        if not self.is_active:
            return False

        should_trigger = False

        if self.alert_type == 'low_stock':
            should_trigger = self.current_quantity <= self.threshold
        elif self.alert_type == 'out_of_stock':
            should_trigger = self.current_quantity <= 0
        elif self.alert_type == 'overstock':
            should_trigger = self.current_quantity >= self.threshold
        elif self.alert_type == 'reorder_point':
            should_trigger = self.current_quantity <= self.threshold

        if should_trigger:
            self.last_triggered = timezone.now()
            self.trigger_count += 1
            self.is_acknowledged = False
            self.save(update_fields=[
                'last_triggered', 'trigger_count', 'is_acknowledged'
            ])
            return True

        return False


class LotTracking(models.Model):
    """تتبع اللوتات (الدُفعات)"""
    product = models.ForeignKey(
        'inventory.Product',
        on_delete=models.CASCADE,
        related_name='lots',
        verbose_name='المنتج'
    )
    lot_number = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='رقم اللوت'
    )
    batch_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='رقم الدُفعة'
    )
    manufacturing_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='تاريخ التصنيع'
    )
    expiry_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='تاريخ انتهاء الصلاحية'
    )
    received_date = models.DateField(
        auto_now_add=True,
        verbose_name='تاريخ الاستلام'
    )
    initial_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='الكمية الأولية'
    )
    current_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='الكمية الحالية'
    )
    location = models.ForeignKey(
        'inventory.Location',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lots',
        verbose_name='الموقع'
    )
    supplier = models.ForeignKey(
        'partners.Supplier',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='المورد'
    )
    cost_per_unit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='تكلفة الوحدة'
    )
    notes = models.TextField(blank=True, verbose_name='ملاحظات')
    is_active = models.BooleanField(default=True, verbose_name='نشط')

    class Meta:
        verbose_name = 'لوت (دُفعة)'
        verbose_name_plural = 'اللوتات (الدُفعات)'
        ordering = ['expiry_date', 'manufacturing_date']

    def __str__(self):
        return f"{self.product} - لوت #{self.lot_number}"

    @property
    def is_expired(self):
        """هل انتهت صلاحية اللوت؟"""
        if self.expiry_date:
            return timezone.now().date() > self.expiry_date
        return False

    @property
    def days_until_expiry(self):
        """عدد الأيام حتى انتهاء الصلاحية"""
        if self.expiry_date:
            delta = self.expiry_date - timezone.now().date()
            return delta.days
        return None

    @property
    def total_value(self):
        """القيمة الإجمالية للوت"""
        return self.current_quantity * self.cost_per_unit


class CycleCount(models.Model):
    """الجرد الدوري"""
    STATUS_CHOICES = [
        ('scheduled', 'مجدول'),
        ('in_progress', 'قيد التنفيذ'),
        ('completed', 'مكتمل'),
        ('cancelled', 'ملغي'),
    ]

    COUNT_TYPE_CHOICES = [
        ('full', 'جرد كامل'),
        ('partial', 'جرد جزئي'),
        ('abc_a', 'جرد فئة A'),
        ('abc_b', 'جرد فئة B'),
        ('abc_c', 'جرد فئة C'),
        ('random', 'جرد عشوائي'),
    ]

    name = models.CharField(max_length=200, verbose_name='اسم الجرد')
    location = models.ForeignKey(
        'inventory.Location',
        on_delete=models.CASCADE,
        related_name='cycle_counts',
        verbose_name='الموقع'
    )
    count_type = models.CharField(
        max_length=20,
        choices=COUNT_TYPE_CHOICES,
        default='full',
        verbose_name='نوع الجرد'
    )
    scheduled_date = models.DateField(verbose_name='تاريخ الجرد المجدول')
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='بدأ في')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='اكتمل في')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='scheduled',
        verbose_name='الحالة'
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_cycle_counts',
        verbose_name='المسؤول'
    )
    supervised_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='supervised_cycle_counts',
        verbose_name='المشرف'
    )
    notes = models.TextField(blank=True, verbose_name='ملاحظات')
    total_items = models.PositiveIntegerField(default=0, verbose_name='إجمالي الأصناف')
    counted_items = models.PositiveIntegerField(default=0, verbose_name='الأصناف المجرودة')
    discrepancies_count = models.PositiveIntegerField(default=0, verbose_name='عدد الفروقات')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')

    class Meta:
        verbose_name = 'جرد دوري'
        verbose_name_plural = 'الجرد الدوري'
        ordering = ['-scheduled_date']

    def __str__(self):
        return f"{self.name} - {self.scheduled_date}"

    @property
    def completion_percentage(self):
        """نسبة الإتمام"""
        if self.total_items == 0:
            return 0
        return round((self.counted_items / self.total_items) * 100, 1)

    @property
    def accuracy_rate(self):
        """نسبة الدقة"""
        if self.counted_items == 0:
            return 0
        accurate = self.counted_items - self.discrepancies_count
        return round((accurate / self.counted_items) * 100, 1)

    def start_count(self, user):
        """بدء الجرد"""
        self.status = 'in_progress'
        self.started_at = timezone.now()
        self.assigned_to = user
        self.save(update_fields=['status', 'started_at', 'assigned_to'])

    def complete_count(self):
        """إتمام الجرد"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        items = self.items.all()
        self.counted_items = items.filter(counted_quantity__isnull=False).count()
        self.discrepancies_count = items.filter(has_discrepancy=True).count()
        self.save()


class CycleCountItem(models.Model):
    """بند في الجرد الدوري"""
    cycle_count = models.ForeignKey(
        CycleCount,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='الجرد'
    )
    product = models.ForeignKey(
        'inventory.Product',
        on_delete=models.CASCADE,
        verbose_name='المنتج'
    )
    system_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='الكمية في النظام'
    )
    counted_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='الكمية المجرودة'
    )
    has_discrepancy = models.BooleanField(default=False, verbose_name='يوجد فرق')
    discrepancy_reason = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='سبب الفرق'
    )
    adjustment_created = models.BooleanField(
        default=False,
        verbose_name='تم إنشاء تسوية'
    )
    counted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='جُرد بواسطة'
    )
    counted_at = models.DateTimeField(null=True, blank=True, verbose_name='تاريخ الجرد')
    notes = models.TextField(blank=True, verbose_name='ملاحظات')

    class Meta:
        verbose_name = 'بند جرد'
        verbose_name_plural = 'بنود الجرد'
        unique_together = ['cycle_count', 'product']

    def __str__(self):
        return f"{self.product} - نظام: {self.system_quantity}, فعلي: {self.counted_quantity}"

    @property
    def variance(self):
        """الفرق بين الكمية الفعلية والنظامية"""
        if self.counted_quantity is not None:
            return self.counted_quantity - self.system_quantity
        return None

    @property
    def variance_percentage(self):
        """نسبة الفرق"""
        if self.variance is not None and self.system_quantity != 0:
            return round((self.variance / self.system_quantity) * 100, 1)
        return None

    def save(self, *args, **kwargs):
        if self.counted_quantity is not None:
            self.has_discrepancy = self.counted_quantity != self.system_quantity
        super().save(*args, **kwargs)
