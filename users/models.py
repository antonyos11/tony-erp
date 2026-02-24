from django.contrib.auth.models import User
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _  # Added
from decimal import Decimal


class UserRole(models.Model):
    """أدوار المستخدمين في النظام"""
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    ROLE_TYPES = [
        ('super_admin', _('صاحب الشركة / رئيس مجلس الإدارة')),
        ('general_manager', _('المدير العام')),
        ('system_admin', _('مشرف نظام')),

        ('branches_manager', _('مدير إدارة الفروع')),
        ('branch_supervisor', _('مشرف فروع')),
        ('branch_manager', _('مدير فرع')),
        ('branch_vice_manager', _('نائب مدير فرع')),

        ('accounting_manager', _('المدير المالي')),
        ('senior_accountant', _('كبير محاسبين')),
        ('accounting_staff', _('محاسب عام')),
        ('cost_accountant', _('محاسب تكاليف')),
        ('treasury_officer', _('محاسب خزنة')),
        ('branch_accountant', _('محاسب فروع')),
        ('internal_auditor', _('مراجع داخلي')),

        ('hr_manager', _('مدير الموارد البشرية')),
        ('hr_recruiter', _('مسؤول توظيف')),
        ('hr_payroll', _('مسؤول رواتب')),
        ('hr_attendance', _('مسؤول حضور وانصراف')),
        ('hr_training', _('مسؤول تدريب وتطوير')),
        ('hr_gov_relations', _('علاقات حكومية')),
        ('hr_staff', _('موظف موارد بشرية')),

        ('procurement_manager', _('مدير مشتريات')),
        ('procurement_lead', _('مشتري رئيسي')),
        ('procurement_officer', _('مشتري فرعي')),
        ('po_officer', _('مسؤول أوامر شراء')),
        ('supplier_followup', _('متابعة الموردين')),

        ('warehouse_manager', _('مدير المخازن')),
        ('store_supervisor', _('مشرف مخازن')),
        ('inventory_staff', _('أمين مخزن رئيسي')),
        ('branch_store_keeper', _('أمين مخزن فرع')),
        ('inventory_controller', _('مسؤول جرد')),
        ('warehouse_worker', _('عامل مخزن / شيال')),

        ('it_manager', _('مدير تقنية المعلومات')),
        ('it_developer', _('مبرمج')),
        ('it_network', _('مسؤول شبكات')),
        ('it_support', _('فني صيانة أجهزة')),

        ('sales_marketing_manager', _('مدير التسويق والمبيعات')),
        ('marketing_manager', _('مدير التسويق')),
        ('campaign_team', _('فريق الحملات الإعلانية')),
        ('graphic_designer', _('مصمم جرافيك')),
        ('content_creator', _('صانع محتوى')),
        ('social_media_specialist', _('مسؤول سوشيال ميديا')),
        ('sales_manager', _('مدير المبيعات')),
        ('sales_supervisor', _('مشرف مبيعات')),
        ('sales_rep_internal', _('مندوب مبيعات داخلي')),
        ('sales_rep_external', _('مندوب مبيعات خارجي')),
        ('cashier', _('كاشير / نقطة بيع')),
        ('pricing_officer', _('مسؤول تسعير')),

        ('quality_manager', _('مدير الجودة')),
        ('quality_inspector', _('مفتش جودة')),
        ('customer_care_lead', _('مسؤول شكاوى ورضا العملاء')),
        ('customer_service_lead', _('مسؤول خدمة العملاء')),
        ('cs_agent', _('موظف خدمة عملاء')),
        ('cs_order_followup', _('متابعة الأوردرات')),
        ('cs_complaints', _('حل الشكاوى')),

        ('operations_manager', _('مدير التشغيل/الإنتاج')),
        ('factory_manager', _('مدير المصنع')),
        ('factory_vice_manager', _('نائب مدير المصنع')),
        ('production_manager', _('مدير الإنتاج')),
        ('production_supervisor', _('مشرف إنتاج')),
        ('foam_line_supervisor', _('مشرف خط الإسفنج')),
        ('spring_line_supervisor', _('مشرف خط السوست')),
        ('upholstery_supervisor', _('مشرف خط التنجيد')),
        ('shift_lead', _('قائد وردية')),
        ('production_technician', _('فني إنتاج')),
        ('production_staff', _('عامل إنتاج')),
        ('packaging_worker', _('عامل تغليف')),
        ('dispatch_controller', _('مسؤول تسليمات المصنع')),
        ('maintenance_manager', _('مدير الصيانة')),
        ('mech_tech', _('فني ميكانيكا')),
        ('elec_tech', _('فني كهرباء')),
        ('line_maint_tech', _('فني صيانة خطوط')),
        ('spareparts_controller', _('مسؤول قطع غيار')),
        ('qa_lab_chemist', _('كيميائي المصنع')),
        ('qa_raw_tester', _('اختبار المواد الخام')),
        ('qa_final_tester', _('فحص المنتج النهائي')),
        ('qa_spec_matcher', _('مطابقة المواصفات')),
        ('hse_officer', _('مسؤول سلامة')),
        ('hse_supervisor', _('مشرف وقاية')),
        ('hse_emergency', _('مسؤول طوارئ')),
        ('raw_store_keeper', _('أمين مخزن مواد خام')),
        ('semi_store_keeper', _('أمين مخزن مواد نصف مصنعة')),
        ('fg_store_keeper', _('أمين مخزن منتج نهائي')),
        ('labor_controller', _('مراقب عمال')),
        ('porter', _('شيال')),
        ('tea_boy', _('عامل بوفيه')),
        ('cleaner', _('عامل نظافة')),
        ('security_guard', _('أمن المصنع')),

        ('viewer', _('مستخدم عرض فقط')),
    ]
    
    name = models.CharField(max_length=50, choices=ROLE_TYPES, unique=True, verbose_name=_('نوع الدور'))
    display_name = models.CharField(max_length=100, verbose_name=_('اسم الدور'))
    description = models.TextField(blank=True, verbose_name=_('وصف الدور'))
    is_active = models.BooleanField(default=True, verbose_name=_('نشط'))
    can_approve = models.BooleanField(default=False, verbose_name=_('يمكنه الموافقة'))
    approval_level = models.IntegerField(default=1, verbose_name=_('مستوى الموافقة'))
    max_approval_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'), verbose_name=_('أقصى مبلغ للموافقة'))
    
    class Meta:
        verbose_name = _('دور')
        verbose_name_plural = _('الأدوار')
        ordering = ['approval_level', 'name']
    
    def __str__(self):
        return self.get_name_display() or self.display_name


