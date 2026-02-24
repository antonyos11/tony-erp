"""
نماذج CRM المتقدمة
====================
المتابعة التلقائية، تقييم العملاء، SLA الدعم الفني
"""

from django.db import models
from django.conf import settings
from django.utils import timezone


class FollowUpRule(models.Model):
    """قواعد المتابعة التلقائية"""
    TRIGGER_CHOICES = [
        ('opportunity_stage_change', 'تغيير مرحلة الفرصة'),
        ('no_activity_days', 'عدم نشاط لأيام'),
        ('quotation_sent', 'بعد إرسال عرض سعر'),
        ('quotation_expired', 'انتهاء عرض سعر'),
        ('ticket_no_response', 'تذكرة بدون رد'),
        ('customer_birthday', 'عيد ميلاد العميل'),
        ('contract_expiring', 'قرب انتهاء العقد'),
        ('no_purchase_days', 'عدم شراء لأيام'),
    ]

    ACTION_CHOICES = [
        ('create_activity', 'إنشاء نشاط'),
        ('send_notification', 'إرسال إشعار'),
        ('escalate', 'تصعيد للمدير'),
        ('send_email', 'إرسال بريد إلكتروني'),
        ('create_ticket', 'إنشاء تذكرة'),
    ]

    name = models.CharField(max_length=200, verbose_name='اسم القاعدة')
    description = models.TextField(blank=True, verbose_name='الوصف')
    trigger = models.CharField(
        max_length=50,
        choices=TRIGGER_CHOICES,
        verbose_name='المشغِّل'
    )
    days_after = models.PositiveIntegerField(
        default=3,
        verbose_name='بعد (أيام)',
        help_text='عدد الأيام بعد الحدث'
    )
    action = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES,
        verbose_name='الإجراء'
    )
    template_message = models.TextField(
        blank=True,
        verbose_name='نموذج الرسالة',
        help_text='يمكنك استخدام {customer_name}, {company}, {amount}'
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='تعيين إلى',
        help_text='المستخدم المسؤول عن تنفيذ الإجراء'
    )
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    execution_count = models.PositiveIntegerField(
        default=0,
        verbose_name='عدد مرات التنفيذ'
    )
    last_executed = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='آخر تنفيذ'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')

    class Meta:
        verbose_name = 'قاعدة متابعة'
        verbose_name_plural = 'قواعد المتابعة'
        ordering = ['trigger', 'days_after']

    def __str__(self):
        return f"{self.name} ({self.get_trigger_display()})"


class FollowUpLog(models.Model):
    """سجل تنفيذ المتابعة"""
    rule = models.ForeignKey(
        FollowUpRule,
        on_delete=models.CASCADE,
        related_name='logs',
        verbose_name='القاعدة'
    )
    customer = models.ForeignKey(
        'crm.Customer',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='followup_logs',
        verbose_name='العميل'
    )
    executed_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ التنفيذ')
    result = models.CharField(
        max_length=20,
        choices=[
            ('success', 'نجاح'),
            ('failed', 'فشل'),
            ('skipped', 'تم تخطيه'),
        ],
        verbose_name='النتيجة'
    )
    details = models.TextField(blank=True, verbose_name='التفاصيل')

    class Meta:
        verbose_name = 'سجل متابعة'
        verbose_name_plural = 'سجلات المتابعة'
        ordering = ['-executed_at']

    def __str__(self):
        return f"{self.rule.name} - {self.customer} - {self.get_result_display()}"


