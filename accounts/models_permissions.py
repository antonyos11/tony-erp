"""
نماذج الصلاحيات المتقدمة - Advanced Permission Models
=====================================================
صلاحيات على مستوى الفرع، قواعد الوصول للبيانات،
حدود مالية، وسياسات الأمان.
"""

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone


class UserBranchPermission(models.Model):
    """
    صلاحيات المستخدم على مستوى الفرع
    يحدد ما يمكن للمستخدم فعله في كل فرع
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='branch_permissions',
        verbose_name='المستخدم'
    )
    branch = models.ForeignKey(
        'branches.Branch',
        on_delete=models.CASCADE,
        related_name='user_permissions',
        verbose_name='الفرع'
    )
    is_default_branch = models.BooleanField(
        default=False,
        verbose_name='الفرع الافتراضي',
        help_text='هل هذا هو الفرع الافتراضي للمستخدم؟'
    )
    can_view = models.BooleanField(default=True, verbose_name='عرض')
    can_create = models.BooleanField(default=False, verbose_name='إنشاء')
    can_edit = models.BooleanField(default=False, verbose_name='تعديل')
    can_delete = models.BooleanField(default=False, verbose_name='حذف')
    can_approve = models.BooleanField(default=False, verbose_name='اعتماد')
    can_export = models.BooleanField(default=False, verbose_name='تصدير')
    financial_limit = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name='الحد المالي',
        help_text='الحد الأقصى للموافقة المالية (0 = بدون حد)'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')

    class Meta:
        unique_together = ['user', 'branch']
        verbose_name = 'صلاحية فرع'
        verbose_name_plural = 'صلاحيات الفروع'
        ordering = ['user', 'branch']

    def __str__(self):
        return f"{self.user} - {self.branch}"

    def clean(self):
        if self.is_default_branch:
            existing = UserBranchPermission.objects.filter(
                user=self.user,
                is_default_branch=True
            ).exclude(pk=self.pk)
            if existing.exists():
                raise ValidationError(
                    'المستخدم لديه فرع افتراضي بالفعل. '
                    'قم بإلغاء الفرع الافتراضي الحالي أولاً.'
                )

    def has_financial_authority(self, amount):
        """التحقق مما إذا كان المبلغ ضمن الحد المالي"""
        if self.financial_limit == 0:
            return True
        from decimal import Decimal
        return Decimal(str(amount)) <= self.financial_limit


class DataAccessRule(models.Model):
    """
    قواعد الوصول على مستوى البيانات
    تحدد نطاق البيانات المرئية لكل دور في كل وحدة
    """
    MODULE_CHOICES = [
        ('sales', 'المبيعات'),
        ('purchases', 'المشتريات'),
        ('inventory', 'المخازن'),
        ('accounting', 'المحاسبة'),
        ('crm', 'علاقات العملاء'),
        ('production', 'الإنتاج'),
        ('hr', 'الموارد البشرية'),
        ('pos', 'نقاط البيع'),
    ]

    ACCESS_LEVEL_CHOICES = [
        ('own_only', 'بياناته فقط'),
        ('own_branch', 'فرعه فقط'),
        ('own_department', 'قسمه فقط'),
        ('selected_branches', 'فروع محددة'),
        ('all_branches', 'جميع الفروع'),
    ]

    role = models.ForeignKey(
        'auth.Group',
        on_delete=models.CASCADE,
        related_name='data_access_rules',
        verbose_name='الدور'
    )
    module = models.CharField(
        max_length=50,
        choices=MODULE_CHOICES,
        verbose_name='الوحدة'
    )
    access_level = models.CharField(
        max_length=30,
        choices=ACCESS_LEVEL_CHOICES,
        default='own_branch',
        verbose_name='مستوى الوصول'
    )
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')

    class Meta:
        unique_together = ['role', 'module']
        verbose_name = 'قاعدة وصول'
        verbose_name_plural = 'قواعد الوصول'
        ordering = ['role', 'module']

    def __str__(self):
        return f"{self.role} - {self.get_module_display()} - {self.get_access_level_display()}"


class SecurityPolicy(models.Model):
    """
    سياسات الأمان - Singleton
    إعدادات أمان قابلة للتخصيص من لوحة التحكم
    """
    min_password_length = models.IntegerField(
        default=8,
        verbose_name='الحد الأدنى لطول كلمة المرور'
    )
    require_uppercase = models.BooleanField(
        default=True,
        verbose_name='تتطلب حروف كبيرة'
    )
    require_lowercase = models.BooleanField(
        default=True,
        verbose_name='تتطلب حروف صغيرة'
    )
    require_numbers = models.BooleanField(
        default=True,
        verbose_name='تتطلب أرقام'
    )
    require_special_chars = models.BooleanField(
        default=True,
        verbose_name='تتطلب رموز خاصة'
    )
    password_expiry_days = models.IntegerField(
        default=90,
        verbose_name='مدة صلاحية كلمة المرور (أيام)',
        help_text='0 = لا تنتهي'
    )
    password_history_count = models.IntegerField(
        default=5,
        verbose_name='عدد كلمات المرور السابقة المحفوظة',
        help_text='لمنع إعادة استخدام كلمات المرور'
    )
    max_login_attempts = models.IntegerField(
        default=5,
        verbose_name='الحد الأقصى لمحاولات تسجيل الدخول'
    )
    lockout_duration_minutes = models.IntegerField(
        default=30,
        verbose_name='مدة القفل (دقائق)'
    )
    session_timeout_minutes = models.IntegerField(
        default=480,
        verbose_name='مهلة انتهاء الجلسة (دقائق)',
        help_text='480 = 8 ساعات'
    )
    require_2fa_for_admins = models.BooleanField(
        default=True,
        verbose_name='تتطلب مصادقة ثنائية للمديرين'
    )
    allowed_ips = models.TextField(
        blank=True,
        default='',
        verbose_name='عناوين IP المسموحة',
        help_text='عنوان واحد لكل سطر. اتركه فارغاً للسماح لجميع العناوين.'
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخر تحديث')
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='آخر تحديث بواسطة'
    )

    class Meta:
        verbose_name = 'سياسة الأمان'
        verbose_name_plural = 'سياسات الأمان'

    def __str__(self):
        return 'سياسة الأمان العامة'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_policy(cls):
        """الحصول على سياسة الأمان (أو إنشاء واحدة افتراضية)"""
        policy, _ = cls.objects.get_or_create(pk=1)
        return policy

    def is_ip_allowed(self, ip_address):
        """التحقق مما إذا كان عنوان IP مسموحاً"""
        if not self.allowed_ips.strip():
            return True
        allowed = [
            ip.strip()
            for ip in self.allowed_ips.strip().split('\n')
            if ip.strip()
        ]
        return ip_address in allowed
