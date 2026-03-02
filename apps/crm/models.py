"""
نماذج تطبيق CRM — RITA ERP
"""
from django.db import models
from apps.core.models import AuditMixin


class CustomerGroup(AuditMixin):
    """مجموعات العملاء (VIP, عادي, متعثر، إلخ)"""
    name = models.CharField(max_length=255, verbose_name="اسم المجموعة")
    description = models.TextField(blank=True, verbose_name="الوصف")
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0,
                                               verbose_name="نسبة خصم %")
    credit_limit = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                        verbose_name="حد ائتمان")
    color = models.CharField(max_length=7, default='#1a73e8', verbose_name="اللون")
    is_active = models.BooleanField(default=True, verbose_name="نشط")

    class Meta:
        verbose_name = "مجموعة عملاء"
        verbose_name_plural = "مجموعات العملاء"

    def __str__(self):
        return self.name


class Lead(AuditMixin):
    """عميل محتمل (Lead)"""
    LEAD_SOURCES = [
        ('walk_in', 'زيارة مباشرة'),
        ('phone', 'هاتف'),
        ('whatsapp', 'واتساب'),
        ('facebook', 'فيسبوك'),
        ('instagram', 'إنستجرام'),
        ('website', 'الموقع الإلكتروني'),
        ('referral', 'ترشيح من عميل'),
        ('exhibition', 'معرض'),
        ('olx', 'OLX'),
        ('jumia', 'جوميا'),
        ('other', 'أخرى'),
    ]
    LEAD_STATUSES = [
        ('new', 'جديد'),
        ('contacted', 'تم التواصل'),
        ('interested', 'مهتم'),
        ('qualified', 'مؤهل'),
        ('negotiation', 'تفاوض'),
        ('won', 'تم البيع'),
        ('lost', 'خسرناه'),
        ('dormant', 'خامل'),
    ]
    PRIORITY_CHOICES = [
        ('low', 'منخفض'),
        ('medium', 'متوسط'),
        ('high', 'مرتفع'),
        ('urgent', 'عاجل'),
    ]

    name = models.CharField(max_length=255, verbose_name="الاسم")
    phone = models.CharField(max_length=20, verbose_name="الهاتف")
    phone2 = models.CharField(max_length=20, blank=True, verbose_name="هاتف 2")
    email = models.EmailField(blank=True, verbose_name="الإيميل")
    company = models.CharField(max_length=255, blank=True, verbose_name="الشركة")
    address = models.TextField(blank=True, verbose_name="العنوان")
    governorate = models.CharField(max_length=100, blank=True, verbose_name="المحافظة")

    source = models.CharField(max_length=20, choices=LEAD_SOURCES, default='walk_in', verbose_name="المصدر")
    status = models.CharField(max_length=20, choices=LEAD_STATUSES, default='new', verbose_name="الحالة")
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium', verbose_name="الأولوية")

    interested_products = models.ManyToManyField('inventory.Product', blank=True,
                                                   verbose_name="المنتجات المهتم بها")
    estimated_value = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                           verbose_name="القيمة التقديرية")

    branch = models.ForeignKey('core.Branch', on_delete=models.PROTECT, verbose_name="الفرع")
    assigned_to = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='assigned_leads', verbose_name="المسؤول")

    converted_to_customer = models.ForeignKey('sales.Customer', on_delete=models.SET_NULL,
                                               null=True, blank=True, verbose_name="تحوّل إلى عميل")
    conversion_date = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ التحويل")

    next_follow_up = models.DateField(null=True, blank=True, verbose_name="تاريخ المتابعة القادمة")
    last_contact_date = models.DateField(null=True, blank=True, verbose_name="آخر تواصل")

    lost_reason = models.TextField(blank=True, verbose_name="سبب الخسارة")
    lost_to_competitor = models.CharField(max_length=255, blank=True, verbose_name="خسرناه لصالح")

    notes = models.TextField(blank=True, verbose_name="ملاحظات")

    class Meta:
        verbose_name = "عميل محتمل"
        verbose_name_plural = "العملاء المحتملين"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"


