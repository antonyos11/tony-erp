from django.db import models
from django.contrib.auth.models import User
from crm.models import Customer, Opportunity


class SocialConversation(models.Model):
    """محادثة موحدة لكل المنصات (واتساب، فيسبوك، انستجرام)"""
    
    PLATFORM_CHOICES = [
        ('whatsapp', 'واتساب'),
        ('facebook', 'فيسبوك'),
        ('instagram', 'انستجرام'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'نشطة'),
        ('closed', 'مغلقة'),
        ('converted', 'تم التحويل لعميل'),
    ]
    
    # المنصة
    platform = models.CharField('المنصة', max_length=20, choices=PLATFORM_CHOICES, default='whatsapp', db_index=True)
    
    # معرّف المستخدم على المنصة
    platform_user_id = models.CharField('معرّف المستخدم', max_length=200, db_index=True)
    phone_number = models.CharField('رقم الهاتف', max_length=20, blank=True)  # للواتساب
    
    customer_name = models.CharField('اسم العميل', max_length=200, blank=True)
    profile_picture = models.URLField('صورة البروفايل', blank=True)
    
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, 
                                 verbose_name='عميل CRM', related_name='social_conversations')
    opportunity = models.ForeignKey(Opportunity, on_delete=models.SET_NULL, null=True, blank=True,
                                   verbose_name='فرصة بيع', related_name='social_conversations')
    
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='active')
    
    # تتبع الاهتمامات
    interested_products = models.JSONField('المنتجات المهتم بها', default=list, blank=True)
    requested_categories = models.JSONField('الفئات المطلوبة', default=list, blank=True)
    
    # معلومات إضافية من المحادثة
    budget_range = models.CharField('الميزانية المتوقعة', max_length=100, blank=True)
    notes = models.TextField('ملاحظات', blank=True)
    
    # Metadata
    first_message_at = models.DateTimeField('أول رسالة', auto_now_add=True)
    last_message_at = models.DateTimeField('آخر رسالة', auto_now=True)
    messages_count = models.IntegerField('عدد الرسائل', default=0)
    
    # AI Context
    conversation_summary = models.TextField('ملخص المحادثة', blank=True)
    ai_sentiment = models.CharField('تحليل المشاعر', max_length=50, blank=True)
    conversion_probability = models.FloatField('احتمالية الشراء', default=0.0)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'محادثة سوشيال ميديا'
        verbose_name_plural = 'محادثات سوشيال ميديا'
        ordering = ['-last_message_at']
        unique_together = ['platform', 'platform_user_id']
        indexes = [
            models.Index(fields=['platform', 'platform_user_id']),
            models.Index(fields=['status', '-last_message_at']),
        ]
    
    def __str__(self):
        return f"[{self.get_platform_display()}] {self.customer_name or self.platform_user_id}"


class SocialMessage(models.Model):
    """رسالة موحدة لكل المنصات"""
    
    MESSAGE_TYPE_CHOICES = [
        ('text', 'نص'),
        ('image', 'صورة'),
        ('document', 'مستند'),
        ('voice', 'صوت'),
        ('video', 'فيديو'),
        ('sticker', 'ستيكر'),
        ('story_mention', 'إشارة في ستوري'),
        ('story_reply', 'رد على ستوري'),
    ]
    
    DIRECTION_CHOICES = [
        ('inbound', 'وارد من العميل'),
        ('outbound', 'صادر للعميل'),
    ]
    
    conversation = models.ForeignKey(SocialConversation, on_delete=models.CASCADE,
                                     related_name='messages', verbose_name='المحادثة')
    
    direction = models.CharField('الاتجاه', max_length=10, choices=DIRECTION_CHOICES)
    message_type = models.CharField('نوع الرسالة', max_length=20, choices=MESSAGE_TYPE_CHOICES, default='text')
    
    content = models.TextField('المحتوى')
    media_url = models.URLField('رابط الوسائط', blank=True)
    
    # Platform Message ID
    platform_message_id = models.CharField('معرّف الرسالة', max_length=200, unique=True, db_index=True)
    
    # AI Processing
    ai_intent = models.CharField('النية المكتشفة', max_length=100, blank=True)
    ai_entities = models.JSONField('الكيانات المستخرجة', default=dict, blank=True)
    
    # Status
    delivered = models.BooleanField('تم التوصيل', default=False)
    read = models.BooleanField('تمت القراءة', default=False)
    
    created_at = models.DateTimeField('تاريخ الإرسال', auto_now_add=True)
    
    class Meta:
        verbose_name = 'رسالة سوشيال ميديا'
        verbose_name_plural = 'رسائل سوشيال ميديا'
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.conversation.platform} - {self.get_direction_display()}"


