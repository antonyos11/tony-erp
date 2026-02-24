"""
نماذج تكامل الساعات الذكية
Smart Watch Integration Models
"""

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class WatchDevice(models.Model):
    """جهاز الساعة الذكية"""
    
    DEVICE_TYPES = [
        ('apple_watch', 'Apple Watch'),
        ('galaxy_watch', 'Samsung Galaxy Watch'),
        ('fitbit', 'Fitbit'),
        ('garmin', 'Garmin'),
        ('wear_os', 'Wear OS'),
        ('other', 'أخرى'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='watch_devices',
        verbose_name='المستخدم'
    )
    
    name = models.CharField('اسم الجهاز', max_length=100)
    device_type = models.CharField('نوع الجهاز', max_length=20, choices=DEVICE_TYPES)
    device_id = models.CharField('معرف الجهاز', max_length=200, unique=True)
    
    # التوكن والمصادقة
    access_token = models.TextField('رمز الوصول', blank=True)
    refresh_token = models.TextField('رمز التحديث', blank=True)
    token_expires_at = models.DateTimeField('انتهاء الرمز', null=True, blank=True)
    
    # الحالة
    is_active = models.BooleanField('نشط', default=True)
    is_connected = models.BooleanField('متصل', default=False)
    last_sync = models.DateTimeField('آخر مزامنة', null=True, blank=True)
    
    # الإعدادات
    notification_enabled = models.BooleanField('الإشعارات مفعلة', default=True)
    quick_actions_enabled = models.BooleanField('الإجراءات السريعة', default=True)
    
    created_at = models.DateTimeField('تاريخ الإضافة', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'ساعة ذكية'
        verbose_name_plural = 'الساعات الذكية'
    
    def __str__(self):
        return f"{self.name} - {self.user.username}"


class WatchNotification(models.Model):
    """إشعار الساعة"""
    
    NOTIFICATION_TYPES = [
        ('alert', 'تنبيه'),
        ('reminder', 'تذكير'),
        ('message', 'رسالة'),
        ('task', 'مهمة'),
        ('approval', 'موافقة'),
        ('call', 'مكالمة'),
    ]
    
    PRIORITIES = [
        ('low', 'منخفضة'),
        ('normal', 'عادية'),
        ('high', 'عالية'),
        ('urgent', 'عاجلة'),
    ]
    
    device = models.ForeignKey(
        WatchDevice,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='الجهاز'
    )
    
    notification_type = models.CharField('نوع الإشعار', max_length=20, choices=NOTIFICATION_TYPES)
    priority = models.CharField('الأولوية', max_length=20, choices=PRIORITIES, default='normal')
    
    title = models.CharField('العنوان', max_length=100)
    body = models.TextField('المحتوى')
    
    # الإجراءات
    action_url = models.URLField('رابط الإجراء', blank=True)
    action_buttons = models.JSONField('أزرار الإجراءات', default=list, blank=True)
    
    # البيانات
    data = models.JSONField('بيانات إضافية', default=dict, blank=True)
    
    # الحالة
    is_sent = models.BooleanField('تم الإرسال', default=False)
    sent_at = models.DateTimeField('تاريخ الإرسال', null=True, blank=True)
    is_read = models.BooleanField('مقروء', default=False)
    read_at = models.DateTimeField('تاريخ القراءة', null=True, blank=True)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    class Meta:
        verbose_name = 'إشعار ساعة'
        verbose_name_plural = 'إشعارات الساعات'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.device.user.username}"


class QuickAction(models.Model):
    """إجراء سريع للساعة"""
    
    ACTION_TYPES = [
        ('check_in', 'تسجيل حضور'),
        ('check_out', 'تسجيل انصراف'),
        ('approve', 'موافقة'),
        ('reject', 'رفض'),
        ('call', 'اتصال'),
        ('message', 'رسالة'),
        ('timer', 'مؤقت'),
        ('custom', 'مخصص'),
    ]
    
    name = models.CharField('الاسم', max_length=100)
    action_type = models.CharField('نوع الإجراء', max_length=20, choices=ACTION_TYPES)
    
    icon = models.CharField('الأيقونة', max_length=50, default='fas fa-bolt')
    color = models.CharField('اللون', max_length=20, default='#007bff')
    
    # الإعداد
    api_endpoint = models.CharField('نقطة API', max_length=200, blank=True)
    request_method = models.CharField('طريقة الطلب', max_length=10, default='POST')
    request_data = models.JSONField('بيانات الطلب', default=dict, blank=True)
    
    # التوفر
    is_global = models.BooleanField('متاح للجميع', default=False)
    available_for = models.ManyToManyField(
        User,
        blank=True,
        related_name='watch_quick_actions',
        verbose_name='متاح لـ'
    )
    
    order = models.IntegerField('الترتيب', default=0)
    is_active = models.BooleanField('نشط', default=True)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    class Meta:
        verbose_name = 'إجراء سريع'
        verbose_name_plural = 'الإجراءات السريعة'
        ordering = ['order']
    
    def __str__(self):
        return self.name


class WatchActionLog(models.Model):
    """سجل إجراءات الساعة"""
    
    device = models.ForeignKey(
        WatchDevice,
        on_delete=models.CASCADE,
        related_name='action_logs',
        verbose_name='الجهاز'
    )
    
    action = models.ForeignKey(
        QuickAction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='الإجراء'
    )
    
    action_name = models.CharField('اسم الإجراء', max_length=100)
    action_type = models.CharField('نوع الإجراء', max_length=20)
    
    # النتيجة
    is_success = models.BooleanField('ناجح', default=True)
    response_data = models.JSONField('بيانات الاستجابة', default=dict, blank=True)
    error_message = models.TextField('رسالة الخطأ', blank=True)
    
    # الموقع (اختياري)
    latitude = models.DecimalField('خط العرض', max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField('خط الطول', max_digits=9, decimal_places=6, null=True, blank=True)
    
    created_at = models.DateTimeField('التاريخ', auto_now_add=True)
    
    class Meta:
        verbose_name = 'سجل إجراء'
        verbose_name_plural = 'سجل الإجراءات'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.action_name} - {self.device.user.username}"


class WatchDashboardWidget(models.Model):
    """ويدجت لوحة الساعة"""
    
    WIDGET_TYPES = [
        ('stats', 'إحصائيات'),
        ('tasks', 'مهام'),
        ('calendar', 'تقويم'),
        ('messages', 'رسائل'),
        ('weather', 'الطقس'),
        ('health', 'الصحة'),
    ]
    
    name = models.CharField('الاسم', max_length=100)
    widget_type = models.CharField('نوع الويدجت', max_length=20, choices=WIDGET_TYPES)
    
    # المصدر
    data_source = models.CharField('مصدر البيانات', max_length=200, blank=True)
    refresh_interval = models.IntegerField('فترة التحديث (ثانية)', default=300)
    
    # التصميم
    size = models.CharField('الحجم', max_length=20, default='small')
    
    is_active = models.BooleanField('نشط', default=True)
    order = models.IntegerField('الترتيب', default=0)
    
    class Meta:
        verbose_name = 'ويدجت ساعة'
        verbose_name_plural = 'ويدجتات الساعات'
        ordering = ['order']
    
    def __str__(self):
        return self.name


class WatchUserSettings(models.Model):
    """إعدادات الساعة للمستخدم"""
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='watch_settings',
        verbose_name='المستخدم'
    )
    
    # الإشعارات
    notify_on_task = models.BooleanField('إشعار المهام', default=True)
    notify_on_message = models.BooleanField('إشعار الرسائل', default=True)
    notify_on_approval = models.BooleanField('إشعار الموافقات', default=True)
    notify_on_reminder = models.BooleanField('إشعار التذكيرات', default=True)
    
    # الإجراءات السريعة المفضلة
    favorite_actions = models.ManyToManyField(
        QuickAction,
        blank=True,
        related_name='favorited_by',
        verbose_name='الإجراءات المفضلة'
    )
    
    # الويدجتات
    enabled_widgets = models.ManyToManyField(
        WatchDashboardWidget,
        blank=True,
        related_name='enabled_for',
        verbose_name='الويدجتات المفعلة'
    )
    
    # التفضيلات
    vibration_enabled = models.BooleanField('الاهتزاز', default=True)
    sound_enabled = models.BooleanField('الصوت', default=True)
    do_not_disturb_start = models.TimeField('بداية عدم الإزعاج', null=True, blank=True)
    do_not_disturb_end = models.TimeField('نهاية عدم الإزعاج', null=True, blank=True)
    
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'إعدادات ساعة'
        verbose_name_plural = 'إعدادات الساعات'
    
    def __str__(self):
        return f"إعدادات {self.user.username}"
