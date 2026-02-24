"""
نماذج نظام السمات والوضع المظلم
Theme System Models
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator

User = get_user_model()

color_validator = RegexValidator(
    regex=r'^#[0-9A-Fa-f]{6}$',
    message='يجب أن يكون اللون بصيغة HEX مثل #FFFFFF'
)


class Theme(models.Model):
    """سمات النظام"""
    
    THEME_TYPES = [
        ('light', 'فاتح'),
        ('dark', 'مظلم'),
        ('custom', 'مخصص'),
    ]
    
    name = models.CharField('اسم السمة', max_length=100)
    slug = models.SlugField('المعرف', unique=True)
    theme_type = models.CharField('نوع السمة', max_length=20, choices=THEME_TYPES, default='light')
    description = models.TextField('الوصف', blank=True)
    
    # الألوان الأساسية
    primary_color = models.CharField('اللون الأساسي', max_length=7, default='#3498db', validators=[color_validator])
    secondary_color = models.CharField('اللون الثانوي', max_length=7, default='#2ecc71', validators=[color_validator])
    accent_color = models.CharField('لون التمييز', max_length=7, default='#9b59b6', validators=[color_validator])
    
    # ألوان الخلفية
    background_color = models.CharField('لون الخلفية', max_length=7, default='#ffffff', validators=[color_validator])
    surface_color = models.CharField('لون السطح', max_length=7, default='#f8f9fa', validators=[color_validator])
    card_color = models.CharField('لون البطاقات', max_length=7, default='#ffffff', validators=[color_validator])
    
    # ألوان النصوص
    text_primary = models.CharField('لون النص الأساسي', max_length=7, default='#212529', validators=[color_validator])
    text_secondary = models.CharField('لون النص الثانوي', max_length=7, default='#6c757d', validators=[color_validator])
    text_muted = models.CharField('لون النص الخافت', max_length=7, default='#adb5bd', validators=[color_validator])
    
    # ألوان الشريط الجانبي
    sidebar_bg = models.CharField('خلفية الشريط الجانبي', max_length=7, default='#343a40', validators=[color_validator])
    sidebar_text = models.CharField('نص الشريط الجانبي', max_length=7, default='#ffffff', validators=[color_validator])
    sidebar_active = models.CharField('العنصر النشط', max_length=7, default='#007bff', validators=[color_validator])
    
    # ألوان الهيدر
    header_bg = models.CharField('خلفية الهيدر', max_length=7, default='#ffffff', validators=[color_validator])
    header_text = models.CharField('نص الهيدر', max_length=7, default='#212529', validators=[color_validator])
    
    # ألوان الحالات
    success_color = models.CharField('لون النجاح', max_length=7, default='#28a745', validators=[color_validator])
    warning_color = models.CharField('لون التحذير', max_length=7, default='#ffc107', validators=[color_validator])
    danger_color = models.CharField('لون الخطر', max_length=7, default='#dc3545', validators=[color_validator])
    info_color = models.CharField('لون المعلومات', max_length=7, default='#17a2b8', validators=[color_validator])
    
    # إعدادات إضافية
    border_radius = models.CharField('نصف قطر الحواف', max_length=10, default='0.375rem')
    box_shadow = models.CharField('الظل', max_length=100, default='0 0.125rem 0.25rem rgba(0,0,0,0.075)')
    font_family = models.CharField('الخط', max_length=200, default="'Tajawal', 'Segoe UI', sans-serif")
    
    # CSS مخصص
    custom_css = models.TextField('CSS مخصص', blank=True)
    
    is_default = models.BooleanField('افتراضي', default=False)
    is_active = models.BooleanField('نشط', default=True)
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'سمة'
        verbose_name_plural = 'السمات'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if self.is_default:
            Theme.objects.exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)
    
    def to_css_vars(self):
        """تحويل السمة إلى متغيرات CSS"""
        return f"""
        :root {{
            --primary-color: {self.primary_color};
            --secondary-color: {self.secondary_color};
            --accent-color: {self.accent_color};
            --background-color: {self.background_color};
            --surface-color: {self.surface_color};
            --card-color: {self.card_color};
            --text-primary: {self.text_primary};
            --text-secondary: {self.text_secondary};
            --text-muted: {self.text_muted};
            --sidebar-bg: {self.sidebar_bg};
            --sidebar-text: {self.sidebar_text};
            --sidebar-active: {self.sidebar_active};
            --header-bg: {self.header_bg};
            --header-text: {self.header_text};
            --success-color: {self.success_color};
            --warning-color: {self.warning_color};
            --danger-color: {self.danger_color};
            --info-color: {self.info_color};
            --border-radius: {self.border_radius};
            --box-shadow: {self.box_shadow};
            --font-family: {self.font_family};
        }}
        {self.custom_css}
        """


class UserThemePreference(models.Model):
    """تفضيلات السمة للمستخدم"""
    
    MODE_CHOICES = [
        ('light', 'فاتح'),
        ('dark', 'مظلم'),
        ('auto', 'تلقائي'),
    ]
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='theme_preference',
        verbose_name='المستخدم'
    )
    theme = models.ForeignKey(
        Theme,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='السمة المختارة'
    )
    mode = models.CharField('الوضع', max_length=10, choices=MODE_CHOICES, default='auto')
    
    # إعدادات إضافية
    compact_mode = models.BooleanField('الوضع المضغوط', default=False)
    sidebar_collapsed = models.BooleanField('طي الشريط الجانبي', default=False)
    font_size = models.CharField('حجم الخط', max_length=10, default='medium')
    
    # التبديل التلقائي
    auto_switch_enabled = models.BooleanField('تبديل تلقائي', default=True)
    dark_mode_start = models.TimeField('بداية الوضع المظلم', default='18:00')
    dark_mode_end = models.TimeField('نهاية الوضع المظلم', default='06:00')
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'تفضيلات سمة المستخدم'
        verbose_name_plural = 'تفضيلات سمات المستخدمين'
    
    def __str__(self):
        return f"تفضيلات {self.user.username}"
    
    def get_current_mode(self):
        """الحصول على الوضع الحالي"""
        if self.mode != 'auto':
            return self.mode
        
        if not self.auto_switch_enabled:
            return 'light'
        
        from datetime import datetime
        now = datetime.now().time()
        
        if self.dark_mode_start <= self.dark_mode_end:
            if self.dark_mode_start <= now <= self.dark_mode_end:
                return 'dark'
        else:
            if now >= self.dark_mode_start or now <= self.dark_mode_end:
                return 'dark'
        
        return 'light'