class WhatsAppConversation(models.Model):
    """محادثة واتساب"""
    
    STATUS_CHOICES = [
        ('active', 'نشطة'),
        ('closed', 'مغلقة'),
        ('converted', 'تم التحويل لعميل'),
    ]
    
    phone_number = models.CharField('رقم الهاتف', max_length=20, unique=True, db_index=True)
    customer_name = models.CharField('اسم العميل', max_length=200, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, 
                                 verbose_name='عميل CRM', related_name='whatsapp_conversations')
    opportunity = models.ForeignKey(Opportunity, on_delete=models.SET_NULL, null=True, blank=True,
                                   verbose_name='فرصة بيع', related_name='whatsapp_conversations')
    
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='active')
    
    # تتبع الاهتمامات
    interested_products = models.JSONField('المنتجات المهتم بها', default=list, blank=True)
    requested_categories = models.JSONField('الفئات المطلوبة', default=list, blank=True)
    
    # معلومات إضافية من المحادثة
    budget_range = models.CharField('الميزانية المتوقعة', max_length=100, blank=True)
    notes = models.TextField('ملاحظات', blank=True)
    
    # Metadata
    first_message_at = models.DateTimeField('أول رسالة', auto_now_add=True)
    last_message_at = models.DateTimeField('آخر رسالة', auto_now=True)
    messages_count = models.IntegerField('عدد الرسائل', default=0)
    
    # AI Context
    conversation_summary = models.TextField('ملخص المحادثة', blank=True)
    ai_sentiment = models.CharField('تحليل المشاعر', max_length=50, blank=True)  # positive, neutral, negative
    conversion_probability = models.FloatField('احتمالية الشراء', default=0.0)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'محادثة واتساب'
        verbose_name_plural = 'محادثات واتساب'
        ordering = ['-last_message_at']
        indexes = [
            models.Index(fields=['phone_number', 'status']),
            models.Index(fields=['status', '-last_message_at']),
        ]
    
    def __str__(self):
        return f"{self.customer_name or self.phone_number} - {self.get_status_display()}"


class WhatsAppMessage(models.Model):
    """رسالة واتساب"""
    
    MESSAGE_TYPE_CHOICES = [
        ('text', 'نص'),
        ('image', 'صورة'),
        ('document', 'مستند'),
        ('voice', 'صوت'),
        ('video', 'فيديو'),
    ]
    
    DIRECTION_CHOICES = [
        ('inbound', 'وارد من العميل'),
        ('outbound', 'صادر للعميل'),
    ]
    
    conversation = models.ForeignKey(WhatsAppConversation, on_delete=models.CASCADE,
                                     related_name='messages', verbose_name='المحادثة')
    
    direction = models.CharField('الاتجاه', max_length=10, choices=DIRECTION_CHOICES)
    message_type = models.CharField('نوع الرسالة', max_length=20, choices=MESSAGE_TYPE_CHOICES, default='text')
    
    content = models.TextField('المحتوى')
    media_url = models.URLField('رابط الوسائط', blank=True)
    
    # WhatsApp Message ID
    whatsapp_message_id = models.CharField('معرّف الرسالة', max_length=200, unique=True, db_index=True)
    
    # AI Processing
    ai_intent = models.CharField('النية المكتشفة', max_length=100, blank=True)  # inquiry, purchase, complaint, etc.
    ai_entities = models.JSONField('الكيانات المستخرجة', default=dict, blank=True)  # products, prices, dates
    
    # Status
    delivered = models.BooleanField('تم التوصيل', default=False)
    read = models.BooleanField('تمت القراءة', default=False)
    
    created_at = models.DateTimeField('تاريخ الإرسال', auto_now_add=True)
    
    class Meta:
        verbose_name = 'رسالة واتساب'
        verbose_name_plural = 'رسائل واتساب'
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.conversation.phone_number} - {self.get_direction_display()}"