class Interaction(AuditMixin):
    """تفاعل/تواصل مع عميل أو Lead"""
    INTERACTION_TYPES = [
        ('call_in', 'مكالمة واردة'),
        ('call_out', 'مكالمة صادرة'),
        ('whatsapp', 'واتساب'),
        ('sms', 'رسالة SMS'),
        ('email', 'إيميل'),
        ('visit_in', 'زيارة للمعرض'),
        ('visit_out', 'زيارة ميدانية'),
        ('meeting', 'اجتماع'),
        ('complaint', 'شكوى'),
        ('inquiry', 'استفسار'),
        ('after_sale', 'متابعة ما بعد البيع'),
        ('delivery_follow', 'متابعة توصيل'),
        ('warranty_claim', 'مطالبة ضمان'),
    ]
    INTERACTION_RESULTS = [
        ('interested', 'مهتم'),
        ('callback', 'سيتصل لاحقاً'),
        ('needs_quote', 'يحتاج عرض سعر'),
        ('will_visit', 'سيزور المعرض'),
        ('ordered', 'طلب'),
        ('complaint_resolved', 'تم حل الشكوى'),
        ('complaint_pending', 'شكوى قيد الحل'),
        ('not_interested', 'غير مهتم'),
        ('no_answer', 'لا يرد'),
        ('wrong_number', 'رقم خاطئ'),
    ]

    customer = models.ForeignKey('sales.Customer', on_delete=models.CASCADE, null=True, blank=True,
                                  related_name='interactions', verbose_name="العميل")
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, null=True, blank=True,
                              related_name='interactions', verbose_name="العميل المحتمل")

    date = models.DateTimeField(verbose_name="التاريخ")
    interaction_type = models.CharField(max_length=20, choices=INTERACTION_TYPES, verbose_name="نوع التواصل")
    result = models.CharField(max_length=20, choices=INTERACTION_RESULTS, blank=True, verbose_name="النتيجة")

    subject = models.CharField(max_length=500, verbose_name="الموضوع")
    details = models.TextField(verbose_name="التفاصيل")

    handled_by = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True,
                                    related_name='handled_interactions', verbose_name="المسؤول")
    branch = models.ForeignKey('core.Branch', on_delete=models.SET_NULL, null=True, verbose_name="الفرع")

    follow_up_required = models.BooleanField(default=False, verbose_name="يحتاج متابعة")
    follow_up_date = models.DateField(null=True, blank=True, verbose_name="تاريخ المتابعة")
    follow_up_notes = models.TextField(blank=True, verbose_name="ملاحظات المتابعة")
    is_follow_up_done = models.BooleanField(default=False, verbose_name="تمت المتابعة")

    quotation = models.ForeignKey('quotations.Quotation', on_delete=models.SET_NULL,
                                   null=True, blank=True, verbose_name="عرض السعر")
    invoice = models.ForeignKey('sales.SalesInvoice', on_delete=models.SET_NULL,
                                 null=True, blank=True, verbose_name="الفاتورة")

    satisfaction_rating = models.IntegerField(null=True, blank=True,
                                               choices=[(1, '😡'), (2, '😞'), (3, '😐'), (4, '😊'), (5, '😍')],
                                               verbose_name="تقييم الرضا")

    class Meta:
        verbose_name = "تفاعل"
        verbose_name_plural = "التفاعلات"
        ordering = ['-date']

    def __str__(self):
        entity = self.customer or self.lead
        return f"{self.get_interaction_type_display()} — {entity}"


