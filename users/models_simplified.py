from django.contrib.auth.models import User
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from decimal import Decimal


class UserRole(models.Model):
    """أدوار المستخدمين في النظام"""
    ROLE_TYPES = [
        ('super_admin', 'مدير عام'),
        ('accounting_manager', 'مدير محاسبة'),
        ('inventory_manager', 'مدير مخزون'),
        ('sales_manager', 'مدير مبيعات'),
        ('production_manager', 'مدير إنتاج'),
        ('hr_manager', 'مدير موارد بشرية'),
        ('accounting_staff', 'موظف محاسبة'),
        ('inventory_staff', 'موظف مخزون'),
        ('sales_staff', 'موظف مبيعات'),
        ('production_staff', 'موظف إنتاج'),
        ('hr_staff', 'موظف موارد بشرية'),
        ('viewer', 'مستخدم عرض فقط'),
    ]
    
    name = models.CharField(max_length=50, choices=ROLE_TYPES, unique=True, verbose_name='نوع الدور')
    display_name = models.CharField(max_length=100, verbose_name='اسم الدور')
    description = models.TextField(blank=True, verbose_name='وصف الدور')
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    can_approve = models.BooleanField(default=False, verbose_name='يمكنه الموافقة')
    approval_level = models.IntegerField(default=1, verbose_name='مستوى الموافقة')
    max_approval_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'), verbose_name='أقصى مبلغ للموافقة')
    
    class Meta:
        verbose_name = 'دور'
        verbose_name_plural = 'الأدوار'
        ordering = ['approval_level', 'name']
        db_table = 'users_role'
    
    def __str__(self):
        return self.get_name_display() or self.display_name


class UserProfile(models.Model):
    """ملف تعريف مستخدم موسع"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', verbose_name='المستخدم')
    
    # معلومات إضافية
    arabic_name = models.CharField(max_length=150, verbose_name='الاسم بالعربية')
    employee_id = models.CharField(max_length=20, unique=True, verbose_name='رقم الموظف')
    phone = models.CharField(max_length=20, blank=True, verbose_name='رقم الهاتف')
    position = models.CharField(max_length=100, blank=True, verbose_name='المنصب')
    
    # أدوار وصلاحيات
    role = models.ForeignKey(UserRole, on_delete=models.PROTECT, verbose_name='الدور الرئيسي')
    secondary_roles = models.ManyToManyField(UserRole, blank=True, related_name='secondary_users', verbose_name='أدوار إضافية')
    
    # إعدادات الوصول
    allowed_ips = models.TextField(blank=True, help_text='عناوين IP مسموحة (واحد في كل سطر)', verbose_name='عناوين IP المسموحة')
    max_concurrent_sessions = models.IntegerField(default=2, verbose_name='أقصى عدد جلسات متزامنة')
    
    # إعدادات الموافقة
    is_approved = models.BooleanField(default=False, verbose_name='موافق عليه')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                  related_name='approved_users', verbose_name='موافق من قبل')
    approval_date = models.DateTimeField(null=True, blank=True, verbose_name='تاريخ الموافقة')
    
    # إعدادات كلمة المرور
    must_change_password = models.BooleanField(default=True, verbose_name='يجب تغيير كلمة المرور')
    password_last_changed = models.DateTimeField(auto_now_add=True, verbose_name='آخر تغيير كلمة مرور')
    account_expires = models.DateTimeField(null=True, blank=True, verbose_name='انتهاء صلاحية الحساب')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')
    
    class Meta:
        verbose_name = 'ملف تعريف مستخدم'
        verbose_name_plural = 'ملفات تعريف المستخدمين'
        db_table = 'users_userprofile'
    
    def __str__(self):
        return f"{self.arabic_name} ({self.user.username})"
    
    def get_all_roles(self):
        """إرجاع جميع أدوار المستخدم (الرئيسي والإضافية)"""
        roles = [self.role]
        roles.extend(list(self.secondary_roles.all()))
        return roles
    
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
    MODULE_CHOICES = [
        ('accounting', 'المحاسبة'),
        ('inventory', 'المخزون'),
        ('sales', 'المبيعات'),
        ('purchases', 'المشتريات'),
        ('production', 'الإنتاج'),
        ('hr', 'الموارد البشرية'),
        ('crm', 'إدارة علاقات العملاء'),
        ('reports', 'التقارير'),
        ('partners', 'الشركاء'),
        ('fleet', 'الأسطول'),
        ('core', 'الإعدادات الأساسية'),
    ]
    
    ACTION_CHOICES = [
        ('view', 'عرض'),
        ('add', 'إضافة'),
        ('change', 'تعديل'),
        ('delete', 'حذف'),
        ('approve', 'موافقة'),
        ('print', 'طباعة'),
        ('export', 'تصدير'),
    ]
    
    role = models.ForeignKey(UserRole, on_delete=models.CASCADE, verbose_name='الدور')
    module = models.CharField(max_length=50, choices=MODULE_CHOICES, verbose_name='الوحدة')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name='العملية')
    is_allowed = models.BooleanField(default=True, verbose_name='مسموح')
    
    class Meta:
        verbose_name = 'صلاحية وحدة'
        verbose_name_plural = 'صلاحيات الوحدات'
        unique_together = ['role', 'module', 'action']
        db_table = 'users_modulepermission'
    
    def __str__(self):
        return f"{self.role} - {self.get_module_display()} - {self.get_action_display()}"


class UserSession(models.Model):
    """جلسات المستخدمين النشطة"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='المستخدم')
    session_key = models.CharField(max_length=40, unique=True, verbose_name='مفتاح الجلسة')
    ip_address = models.GenericIPAddressField(verbose_name='عنوان IP')
    user_agent = models.TextField(verbose_name='معلومات المتصفح')
    login_time = models.DateTimeField(auto_now_add=True, verbose_name='وقت تسجيل الدخول')
    last_activity = models.DateTimeField(auto_now=True, verbose_name='آخر نشاط')
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    
    class Meta:
        verbose_name = 'جلسة مستخدم'
        verbose_name_plural = 'جلسات المستخدمين'
        db_table = 'users_usersession'
    
    def __str__(self):
        return f"{self.user.username} - {self.ip_address}"