class WhatsAppConfiguration(models.Model):
    """إعدادات الواتساب"""
    
    name = models.CharField('الاسم', max_length=100, unique=True)
    
    # WhatsApp Business API
    whatsapp_api_url = models.URLField('رابط WhatsApp API')
    whatsapp_api_token = models.CharField('Token', max_length=500)
    phone_number_id = models.CharField('معرّف رقم الهاتف', max_length=100)
    
    # n8n Webhook
    n8n_webhook_url = models.URLField('رابط n8n Webhook', blank=True)
    
    # AI Settings
    ai_provider = models.CharField('مزود الذكاء الصناعي', max_length=50, 
                                   choices=[('openai', 'OpenAI'), ('anthropic', 'Anthropic')],
                                   default='openai')
    ai_api_key = models.CharField('AI API Key', max_length=500, blank=True)
    ai_model = models.CharField('نموذج الذكاء الصناعي', max_length=100, default='gpt-4')
    
    # System Prompts
    system_prompt = models.TextField('نص التعليمات للـ AI', default='''أنت مساعد مبيعات ذكي لشركة بيع منتجات.
مهمتك:
1. الترحيب بالعملاء بطريقة ودودة واحترافية
2. فهم احتياجاتهم وتقديم المنتجات المناسبة
3. الإجابة على الأسئلة بدقة
4. تشجيع العميل على الشراء بطريقة لطيفة
5. تسجيل اهتمامات العميل

كن مهذباً، سريعاً في الرد، ومفيداً.''')
    
    # Auto-assign to CRM
    auto_create_customer = models.BooleanField('إنشاء عميل تلقائياً', default=True)
    auto_create_opportunity = models.BooleanField('إنشاء فرصة بيع تلقائياً', default=True)
    default_opportunity_stage = models.CharField('مرحلة الفرصة الافتراضية', max_length=50, default='مبدئي')
    
    # Business hours
    business_hours_enabled = models.BooleanField('تفعيل ساعات العمل', default=False)
    business_hours_start = models.TimeField('بداية العمل', null=True, blank=True)
    business_hours_end = models.TimeField('نهاية العمل', null=True, blank=True)
    outside_hours_message = models.TextField('رسالة خارج أوقات العمل', blank=True,
                                            default='شكراً لتواصلك. نحن خارج أوقات العمل حالياً. سنرد عليك في أقرب وقت.')
    
    is_active = models.BooleanField('مفعّل', default=True)
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'إعدادات واتساب'
        verbose_name_plural = 'إعدادات واتساب'
    
    def __str__(self):
        return self.name