class UserProfile(models.Model):
    """ملف تعريف مستخدم موسع"""
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', verbose_name=_('المستخدم'))
    
    # معلومات إضافية
    arabic_name = models.CharField(max_length=150, verbose_name=_('الاسم بالعربية'))
    employee_id = models.CharField(max_length=20, unique=True, verbose_name=_('رقم الموظف'))
    phone = models.CharField(max_length=20, blank=True, verbose_name=_('رقم الهاتف'))
    position = models.CharField(max_length=100, blank=True, verbose_name=_('المنصب'))
    
    # أدوار وصلاحيات
    role = models.ForeignKey(UserRole, on_delete=models.PROTECT, verbose_name=_('الدور الرئيسي'))
    secondary_roles = models.ManyToManyField(UserRole, blank=True, related_name='secondary_users', verbose_name=_('أدوار إضافية'))

    # الربط بالمدير المباشر لإتاحة إدارة الفريق بحسب الدور الإداري
    managed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_users',
        verbose_name=_('المدير المباشر')
    )
    
    # إعدادات الوصول
    allowed_ips = models.TextField(blank=True, help_text=_('عناوين IP مسموحة (واحد في كل سطر)'), verbose_name=_('عناوين IP المسموحة'))
    max_concurrent_sessions = models.IntegerField(default=2, verbose_name=_('أقصى عدد جلسات متزامنة'))
    
    # إعدادات الموافقة
    is_approved = models.BooleanField(default=False, verbose_name=_('موافق عليه'))
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                  related_name='approved_users', verbose_name=_('موافق من قبل'))
    approval_date = models.DateTimeField(null=True, blank=True, verbose_name=_('تاريخ الموافقة'))
    
    # إعدادات كلمة المرور
    must_change_password = models.BooleanField(default=True, verbose_name=_('يجب تغيير كلمة المرور'))
    password_last_changed = models.DateTimeField(auto_now_add=True, verbose_name=_('آخر تغيير كلمة مرور'))
    account_expires = models.DateTimeField(null=True, blank=True, verbose_name=_('انتهاء صلاحية الحساب'))
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('تاريخ الإنشاء'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('تاريخ التحديث'))
    
    class Meta:
        verbose_name = _('ملف تعريف مستخدم')
        verbose_name_plural = _('ملفات تعريف المستخدمين')
    
    def __str__(self):
        return f"{self.arabic_name} ({self.user.username})"
    
    def get_all_roles(self):
        """إرجاع جميع أدوار المستخدم (الرئيسي والإضافية)"""
        roles = [self.role]
        roles.extend(list(self.secondary_roles.all()))
        return roles

    def is_managed_by(self, manager: User) -> bool:
        """فحص ما إذا كان المستخدم تابعاً لمدير محدد."""
        return bool(manager and self.managed_by_id == manager.id)
    
    def has_role(self, role_name):
        """فحص إذا كان المستخدم لديه دور معين"""
        all_roles = self.get_all_roles()
        return any(role.name == role_name for role in all_roles)
    
    def can_approve_amount(self, amount):
        """فحص إذا كان المستخدم يمكنه الموافقة على مبلغ معين"""
        max_amount = max(role.max_approval_amount for role in self.get_all_roles() if role.can_approve)
        return amount <= max_amount


