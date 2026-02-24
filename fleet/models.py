from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

try:
    # استيراد نماذج المحاسبة عند توفرها
    from accounting.models import JournalEntry, JournalEntryItem, Account
except Exception:  # pragma: no cover - في حال عدم توافر التطبيق بعد
    JournalEntry = None
    JournalEntryItem = None
    Account = None

User = get_user_model()


class Driver(models.Model):
    """سائق في النظام."""
    name = models.CharField(max_length=120, verbose_name='اسم السائق')
    phone = models.CharField(max_length=40, blank=True, verbose_name='الهاتف')
    license_number = models.CharField(max_length=60, blank=True, verbose_name='رقم الرخصة')
    license_expiry = models.DateField(null=True, blank=True, verbose_name='انتهاء الرخصة')
    active = models.BooleanField(default=True, verbose_name='نشط')
    notes = models.TextField(blank=True, verbose_name='ملاحظات')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'سائق'
        verbose_name_plural = 'السائقون'
        permissions = [
            ("manage_driver", "إدارة السائق"),
        ]

    def __str__(self):
        return self.name


class Vehicle(models.Model):
    """مركبة (سيارة / شاحنة)."""
    STATUS_CHOICES = [
        ('available', 'متاحة'),
        ('in_use', 'قيد الاستخدام'),
        ('maintenance', 'صيانة'),
        ('inactive', 'متوقفة'),
    ]

    name = models.CharField(max_length=120, verbose_name='اسم المركبة')
    plate_number = models.CharField(max_length=40, unique=True, verbose_name='رقم اللوحة')
    type = models.CharField(max_length=60, blank=True, verbose_name='النوع/التصنيف')
    model_year = models.PositiveIntegerField(null=True, blank=True, verbose_name='سنة الصنع')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available', verbose_name='الحالة')
    current_odometer = models.PositiveIntegerField(default=0, verbose_name='عداد (كم)')
    notes = models.TextField(blank=True, verbose_name='ملاحظات')

    class Meta:
        verbose_name = 'مركبة'
        verbose_name_plural = 'المركبات'
        permissions = [
            ("manage_vehicle", "إدارة مركبة"),
        ]

    def __str__(self):
        return f"{self.plate_number} - {self.name}" if self.name else self.plate_number

    @property
    def total_expenses(self):
        return sum(exp.amount for exp in self.expenses.all())  # type: ignore

    @property
    def expenses_by_category(self):
        data = {}
        for exp in self.expenses.all():  # type: ignore
            data.setdefault(exp.category, 0)
            data[exp.category] += exp.amount
        return data


class VehicleDocumentQuerySet(models.QuerySet):
    def expiring_within(self, days=30):
        today = timezone.now().date()
        future = today + timezone.timedelta(days=days)
        return self.filter(expiry_date__gte=today, expiry_date__lte=future)

    def expired(self):
        today = timezone.now().date()
        return self.filter(expiry_date__lt=today)


class VehicleDocument(models.Model):
    """مستندات المركبة (رخصة، تأمين...)."""
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    vehicle = models.ForeignKey(Vehicle, related_name='documents', on_delete=models.CASCADE)
    doc_type = models.CharField(max_length=80, verbose_name='نوع المستند')
    file = models.FileField(upload_to='vehicles/docs/', verbose_name='الملف')
    expiry_date = models.DateField(null=True, blank=True, verbose_name='تاريخ الانتهاء')
    notes = models.CharField(max_length=255, blank=True, verbose_name='ملاحظات')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    # مدير مخصص يدعم التوابع expiring_within و expired
    objects = VehicleDocumentQuerySet.as_manager()

    class Meta:
        verbose_name = 'مستند مركبة'
        verbose_name_plural = 'مستندات المركبات'

    def __str__(self):
        return f"{self.vehicle} - {self.doc_type}"