class LeadScore(models.Model):
    """تقييم العملاء المحتملين (Lead Scoring)"""
    GRADE_CHOICES = [
        ('A', 'A - عميل ذهبي'),
        ('B', 'B - عميل مهم'),
        ('C', 'C - عميل عادي'),
        ('D', 'D - يحتاج متابعة'),
        ('F', 'F - غير نشط'),
    ]

    customer = models.OneToOneField(
        'crm.Customer',
        on_delete=models.CASCADE,
        related_name='lead_score',
        verbose_name='العميل'
    )
    demographic_score = models.IntegerField(
        default=0,
        verbose_name='نقاط ديموغرافية',
        help_text='حسب نوع الشركة والحجم والموقع'
    )
    behavior_score = models.IntegerField(
        default=0,
        verbose_name='نقاط السلوك',
        help_text='حسب التفاعل مع الشركة'
    )
    financial_score = models.IntegerField(
        default=0,
        verbose_name='نقاط مالية',
        help_text='حسب حجم الصفقات والمشتريات'
    )
    engagement_score = models.IntegerField(
        default=0,
        verbose_name='نقاط التفاعل',
        help_text='حسب سرعة الاستجابة والتواصل'
    )
    recency_score = models.IntegerField(
        default=0,
        verbose_name='نقاط الحداثة',
        help_text='حسب آخر تعامل'
    )
    manual_adjustment = models.IntegerField(
        default=0,
        verbose_name='تعديل يدوي',
        help_text='تعديل يدوي من المدير (+/-)'
    )
    grade = models.CharField(
        max_length=1,
        choices=GRADE_CHOICES,
        default='C',
        verbose_name='التصنيف'
    )
    last_calculated = models.DateTimeField(
        auto_now=True,
        verbose_name='آخر حساب'
    )
    notes = models.TextField(blank=True, verbose_name='ملاحظات')

    class Meta:
        verbose_name = 'تقييم عميل'
        verbose_name_plural = 'تقييمات العملاء'
        ordering = ['-financial_score', '-behavior_score']

    def __str__(self):
        return f"{self.customer} - {self.grade} ({self.total_score})"

    @property
    def total_score(self):
        return (
            self.demographic_score +
            self.behavior_score +
            self.financial_score +
            self.engagement_score +
            self.recency_score +
            self.manual_adjustment
        )

    def calculate_grade(self):
        score = self.total_score
        if score >= 80:
            self.grade = 'A'
        elif score >= 60:
            self.grade = 'B'
        elif score >= 40:
            self.grade = 'C'
        elif score >= 20:
            self.grade = 'D'
        else:
            self.grade = 'F'
        return self.grade

    def save(self, *args, **kwargs):
        self.calculate_grade()
        super().save(*args, **kwargs)


class SupportSLA(models.Model):
    """اتفاقية مستوى الخدمة للدعم الفني"""
    PRIORITY_CHOICES = [
        ('critical', 'حرج'),
        ('high', 'عالي'),
        ('medium', 'متوسط'),
        ('low', 'منخفض'),
    ]

    name = models.CharField(max_length=200, verbose_name='اسم الـ SLA')
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        unique=True,
        verbose_name='الأولوية'
    )
    first_response_hours = models.PositiveIntegerField(
        verbose_name='مهلة الرد الأول (ساعات)'
    )
    resolution_hours = models.PositiveIntegerField(
        verbose_name='مهلة الحل (ساعات)'
    )
    escalation_after_hours = models.PositiveIntegerField(
        verbose_name='تصعيد بعد (ساعات)'
    )
    escalate_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='تصعيد إلى'
    )
    is_active = models.BooleanField(default=True, verbose_name='نشط')

    class Meta:
        verbose_name = 'اتفاقية مستوى خدمة'
        verbose_name_plural = 'اتفاقيات مستوى الخدمة'
        ordering = ['first_response_hours']

    def __str__(self):
        return f"{self.name} ({self.get_priority_display()})"

    def check_sla_breach(self, ticket_created_at, first_response_at=None, resolved_at=None):
        """
        فحص التزام التذكرة بـ SLA
        """
        now = timezone.now()
        hours_since_creation = (now - ticket_created_at).total_seconds() / 3600

        result = {
            'first_response_breached': False,
            'resolution_breached': False,
            'should_escalate': False,
            'hours_since_creation': round(hours_since_creation, 1),
        }

        if not first_response_at and hours_since_creation > self.first_response_hours:
            result['first_response_breached'] = True

        if not resolved_at and hours_since_creation > self.resolution_hours:
            result['resolution_breached'] = True

        if hours_since_creation > self.escalation_after_hours:
            result['should_escalate'] = True

        return result