class ModulePermission(models.Model):
    """صلاحيات الوحدات النمطية"""
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    MODULE_CHOICES = [
        ('accounting', _('المحاسبة')),
        ('inventory', _('المخزون')),
        ('sales', _('المبيعات')),
        ('purchases', _('المشتريات')),
        ('production', _('الإنتاج')),
        ('maintenance', _('الصيانة')),
        ('hr', _('الموارد البشرية')),
        ('crm', _('إدارة علاقات العملاء')),
        ('reports', _('التقارير')),
        ('partners', _('الشركاء')),
        ('fleet', _('الأسطول')),
        ('core', _('الإعدادات الأساسية')),
        ('pos', _('نقطة البيع')),
        ('ecommerce', _('المتجر الإلكتروني')),
        ('eservices', _('الخدمات الإلكترونية')),
        ('shipping', _('إدارة الشحن')),
        ('woocommerce_integration', _('تكامل WooCommerce')),
    ]
    
    ACTION_CHOICES = [
        ('view', _('عرض')),
        ('add', _('إضافة')),
        ('change', _('تعديل')),
        ('delete', _('حذف')),
        ('approve', _('موافقة')),
        ('print', _('طباعة')),
        ('export', _('تصدير')),
    ]
    
    role = models.ForeignKey(UserRole, on_delete=models.CASCADE, verbose_name=_('الدور'))
    module = models.CharField(max_length=50, choices=MODULE_CHOICES, verbose_name=_('الوحدة'))
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name=_('العملية'))
    is_allowed = models.BooleanField(default=True, verbose_name=_('مسموح'))
    
    class Meta:
        verbose_name = _('صلاحية وحدة')
        verbose_name_plural = _('صلاحيات الوحدات')
        unique_together = ['role', 'module', 'action']
    
    def __str__(self):
        return f"{self.role} - {self.get_module_display()} - {self.get_action_display()}"


class ResourcePermission(models.Model):
    """صلاحيات تفصيلية (مورد/شاشة داخل الوحدة) لتجاوز أو تدقيق صلاحيات الوحدة العامة.

    أمثلة الموارد:
        - invoice_list, invoice_create داخل sales
        - vehicle_dashboard داخل fleet
        - user_dashboard داخل users
    """
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    role = models.ForeignKey(UserRole, on_delete=models.CASCADE, verbose_name=_('الدور'))
    module = models.CharField(max_length=50, choices=ModulePermission.MODULE_CHOICES, verbose_name=_('الوحدة'))
    resource = models.CharField(max_length=100, verbose_name=_('المورد / الشاشة'))
    action = models.CharField(max_length=20, choices=ModulePermission.ACTION_CHOICES, verbose_name=_('العملية'))
    is_allowed = models.BooleanField(default=True, verbose_name=_('مسموح'))
    description = models.CharField(max_length=255, blank=True, verbose_name=_('وصف'))

    class Meta:
        verbose_name = _('صلاحية مورد')
        verbose_name_plural = _('صلاحيات الموارد')
        unique_together = ['role', 'module', 'resource', 'action']

    def __str__(self):
        return f"{self.role} - {self.module}:{self.resource} - {self.action}"


class UserSession(models.Model):
    """جلسات المستخدمين النشطة"""
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('المستخدم'))
    session_key = models.CharField(max_length=40, unique=True, verbose_name=_('مفتاح الجلسة'))
    ip_address = models.GenericIPAddressField(verbose_name=_('عنوان IP'))
    user_agent = models.TextField(verbose_name=_('معلومات المتصفح'))
    login_time = models.DateTimeField(auto_now_add=True, verbose_name=_('وقت تسجيل الدخول'))
    last_activity = models.DateTimeField(auto_now=True, verbose_name=_('آخر نشاط'))
    is_active = models.BooleanField(default=True, verbose_name=_('نشط'))
    
    class Meta:
        verbose_name = _('جلسة مستخدم')
        verbose_name_plural = _('جلسات المستخدمين')
    
    def __str__(self):
        return f"{self.user.username} - {self.ip_address}"