class VehicleExpense(models.Model):
    """مصروفات المركبة (صيانة، ترخيص، مخالفات، وقود...)."""
    CATEGORY_CHOICES = [
        ('maintenance', 'صيانة'),
        ('license', 'ترخيص / تأمين'),
        ('fine', 'مخالفة'),
        ('fuel', 'وقود'),
        ('other', 'أخرى'),
    ]
    vehicle = models.ForeignKey(Vehicle, related_name='expenses', on_delete=models.CASCADE)
    driver = models.ForeignKey('fleet.Driver', null=True, blank=True, related_name='expenses', on_delete=models.SET_NULL, verbose_name='السائق (إن وجد)')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, verbose_name='التصنيف')
    description = models.CharField(max_length=255, blank=True, verbose_name='الوصف')
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='المبلغ')
    date = models.DateField(verbose_name='التاريخ')
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, verbose_name='أنشئ بواسطة')
    created_at = models.DateTimeField(auto_now_add=True)
    journal_entry = models.ForeignKey('accounting.JournalEntry', null=True, blank=True, on_delete=models.SET_NULL, verbose_name='قيد محاسبي مرتبط')
    advance = models.ForeignKey('fleet.DriverAdvance', null=True, blank=True, related_name='expenses', on_delete=models.SET_NULL, verbose_name='عهدة مرتبطة')

    class Meta:
        verbose_name = 'مصروف مركبة'
        verbose_name_plural = 'مصروفات المركبات'
        ordering = ['-date', '-id']
        permissions = [
            ("manage_vehicleexpense", "إدارة مصروف مركبة"),
        ]

    def __str__(self):
        return f"{self.vehicle} - {self.get_category_display()} - {self.amount}"  # type: ignore

    def ensure_journal_entry(self, user=None):
        """إنشاء قيد محاسبي تلقائي للمصروف إذا توفرت إعدادات الحسابات ولم يكن منشأ سابقاً.

        القاعدة البسيطة: مدين حساب المصروف (حسب التصنيف) / دائن الحساب النقدي الافتراضي.
        يتم الترحيل مباشرة إذا كان القيد متوازن.
        """
        if getattr(self, 'journal_entry_id', None) or not Account:
            return self.journal_entry
        settings = FleetAccountingSettings.get()
        debit_acc = settings.get_account_for_category(self.category)
        credit_acc = settings.default_credit_account
        if not (debit_acc and credit_acc):
            return None
        # إنشاء القيد
        if JournalEntry is None or JournalEntryItem is None:
            return None
        je = JournalEntry.objects.create(
            date=self.date,
            entry_type='manual',
            description=f"مصروف مركبة {self.vehicle.plate_number} - {self.get_category_display()} - {self.amount}"  # type: ignore
            ,
            reference=f"FEXP-{self.pk}",
            created_by=user if user and getattr(user, 'is_authenticated', False) else None,
            is_posted=False,
        )
        JournalEntryItem.objects.create(
            journal_entry=je,
            account=debit_acc,
            type='debit',
            amount=self.amount,
            description=self.description or je.description,
        )
        JournalEntryItem.objects.create(
            journal_entry=je,
            account=credit_acc,
            type='credit',
            amount=self.amount,
            description=self.description or je.description,
        )
        if je.total_debit == je.total_credit:
            je.is_posted = True
            je.save(update_fields=['is_posted'])
        self.journal_entry = je
        self.save(update_fields=['journal_entry'])
        return je


