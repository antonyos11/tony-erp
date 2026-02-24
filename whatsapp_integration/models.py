from django.db import models
from django.contrib.auth.models import User
from crm.models import Customer
from inventory.models import Product


class WhatsAppConfig(models.Model):
    """إعدادات واتساب"""
    name = models.CharField('اسم الإعداد', max_length=100, default='default')
    
    # n8n Settings
    n8n_webhook_url = models.URLField('رابط n8n Webhook', blank=True)
    n8n_api_key = models.CharField('مفتاح n8n API', max_length=255, blank=True)
    
    # WhatsApp Business API
    whatsapp_phone_id = models.CharField('Phone Number ID', max_length=100, blank=True)
    whatsapp_token = models.CharField('Access Token', max_length=500, blank=True)
    whatsapp_verify_token = models.CharField('Verify Token', max_length=100, blank=True)
    
    # Auto-reply settings
    welcome_message = models.TextField('رسالة الترحيب', default='مرحباً بك! كيف يمكننا مساعدتك؟')
    product_inquiry_response = models.TextField(
        'رسالة الاستفسار عن المنتجات', 
        default='شكراً لاستفسارك. سنرسل لك قائمة المنتجات المتاحة.'
    )
    order_confirmation = models.TextField('رسالة تأكيد الطلب', default='تم استلام طلبك بنجاح!')
    
    # AI Settings
    use_ai_responses = models.BooleanField('استخدام الرد الذكي', default=False)
    ai_model = models.CharField('نموذج AI', max_length=50, default='gpt-3.5-turbo')
    ai_api_key = models.CharField('مفتاح OpenAI', max_length=255, blank=True)
    
    is_active = models.BooleanField('مفعل', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'إعدادات واتساب'
        verbose_name_plural = 'إعدادات واتساب'
    
    def __str__(self):
        return f"إعدادات واتساب - {self.name}"


class WhatsAppConversation(models.Model):
    """المحادثات"""
    STATUS_CHOICES = [
        ('open', 'مفتوحة'),
        ('pending', 'قيد الانتظار'),
        ('resolved', 'تم الحل'),
        ('closed', 'مغلقة'),
    ]
    
    phone_number = models.CharField('رقم الهاتف', max_length=20, db_index=True)
    customer_name = models.CharField('اسم العميل', max_length=200, blank=True)
    customer = models.ForeignKey(
        Customer, on_delete=models.SET_NULL, 
        null=True, blank=True, 
        verbose_name='العميل في CRM',
        related_name='wa_integration_conversations'
    )
    
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='open')
    assigned_to = models.ForeignKey(
        User, on_delete=models.SET_NULL, 
        null=True, blank=True,
        verbose_name='مسند إلى',
        related_name='wa_integration_assigned_conversations'
    )
    
    last_message_at = models.DateTimeField('آخر رسالة', auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # CRM Integration
    auto_registered = models.BooleanField('تم التسجيل تلقائياً', default=False)
    
    class Meta:
        verbose_name = 'محادثة واتساب'
        verbose_name_plural = 'محادثات واتساب'
        ordering = ['-last_message_at']
    
    def __str__(self):
        return f"{self.customer_name or self.phone_number}"


class WhatsAppMessage(models.Model):
    """الرسائل"""
    DIRECTION_CHOICES = [
        ('incoming', 'واردة'),
        ('outgoing', 'صادرة'),
    ]
    
    TYPE_CHOICES = [
        ('text', 'نص'),
        ('image', 'صورة'),
        ('document', 'مستند'),
        ('audio', 'صوت'),
        ('video', 'فيديو'),
        ('location', 'موقع'),
        ('contact', 'جهة اتصال'),
        ('button', 'زر'),
        ('list', 'قائمة'),
    ]
    
    conversation = models.ForeignKey(
        WhatsAppConversation, on_delete=models.CASCADE,
        related_name='messages', verbose_name='المحادثة'
    )
    
    whatsapp_message_id = models.CharField('WhatsApp Message ID', max_length=100, blank=True)
    direction = models.CharField('الاتجاه', max_length=10, choices=DIRECTION_CHOICES)
    message_type = models.CharField('نوع الرسالة', max_length=20, choices=TYPE_CHOICES, default='text')
    
    content = models.TextField('المحتوى')
    media_url = models.URLField('رابط الوسائط', blank=True)
    
    # Intent Detection
    detected_intent = models.CharField('النية المكتشفة', max_length=50, blank=True)
    confidence = models.FloatField('مستوى الثقة', default=0)
    
    # Product mentions
    mentioned_products = models.ManyToManyField(
        Product, blank=True, verbose_name='المنتجات المذكورة'
    )
    
    is_read = models.BooleanField('مقروءة', default=False)
    sent_at = models.DateTimeField('وقت الإرسال', auto_now_add=True)
    delivered_at = models.DateTimeField('وقت التسليم', null=True, blank=True)
    read_at = models.DateTimeField('وقت القراءة', null=True, blank=True)
    
    class Meta:
        verbose_name = 'رسالة واتساب'
        verbose_name_plural = 'رسائل واتساب'
        ordering = ['sent_at']
    
    def __str__(self):
        return f"{self.get_direction_display()}: {self.content[:50]}"


class WhatsAppTemplate(models.Model):
    """قوالب الرسائل"""
    CATEGORY_CHOICES = [
        ('welcome', 'ترحيب'),
        ('product', 'منتجات'),
        ('order', 'طلبات'),
        ('payment', 'دفع'),
        ('shipping', 'شحن'),
        ('support', 'دعم'),
        ('marketing', 'تسويق'),
    ]
    
    name = models.CharField('اسم القالب', max_length=100)
    category = models.CharField('الفئة', max_length=20, choices=CATEGORY_CHOICES)
    
    # Template Content
    header = models.CharField('العنوان', max_length=60, blank=True)
    body = models.TextField('المحتوى')
    footer = models.CharField('التذييل', max_length=60, blank=True)
    
    # Buttons
    buttons = models.JSONField('الأزرار', default=list, blank=True)
    
    # Variables
    variables = models.JSONField('المتغيرات', default=list, blank=True)
    
    is_active = models.BooleanField('مفعل', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'قالب رسالة'
        verbose_name_plural = 'قوالب الرسائل'
    
    def __str__(self):
        return self.name


class ProductCatalog(models.Model):
    """كتالوج المنتجات للواتساب"""
    product = models.OneToOneField(
        Product, on_delete=models.CASCADE,
        related_name='whatsapp_catalog',
        verbose_name='المنتج'
    )
    
    whatsapp_description = models.TextField('وصف واتساب', blank=True)
    whatsapp_image_url = models.URLField('رابط الصورة', blank=True)
    
    # Keywords for search
    keywords = models.TextField('كلمات البحث', blank=True, help_text='كلمات مفتاحية مفصولة بفاصلة')
    
    # Availability
    is_available_on_whatsapp = models.BooleanField('متاح على واتساب', default=True)
    
    # Quick replies for this product
    quick_replies = models.JSONField('ردود سريعة', default=list, blank=True)
    
    class Meta:
        verbose_name = 'كتالوج منتج'
        verbose_name_plural = 'كتالوج المنتجات'
    
    def __str__(self):
        return f"كتالوج: {self.product.name}"


class AutoReplyRule(models.Model):
    """قواعد الرد التلقائي"""
    MATCH_TYPE_CHOICES = [
        ('exact', 'مطابقة تامة'),
        ('contains', 'يحتوي على'),
        ('starts_with', 'يبدأ بـ'),
        ('regex', 'تعبير منتظم'),
    ]
    
    ACTION_CHOICES = [
        ('reply', 'رد برسالة'),
        ('send_products', 'إرسال منتجات'),
        ('create_lead', 'إنشاء عميل محتمل'),
        ('assign_agent', 'تحويل لموظف'),
        ('webhook', 'تشغيل Webhook'),
    ]
    
    name = models.CharField('اسم القاعدة', max_length=100)
    priority = models.IntegerField('الأولوية', default=0)
    
    # Trigger
    trigger_text = models.CharField('نص التفعيل', max_length=255)
    match_type = models.CharField('نوع المطابقة', max_length=20, choices=MATCH_TYPE_CHOICES, default='contains')
    
    # Action
    action = models.CharField('الإجراء', max_length=20, choices=ACTION_CHOICES)
    response_template = models.ForeignKey(
        WhatsAppTemplate, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='قالب الرد'
    )
    response_text = models.TextField('نص الرد', blank=True)
    webhook_url = models.URLField('رابط Webhook', blank=True)
    
    is_active = models.BooleanField('مفعل', default=True)
    
    class Meta:
        verbose_name = 'قاعدة رد تلقائي'
        verbose_name_plural = 'قواعد الرد التلقائي'
        ordering = ['-priority']
    
    def __str__(self):
        return self.name