class SocialPlatformConfig(models.Model):
    """إعدادات موحدة لجميع منصات السوشيال ميديا"""
    
    PLATFORM_CHOICES = [
        ('whatsapp', 'واتساب'),
        ('facebook', 'فيسبوك ماسنجر'),
        ('instagram', 'انستجرام'),
    ]
    
    name = models.CharField('الاسم', max_length=100)
    platform = models.CharField('المنصة', max_length=20, choices=PLATFORM_CHOICES, unique=True)
    
    # Meta/Facebook API Settings (used for all 3 platforms)
    page_id = models.CharField('معرّف الصفحة', max_length=100, blank=True, 
                               help_text='للفيسبوك والانستجرام')
    page_access_token = models.CharField('Page Access Token', max_length=500)
    app_secret = models.CharField('App Secret', max_length=200, blank=True,
                                 help_text='للتحقق من الـ webhook')
    verify_token = models.CharField('Verify Token', max_length=200, blank=True,
                                   help_text='للتحقق من الـ webhook')
    
    # WhatsApp specific
    phone_number_id = models.CharField('معرّف رقم الهاتف', max_length=100, blank=True,
                                       help_text='للواتساب فقط')
    whatsapp_business_account_id = models.CharField('معرّف حساب واتساب بيزنس', max_length=100, blank=True)
    
    # Instagram specific
    instagram_account_id = models.CharField('معرّف حساب الانستجرام', max_length=100, blank=True)
    
    # n8n Webhook
    n8n_webhook_url = models.URLField('رابط n8n Webhook', blank=True)
    
    # AI Settings
    ai_provider = models.CharField('مزود الذكاء الصناعي', max_length=50, 
                                   choices=[('openai', 'OpenAI'), ('anthropic', 'Anthropic'), ('gemini', 'Google Gemini')],
                                   default='openai')
    ai_api_key = models.CharField('AI API Key', max_length=500, blank=True)
    ai_model = models.CharField('نموذج الذكاء الصناعي', max_length=100, default='gpt-4')
    
    # System Prompt
    system_prompt = models.TextField('نص التعليمات للـ AI', default='''أنت مساعد مبيعات ذكي لشركة بيع منتجات.
مهمتك:
1. الترحيب بالعملاء بطريقة ودودة واحترافية
2. فهم احتياجاتهم وتقديم المنتجات المناسبة
3. الإجابة على الأسئلة بدقة
4. تشجيع العميل على الشراء بطريقة لطيفة
5. تسجيل اهتمامات العميل

كن مهذباً، سريعاً في الرد، ومفيداً.''')
    
    # Auto CRM
    auto_create_customer = models.BooleanField('إنشاء عميل تلقائياً', default=True)
    auto_create_opportunity = models.BooleanField('إنشاء فرصة بيع تلقائياً', default=True)
    
    # Business hours
    business_hours_enabled = models.BooleanField('تفعيل ساعات العمل', default=False)
    business_hours_start = models.TimeField('بداية العمل', null=True, blank=True)
    business_hours_end = models.TimeField('نهاية العمل', null=True, blank=True)
    outside_hours_message = models.TextField('رسالة خارج أوقات العمل', blank=True,
                                            default='شكراً لتواصلك. نحن خارج أوقات العمل حالياً. سنرد عليك في أقرب وقت.')
    
    is_active = models.BooleanField('مفعّل', default=True)
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'إعدادات منصة سوشيال'
        verbose_name_plural = 'إعدادات منصات السوشيال'
    
    def __str__(self):
        return f"{self.get_platform_display()} - {self.name}"


class ProductKnowledgeBase(models.Model):
    """قاعدة معرفة المنتجات للـ AI"""
    
    product_name = models.CharField('اسم المنتج', max_length=200, db_index=True)
    product_code = models.CharField('كود المنتج', max_length=100, blank=True)
    
    # Product reference (optional link to actual product)
    content_type = models.CharField('نوع', max_length=100, blank=True)
    object_id = models.PositiveIntegerField('معرّف المنتج', null=True, blank=True)
    
    # Knowledge
    description = models.TextField('الوصف')
    features = models.JSONField('المميزات', default=list)
    specifications = models.JSONField('المواصفات', default=dict)
    
    price = models.DecimalField('السعر', max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField('العملة', max_length=10, default='EGP')
    
    # For AI
    keywords = models.JSONField('الكلمات المفتاحية', default=list)
    common_questions = models.JSONField('الأسئلة الشائعة', default=list)
    
    # Availability
    in_stock = models.BooleanField('متوفر', default=True)
    stock_quantity = models.IntegerField('الكمية المتوفرة', null=True, blank=True)
    
    category = models.CharField('الفئة', max_length=100, blank=True, db_index=True)
    tags = models.JSONField('الوسوم', default=list)
    
    # Sales info
    popularity_score = models.IntegerField('معدل الشعبية', default=0)
    times_mentioned = models.IntegerField('مرات الذكر', default=0)
    times_purchased = models.IntegerField('مرات الشراء', default=0)
    
    is_active = models.BooleanField('مفعّل', default=True)
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'معلومات منتج للـ AI'
        verbose_name_plural = 'قاعدة معرفة المنتجات'
        ordering = ['-popularity_score', 'product_name']
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['-popularity_score']),
        ]
    
    def __str__(self):
        return self.product_name


class ExcludedCategory(models.Model):
    """الفئات المستبعدة من قاعدة المعرفة"""
    
    category_name = models.CharField('اسم الفئة', max_length=200, unique=True)
    reason = models.TextField('سبب الاستبعاد', blank=True)
    excluded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='تم الاستبعاد بواسطة')
    created_at = models.DateTimeField('تاريخ الاستبعاد', auto_now_add=True)
    
    class Meta:
        verbose_name = 'فئة مستبعدة'
        verbose_name_plural = 'الفئات المستبعدة'
        ordering = ['category_name']
    
    def __str__(self):
        return self.category_name
