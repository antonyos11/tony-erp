"""
نماذج الصلاحيات والهيكل الإداري — RITA ERP
"""
from django.db import models
from apps.core.models import AuditMixin


class Role(AuditMixin):
    """الأدوار الوظيفية"""
    ROLE_LEVELS = [
        ('owner', 'إدارة عليا'),
        ('ceo', 'مدير عام'),
        ('cfo', 'مدير مالي'),
        ('account_manager', 'مدير حسابات'),
        ('accountant', 'محاسب'),
        ('branch_manager', 'مدير فرع'),
        ('salesperson', 'بائع'),
        ('cashier', 'كاشير'),
        ('storekeeper', 'أمين مخزن'),
        ('production_manager', 'مدير إنتاج'),
        ('production_supervisor', 'مشرف خط إنتاج'),
        ('custom', 'مخصص'),
    ]
    name = models.CharField(max_length=100, verbose_name="اسم الدور")
    level = models.CharField(max_length=30, choices=ROLE_LEVELS, verbose_name="المستوى")
    description = models.TextField(blank=True, verbose_name="الوصف")
    max_discount_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=0, verbose_name="أقصى نسبة خصم %"
    )
    can_see_cost = models.BooleanField(default=False, verbose_name="يرى التكلفة")
    can_see_profit = models.BooleanField(default=False, verbose_name="يرى الأرباح")
    can_see_other_branches = models.BooleanField(default=False, verbose_name="يرى فروع أخرى")
    can_delete = models.BooleanField(default=False, verbose_name="يستطيع الحذف")
    can_modify_prices = models.BooleanField(default=False, verbose_name="يعدّل الأسعار")
    can_approve_entries = models.BooleanField(default=False, verbose_name="يعتمد القيود")
    can_create_users = models.BooleanField(default=False, verbose_name="ينشئ مستخدمين")
    is_active = models.BooleanField(default=True, verbose_name="نشط")

    class Meta:
        verbose_name = "دور وظيفي"
        verbose_name_plural = "الأدوار الوظيفية"

    def __str__(self):
        return self.name


class Permission(AuditMixin):
    """صلاحية محددة"""
    MODULES = [
        ('accounts', 'المحاسبة'),
        ('inventory', 'المخزون'),
        ('production', 'الإنتاج'),
        ('sales', 'المبيعات'),
        ('purchases', 'المشتريات'),
        ('hr', 'الموارد البشرية'),
        ('reports', 'التقارير'),
        ('settings', 'الإعدادات'),
    ]
    ACTIONS = [
        ('view', 'عرض'),
        ('create', 'إنشاء'),
        ('edit', 'تعديل'),
        ('delete', 'حذف'),
        ('approve', 'اعتماد'),
        ('export', 'تصدير'),
    ]
    role = models.ForeignKey(
        Role, on_delete=models.CASCADE, related_name='permissions', verbose_name="الدور"
    )
    module = models.CharField(max_length=20, choices=MODULES, verbose_name="القسم")
    action = models.CharField(max_length=20, choices=ACTIONS, verbose_name="الإجراء")
    is_allowed = models.BooleanField(default=False, verbose_name="مسموح")

    class Meta:
        verbose_name = "صلاحية"
        verbose_name_plural = "الصلاحيات"
        unique_together = ['role', 'module', 'action']

    def __str__(self):
        return f"{self.role.name} — {self.get_module_display()} — {self.get_action_display()}"


class UserRole(AuditMixin):
    """ربط المستخدم بدور وظيفي"""
    user = models.ForeignKey(
        'core.User', on_delete=models.CASCADE, related_name='user_roles', verbose_name="المستخدم"
    )
    role = models.ForeignKey(
        Role, on_delete=models.CASCADE, related_name='user_roles', verbose_name="الدور"
    )
    is_primary = models.BooleanField(default=False, verbose_name="دور أساسي")
    is_active = models.BooleanField(default=True, verbose_name="نشط")

    class Meta:
        verbose_name = "دور المستخدم"
        verbose_name_plural = "أدوار المستخدمين"
        unique_together = ['user', 'role']

    def __str__(self):
        return f"{self.user} — {self.role}"


class AuditLog(models.Model):
    """سجل التدقيق — كل حركة في النظام"""
    ACTION_TYPES = [
        ('create', 'إنشاء'),
        ('update', 'تعديل'),
        ('delete', 'حذف'),
        ('approve', 'اعتماد'),
        ('login', 'تسجيل دخول'),
        ('logout', 'تسجيل خروج'),
        ('failed_login', 'محاولة دخول فاشلة'),
        ('permission_denied', 'رفض صلاحية'),
        ('price_change', 'تعديل سعر'),
        ('discount', 'خصم'),
    ]
    user = models.ForeignKey(
        'core.User', on_delete=models.SET_NULL, null=True, verbose_name="المستخدم"
    )
    action = models.CharField(max_length=30, choices=ACTION_TYPES, verbose_name="الإجراء")
    module = models.CharField(max_length=100, verbose_name="القسم")
    model_name = models.CharField(max_length=100, verbose_name="الجدول")
    object_id = models.CharField(max_length=50, blank=True, verbose_name="رقم السجل")
    description = models.TextField(verbose_name="الوصف")
    old_value = models.JSONField(null=True, blank=True, verbose_name="القيمة القديمة")
    new_value = models.JSONField(null=True, blank=True, verbose_name="القيمة الجديدة")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="عنوان IP")
    branch = models.ForeignKey(
        'core.Branch', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="الفرع"
    )
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="التوقيت")

    class Meta:
        verbose_name = "سجل تدقيق"
        verbose_name_plural = "سجلات التدقيق"
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user} — {self.get_action_display()} — {self.timestamp}"


class Delegation(AuditMixin):
    """تفويض صلاحيات مؤقت"""
    delegator = models.ForeignKey(
        'core.User', on_delete=models.CASCADE,
        related_name='delegations_given', verbose_name="المفوِّض"
    )
    delegate = models.ForeignKey(
        'core.User', on_delete=models.CASCADE,
        related_name='delegations_received', verbose_name="المفوَّض إليه"
    )
    role = models.ForeignKey(
        Role, on_delete=models.CASCADE, verbose_name="الدور المفوَّض"
    )
    start_date = models.DateTimeField(verbose_name="بداية التفويض")
    end_date = models.DateTimeField(verbose_name="نهاية التفويض")
    reason = models.TextField(verbose_name="السبب")
    is_active = models.BooleanField(default=True, verbose_name="نشط")

    class Meta:
        verbose_name = "تفويض"
        verbose_name_plural = "التفويضات"

    def __str__(self):
        return f"تفويض من {self.delegator} إلى {self.delegate}"