class Trip(models.Model):
    """رحلة/مشوار لسائق ومركبة."""
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    vehicle = models.ForeignKey(Vehicle, related_name='trips', on_delete=models.CASCADE)
    driver = models.ForeignKey(Driver, related_name='trips', on_delete=models.CASCADE)
    start_time = models.DateTimeField(verbose_name='وقت البداية')
    end_time = models.DateTimeField(null=True, blank=True, verbose_name='وقت النهاية')
    origin = models.CharField(max_length=120, verbose_name='نقطة الانطلاق')
    destination = models.CharField(max_length=120, verbose_name='الوجهة')
    odometer_start = models.PositiveIntegerField(null=True, blank=True, verbose_name='قراءة العداد (بداية)')
    odometer_end = models.PositiveIntegerField(null=True, blank=True, verbose_name='قراءة العداد (نهاية)')
    distance_km = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name='المسافة (كم)')
    purpose = models.CharField(max_length=160, blank=True, verbose_name='الغرض')
    notes = models.TextField(blank=True, verbose_name='ملاحظات')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'رحلة'
        verbose_name_plural = 'الرحلات'
        ordering = ['-start_time']
        permissions = [
            ("manage_trip", "إدارة رحلة"),
        ]

    def __str__(self):
        return f"{self.vehicle} {self.origin}->{self.destination} {self.start_time:%Y-%m-%d}" if getattr(self, 'vehicle_id', None) else str(self.start_time)

    @property
    def duration_hours(self):
        if self.end_time and self.start_time:
            delta = self.end_time - self.start_time
            return round(delta.total_seconds() / 3600, 2)
        return None

    def save(self, *args, **kwargs):
        is_update = self.pk is not None
        if is_update:
            # منع تعديل odometer_start بعد الحفظ الأول (حماية النزاهة)
            orig = Trip.objects.filter(pk=self.pk).only('odometer_start').first()
            if orig and orig.odometer_start is not None and self.odometer_start != orig.odometer_start:
                self.odometer_start = orig.odometer_start
        # إذا تم إدخال end_time بدون odometer_end حاول تعيينه من current_odometer
        if self.end_time and self.odometer_end is None and getattr(self, 'vehicle_id', None):
            # لا نفرض لكن نحاول ملء آلي إذا كان العداد الحالي >= البداية
            if self.odometer_start is not None and self.vehicle and self.vehicle.current_odometer >= self.odometer_start:
                self.odometer_end = self.vehicle.current_odometer
        # تحقق من صحة القراءات
        if self.odometer_start is not None and self.odometer_end is not None:
            if self.odometer_end < self.odometer_start:
                # تصحيح تلقائي بسيط: اجعل النهاية مساوية للبداية
                self.odometer_end = self.odometer_start
            self.distance_km = (self.odometer_end - self.odometer_start)
        # حفظ أساسي
        super().save(*args, **kwargs)
        # تحديث عداد المركبة إذا كانت النهاية أكبر من الحالي
        if self.odometer_end and self.vehicle and self.vehicle.current_odometer < self.odometer_end:
            self.vehicle.current_odometer = self.odometer_end
            self.vehicle.save(update_fields=['current_odometer'])


class FleetAccountingSettings(models.Model):
    """إعدادات ربط مصروفات الأسطول بالحسابات المحاسبية.

    يتم تعريف حساب مدين لكل فئة + حساب دائن (نقدية / بنك).
    يستخدم أول سجل (singleton بسيط) عبر الدالة get().
    """
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    maintenance_account = models.ForeignKey('accounting.Account', null=True, blank=True, on_delete=models.SET_NULL, related_name='+', verbose_name='حساب صيانة')
    license_account = models.ForeignKey('accounting.Account', null=True, blank=True, on_delete=models.SET_NULL, related_name='+', verbose_name='حساب ترخيص/تأمين')
    fine_account = models.ForeignKey('accounting.Account', null=True, blank=True, on_delete=models.SET_NULL, related_name='+', verbose_name='حساب مخالفات')
    fuel_account = models.ForeignKey('accounting.Account', null=True, blank=True, on_delete=models.SET_NULL, related_name='+', verbose_name='حساب وقود')
    other_expense_account = models.ForeignKey('accounting.Account', null=True, blank=True, on_delete=models.SET_NULL, related_name='+', verbose_name='حساب مصروفات أخرى')
    default_credit_account = models.ForeignKey('accounting.Account', null=True, blank=True, on_delete=models.SET_NULL, related_name='+', verbose_name='حساب دائن افتراضي (نقدية / بنك)')
    auto_create_journals = models.BooleanField(default=True, verbose_name='إنشاء قيود تلقائياً')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'إعدادات محاسبة الأسطول'
        verbose_name_plural = 'إعدادات محاسبة الأسطول'

    def __str__(self):
        return 'إعدادات محاسبة الأسطول'

    @classmethod
    def get(cls):
        obj = cls.objects.first()
        if obj:
            return obj
        return cls.objects.create()

    def get_account_for_category(self, category: str):
        mapping = {
            'maintenance': self.maintenance_account,
            'license': self.license_account,
            'fine': self.fine_account,
            'fuel': self.fuel_account,
            'other': self.other_expense_account,
        }
        return mapping.get(category)


class DriverViolation(models.Model):
    """مخالفة سير على سائق.

    ترتبط اختيارياً بالمركبة، ويمكن إرفاق صورة/ملف إيصال المخالفة. عند حفظها يمكن لاحقاً ربطها بمصروف (أو احتسابها ضمن مصروفات السائق عبر جمع الغرامات).
    """
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    driver = models.ForeignKey(Driver, related_name='violations', on_delete=models.CASCADE, verbose_name='السائق')
    vehicle = models.ForeignKey(Vehicle, related_name='violations', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='المركبة')
    violation_type = models.CharField(max_length=120, verbose_name='نوع المخالفة')
    date = models.DateField(verbose_name='التاريخ')
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'), verbose_name='قيمة المخالفة')
    receipt = models.FileField(upload_to='fleet/violations/', null=True, blank=True, verbose_name='إيصال/مرفق')
    notes = models.TextField(blank=True, verbose_name='ملاحظات')
    is_paid = models.BooleanField(default=False, verbose_name='مدفوعة')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'مخالفة سائق'
        verbose_name_plural = 'مخالفات السائقين'
        ordering = ['-date', '-id']
        permissions = [
            ("manage_driverviolation", "إدارة مخالفة سائق"),
        ]

    def __str__(self):
        return f"{self.driver} - {self.violation_type} - {self.amount}" if getattr(self, 'driver_id', None) else self.violation_type