class UserActivity(models.Model):
    """سجل أنشطة المستخدمين"""
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('المستخدم'))
    action = models.CharField(max_length=50, verbose_name=_('العملية'))
    module = models.CharField(max_length=50, verbose_name=_('الوحدة'))
    object_id = models.CharField(max_length=50, blank=True, verbose_name=_('معرف الكائن'))
    description = models.TextField(verbose_name=_('وصف العملية'))
    
    ip_address = models.GenericIPAddressField(verbose_name=_('عنوان IP'))
    user_agent = models.TextField(blank=True, verbose_name=_('معلومات المتصفح'))
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_('الوقت'))
    
    success = models.BooleanField(default=True, verbose_name=_('نجحت العملية'))

    error_message = models.TextField(blank=True, verbose_name=_('رسالة الخطأ'))
    
    class Meta:
        verbose_name = _('نشاط مستخدم')
        verbose_name_plural = _('أنشطة المستخدمين')
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.user.username} - {self.action} - {self.timestamp}"


class SecurityAlert(models.Model):
    """تنبيهات الأمان"""
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    ALERT_TYPES = [
        ('failed_login', _('فشل تسجيل دخول')),
        ('multiple_sessions', _('جلسات متعددة')),
        ('suspicious_ip', _('IP مشكوك فيه')),
        ('permission_violation', _('انتهاك صلاحيات')),
        ('password_expired', _('انتهاء صلاحية كلمة المرور')),
    ]
    
    alert_type = models.CharField(max_length=50, choices=ALERT_TYPES, verbose_name=_('نوع التنبيه'))
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='security_alerts', verbose_name=_('المستخدم'))
    description = models.TextField(verbose_name=_('وصف التنبيه'))
    
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name=_('عنوان IP'))
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_('الوقت'))
    is_resolved = models.BooleanField(default=False, verbose_name=_('تم حله'))
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                  related_name='resolved_alerts', verbose_name=_('حُل بواسطة'))
    
    class Meta:
        verbose_name = _('تنبيه أمني')
        verbose_name_plural = _('التنبيهات الأمنية')
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.get_alert_type_display()} - {self.timestamp}"


# دوال مساعدة للمستخدم

def get_user_profile(user):
    """الحصول على ملف تعريف المستخدم"""
    try:
        return user.profile
    except UserProfile.DoesNotExist:
        return None

def user_has_permission(user, module, action):
    """فحص صلاحيات المستخدم"""
    if user.is_superuser:
        return True
        
    profile = get_user_profile(user)
    
    # فحص صلاحيات ModulePermission إذا وُجد ملف تعريف
    if profile:
        all_roles = profile.get_all_roles()
        module_perm_found = False
        for role in all_roles:
            try:
                permission = ModulePermission.objects.get(
                    role=role,
                    module=module,
                    action=action
                )
                module_perm_found = True
                if permission.is_allowed:
                    return True
            except ModulePermission.DoesNotExist:
                continue
        # إذا وُجدت سجلات صريحة ولكنها كلها is_allowed=False، نرفض
        if module_perm_found:
            return False
    
    # Fallback: فحص صلاحيات Django المدمجة (المجموعات والأذونات)
    django_perm_prefix_map = {
        'view': 'view_', 'add': 'add_', 'change': 'change_',
        'delete': 'delete_', 'approve': 'change_', 'print': 'view_',
        'export': 'view_',
    }
    prefix = django_perm_prefix_map.get(action)
    if prefix:
        user_perms = user.get_all_permissions()
        if any(p.startswith(f'{module}.{prefix}') for p in user_perms):
            return True
    
    # Fallback: فحص عضوية المجموعة المرتبطة بالوحدة
    user_groups = set(user.groups.values_list('name', flat=True))
    if any(g.startswith(f'{module}_') for g in user_groups):
        return True
    
    return False


def user_has_resource_permission(user, module, resource, action):
    """فحص صلاحية تفصيلية، مع الرجوع لصلاحية الوحدة إذا لم توجد صلاحية مورد صريحة."""
    if user.is_superuser:
        return True
    profile = get_user_profile(user)
    if not profile:
        return False
    roles = profile.get_all_roles()
    from .models import ResourcePermission, ModulePermission as MP  # local import to avoid circular
    explicit_found = False
    for role in roles:
        try:
            perm = ResourcePermission.objects.get(role=role, module=module, resource=resource, action=action)
            explicit_found = True
            if perm.is_allowed:
                return True
        except ResourcePermission.DoesNotExist:
            continue
    if explicit_found:
        # وجدنا واحدة صريحة ولكن جميعها غير مسموحة
        return False
    # fallback إلى صلاحية الوحدة
    return user_has_permission(user, module, action)


# إضافة دوال جديدة لكائن User
User.add_to_class('has_resource_permission', lambda self, module, resource, action: user_has_resource_permission(self, module, resource, action))

# إضافة الدوال للنموذج User
User.add_to_class('get_profile', lambda self: get_user_profile(self))
User.add_to_class('has_module_permission', lambda self, module, action: user_has_permission(self, module, action))
from showrooms.permissions import showroom_has_action  # safe import; showrooms app installed
User.add_to_class('has_showroom_module_permission', lambda self, showroom_id, module, action: showroom_has_action(self, showroom_id, module, action))