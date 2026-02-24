"""
نماذج المساعد الذكي
==================
يحتوي على نماذج المحادثات والرسائل والإعدادات
"""
import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class AIAssistantSettings(models.Model):
    """إعدادات المساعد الذكي"""
    
    ASSISTANT_TYPE_CHOICES = [
        ('store', _('مساعد المتجر')),
        ('system', _('مساعد النظام')),
    ]
    
    PROVIDER_CHOICES = [
        ('openai', 'OpenAI (GPT)'),
        ('anthropic', 'Anthropic (Claude)'),
        ('google', 'Google (Gemini)'),
        ('local', _('نموذج محلي')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assistant_type = models.CharField(
        _('نوع المساعد'),
        max_length=20,
        choices=ASSISTANT_TYPE_CHOICES,
        unique=True
    )
    name = models.CharField(_('اسم المساعد'), max_length=100)
    welcome_message = models.TextField(_('رسالة الترحيب'), blank=True)
    provider = models.CharField(
        _('مزود الخدمة'),
        max_length=20,
        choices=PROVIDER_CHOICES,
        default='openai'
    )
    api_key = models.CharField(_('مفتاح API'), max_length=255, blank=True)
    model_name = models.CharField(
        _('اسم النموذج'),
        max_length=100,
        default='gpt-3.5-turbo'
    )
    system_prompt = models.TextField(
        _('تعليمات النظام'),
        blank=True,
        help_text=_('التعليمات التي يتبعها المساعد')
    )
    max_tokens = models.PositiveIntegerField(_('الحد الأقصى للتوكنز'), default=1000)
    temperature = models.FloatField(_('درجة الإبداعية'), default=0.7)
    is_active = models.BooleanField(_('نشط'), default=True)
    
    # إعدادات إضافية
    enable_product_search = models.BooleanField(
        _('تفعيل البحث في المنتجات'),
        default=True,
        help_text=_('للمساعد المتجر فقط')
    )
    enable_order_tracking = models.BooleanField(
        _('تفعيل تتبع الطلبات'),
        default=True
    )
    enable_faq = models.BooleanField(
        _('تفعيل الأسئلة الشائعة'),
        default=True
    )
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('إعدادات المساعد الذكي')
        verbose_name_plural = _('إعدادات المساعدين الذكية')
    
    def __str__(self):
        return f"{self.name} ({self.get_assistant_type_display()})"


class ChatSession(models.Model):
    """جلسة محادثة"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('المستخدم'),
        related_name='ai_chat_sessions'
    )
    session_key = models.CharField(
        _('مفتاح الجلسة'),
        max_length=100,
        blank=True,
        help_text=_('للزوار غير المسجلين')
    )
    assistant_settings = models.ForeignKey(
        AIAssistantSettings,
        on_delete=models.CASCADE,
        verbose_name=_('إعدادات المساعد'),
        related_name='sessions'
    )
    title = models.CharField(_('عنوان المحادثة'), max_length=200, blank=True)
    is_active = models.BooleanField(_('نشطة'), default=True)
    started_at = models.DateTimeField(_('بداية المحادثة'), auto_now_add=True)
    ended_at = models.DateTimeField(_('نهاية المحادثة'), null=True, blank=True)
    
    # معلومات إضافية
    user_agent = models.TextField(_('معلومات المتصفح'), blank=True)
    ip_address = models.GenericIPAddressField(_('عنوان IP'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('جلسة محادثة')
        verbose_name_plural = _('جلسات المحادثات')
        ordering = ['-started_at']
    
    def __str__(self):
        if self.user:
            return f"محادثة {self.user.username} - {self.started_at.strftime('%Y-%m-%d %H:%M')}"
        return f"محادثة زائر - {self.started_at.strftime('%Y-%m-%d %H:%M')}"
    
    def get_messages_count(self):
        return self.messages.count()
    
    def end_session(self):
        self.is_active = False
        self.ended_at = timezone.now()
        self.save()


class ChatMessage(models.Model):
    """رسالة في المحادثة"""
    
    ROLE_CHOICES = [
        ('user', _('المستخدم')),
        ('assistant', _('المساعد')),
        ('system', _('النظام')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        verbose_name=_('الجلسة'),
        related_name='messages'
    )
    role = models.CharField(_('الدور'), max_length=20, choices=ROLE_CHOICES)
    content = models.TextField(_('المحتوى'))
    
    # معلومات تقنية
    tokens_used = models.PositiveIntegerField(_('التوكنز المستخدمة'), default=0)
    processing_time = models.FloatField(_('وقت المعالجة (ثواني)'), default=0)
    
    # للرسائل التي تحتوي على معلومات منتجات
    related_products = models.JSONField(
        _('المنتجات المرتبطة'),
        default=list,
        blank=True
    )
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('رسالة محادثة')
        verbose_name_plural = _('رسائل المحادثات')
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.get_role_display()}: {self.content[:50]}..."


class FAQ(models.Model):
    """الأسئلة الشائعة"""
    
    CATEGORY_CHOICES = [
        ('general', _('عام')),
        ('products', _('المنتجات')),
        ('orders', _('الطلبات')),
        ('shipping', _('الشحن')),
        ('payment', _('الدفع')),
        ('returns', _('المرتجعات')),
        ('account', _('الحساب')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assistant_type = models.CharField(
        _('نوع المساعد'),
        max_length=20,
        choices=AIAssistantSettings.ASSISTANT_TYPE_CHOICES
    )
    category = models.CharField(
        _('التصنيف'),
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='general'
    )
    question = models.TextField(_('السؤال'))
    answer = models.TextField(_('الإجابة'))
    keywords = models.TextField(
        _('الكلمات المفتاحية'),
        blank=True,
        help_text=_('كلمات مفتاحية مفصولة بفواصل')
    )
    order = models.PositiveIntegerField(_('الترتيب'), default=0)
    is_active = models.BooleanField(_('نشط'), default=True)
    
    # إحصائيات
    views_count = models.PositiveIntegerField(_('عدد المشاهدات'), default=0)
    helpful_count = models.PositiveIntegerField(_('عدد مرات المساعدة'), default=0)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('سؤال شائع')
        verbose_name_plural = _('الأسئلة الشائعة')
        ordering = ['category', 'order']
    
    def __str__(self):
        return self.question[:100]
    
    def get_keywords_list(self):
        if self.keywords:
            return [k.strip() for k in self.keywords.split(',')]
        return []


class QuickReply(models.Model):
    """ردود سريعة جاهزة"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assistant_type = models.CharField(
        _('نوع المساعد'),
        max_length=20,
        choices=AIAssistantSettings.ASSISTANT_TYPE_CHOICES
    )
    title = models.CharField(_('العنوان'), max_length=100)
    content = models.TextField(_('المحتوى'))
    icon = models.CharField(_('الأيقونة'), max_length=50, default='bi-chat-dots')
    order = models.PositiveIntegerField(_('الترتيب'), default=0)
    is_active = models.BooleanField(_('نشط'), default=True)
    
    class Meta:
        verbose_name = _('رد سريع')
        verbose_name_plural = _('الردود السريعة')
        ordering = ['order']
    
    def __str__(self):
        return self.title
