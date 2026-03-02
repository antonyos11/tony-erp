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
    action = models.CharField(max_length=30, choices=ACTION_TYPES, verbose_name="الإجراء", db_index=True)
    module = models.CharField(max_length=100, verbose_name="القسم", db_index=True)
    model_name = models.CharField(max_length=100, verbose_name="الجدول", db_index=True)
    object_id = models.CharField(max_length=50, blank=True, verbose_name="رقم السجل", db_index=True)
    description = models.TextField(verbose_name="الوصف")
    old_value = models.JSONField(null=True, blank=True, verbose_name="القيمة القديمة")
    new_value = models.JSONField(null=True, blank=True, verbose_name="القيمة الجديدة")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="عنوان IP", db_index=True)
    user_agent = models.CharField(max_length=512, blank=True, verbose_name="المتصفح")
    branch = models.ForeignKey(
        'core.Branch', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="الفرع"
    )
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="التوقيت", db_index=True)

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


# ═══════════════════════════════════════════════════════════════
# الجديد  Sprint 22A — الصلاحيات الدقيقة (Granular Permissions)
# ═══════════════════════════════════════════════════════════════

from django.conf import settings


class SystemPermission(models.Model):
    """
    صلاحية نظامية دقيقة
    كل صلاحية = فعل واحد على كائن واحد
    مثال: view_sales_invoice, create_sales_invoice, approve_journal_entry
    """
    code = models.CharField(max_length=100, unique=True, verbose_name="كود الصلاحية")
    name = models.CharField(max_length=255, verbose_name="اسم الصلاحية")
    module = models.CharField(max_length=50, verbose_name="القسم", choices=[
        ('dashboard', 'لوحة التحكم'),
        ('accounts', 'المحاسبة'),
        ('inventory', 'المخزون'),
        ('production', 'الإنتاج'),
        ('sales', 'المبيعات'),
        ('purchases', 'المشتريات'),
        ('hr', 'الموارد البشرية'),
        ('treasury', 'الخزينة والبنوك'),
        ('expenses', 'المصروفات'),
        ('crm', 'إدارة العملاء'),
        ('quotations', 'عروض الأسعار'),
        ('delivery', 'التوصيل'),
        ('warranty', 'الضمان'),
        ('reports', 'التقارير'),
        ('notifications', 'الإشعارات'),
        ('authorization', 'الصلاحيات'),
        ('settings', 'الإعدادات'),
    ])
    action = models.CharField(max_length=50, verbose_name="الإجراء", choices=[
        ('view', 'عرض'),
        ('create', 'إنشاء'),
        ('edit', 'تعديل'),
        ('delete', 'حذف'),
        ('approve', 'اعتماد'),
        ('cancel', 'إلغاء'),
        ('post', 'ترحيل'),
        ('close', 'إقفال'),
        ('export', 'تصدير'),
        ('print', 'طباعة'),
        ('receive', 'استلام'),
        ('issue', 'صرف'),
        ('transfer', 'تحويل'),
        ('adjust', 'تسوية'),
        ('count', 'جرد'),
        ('start', 'بدء'),
        ('complete', 'إكمال'),
        ('collect', 'تحصيل'),
        ('pay', 'دفع'),
        ('payroll', 'رواتب'),
        ('update_progress', 'تحديث تقدم'),
        ('report_waste', 'تسجيل هالك'),
        ('quality_check', 'فحص جودة'),
        ('view_cost', 'رؤية التكلفة'),
        ('view_profit', 'رؤية الربح'),
        ('give_discount', 'منح خصم'),
        ('view_other_branches', 'رؤية فروع أخرى'),
        ('manage_users', 'إدارة المستخدمين'),
        ('audit_log', 'سجل المراجعة'),
    ])
    description = models.TextField(blank=True, verbose_name="الوصف")
    is_sensitive = models.BooleanField(default=False, verbose_name="حساسة",
                                       help_text="الصلاحيات الحساسة تحتاج اعتماد خاص")

    class Meta:
        verbose_name = "صلاحية نظامية"
        verbose_name_plural = "الصلاحيات النظامية"
        unique_together = ['module', 'action']
        ordering = ['module', 'action']

    def __str__(self):
        return f"{self.code} ({self.name})"