class Complaint(AuditMixin):
    """شكاوى العملاء"""
    COMPLAINT_STATUSES = [
        ('open', 'مفتوحة'),
        ('in_progress', 'جاري المعالجة'),
        ('waiting_customer', 'في انتظار العميل'),
        ('waiting_parts', 'في انتظار قطع غيار'),
        ('resolved', 'محلولة'),
        ('closed', 'مغلقة'),
        ('reopened', 'أعيد فتحها'),
    ]
    COMPLAINT_TYPES = [
        ('product_quality', 'جودة المنتج'),
        ('product_defect', 'عيب صناعة'),
        ('delivery_delay', 'تأخير توصيل'),
        ('delivery_damage', 'تلف أثناء التوصيل'),
        ('wrong_product', 'منتج خاطئ'),
        ('missing_parts', 'أجزاء ناقصة'),
        ('price_dispute', 'خلاف على السعر'),
        ('service', 'خدمة سيئة'),
        ('warranty', 'ضمان'),
        ('other', 'أخرى'),
    ]
    SEVERITY_CHOICES = [
        ('low', 'بسيطة'),
        ('medium', 'متوسطة'),
        ('high', 'خطيرة'),
        ('critical', 'حرجة'),
    ]

    complaint_number = models.CharField(max_length=50, unique=True, verbose_name="رقم الشكوى")
    date = models.DateTimeField(verbose_name="التاريخ")
    customer = models.ForeignKey('sales.Customer', on_delete=models.PROTECT,
                                  related_name='complaints', verbose_name="العميل")

    complaint_type = models.CharField(max_length=20, choices=COMPLAINT_TYPES, verbose_name="نوع الشكوى")
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='medium', verbose_name="الخطورة")
    status = models.CharField(max_length=20, choices=COMPLAINT_STATUSES, default='open', verbose_name="الحالة")

    subject = models.CharField(max_length=500, verbose_name="الموضوع")
    description = models.TextField(verbose_name="تفاصيل الشكوى")

    product = models.ForeignKey('inventory.Product', on_delete=models.SET_NULL, null=True, blank=True,
                                 verbose_name="المنتج")
    invoice = models.ForeignKey('sales.SalesInvoice', on_delete=models.SET_NULL, null=True, blank=True,
                                 verbose_name="الفاتورة")

    branch = models.ForeignKey('core.Branch', on_delete=models.PROTECT, verbose_name="الفرع")
    assigned_to = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='assigned_complaints', verbose_name="المسؤول")

    resolution = models.TextField(blank=True, verbose_name="الحل")
    resolution_date = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الحل")
    resolution_type = models.CharField(max_length=20, blank=True, choices=[
        ('replaced', 'تم الاستبدال'),
        ('repaired', 'تم الإصلاح'),
        ('refunded', 'تم الاسترداد'),
        ('discount', 'تم منح خصم'),
        ('apologized', 'تم الاعتذار'),
        ('no_action', 'لا يحتاج إجراء'),
    ], verbose_name="نوع الحل")
    resolution_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="تكلفة الحل")

    customer_satisfaction = models.IntegerField(null=True, blank=True,
                                                 choices=[(1, '😡'), (2, '😞'), (3, '😐'), (4, '😊'), (5, '😍')],
                                                 verbose_name="رضا العميل بعد الحل")

    image1 = models.ImageField(upload_to='complaints/', null=True, blank=True, verbose_name="صورة 1")
    image2 = models.ImageField(upload_to='complaints/', null=True, blank=True, verbose_name="صورة 2")

    class Meta:
        verbose_name = "شكوى"
        verbose_name_plural = "الشكاوى"
        ordering = ['-date']

    def __str__(self):
        return f"{self.complaint_number} - {self.customer.name}"


