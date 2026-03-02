from django.db import models


class Notification(models.Model):
    """إشعار"""
    NOTIFICATION_TYPES = [
        ('info', 'معلومة'),
        ('warning', 'تحذير'),
        ('danger', 'خطر'),
        ('success', 'نجاح'),
    ]
    NOTIFICATION_CATEGORIES = [
        ('stock_low', 'مخزون منخفض'),
        ('stock_out', 'نفاد مخزون'),
        ('invoice_overdue', 'فاتورة متأخرة'),
        ('installment_due', 'قسط مستحق'),
        ('installment_overdue', 'قسط متأخر'),
        ('contract_expiring', 'عقد قارب على الانتهاء'),
        ('contract_expired', 'عقد منتهي'),
        ('quotation_expiring', 'عرض سعر قارب على الانتهاء'),
        ('quotation_follow_up', 'متابعة عرض سعر'),
        ('production_delayed', 'أمر إنتاج متأخر'),
        ('production_completed', 'أمر إنتاج مكتمل'),
        ('leave_request', 'طلب إجازة'),
        ('advance_request', 'طلب سلفة'),
        ('expense_pending', 'مصروف في انتظار الاعتماد'),
        ('check_due', 'شيك مستحق'),
        ('check_bounced', 'شيك مرتجع'),
        ('payroll_ready', 'مسيّر رواتب جاهز'),
        ('budget_exceeded', 'تجاوز ميزانية'),
        ('general', 'عام'),
    ]

    user = models.ForeignKey('core.User', on_delete=models.CASCADE, related_name='notifications', verbose_name="المستخدم")
    title = models.CharField(max_length=255, verbose_name="العنوان")
    message = models.TextField(verbose_name="الرسالة")
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='info', verbose_name="النوع")
    category = models.CharField(max_length=30, choices=NOTIFICATION_CATEGORIES, default='general', verbose_name="الفئة")

    # رابط الإجراء
    action_url = models.CharField(max_length=500, blank=True, verbose_name="رابط الإجراء")

    # الحالة
    is_read = models.BooleanField(default=False, verbose_name="مقروء")
    read_at = models.DateTimeField(null=True, blank=True, verbose_name="وقت القراءة")

    # المصدر
    source_model = models.CharField(max_length=100, blank=True, verbose_name="المصدر")
    source_id = models.CharField(max_length=50, blank=True, verbose_name="رقم المصدر")

    # الفرع
    branch = models.ForeignKey('core.Branch', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="الفرع")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="التاريخ")

    class Meta:
        verbose_name = "إشعار"
        verbose_name_plural = "الإشعارات"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} — {self.user}"


class NotificationSetting(models.Model):
    """إعدادات الإشعارات لكل مستخدم"""
    user = models.OneToOneField('core.User', on_delete=models.CASCADE, related_name='notification_settings')

    # ما الإشعارات التي يريد استقبالها
    stock_alerts = models.BooleanField(default=True, verbose_name="تنبيهات المخزون")
    invoice_alerts = models.BooleanField(default=True, verbose_name="تنبيهات الفواتير")
    production_alerts = models.BooleanField(default=True, verbose_name="تنبيهات الإنتاج")
    hr_alerts = models.BooleanField(default=True, verbose_name="تنبيهات الموارد البشرية")
    financial_alerts = models.BooleanField(default=True, verbose_name="تنبيهات مالية")

    # البريد الإلكتروني
    email_notifications = models.BooleanField(default=False, verbose_name="إشعارات بالإيميل")

    class Meta:
        verbose_name = "إعدادات إشعارات"
        verbose_name_plural = "إعدادات الإشعارات"

    def __str__(self):
        return f"إعدادات إشعارات {self.user}"
