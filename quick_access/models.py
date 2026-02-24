"""
نماذج الوصول السريع
Quick Access Models
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator


class UserPreference(models.Model):
    """تفضيلات المستخدم للوصول السريع"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='quick_access_prefs')
    favorite_shortcuts = models.JSONField(default=list, blank=True, help_text="قائمة الاختصارات المفضلة")
    dashboard_widgets = models.JSONField(default=list, blank=True, help_text="Widgets المعروضة في اللوحة")
    default_view = models.CharField(max_length=50, default='grid', choices=[
        ('grid', 'شبكة'),
        ('list', 'قائمة'),
        ('compact', 'مضغوط')
    ])
    theme = models.CharField(max_length=20, default='auto', choices=[
        ('light', 'فاتح'),
        ('dark', 'داكن'),
        ('auto', 'تلقائي')
    ])
    sidebar_collapsed = models.BooleanField(default=False)
    notifications_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("تفضيلات المستخدم")
        verbose_name_plural = _("تفضيلات المستخدمين")
        
    def __str__(self):
        return f"تفضيلات {self.user.username}"


class QuickAction(models.Model):
    """الإجراءات السريعة المتاحة في النظام"""
    name = models.CharField(max_length=100, verbose_name="الاسم")
    name_en = models.CharField(max_length=100, verbose_name="الاسم بالإنجليزية")
    description = models.TextField(blank=True, verbose_name="الوصف")
    icon = models.CharField(max_length=50, default='bi-lightning', verbose_name="أيقونة Bootstrap")
    url = models.CharField(max_length=200, verbose_name="رابط URL")
    category = models.CharField(max_length=50, choices=[
        ('sales', 'المبيعات'),
        ('purchases', 'المشتريات'),
        ('inventory', 'المخزون'),
        ('accounting', 'المحاسبة'),
        ('hr', 'الموارد البشرية'),
        ('crm', 'إدارة العملاء'),
        ('reports', 'التقارير'),
        ('settings', 'الإعدادات'),
        ('other', 'أخرى')
    ], default='other')
    permission_required = models.CharField(max_length=200, blank=True, help_text="الصلاحية المطلوبة")
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    color = models.CharField(max_length=20, default='#3b82f6')
    keyboard_shortcut = models.CharField(max_length=20, blank=True, help_text="مثل: Ctrl+Alt+S")
    usage_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("إجراء سريع")
        verbose_name_plural = _("الإجراءات السريعة")
        ordering = ['category', 'sort_order', 'name']
        
    def __str__(self):
        return self.name
    
    def increment_usage(self):
        """زيادة عداد الاستخدام"""
        self.usage_count += 1
        self.save(update_fields=['usage_count'])


class FrequentlyUsedReport(models.Model):
    """التقارير الأكثر استخداماً"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='frequent_reports')
    report_name = models.CharField(max_length=200)
    report_url = models.CharField(max_length=300)
    report_type = models.CharField(max_length=50)
    access_count = models.IntegerField(default=1)
    last_accessed = models.DateTimeField(auto_now=True)
    parameters = models.JSONField(default=dict, blank=True)
    
    class Meta:
        verbose_name = _("تقرير متكرر")
        verbose_name_plural = _("التقارير المتكررة")
        ordering = ['-access_count', '-last_accessed']
        unique_together = ['user', 'report_name']
        
    def __str__(self):
        return f"{self.user.username} - {self.report_name} ({self.access_count})"


class ScheduledReport(models.Model):
    """التقارير المجدولة"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='scheduled_reports')
    name = models.CharField(max_length=200, verbose_name="اسم التقرير")
    report_type = models.CharField(max_length=100, verbose_name="نوع التقرير")
    report_url = models.CharField(max_length=300)
    frequency = models.CharField(max_length=20, choices=[
        ('daily', 'يومي'),
        ('weekly', 'أسبوعي'),
        ('monthly', 'شهري'),
        ('quarterly', 'ربع سنوي'),
    ], default='daily')
    day_of_week = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(6)])
    day_of_month = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(31)])
    time_of_day = models.TimeField()
    email_recipients = models.TextField(help_text="عناوين البريد الإلكتروني، مفصولة بفواصل")
    parameters = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    last_run = models.DateTimeField(null=True, blank=True)
    next_run = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _("تقرير مجدول")
        verbose_name_plural = _("التقارير المجدولة")
        ordering = ['next_run']
        
    def __str__(self):
        return f"{self.name} ({self.get_frequency_display()})"


class BulkActionHistory(models.Model):
    """سجل العمليات الجماعية"""
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action_type = models.CharField(max_length=50, verbose_name="نوع العملية")
    model_name = models.CharField(max_length=100)
    affected_count = models.IntegerField(default=0)
    success_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    parameters = models.JSONField(default=dict, blank=True)
    errors_log = models.JSONField(default=list, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    duration_seconds = models.FloatField(default=0.0)
    
    class Meta:
        verbose_name = _("عملية جماعية")
        verbose_name_plural = _("سجل العمليات الجماعية")
        ordering = ['-timestamp']
        
    def __str__(self):
        return f"{self.action_type} - {self.affected_count} عنصر ({self.timestamp.strftime('%Y-%m-%d %H:%M')})"