class Task(AuditMixin):
    """مهام ومتابعات"""
    TASK_STATUSES = [
        ('pending', 'في الانتظار'),
        ('in_progress', 'جاري'),
        ('completed', 'مكتمل'),
        ('cancelled', 'ملغي'),
        ('overdue', 'متأخر'),
    ]

    title = models.CharField(max_length=500, verbose_name="العنوان")
    description = models.TextField(blank=True, verbose_name="التفاصيل")

    assigned_to = models.ForeignKey('core.User', on_delete=models.CASCADE,
                                     related_name='tasks', verbose_name="المسؤول")
    assigned_by = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True,
                                     related_name='assigned_tasks', verbose_name="كلّفه")

    due_date = models.DateField(verbose_name="تاريخ الاستحقاق")
    status = models.CharField(max_length=20, choices=TASK_STATUSES, default='pending', verbose_name="الحالة")
    priority = models.CharField(max_length=10, choices=[
        ('low', 'منخفض'), ('medium', 'متوسط'), ('high', 'مرتفع'), ('urgent', 'عاجل'),
    ], default='medium', verbose_name="الأولوية")

    customer = models.ForeignKey('sales.Customer', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="العميل")
    lead = models.ForeignKey(Lead, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Lead")
    complaint = models.ForeignKey(Complaint, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="الشكوى")
    branch = models.ForeignKey('core.Branch', on_delete=models.SET_NULL, null=True, verbose_name="الفرع")

    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الإكمال")
    completion_notes = models.TextField(blank=True, verbose_name="ملاحظات الإكمال")

    class Meta:
        verbose_name = "مهمة"
        verbose_name_plural = "المهام"
        ordering = ['due_date']

    def __str__(self):
        return self.title


class CustomerRating(models.Model):
    """تقييم/تصنيف العميل الداخلي"""
    customer = models.OneToOneField('sales.Customer', on_delete=models.CASCADE,
                                     related_name='rating', verbose_name="العميل")

    total_purchases = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="إجمالي المشتريات")
    total_invoices = models.IntegerField(default=0, verbose_name="عدد الفواتير")
    total_returns = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="إجمالي المرتجعات")
    return_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="نسبة المرتجعات %")
    avg_payment_days = models.IntegerField(default=0, verbose_name="متوسط أيام السداد")
    total_complaints = models.IntegerField(default=0, verbose_name="عدد الشكاوى")
    last_purchase_date = models.DateField(null=True, blank=True, verbose_name="آخر عملية شراء")
    days_since_last_purchase = models.IntegerField(default=0, verbose_name="أيام منذ آخر شراء")

    score = models.IntegerField(default=0, verbose_name="النقاط")
    grade = models.CharField(max_length=5, default='C', choices=[
        ('A+', 'ممتاز'),
        ('A', 'جيد جداً'),
        ('B', 'جيد'),
        ('C', 'متوسط'),
        ('D', 'ضعيف'),
        ('F', 'سيء'),
    ], verbose_name="التصنيف")

    notes = models.TextField(blank=True, verbose_name="ملاحظات")
    last_updated = models.DateTimeField(auto_now=True, verbose_name="آخر تحديث")

    class Meta:
        verbose_name = "تقييم عميل"
        verbose_name_plural = "تقييمات العملاء"

    def __str__(self):
        return f"{self.customer.name} — {self.grade} ({self.score})"


class SMSLog(models.Model):
    """سجل الرسائل"""
    customer = models.ForeignKey('sales.Customer', on_delete=models.SET_NULL, null=True, blank=True)
    lead = models.ForeignKey(Lead, on_delete=models.SET_NULL, null=True, blank=True)
    phone = models.CharField(max_length=20, verbose_name="الرقم")
    message = models.TextField(verbose_name="الرسالة")
    message_type = models.CharField(max_length=20, choices=[
        ('sms', 'SMS'),
        ('whatsapp', 'واتساب'),
    ], verbose_name="النوع")
    status = models.CharField(max_length=20, choices=[
        ('sent', 'مُرسل'),
        ('delivered', 'تم التوصيل'),
        ('failed', 'فشل'),
    ], default='sent', verbose_name="الحالة")
    sent_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإرسال")
    sent_by = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True)

    class Meta:
        verbose_name = "رسالة"
        verbose_name_plural = "سجل الرسائل"
        ordering = ['-sent_at']

    def __str__(self):
        return f"{self.phone} — {self.message[:40]}"
