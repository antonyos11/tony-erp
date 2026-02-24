from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import uuid


class PrinterConfiguration(models.Model):
    """
    إعداد الطابعات الموحد - ربط نوع المستند → الطابعة الفعلية.
    Unified printer routing configuration.
    Maps document types → physical printers.
    """
    PRINTER_TYPE_CHOICES = [
        ('zebra', _('Zebra ZPL (باركود/ملصقات)')),
        ('thermal', _('XPrinter ESC/POS (إيصالات)')),
        ('a4', _('A4 ليزر/حبر (مستندات)')),
        ('card', _('طابعة بطاقات هوية')),
    ]

    DOCUMENT_TYPE_CHOICES = [
        # الإنتاج
        ('production_barcode', _('ملصق باركود إنتاج')),
        ('warranty_label', _('ملصق ضمان')),
        # المبيعات
        ('sales_invoice', _('فاتورة مبيعات (A4)')),
        ('sales_receipt', _('إيصال مبيعات (حراري)')),
        # المشتريات
        ('purchase_order', _('أمر شراء (A4)')),
        # الموارد البشرية
        ('hr_id_card', _('بطاقة هوية موظف')),
        # المحاسبة
        ('journal_entry', _('قيد محاسبي (A4)')),
        ('trial_balance', _('ميزان المراجعة (A4)')),
        # المخزون
        ('product_barcode', _('باركود منتج')),
        # عام
        ('generic_a4', _('مستند A4 عام')),
        ('generic_receipt', _('إيصال عام')),
    ]

    CONNECTION_TYPE_CHOICES = [
        ('network', _('شبكة (IP:Port)')),
        ('cups', _('CUPS (Linux)')),
        ('usb', _('USB مباشر')),
        ('shared', _('طابعة مشاركة Windows')),
        ('agent', _('وكيل الطباعة WebSocket')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('اسم الطابعة'), max_length=200)
    printer_type = models.CharField(_('نوع الطابعة'), max_length=20, choices=PRINTER_TYPE_CHOICES)
    document_type = models.CharField(_('نوع المستند'), max_length=30, choices=DOCUMENT_TYPE_CHOICES)
    connection_type = models.CharField(_('نوع الاتصال'), max_length=20, choices=CONNECTION_TYPE_CHOICES, default='agent')

    # تفاصيل الاتصال
    ip_address = models.GenericIPAddressField(_('عنوان IP'), blank=True, null=True)
    port = models.PositiveIntegerField(_('المنفذ'), default=9100)
    cups_printer_name = models.CharField(_('اسم طابعة CUPS/OS'), max_length=200, blank=True, default='')
    shared_printer_name = models.CharField(_('اسم الطابعة المشتركة'), max_length=200, blank=True, default='')

    is_active = models.BooleanField(_('مفعّل'), default=True)
    is_default = models.BooleanField(_('افتراضي لهذا النوع'), default=False)

    # إحصائيات
    total_prints = models.PositiveIntegerField(default=0)
    last_print_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = _('إعداد طابعة')
        verbose_name_plural = _('إعدادات الطابعات')
        ordering = ['document_type', '-is_default', 'name']

    def __str__(self):
        default_mark = ' ★' if self.is_default else ''
        return f"{self.name} → {self.get_document_type_display()}{default_mark}"

    def increment_print_count(self):
        from django.utils import timezone
        PrinterConfiguration.objects.filter(pk=self.pk).update(
            total_prints=models.F('total_prints') + 1,
            last_print_at=timezone.now(),
        )


class UnifiedPrintJob(models.Model):
    """
    طابور الطباعة الموحد - كل عمليات الطباعة من كل الأنظمة تمر من هنا.
    Central print job queue - all prints across all modules go through here.
    """
    STATUS_CHOICES = [
        ('queued', _('في الطابور')),
        ('sent', _('أُرسل للوكيل')),
        ('printing', _('جاري الطباعة')),
        ('completed', _('مكتمل')),
        ('failed', _('فشل')),
        ('cancelled', _('ملغى')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document_type = models.CharField(
        _('نوع المستند'), max_length=30,
        choices=PrinterConfiguration.DOCUMENT_TYPE_CHOICES,
    )
    printer = models.ForeignKey(
        PrinterConfiguration,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='print_jobs',
        verbose_name=_('الطابعة'),
    )

    # الحمولة (واحد منها يُملأ)
    zpl_command = models.TextField(_('أمر ZPL'), blank=True, default='')
    escpos_data = models.BinaryField(_('بيانات ESC/POS'), blank=True, default=b'')
    pdf_base64 = models.TextField(_('PDF (base64)'), blank=True, default='')
    html_content = models.TextField(_('محتوى HTML'), blank=True, default='')

    # بيانات وصفية
    title = models.CharField(_('عنوان المهمة'), max_length=300, blank=True, default='')
    copies = models.PositiveIntegerField(default=1)
    status = models.CharField(_('الحالة'), max_length=20, choices=STATUS_CHOICES, default='queued')
    error_message = models.TextField(blank=True, default='')

    # تتبع المصدر
    source_app = models.CharField(_('التطبيق المصدر'), max_length=50, blank=True, default='')
    source_model = models.CharField(_('النموذج المصدر'), max_length=100, blank=True, default='')
    source_id = models.CharField(_('معرّف الكائن'), max_length=100, blank=True, default='')

    # التدقيق
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name=_('طُلب بواسطة'),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _('مهمة طباعة')
        verbose_name_plural = _('مهام الطباعة')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at'], name='printjob_status_created_idx'),
            models.Index(fields=['document_type', 'status'], name='printjob_doctype_status_idx'),
        ]

    def __str__(self):
        return f"[{self.get_status_display()}] {self.title or self.document_type} ({self.created_at:%Y-%m-%d %H:%M})"


# ══════════════════════════════════════════════════════════════
# Phase 2: Multi-Device Printing Architecture
# ══════════════════════════════════════════════════════════════

class PrintStation(models.Model):
    """
    محطة طباعة — تمثل جهاز كمبيوتر يعمل عليه وكيل الطباعة (Print Agent).
    Represents a physical workstation (PC) running a Print Agent.
    Auto-registered when the agent connects and broadcasts its identity.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # الهوية — يُرسلها الوكيل عند الاتصال
    machine_name = models.CharField(
        _('اسم الجهاز'),
        max_length=200,
        unique=True,
        help_text=_('اسم الجهاز (Hostname) — يُكتشف تلقائياً من الوكيل'),
    )
    machine_ip = models.GenericIPAddressField(
        _('عنوان IP'),
        blank=True,
        null=True,
        help_text=_('عنوان IP المُرسل من الوكيل'),
    )
    agent_port = models.PositiveIntegerField(_('منفذ الوكيل'), default=9876)
    agent_version = models.CharField(_('إصدار الوكيل'), max_length=20, blank=True, default='')
    os_platform = models.CharField(
        _('نظام التشغيل'),
        max_length=20,
        choices=[('windows', 'Windows'), ('linux', 'Linux'), ('macos', 'macOS')],
        default='windows',
    )

    # اسم مفهوم يحدده المدير
    display_name = models.CharField(
        _('الاسم المعروض'),
        max_length=200,
        blank=True,
        help_text=_("اسم ودي مثل 'جهاز التغليف' أو 'كاشير المبيعات 1'"),
    )
    location = models.CharField(
        _('الموقع'),
        max_length=200,
        blank=True,
        help_text=_("الموقع الفعلي: 'خط التغليف' أو 'صالة العرض 1'"),
    )

    # الطابعات المكتشفة (JSON خام من الوكيل)
    discovered_printers = models.JSONField(
        _('الطابعات المكتشفة'),
        default=list,
        blank=True,
        help_text=_('قائمة الطابعات المُرسلة من الوكيل عند الاتصال'),
    )

    # تتبع الحالة
    is_online = models.BooleanField(_('متصل'), default=False)
    last_seen = models.DateTimeField(_('آخر ظهور'), null=True, blank=True)
    first_seen = models.DateTimeField(_('أول ظهور'), auto_now_add=True)
    is_active = models.BooleanField(
        _('مفعّل'),
        default=True,
        help_text=_('يمكن للمدير تعطيل محطة'),
    )

    # ربط بالمستخدمين
    assigned_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='print_stations',
        verbose_name=_('المستخدمون المعيّنون'),
        help_text=_('المستخدمون المرتبطون بهذه المحطة (للتوجيه التلقائي)'),
    )

    class Meta:
        ordering = ['display_name', 'machine_name']
        verbose_name = _('محطة طباعة')
        verbose_name_plural = _('محطات الطباعة')

    def __str__(self):
        label = self.display_name or self.machine_name
        status = '🟢' if self.is_online else '🔴'
        return f"{status} {label}"

    def mark_online(self):
        self.is_online = True
        self.last_seen = timezone.now()
        self.save(update_fields=['is_online', 'last_seen'])

    def mark_offline(self):
        self.is_online = False
        self.save(update_fields=['is_online'])

    def update_discovered_printers(self, printers_list: list, agent_version: str = '', os_platform: str = ''):
        self.discovered_printers = printers_list
        self.last_seen = timezone.now()
        self.is_online = True
        update_fields = ['discovered_printers', 'last_seen', 'is_online']
        if agent_version:
            self.agent_version = agent_version
            update_fields.append('agent_version')
        if os_platform:
            self.os_platform = os_platform
            update_fields.append('os_platform')
        self.save(update_fields=update_fields)


class PrinterMapping(models.Model):
    """
    خريطة توجيه الطابعات — تربط نوع مستند بطابعة محددة على محطة محددة.
    Maps a specific document type to a specific printer ON a specific station.
      Station A + 'barcode'       → ZDesigner ZD220
      Station A + 'sales_receipt' → (None = غير متاح هنا)
      Station B + 'sales_receipt' → XP-80
    """
    DOCUMENT_TYPE_CHOICES = [
        ('barcode', _('ملصق باركود (Zebra ZPL)')),
        ('production_barcode', _('باركود إنتاج')),
        ('warranty_label', _('ملصق ضمان')),
        ('sales_receipt', _('إيصال مبيعات (POS)')),
        ('kitchen_receipt', _('إيصال مطبخ')),
        ('sales_invoice', _('فاتورة مبيعات (A4)')),
        ('purchase_order', _('أمر شراء (A4)')),
        ('delivery_note', _('إذن تسليم (A4)')),
        ('hr_document', _('مستند موارد بشرية (A4)')),
        ('trial_balance', _('ميزان المراجعة (A4)')),
        ('general', _('مستند عام')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    station = models.ForeignKey(
        PrintStation,
        on_delete=models.CASCADE,
        related_name='printer_mappings',
        verbose_name=_('المحطة'),
    )
    document_type = models.CharField(
        _('نوع المستند'),
        max_length=50,
        choices=DOCUMENT_TYPE_CHOICES,
    )

    # الطابعة المستهدفة
    printer_config = models.ForeignKey(
        PrinterConfiguration,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='station_mappings',
        verbose_name=_('إعداد الطابعة'),
        help_text=_('طابعة شبكية من إعدادات الطابعات (Zebra TCP مثلاً)'),
    )
    local_printer_name = models.CharField(
        _('اسم الطابعة المحلية'),
        max_length=300,
        blank=True,
        help_text=_(
            'اسم الطابعة المحلية على المحطة (من discovered_printers). '
            'يُستخدم عند الطباعة عبر تعريف نظام التشغيل المحلي.'
        ),
    )

    copies = models.PositiveIntegerField(_('عدد النسخ'), default=1)
    is_enabled = models.BooleanField(_('مفعّل'), default=True)
    priority = models.PositiveIntegerField(
        _('الأولوية'),
        default=0,
        help_text=_('الأعلى = تُجرّب أولاً عند وجود عدة تعيينات'),
    )

    class Meta:
        ordering = ['station', 'document_type', '-priority']
        unique_together = [('station', 'document_type', 'local_printer_name')]
        verbose_name = _('تعيين طابعة')
        verbose_name_plural = _('تعيينات الطابعات')

    def __str__(self):
        printer_label = self.local_printer_name or (self.printer_config.name if self.printer_config else '—')
        return f"{self.station} │ {self.get_document_type_display()} → {printer_label}"


class StationSession(models.Model):
    """
    جلسة محطة — تتبع المستخدم النشط حالياً على كل محطة.
    Tracks which user is currently active on which station.
    Populated via middleware or explicit login-to-station step.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='station_session',
        verbose_name=_('المستخدم'),
    )
    station = models.ForeignKey(
        PrintStation,
        on_delete=models.CASCADE,
        related_name='active_sessions',
        verbose_name=_('المحطة'),
    )
    session_key = models.CharField(max_length=40, blank=True)
    client_ip = models.GenericIPAddressField(_('عنوان IP العميل'), blank=True, null=True)
    connected_at = models.DateTimeField(_('وقت الاتصال'), auto_now=True)

    class Meta:
        verbose_name = _('جلسة محطة')
        verbose_name_plural = _('جلسات المحطات')

    def __str__(self):
        return f"{self.user} @ {self.station}"


class PrintTemplate(models.Model):
    """
    قالب طباعة مخصص — يحدد الأبعاد والتنسيق لكل نوع مستند.
    Custom print template — defines dimensions and formatting per document type.
    """
    TEMPLATE_TYPE_CHOICES = [
        ('barcode_label', _('ملصق باركود')),
        ('warranty_label', _('ملصق ضمان')),
        ('pos_receipt', _('إيصال نقطة بيع')),
        ('sales_invoice', _('فاتورة مبيعات')),
        ('production_label', _('ملصق إنتاج')),
        ('shipping_label', _('ملصق شحن')),
    ]

    UNIT_CHOICES = [
        ('mm', _('ملليمتر')),
        ('in', _('بوصة')),
        ('dots', _('نقاط (dots)')),
    ]

    name = models.CharField(_('اسم القالب'), max_length=100)
    template_type = models.CharField(
        _('نوع القالب'), max_length=30, choices=TEMPLATE_TYPE_CHOICES,
    )
    width = models.DecimalField(
        _('العرض'), max_digits=7, decimal_places=2,
        help_text=_('عرض الملصق/الإيصال'),
    )
    height = models.DecimalField(
        _('الارتفاع'), max_digits=7, decimal_places=2,
        help_text=_('ارتفاع الملصق/الإيصال (0 = لفة مستمرة)'),
    )
    unit = models.CharField(
        _('وحدة القياس'), max_length=5, choices=UNIT_CHOICES, default='mm',
    )
    dpi = models.PositiveIntegerField(_('دقة الطباعة (DPI)'), default=203)

    # ZPL/ESC-POS template content
    zpl_template = models.TextField(
        _('قالب ZPL'), blank=True,
        help_text=_('قالب ZPL مع متغيرات مثل {product_name}, {sku}, {barcode}'),
    )
    escpos_template = models.TextField(
        _('قالب ESC/POS'), blank=True,
        help_text=_('قالب ESC/POS بتنسيق JSON للأوامر'),
    )
    html_template = models.TextField(
        _('قالب HTML'), blank=True,
        help_text=_('قالب HTML للطباعة عبر المتصفح'),
    )

    # Margins
    margin_top = models.DecimalField(
        _('هامش علوي'), max_digits=5, decimal_places=2, default=0,
    )
    margin_left = models.DecimalField(
        _('هامش أيسر'), max_digits=5, decimal_places=2, default=0,
    )

    # Font settings
    font_size = models.PositiveIntegerField(_('حجم الخط الافتراضي'), default=24)
    barcode_height = models.PositiveIntegerField(
        _('ارتفاع الباركود (نقاط)'), default=80,
    )
    barcode_width = models.PositiveIntegerField(
        _('عرض خط الباركود (نقاط)'), default=2,
    )

    is_default = models.BooleanField(_('القالب الافتراضي'), default=False)
    is_active = models.BooleanField(_('نشط'), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['template_type', 'name']
        verbose_name = _('قالب طباعة')
        verbose_name_plural = _('قوالب الطباعة')

    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()}) — {self.width}×{self.height}{self.unit}"

    def render_zpl(self, context: dict) -> str:
        """Render ZPL template with context variables."""
        if not self.zpl_template:
            return ''
        result = self.zpl_template
        for key, value in context.items():
            result = result.replace(f'{{{key}}}', str(value))
        return result

    def render_escpos(self, context: dict) -> str:
        """Render ESC/POS template with context variables."""
        if not self.escpos_template:
            return ''
        result = self.escpos_template
        for key, value in context.items():
            result = result.replace(f'{{{key}}}', str(value))
        return result

    def get_dimensions_dots(self) -> tuple:
        """Return (width_dots, height_dots) based on unit and DPI."""
        if self.unit == 'dots':
            return int(self.width), int(self.height)
        elif self.unit == 'mm':
            factor = self.dpi / 25.4
            return int(float(self.width) * factor), int(float(self.height) * factor)
        elif self.unit == 'in':
            return int(float(self.width) * self.dpi), int(float(self.height) * self.dpi)
        return int(self.width), int(self.height)

    def save(self, *args, **kwargs):
        # Ensure only one default per template_type
        if self.is_default:
            PrintTemplate.objects.filter(
                template_type=self.template_type, is_default=True,
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)