class UserActivity(models.Model):
    """سجل أنشطة المستخدمين"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='المستخدم')
    action = models.CharField(max_length=50, verbose_name='العملية')
    module = models.CharField(max_length=50, verbose_name='الوحدة')
    object_id = models.CharField(max_length=50, blank=True, verbose_name='معرف الكائن')
    description = models.TextField(verbose_name='وصف العملية')
    
    ip_address = models.GenericIPAddressField(verbose_name='عنوان IP')
    user_agent = models.TextField(blank=True, verbose_name='معلومات المتصفح')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='الوقت')
    
    success = models.BooleanField(default=True, verbose_name='نجحت العملية')
    error_message = models.TextField(blank=True, verbose_name='رسالة الخطأ')
    
    class Meta:
        verbose_name = 'نشاط مستخدم'
        verbose_name_plural = 'أنشطة المستخدمين'
        ordering = ['-timestamp']
        db_table = 'users_useractivity'
    
    def __str__(self):
        return f"{self.user.username} - {self.action} - {self.timestamp}"


class SecurityAlert(models.Model):
    """تنبيهات الأمان"""
    ALERT_TYPES = [
        ('failed_login', 'فشل تسجيل دخول'),
        ('multiple_sessions', 'جلسات متعددة'),
        ('suspicious_ip', 'IP مشكوك فيه'),
        ('permission_violation', 'انتهاك صلاحيات'),
        ('password_expired', 'انتهاء صلاحية كلمة المرور'),
    ]
    
    alert_type = models.CharField(max_length=50, choices=ALERT_TYPES, verbose_name='نوع التنبيه')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name='المستخدم')
    description = models.TextField(verbose_name='وصف التنبيه')
    
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='عنوان IP')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='الوقت')
    is_resolved = models.BooleanField(default=False, verbose_name='تم حله')
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                  related_name='resolved_alerts', verbose_name='حُل بواسطة')
    
    class Meta:
        verbose_name = 'تنبيه أمني'
        verbose_name_plural = 'التنبيهات الأمنية'
        ordering = ['-timestamp']
        db_table = 'users_securityalert'
    
    def __str__(self):
        return f"{self.get_alert_type_display()} - {self.timestamp}"


# إضافة دوال مساعدة للمستخدم
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
    if not profile:
        return False
        
    all_roles = profile.get_all_roles()
    for role in all_roles:
        try:
            permission = ModulePermission.objects.get(
                role=role,
                module=module,
                action=action
            )
            if permission.is_allowed:
                return True
        except ModulePermission.DoesNotExist:
            continue
    
    return False

# إضافة الدوال للنموذج User
User.add_to_class('get_profile', lambda self: get_user_profile(self))
User.add_to_class('has_module_permission', lambda self, module, action: user_has_permission(self, module, action))