class DriverAdvance(models.Model):
    """عهدة (سلفة / مصروفات تحت التسوية) ممنوحة لسائق."""
    STATUS_CHOICES = [
        ('open', 'مفتوحة'),
        ('settled', 'مُقفلة'),
    ]
    driver = models.ForeignKey(Driver, related_name='advances', on_delete=models.CASCADE, verbose_name='السائق')
    date = models.DateField(verbose_name='تاريخ العهدة')
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='قيمة العهدة')
    description = models.CharField(max_length=255, blank=True, verbose_name='الوصف')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='open', verbose_name='الحالة')
    settlement_date = models.DateField(null=True, blank=True, verbose_name='تاريخ التصفية')
    notes = models.TextField(blank=True, verbose_name='ملاحظات')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'عهدة سائق'
        verbose_name_plural = 'عهد السائقين'
        ordering = ['-date', '-id']
        permissions = [
            ("manage_driveradvance", "إدارة عهدة سائق"),
        ]

    def __str__(self):
        return f"عهدة {self.driver} {self.amount}" if getattr(self, 'driver_id', None) else f"عهدة {getattr(self, 'id', '')}"

    @property
    def utilized_amount(self):
        total = sum(exp.amount for exp in self.expenses.all()) if hasattr(self, 'expenses') else Decimal('0')  # type: ignore
        return total

    @property
    def remaining_amount(self):
        return (self.amount or Decimal('0')) - self.utilized_amount

    def can_settle(self, tolerance=Decimal('0.05')):
        return self.status == 'open' and abs(self.remaining_amount) <= tolerance

    def settle(self, date=None):
        if self.status != 'settled':
            self.status = 'settled'
            from django.utils import timezone as _tz
            self.settlement_date = date or _tz.now().date()
            self.save(update_fields=['status', 'settlement_date'])
        return self


class DriverLocationPing(models.Model):
    """نقطة تتبع (GPS) لسائق/مركبة.

    الهدف: استقبال pings دورية من الموبايل/التطبيق لتتبع السائقين والمناديب.
    """
    driver = models.ForeignKey(Driver, related_name='location_pings', on_delete=models.CASCADE, verbose_name='السائق')
    vehicle = models.ForeignKey(Vehicle, null=True, blank=True, related_name='location_pings', on_delete=models.SET_NULL, verbose_name='المركبة')
    trip = models.ForeignKey(Trip, null=True, blank=True, related_name='location_pings', on_delete=models.SET_NULL, verbose_name='الرحلة')

    latitude = models.DecimalField(max_digits=10, decimal_places=7, verbose_name='خط العرض')
    longitude = models.DecimalField(max_digits=10, decimal_places=7, verbose_name='خط الطول')
    accuracy_m = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name='الدقة (متر)')
    speed_mps = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name='السرعة (م/ث)')
    heading_deg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name='الاتجاه (درجة)')

    recorded_at = models.DateTimeField(default=timezone.now, verbose_name='وقت التسجيل (من الجهاز)')
    source = models.CharField(max_length=80, blank=True, verbose_name='المصدر')
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, verbose_name='أنشئ بواسطة')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'نقطة تتبع سائق'
        verbose_name_plural = 'نقاط تتبع السائقين'
        ordering = ['-recorded_at', '-id']
        indexes = [
            models.Index(fields=['driver', 'recorded_at']),
            models.Index(fields=['vehicle', 'recorded_at']),
        ]
        permissions = [
            ("manage_driverlocationping", "إدارة تتبع السائق"),
        ]

    def __str__(self):
        return f"{self.driver} @ {self.recorded_at:%Y-%m-%d %H:%M}"


# تمت إضافة المدير المخصص داخل الكلاس أعلاه (objects = VehicleDocumentQuerySet.as_manager())