class SystemRole(models.Model):
    """
    دور نظامي مع Scope
    الـ Scope يحدد نطاق الدور:
    - all = كل الفروع والمخازن
    - branch = فرعه فقط
    - warehouse = مخزنه فقط
    - production_line = خط إنتاجه فقط
    - assigned = المسند إليه فقط
    """
    SCOPE_CHOICES = [
        ('all', 'كل الفروع'),
        ('branch', 'فرعه فقط'),
        ('warehouse', 'مخزنه فقط'),
        ('production_line', 'خط إنتاجه فقط'),
        ('assigned', 'المسند إليه فقط'),
    ]

    code = models.CharField(max_length=50, unique=True, verbose_name="كود الدور")
    name = models.CharField(max_length=255, verbose_name="اسم الدور")
    description = models.TextField(blank=True, verbose_name="الوصف")
    scope = models.CharField(max_length=20, choices=SCOPE_CHOICES, default='branch', verbose_name="النطاق")

    # الصلاحيات
    permissions = models.ManyToManyField(SystemPermission, blank=True,
                                          related_name='roles', verbose_name="الصلاحيات")

    # سقف الاعتماد
    invoice_approval_limit = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                                   verbose_name="سقف اعتماد الفواتير")
    expense_approval_limit = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                                   verbose_name="سقف اعتماد المصروفات")
    return_approval_limit = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                                  verbose_name="سقف اعتماد المرتجعات")
    max_discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0,
                                                    verbose_name="أقصى خصم %")

    # التفويض — من ينشئ هذا الدور ويمنحه
    can_be_granted_by = models.ManyToManyField('self', blank=True, symmetrical=False,
                                                related_name='can_grant', verbose_name="يُمنح بواسطة")

    # هل نظامي (لا يُحذف)
    is_system = models.BooleanField(default=False, verbose_name="دور نظامي")
    is_active = models.BooleanField(default=True, verbose_name="نشط")

    # ترتيب العرض
    sort_order = models.IntegerField(default=0, verbose_name="الترتيب")

    class Meta:
        verbose_name = "دور نظامي"
        verbose_name_plural = "الأدوار النظامية"
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name

    def has_permission(self, module, action):
        """هل الدور يملك صلاحية معينة؟"""
        return self.permissions.filter(module=module, action=action).exists()

    def has_any_permission_in_module(self, module):
        """هل الدور يملك أي صلاحية في هذا القسم؟"""
        return self.permissions.filter(module=module).exists()

    def get_modules(self):
        """قائمة الأقسام المسموح بها"""
        return list(self.permissions.values_list('module', flat=True).distinct())


class UserRoleAssignment(models.Model):
    """
    تعيين دور لمستخدم
    المستخدم ممكن يكون عنده أكثر من دور (نادر لكن ممكن)
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                              related_name='role_assignments', verbose_name="المستخدم")
    role = models.ForeignKey(SystemRole, on_delete=models.PROTECT, verbose_name="الدور")

    # النطاق المحدد
    branch = models.ForeignKey('core.Branch', on_delete=models.SET_NULL, null=True, blank=True,
                               verbose_name="الفرع")
    warehouse = models.ForeignKey('core.Warehouse', on_delete=models.SET_NULL, null=True, blank=True,
                                  verbose_name="المخزن")
    production_line = models.ForeignKey('production.ProductionLine', on_delete=models.SET_NULL,
                                        null=True, blank=True, verbose_name="خط الإنتاج")

    # التعيين
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                     related_name='granted_roles', verbose_name="عيّنه")
    assigned_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ التعيين")

    is_active = models.BooleanField(default=True, verbose_name="نشط")

    class Meta:
        verbose_name = "تعيين دور"
        verbose_name_plural = "تعيينات الأدوار"
        unique_together = ['user', 'role']

    def __str__(self):
        return f"{self.user.username} → {self.role.name}"


# ═══════════════════════════════════════════════════════════════
# Sprint 23 — نظام طلبات الاعتماد (Approval Requests)
# ═══════════════════════════════════════════════════════════════

class ApprovalRequest(AuditMixin):
    """طلب اعتماد"""
    REQUEST_TYPES = [
        ('invoice', 'فاتورة'),
        ('return', 'مرتجع'),
        ('expense', 'مصروف'),
        ('purchase', 'أمر شراء'),
        ('stock_adjustment', 'تسوية مخزون'),
        ('discount', 'خصم تجاوز الحد'),
        ('production', 'أمر إنتاج'),
        ('payroll', 'مسيّر رواتب'),
    ]
    STATUSES = [
        ('pending', 'في الانتظار'),
        ('approved', 'معتمد'),
        ('rejected', 'مرفوض'),
        ('cancelled', 'ملغي'),
    ]

    request_type = models.CharField(max_length=20, choices=REQUEST_TYPES, verbose_name="النوع")
    status = models.CharField(max_length=20, choices=STATUSES, default='pending', verbose_name="الحالة")

    # الطالب
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='approval_requests', verbose_name="الطالب"
    )
    branch = models.ForeignKey(
        'core.Branch', on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="الفرع"
    )

    # المستند
    source_model = models.CharField(max_length=100, verbose_name="المصدر")
    source_id = models.IntegerField(verbose_name="رقم المصدر")
    description = models.TextField(verbose_name="الوصف")
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="المبلغ")

    # المعتمد
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='processed_approvals', verbose_name="المعتمد"
    )
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ المعالجة")
    rejection_reason = models.TextField(blank=True, verbose_name="سبب الرفض")

    class Meta:
        verbose_name = "طلب اعتماد"
        verbose_name_plural = "طلبات الاعتماد"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_request_type_display()} — {self.requested_by} — {self.get_status_display()}"

    @property
    def is_pending(self):
        return self.status == 'pending'

    @property
    def status_badge_class(self):
        return {
            'pending': 'warning',
            'approved': 'success',
            'rejected': 'danger',
            'cancelled': 'secondary',
        }.get(self.status, 'secondary')


class SecurityViolationLog(models.Model):
    """سجل محاولات الوصول غير المصرح"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    attempted_url = models.CharField(max_length=500, verbose_name="الـ URL")
    attempted_module = models.CharField(max_length=50, verbose_name="القسم")
    attempted_action = models.CharField(max_length=50, verbose_name="الإجراء")
    ip_address = models.GenericIPAddressField(null=True, verbose_name="عنوان IP")
    user_agent = models.TextField(blank=True, verbose_name="المتصفح")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="التوقيت")

    class Meta:
        verbose_name = "محاولة وصول غير مصرح"
        verbose_name_plural = "سجل الأمان"
        ordering = ['-timestamp']
