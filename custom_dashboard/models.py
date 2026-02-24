"""
نماذج لوحة التحكم المخصصة
Custom Dashboard Models
"""

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class DashboardLayout(models.Model):
    """تخطيطات لوحة التحكم"""
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='dashboard_layouts',
        verbose_name='المستخدم'
    )
    name = models.CharField('اسم التخطيط', max_length=100)
    description = models.TextField('الوصف', blank=True)
    is_default = models.BooleanField('افتراضي', default=False)
    is_active = models.BooleanField('نشط', default=True)
    
    # إعدادات التخطيط
    columns = models.IntegerField('عدد الأعمدة', default=3)
    layout_config = models.JSONField('تكوين التخطيط', default=dict)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'تخطيط لوحة التحكم'
        verbose_name_plural = 'تخطيطات لوحة التحكم'
        ordering = ['-is_default', '-updated_at']
    
    def __str__(self):
        return f"{self.name} - {self.user.username}"
    
    def save(self, *args, **kwargs):
        if self.is_default:
            DashboardLayout.objects.filter(
                user=self.user
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class Widget(models.Model):
    """الويدجتس المتاحة"""
    
    WIDGET_TYPES = [
        ('stats', 'إحصائيات'),
        ('chart', 'رسم بياني'),
        ('list', 'قائمة'),
        ('table', 'جدول'),
        ('calendar', 'تقويم'),
        ('quick_action', 'إجراء سريع'),
        ('notification', 'إشعارات'),
        ('custom', 'مخصص'),
    ]
    
    SIZE_CHOICES = [
        ('small', 'صغير'),
        ('medium', 'متوسط'),
        ('large', 'كبير'),
        ('full', 'كامل العرض'),
    ]
    
    name = models.CharField('اسم الويدجت', max_length=100)
    slug = models.SlugField('المعرف', unique=True)
    widget_type = models.CharField('نوع الويدجت', max_length=20, choices=WIDGET_TYPES)
    description = models.TextField('الوصف', blank=True)
    
    # الإعدادات
    icon = models.CharField('الأيقونة', max_length=50, default='fas fa-chart-bar')
    color = models.CharField('اللون', max_length=20, default='primary')
    default_size = models.CharField('الحجم الافتراضي', max_length=10, choices=SIZE_CHOICES, default='medium')
    min_width = models.IntegerField('الحد الأدنى للعرض', default=1)
    min_height = models.IntegerField('الحد الأدنى للارتفاع', default=1)
    
    # مصدر البيانات
    data_source = models.CharField('مصدر البيانات', max_length=200, blank=True)
    data_config = models.JSONField('تكوين البيانات', default=dict)
    refresh_interval = models.IntegerField('فترة التحديث (ثواني)', default=60)
    
    # القالب
    template_name = models.CharField('اسم القالب', max_length=200, blank=True)
    
    # الصلاحيات
    required_permission = models.CharField('الصلاحية المطلوبة', max_length=100, blank=True)
    allowed_roles = models.JSONField('الأدوار المسموحة', default=list)
    
    is_active = models.BooleanField('نشط', default=True)
    is_system = models.BooleanField('ويدجت نظام', default=False)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    class Meta:
        verbose_name = 'ويدجت'
        verbose_name_plural = 'الويدجتس'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class DashboardWidget(models.Model):
    """الويدجتس في لوحة التحكم"""
    
    layout = models.ForeignKey(
        DashboardLayout,
        on_delete=models.CASCADE,
        related_name='widgets',
        verbose_name='التخطيط'
    )
    widget = models.ForeignKey(
        Widget,
        on_delete=models.CASCADE,
        related_name='dashboard_instances',
        verbose_name='الويدجت'
    )
    
    # الموقع
    position_x = models.IntegerField('الموقع X', default=0)
    position_y = models.IntegerField('الموقع Y', default=0)
    width = models.IntegerField('العرض', default=1)
    height = models.IntegerField('الارتفاع', default=1)
    
    # التخصيص
    title_override = models.CharField('عنوان مخصص', max_length=100, blank=True)
    custom_config = models.JSONField('إعدادات مخصصة', default=dict)
    
    # العرض
    is_visible = models.BooleanField('مرئي', default=True)
    is_collapsed = models.BooleanField('مطوي', default=False)
    
    order = models.IntegerField('الترتيب', default=0)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    class Meta:
        verbose_name = 'ويدجت لوحة التحكم'
        verbose_name_plural = 'ويدجتس لوحة التحكم'
        ordering = ['order', 'position_y', 'position_x']
    
    def __str__(self):
        return f"{self.widget.name} in {self.layout.name}"
    
    def get_title(self):
        return self.title_override or self.widget.name


class WidgetData(models.Model):
    """بيانات الويدجت المُخزَّنة مؤقتاً"""
    
    widget = models.ForeignKey(
        Widget,
        on_delete=models.CASCADE,
        related_name='cached_data',
        verbose_name='الويدجت'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='widget_data',
        verbose_name='المستخدم',
        null=True,
        blank=True
    )
    
    data = models.JSONField('البيانات', default=dict)
    cached_at = models.DateTimeField('تاريخ التخزين', auto_now=True)
    expires_at = models.DateTimeField('تاريخ الانتهاء')
    
    class Meta:
        verbose_name = 'بيانات ويدجت'
        verbose_name_plural = 'بيانات الويدجتس'
    
    def __str__(self):
        return f"Data for {self.widget.name}"


class QuickActionWidget(models.Model):
    """الإجراءات السريعة في لوحة التحكم"""
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='quick_actions',
        verbose_name='المستخدم'
    )
    name = models.CharField('اسم الإجراء', max_length=100)
    icon = models.CharField('الأيقونة', max_length=50)
    color = models.CharField('اللون', max_length=20, default='primary')
    url = models.CharField('الرابط', max_length=500)
    description = models.CharField('الوصف', max_length=200, blank=True)
    
    order = models.IntegerField('الترتيب', default=0)
    is_active = models.BooleanField('نشط', default=True)
    usage_count = models.IntegerField('عدد الاستخدامات', default=0)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    class Meta:
        verbose_name = 'إجراء سريع'
        verbose_name_plural = 'الإجراءات السريعة'
        ordering = ['order', '-usage_count']
    
    def __str__(self):
        return self.name
