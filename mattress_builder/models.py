"""
نماذج نظام بناء المراتب المخصصة - Mattress Builder Models
تمكن العملاء من تصميم مراتبهم الخاصة بطريقة تفاعلية
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import json
import hashlib

User = get_user_model()


class MattressFeelingType(models.Model):
    """أنواع إحساس المرتبة - يتم إدارتها من لوحة التحكم"""
    FIRMNESS_LEVELS = [
        ('extra_soft', _('ناعم جداً')),
        ('soft', _('ناعم')),
        ('medium_soft', _('متوسط الليونة')),
        ('medium', _('متوسط')),
        ('medium_firm', _('متوسط الصلابة')),
        ('firm', _('صلب')),
        ('extra_firm', _('صلب جداً')),
    ]
    
    name = models.CharField(max_length=100, verbose_name=_("اسم الإحساس"))
    name_en = models.CharField(max_length=100, verbose_name=_("الاسم بالإنجليزية"), blank=True)
    firmness_level = models.CharField(
        max_length=20,
        choices=FIRMNESS_LEVELS,
        verbose_name=_("مستوى الصلابة")
    )
    firmness_score = models.PositiveIntegerField(
        default=5,
        verbose_name=_("درجة الصلابة (1-10)"),
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text=_("1=ناعم جداً، 10=صلب جداً")
    )
    description = models.TextField(blank=True, verbose_name=_("الوصف"))
    icon = models.CharField(max_length=50, blank=True, verbose_name=_("أيقونة"))
    color = models.CharField(max_length=7, default='#3b82f6', verbose_name=_("اللون"))
    
    # الإعدادات
    ideal_for = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("مناسب لـ"),
        help_text=_('مثال: ["النوم على الظهر", "آلام الظهر", "الأطفال"]')
    )
    benefits = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("الفوائد"),
        help_text=_('مثال: ["راحة فائقة", "دعم العمود الفقري"]')
    )
    
    # سعر إضافي (اختياري)
    extra_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0'),
        verbose_name=_("سعر إضافي"),
        help_text=_("سعر إضافي لهذا الإحساس إن وجد")
    )
    
    # قواعد الحساب التلقائي
    auto_detect_rules = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("قواعد الكشف التلقائي"),
        help_text=_('JSON: {"min_density": 30, "max_density": 50, "required_categories": ["foam","springs"]}')
    )
    
    is_active = models.BooleanField(default=True, verbose_name=_("مفعل"))
    sort_order = models.PositiveIntegerField(default=0, verbose_name=_("ترتيب العرض"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("نوع إحساس المرتبة")
        verbose_name_plural = _("أنواع إحساس المرتبة")
        ordering = ['firmness_score', 'sort_order']
    
    def __str__(self):
        return f"{self.name} ({self.get_firmness_level_display()})"


class AIRecommendationConfig(models.Model):
    """إعدادات اقتراحات الذكاء الاصطناعي - قواعد ذكية بدون ربط خارجي"""
    TRIGGER_TYPES = [
        ('on_size_select', _('عند اختيار المقاس')),
        ('on_component_add', _('عند إضافة مكون')),
        ('on_component_remove', _('عند إزالة مكون')),
        ('on_budget_exceed', _('عند تجاوز الميزانية')),
        ('on_category_complete', _('عند اكتمال فئة')),
        ('on_feeling_mismatch', _('عند عدم تطابق الإحساس')),
        ('on_thickness_threshold', _('عند تجاوز حد السماكة')),
        ('always', _('دائماً')),
    ]
    
    SUGGESTION_TYPES = [
        ('add_component', _('اقتراح إضافة مكون')),
        ('remove_component', _('اقتراح إزالة مكون')),
        ('upgrade_component', _('اقتراح ترقية مكون')),
        ('change_size', _('اقتراح تغيير المقاس')),
        ('suggest_feeling', _('اقتراح إحساس المرتبة')),
        ('cost_saving', _('اقتراح توفير')),
        ('quality_tip', _('نصيحة جودة')),
        ('health_tip', _('نصيحة صحية')),
        ('custom_message', _('رسالة مخصصة')),
    ]
    
    name = models.CharField(max_length=200, verbose_name=_("اسم الاقتراح"))
    description = models.TextField(blank=True, verbose_name=_("الوصف"))
    
    # المحفز
    trigger_type = models.CharField(
        max_length=30,
        choices=TRIGGER_TYPES,
        verbose_name=_("نوع المحفز")
    )
    trigger_conditions = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("شروط التفعيل"),
        help_text=_('''JSON مثال: {
            "component_category": "foam",
            "min_price": 2000,
            "max_thickness": 30,
            "selected_components_count": 3,
            "feeling_score_range": [1, 4]
        }''')
    )
    
    # الاقتراح
    suggestion_type = models.CharField(
        max_length=30,
        choices=SUGGESTION_TYPES,
        verbose_name=_("نوع الاقتراح")
    )
    suggestion_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("بيانات الاقتراح"),
        help_text=_('''JSON مثال: {
            "component_id": 5,
            "message": "جرب إضافة طبقة ميموري فوم",
            "discount_hint": "وفر 15% مع هذا البديل"
        }''')
    )
    
    # الرسالة
    message_ar = models.TextField(verbose_name=_("الرسالة بالعربية"))
    message_en = models.TextField(blank=True, verbose_name=_("الرسالة بالإنجليزية"))
    icon = models.CharField(max_length=50, default='bi bi-lightbulb', verbose_name=_("أيقونة"))
    message_style = models.CharField(
        max_length=20,
        choices=[
            ('info', _('معلومة 💡')),
            ('tip', _('نصيحة 🎯')),
            ('upgrade', _('ترقية ⬆️')),
            ('warning', _('تحذير ⚠️')),
            ('success', _('ممتاز ✅')),
            ('savings', _('توفير 💰')),
            ('health', _('صحي 🏥')),
        ],
        default='tip',
        verbose_name=_("نمط الرسالة")
    )
    
    # الأولوية
    priority = models.PositiveIntegerField(
        default=50,
        verbose_name=_("الأولوية"),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_("0-100، الأعلى يظهر أولاً")
    )
    
    # المكون المقترح (اختياري)
    suggested_component = models.ForeignKey(
        'MattressComponent',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ai_recommendations',
        verbose_name=_("المكون المقترح")
    )
    suggested_feeling = models.ForeignKey(
        MattressFeelingType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ai_recommendations',
        verbose_name=_("الإحساس المقترح")
    )
    
    is_active = models.BooleanField(default=True, verbose_name=_("مفعل"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("اقتراح ذكاء اصطناعي")
        verbose_name_plural = _("اقتراحات الذكاء الاصطناعي")
        ordering = ['-priority', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_trigger_type_display()})"
    
    def evaluate(self, design_context):
        """تقييم هل يجب عرض هذا الاقتراح بناءً على السياق"""
        conditions = self.trigger_conditions
        if not conditions:
            return True
        
        # فحص الشروط
        selected_components = design_context.get('selected_components', [])
        selected_categories = design_context.get('selected_categories', [])
        total_price = design_context.get('total_price', 0)
        total_thickness = design_context.get('total_thickness', 0)
        feeling_score = design_context.get('feeling_score', 5)
        size_id = design_context.get('size_id')
        
        # فحص الفئة
        if 'component_category' in conditions:
            if conditions['component_category'] not in selected_categories:
                return False
        
        # فحص السعر
        if 'min_price' in conditions and total_price < conditions['min_price']:
            return False
        if 'max_price' in conditions and total_price > conditions['max_price']:
            return False
        
        # فحص السماكة
        if 'max_thickness' in conditions and total_thickness > conditions['max_thickness']:
            return True  # تنبيه تجاوز
        if 'min_thickness' in conditions and total_thickness < conditions['min_thickness']:
            return True
        
        # فحص عدد المكونات
        if 'selected_components_count' in conditions:
            if len(selected_components) < conditions['selected_components_count']:
                return False
        
        # فحص نطاق الإحساس
        if 'feeling_score_range' in conditions:
            fr = conditions['feeling_score_range']
            if not (fr[0] <= feeling_score <= fr[1]):
                return False
        
        # فحص المقاس
        if 'size_id' in conditions and size_id != conditions['size_id']:
            return False
        
        return True


class MattressSize(models.Model):
    """أحجام المراتب المتاحة"""
    name = models.CharField(max_length=100, verbose_name=_("اسم الحجم"))
    name_en = models.CharField(max_length=100, verbose_name=_("الاسم بالإنجليزية"), blank=True)
    width = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        verbose_name=_("العرض (سم)")
    )
    length = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        verbose_name=_("الطول (سم)")
    )
    height_default = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        default=Decimal('25'),
        verbose_name=_("الارتفاع الافتراضي (سم)")
    )
    price_multiplier = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('1.0'),
        verbose_name=_("معامل السعر"),
        help_text=_("يضرب في السعر الأساسي")
    )
    base_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0'),
        verbose_name=_("السعر الأساسي")
    )
    is_active = models.BooleanField(default=True, verbose_name=_("مفعل"))
    sort_order = models.PositiveIntegerField(default=0, verbose_name=_("ترتيب العرض"))
    image = models.ImageField(
        upload_to='mattress_builder/sizes/', 
        blank=True, 
        null=True, 
        verbose_name=_("صورة توضيحية")
    )
    icon = models.CharField(
        max_length=50, 
        blank=True,
        verbose_name=_("أيقونة"),
        help_text=_("مثل: fa-bed, fa-user, etc")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("حجم المرتبة")
        verbose_name_plural = _("أحجام المراتب")
        ordering = ['sort_order', 'width']
    
    def __str__(self):
        return f"{self.name} ({self.width}×{self.length} سم)"
    
    @property
    def area(self):
        """حساب المساحة"""
        return self.width * self.length / 10000  # متر مربع
    
    @property
    def display_dimensions(self):
        """عرض الأبعاد بشكل مناسب"""
        return f"{self.width} × {self.length} سم"


class MattressComponentCategory(models.Model):
    """فئات مكونات المراتب"""
    CATEGORY_TYPES = [
        ('springs', _('السوست')),
        ('foam', _('الإسفنج')),
        ('fabric', _('القماش الخارجي')),
        ('padding', _('الحشوات')),
        ('comfort', _('طبقات الراحة')),
        ('cooling', _('أنظمة التبريد')),
        ('support', _('طبقات الدعم')),
        ('base', _('القاعدة')),
        ('extras', _('إضافات')),
    ]
    
    name = models.CharField(max_length=100, verbose_name=_("اسم الفئة"))
    name_en = models.CharField(max_length=100, verbose_name=_("الاسم بالإنجليزية"), blank=True)
    category_type = models.CharField(
        max_length=20, 
        choices=CATEGORY_TYPES, 
        verbose_name=_("نوع الفئة")
    )
    description = models.TextField(blank=True, verbose_name=_("الوصف"))
    icon = models.CharField(max_length=50, blank=True, verbose_name=_("أيقونة"))
    color = models.CharField(
        max_length=7, 
        default='#3b82f6',
        verbose_name=_("اللون"),
        help_text=_("كود اللون الهيكس")
    )
    layer_order = models.PositiveIntegerField(
        default=0, 
        verbose_name=_("ترتيب الطبقة"),
        help_text=_("من الأسفل للأعلى: 1=قاعدة، 5=سطح")
    )
    is_required = models.BooleanField(
        default=False, 
        verbose_name=_("مطلوب"),
        help_text=_("هل يجب اختيار مكون من هذه الفئة؟")
    )
    max_selections = models.PositiveIntegerField(
        default=1, 
        verbose_name=_("الحد الأقصى للاختيارات"),
        help_text=_("عدد المكونات التي يمكن اختيارها من هذه الفئة")
    )
    is_active = models.BooleanField(default=True, verbose_name=_("مفعلة"))
    sort_order = models.PositiveIntegerField(default=0, verbose_name=_("ترتيب العرض"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("فئة المكونات")
        verbose_name_plural = _("فئات المكونات")
        ordering = ['sort_order', 'layer_order']
    
    def __str__(self):
        return self.name


class MattressComponent(models.Model):
    """المكونات الفعلية للمراتب"""
    QUALITY_LEVELS = [
        ('basic', _('أساسي')),
        ('standard', _('قياسي')),
        ('premium', _('ممتاز')),
        ('luxury', _('فاخر')),
    ]
    
    category = models.ForeignKey(
        MattressComponentCategory, 
        on_delete=models.CASCADE, 
        related_name='components',
        verbose_name=_("الفئة")
    )
    name = models.CharField(max_length=200, verbose_name=_("اسم المكون"))
    name_en = models.CharField(max_length=200, verbose_name=_("الاسم بالإنجليزية"), blank=True)
    description = models.TextField(blank=True, verbose_name=_("الوصف"))
    short_description = models.CharField(
        max_length=255, 
        blank=True, 
        verbose_name=_("وصف مختصر")
    )
    
    # التسعير
    base_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0'),
        verbose_name=_("السعر الأساسي")
    )
    price_per_sqm = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0'),
        verbose_name=_("السعر لكل متر مربع"),
        help_text=_("إذا كان السعر يعتمد على المساحة")
    )
    pricing_type = models.CharField(
        max_length=20,
        choices=[
            ('fixed', _('ثابت')),
            ('per_sqm', _('حسب المساحة')),
            ('both', _('ثابت + حسب المساحة')),
        ],
        default='fixed',
        verbose_name=_("نوع التسعير")
    )
    
    # المواصفات
    quality_level = models.CharField(
        max_length=20, 
        choices=QUALITY_LEVELS, 
        default='standard',
        verbose_name=_("مستوى الجودة")
    )
    thickness = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name=_("السماكة (سم)")
    )
    density = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name=_("الكثافة (كجم/م³)")
    )
    specifications = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("المواصفات التفصيلية"),
        help_text=_("JSON: {\"hardness\": \"medium\", \"warranty\": \"10 years\"}")
    )
    
    # الوسائط
    image = models.ImageField(
        upload_to='mattress_builder/components/', 
        blank=True, 
        null=True,
        verbose_name=_("الصورة")
    )
    icon = models.CharField(max_length=50, blank=True, verbose_name=_("أيقونة"))
    texture_pattern = models.CharField(
        max_length=50, 
        blank=True,
        verbose_name=_("نمط الملمس"),
        help_text=_("للعرض المرئي: dots, lines, waves, etc")
    )
    
    # ربط بالمخزون (اختياري)
    inventory_product = models.ForeignKey(
        'inventory.Product',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mattress_components',
        verbose_name=_("المنتج في المخزون")
    )
    
    # التوافق والقواعد
    compatible_with = models.ManyToManyField(
        'self',
        blank=True,
        symmetrical=False,
        related_name='compatible_components',
        verbose_name=_("متوافق مع")
    )
    incompatible_with = models.ManyToManyField(
        'self',
        blank=True,
        symmetrical=False,
        related_name='incompatible_components',
        verbose_name=_("غير متوافق مع")
    )
    
    # الحالة
    is_active = models.BooleanField(default=True, verbose_name=_("مفعل"))
    is_featured = models.BooleanField(default=False, verbose_name=_("مميز"))
    is_popular = models.BooleanField(default=False, verbose_name=_("شائع"))
    popularity_score = models.PositiveIntegerField(
        default=0, 
        verbose_name=_("درجة الشعبية"),
        help_text=_("يزيد تلقائياً مع كل اختيار")
    )
    sort_order = models.PositiveIntegerField(default=0, verbose_name=_("ترتيب العرض"))
    
    # الفوائد (للعرض)
    benefits = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("الفوائد"),
        help_text=_("مصفوفة من الفوائد مثل: [\"راحة فائقة\", \"دعم للظهر\"]")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("مكون المرتبة")
        verbose_name_plural = _("مكونات المراتب")
        ordering = ['category__sort_order', 'sort_order', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.category.name})"
    
    def calculate_price(self, mattress_size):
        """حساب السعر بناءً على الحجم"""
        if self.pricing_type == 'fixed':
            return self.base_price
        elif self.pricing_type == 'per_sqm':
            return self.price_per_sqm * mattress_size.area
        else:  # both
            return self.base_price + (self.price_per_sqm * mattress_size.area)
    
    def increment_popularity(self):
        """زيادة درجة الشعبية"""
        self.popularity_score += 1
        self.save(update_fields=['popularity_score'])


class MattressRecommendationRule(models.Model):
    """قواعد الاقتراحات الذكية"""
    CONDITION_TYPES = [
        ('component_selected', _('عند اختيار مكون معين')),
        ('budget_range', _('نطاق الميزانية')),
        ('quality_preference', _('تفضيل الجودة')),
        ('size_selected', _('عند اختيار حجم معين')),
        ('total_price', _('السعر الإجمالي')),
    ]
    
    ACTION_TYPES = [
        ('suggest_component', _('اقتراح مكون')),
        ('suggest_upgrade', _('اقتراح ترقية')),
        ('suggest_bundle', _('اقتراح حزمة')),
        ('show_message', _('عرض رسالة')),
    ]
    
    name = models.CharField(max_length=200, verbose_name=_("اسم القاعدة"))
    description = models.TextField(blank=True, verbose_name=_("الوصف"))
    
    # الشروط
    condition_type = models.CharField(
        max_length=30, 
        choices=CONDITION_TYPES,
        verbose_name=_("نوع الشرط")
    )
    condition_data = models.JSONField(
        default=dict,
        verbose_name=_("بيانات الشرط"),
        help_text=_("JSON: {\"component_id\": 5, \"min_price\": 2000}")
    )
    
    # الإجراء
    action_type = models.CharField(
        max_length=30, 
        choices=ACTION_TYPES,
        verbose_name=_("نوع الإجراء")
    )
    action_data = models.JSONField(
        default=dict,
        verbose_name=_("بيانات الإجراء"),
        help_text=_("JSON: {\"component_id\": 10, \"message\": \"جرب هذا!\"}")
    )
    
    # الرسالة المعروضة
    message = models.TextField(
        blank=True,
        verbose_name=_("الرسالة"),
        help_text=_("الرسالة التي تظهر للعميل")
    )
    message_type = models.CharField(
        max_length=20,
        choices=[
            ('info', _('معلومة')),
            ('tip', _('نصيحة')),
            ('upgrade', _('ترقية')),
            ('warning', _('تحذير')),
        ],
        default='tip',
        verbose_name=_("نوع الرسالة")
    )
    
    # الأولوية
    priority = models.PositiveIntegerField(
        default=50, 
        verbose_name=_("الأولوية"),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_("0-100، الأعلى يظهر أولاً")
    )
    
    # الحالة
    is_active = models.BooleanField(default=True, verbose_name=_("مفعلة"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("قاعدة الاقتراح")
        verbose_name_plural = _("قواعد الاقتراحات")
        ordering = ['-priority', 'name']
    
    def __str__(self):
        return self.name
    
    def check_condition(self, design_data):
        """فحص إذا كان الشرط متحقق"""
        # TODO: تنفيذ منطق الفحص
        return True
    
    def execute_action(self, design_data):
        """تنفيذ الإجراء"""
        # TODO: تنفيذ منطق الإجراء
        return self.action_data


class CustomMattressDesign(models.Model):
    """تصميمات المراتب المخصصة من العملاء"""
    STATUS_CHOICES = [
        ('draft', _('مسودة')),
        ('pending_approval', _('في انتظار الموافقة')),
        ('approved', _('موافق عليه')),
        ('rejected', _('مرفوض')),
        ('in_production', _('تحت الإنتاج')),
        ('completed', _('مكتمل')),
        ('cancelled', _('ملغي')),
    ]
    
    # معلومات العميل
    customer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='mattress_designs',
        verbose_name=_("العميل")
    )
    customer_name = models.CharField(
        max_length=200, 
        blank=True,
        verbose_name=_("اسم العميل"),
        help_text=_("يتم ملؤه تلقائياً من بيانات المستخدم")
    )
    customer_phone = models.CharField(max_length=20, blank=True, verbose_name=_("رقم الهاتف"))
    customer_email = models.EmailField(blank=True, verbose_name=_("البريد الإلكتروني"))
    
    # التصميم
    design_name = models.CharField(
        max_length=200, 
        verbose_name=_("اسم التصميم"),
        help_text=_("اسم اختياري للتصميم")
    )
    published_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_("الاسم المنشور"),
        help_text=_("الاسم الذي يظهر للعملاء الآخرين عند نشر التصميم")
    )
    design_hash = models.CharField(
        max_length=64,
        blank=True,
        db_index=True,
        verbose_name=_("بصمة التصميم"),
        help_text=_("Hash فريد للكشف عن التصميمات المتكررة")
    )
    is_public = models.BooleanField(
        default=False,
        verbose_name=_("منشور للجمهور"),
        help_text=_("هل يمكن للعملاء الآخرين شراء هذا التصميم؟")
    )
    sales_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_("عدد مرات البيع")
    )
    designer_commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('10'),
        verbose_name=_("نسبة عمولة المصمم %"),
        help_text=_("النسبة المئوية التي يحصل عليها المصمم عند بيع تصميمه")
    )
    mattress_size = models.ForeignKey(
        MattressSize,
        on_delete=models.PROTECT,
        related_name='designs',
        verbose_name=_("حجم المرتبة")
    )
    selected_components = models.ManyToManyField(
        MattressComponent,
        through='DesignComponent',
        related_name='designs',
        verbose_name=_("المكونات المختارة")
    )
    
    # إحساس المرتبة
    feeling_type = models.ForeignKey(
        MattressFeelingType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='designs',
        verbose_name=_("إحساس المرتبة")
    )
    feeling_auto_detected = models.BooleanField(
        default=False,
        verbose_name=_("تم الكشف تلقائياً"),
        help_text=_("هل تم تحديد الإحساس تلقائياً بناءً على المكونات؟")
    )
    feeling_score = models.PositiveIntegerField(
        default=5,
        verbose_name=_("درجة الإحساس"),
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text=_("1=ناعم جداً، 10=صلب جداً")
    )
    
    # التفاصيل
    design_data = models.JSONField(
        default=dict,
        verbose_name=_("بيانات التصميم الكاملة"),
        help_text=_("JSON كامل للتصميم مع جميع الخيارات")
    )
    notes = models.TextField(blank=True, verbose_name=_("ملاحظات العميل"))
    admin_notes = models.TextField(blank=True, verbose_name=_("ملاحظات الإدارة"))
    
    # التسعير
    base_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0'),
        verbose_name=_("السعر الأساسي")
    )
    components_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0'),
        verbose_name=_("سعر المكونات")
    )
    discount_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0'),
        verbose_name=_("قيمة الخصم")
    )
    final_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0'),
        verbose_name=_("السعر النهائي")
    )
    
    # الحالة
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='draft',
        verbose_name=_("الحالة")
    )
    
    # الموافقة
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_designs',
        verbose_name=_("تمت الموافقة بواسطة")
    )
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name=_("تاريخ الموافقة"))
    rejection_reason = models.TextField(blank=True, verbose_name=_("سبب الرفض"))
    
    # الإنتاج
    production_order = models.ForeignKey(
        'production.ProductionOrder',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='custom_designs',
        verbose_name=_("أمر الإنتاج")
    )
    estimated_production_days = models.PositiveIntegerField(
        default=7,
        verbose_name=_("مدة الإنتاج المقدرة (أيام)")
    )
    
    # الصور
    preview_image = models.ImageField(
        upload_to='mattress_builder/designs/', 
        blank=True, 
        null=True,
        verbose_name=_("صورة المعاينة")
    )
    
    # التتبع
    view_count = models.PositiveIntegerField(default=0, verbose_name=_("عدد المشاهدات"))
    is_template = models.BooleanField(
        default=False, 
        verbose_name=_("حفظ كقالب"),
        help_text=_("هل يمكن استخدام هذا التصميم كقالب؟")
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاريخ الإنشاء"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("آخر تحديث"))
    submitted_at = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name=_("تاريخ الإرسال للموافقة")
    )
    
    class Meta:
        verbose_name = _("تصميم مرتبة مخصص")
        verbose_name_plural = _("تصميمات المراتب المخصصة")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['customer', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.design_name} - {self.customer.get_full_name() or self.customer.username}"
    
    def generate_design_hash(self):
        """توليد بصمة فريدة للتصميم بناءً على المقاس والمكونات والإحساس"""
        components = list(
            self.design_components.order_by('component_id')
            .values_list('component_id', 'quantity')
        )
        hash_data = {
            'size_id': self.mattress_size_id,
            'components': components,
            'feeling_id': self.feeling_type_id,
        }
        hash_str = json.dumps(hash_data, sort_keys=True)
        return hashlib.sha256(hash_str.encode()).hexdigest()
    
    def find_duplicate_designs(self):
        """البحث عن تصميمات مطابقة موجودة ومنشورة"""
        if not self.design_hash:
            self.design_hash = self.generate_design_hash()
        duplicates = CustomMattressDesign.objects.filter(
            design_hash=self.design_hash,
            is_public=True,
            status__in=['approved', 'completed', 'in_production'],
        ).exclude(pk=self.pk)
        return duplicates
    
    def calculate_total_price(self):
        """حساب السعر الإجمالي"""
        components_total = Decimal('0')
        
        # حساب سعر الحجم
        size_price = self.mattress_size.base_price
        
        # حساب سعر المكونات
        for design_component in self.design_components.all():
            component_price = design_component.component.calculate_price(self.mattress_size)
            components_total += component_price * design_component.quantity
        
        # إضافة سعر الإحساس
        feeling_price = Decimal('0')
        if self.feeling_type:
            feeling_price = self.feeling_type.extra_price or Decimal('0')
        
        # الحساب النهائي
        subtotal = size_price + components_total + feeling_price
        total = subtotal - self.discount_amount
        
        # تحديث الحقول
        self.base_price = size_price
        self.components_price = components_total
        self.final_price = total
        
        return total
    
    def submit_for_approval(self):
        """إرسال التصميم للموافقة"""
        from django.utils import timezone
        self.status = 'pending_approval'
        self.submitted_at = timezone.now()
        self.calculate_total_price()
        self.save()
    
    def approve(self, user):
        """الموافقة على التصميم"""
        from django.utils import timezone
        self.status = 'approved'
        self.approved_by = user
        self.approved_at = timezone.now()
        self.save()
    
    def reject(self, reason, user):
        """رفض التصميم"""
        self.status = 'rejected'
        self.rejection_reason = reason
        self.approved_by = user
        self.save()
    
    def auto_detect_feeling(self):
        """كشف إحساس المرتبة تلقائياً بناءً على المكونات المختارة"""
        from .models import MattressFeelingType
        
        # حساب متوسط الكثافة والسماكة
        components = self.design_components.select_related('component', 'component__category').all()
        if not components.exists():
            return None
        
        total_density = Decimal('0')
        density_count = 0
        total_thickness = Decimal('0')
        category_types = set()
        quality_scores = {'basic': 1, 'standard': 2, 'premium': 3, 'luxury': 4}
        total_quality = 0
        quality_count = 0
        
        for dc in components:
            comp = dc.component
            if comp.density:
                total_density += comp.density
                density_count += 1
            if comp.thickness:
                total_thickness += comp.thickness
            category_types.add(comp.category.category_type)
            total_quality += quality_scores.get(comp.quality_level, 2)
            quality_count += 1
        
        avg_density = total_density / density_count if density_count > 0 else Decimal('40')
        avg_quality = total_quality / quality_count if quality_count > 0 else 2
        
        # حساب درجة الصلابة (1-10)
        firmness = 5  # افتراضي متوسط
        if avg_density < 25:
            firmness = 2
        elif avg_density < 35:
            firmness = 3
        elif avg_density < 45:
            firmness = 5
        elif avg_density < 55:
            firmness = 7
        elif avg_density < 65:
            firmness = 8
        else:
            firmness = 9
        
        # تعديل بناءً على السوست
        if 'springs' in category_types:
            firmness = min(10, firmness + 1)
        
        # البحث عن أقرب إحساس
        feelings = MattressFeelingType.objects.filter(is_active=True)
        closest = None
        min_diff = 11
        for f in feelings:
            diff = abs(f.firmness_score - firmness)
            if diff < min_diff:
                min_diff = diff
                closest = f
        
        if closest:
            self.feeling_type = closest
            self.feeling_auto_detected = True
            self.feeling_score = firmness
            self.save(update_fields=['feeling_type', 'feeling_auto_detected', 'feeling_score'])
        
        return closest


class DesignComponent(models.Model):
    """جدول وسيط للمكونات المختارة في التصميم"""
    design = models.ForeignKey(
        CustomMattressDesign,
        on_delete=models.CASCADE,
        related_name='design_components',
        verbose_name=_("التصميم")
    )
    component = models.ForeignKey(
        MattressComponent,
        on_delete=models.PROTECT,
        verbose_name=_("المكون")
    )
    quantity = models.PositiveIntegerField(
        default=1,
        verbose_name=_("الكمية")
    )
    layer_position = models.PositiveIntegerField(
        default=0,
        verbose_name=_("موضع الطبقة"),
        help_text=_("ترتيب الطبقة في التصميم")
    )
    custom_specifications = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("مواصفات مخصصة"),
        help_text=_("تخصيصات إضافية لهذا المكون")
    )
    price_at_selection = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("السعر وقت الاختيار"),
        help_text=_("سعر المكون وقت اختياره (لحفظ السعر)")
    )
    
    class Meta:
        verbose_name = _("مكون التصميم")
        verbose_name_plural = _("مكونات التصميم")
        ordering = ['layer_position']
        unique_together = ['design', 'component', 'layer_position']
    
    def __str__(self):
        return f"{self.component.name} في {self.design.design_name}"
    
    def save(self, *args, **kwargs):
        # حفظ السعر وقت الاختيار
        if not self.price_at_selection:
            self.price_at_selection = self.component.calculate_price(self.design.mattress_size)
        super().save(*args, **kwargs)


class MattressTemplate(models.Model):
    """قوالب المراتب الجاهزة (تصميمات شائعة)"""
    name = models.CharField(max_length=200, verbose_name=_("اسم القالب"))
    name_en = models.CharField(max_length=200, verbose_name=_("الاسم بالإنجليزية"), blank=True)
    description = models.TextField(verbose_name=_("الوصف"))
    short_description = models.CharField(max_length=255, blank=True, verbose_name=_("وصف مختصر"))
    
    # التصميم
    base_design = models.ForeignKey(
        CustomMattressDesign,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='templates',
        verbose_name=_("التصميم الأساسي")
    )
    template_data = models.JSONField(
        default=dict,
        verbose_name=_("بيانات القالب"),
        help_text=_("المكونات والإعدادات الافتراضية")
    )
    
    # الفئة المستهدفة
    target_audience = models.CharField(
        max_length=50,
        choices=[
            ('comfort', _('الراحة')),
            ('support', _('الدعم')),
            ('luxury', _('الفخامة')),
            ('budget', _('اقتصادي')),
            ('medical', _('طبي')),
            ('kids', _('للأطفال')),
        ],
        default='comfort',
        verbose_name=_("الفئة المستهدفة")
    )
    
    # التسعير
    starting_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("السعر ابتداءً من")
    )
    discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0'),
        verbose_name=_("نسبة الخصم %"),
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    # الوسائط
    image = models.ImageField(
        upload_to='mattress_builder/templates/',
        verbose_name=_("الصورة")
    )
    icon = models.CharField(max_length=50, blank=True, verbose_name=_("أيقونة"))
    
    # الميزات
    features = models.JSONField(
        default=list,
        verbose_name=_("الميزات"),
        help_text=_("قائمة بميزات هذا القالب")
    )
    
    # الحالة
    is_active = models.BooleanField(default=True, verbose_name=_("مفعل"))
    is_featured = models.BooleanField(default=False, verbose_name=_("مميز"))
    is_popular = models.BooleanField(default=False, verbose_name=_("شائع"))
    usage_count = models.PositiveIntegerField(default=0, verbose_name=_("عدد الاستخدامات"))
    sort_order = models.PositiveIntegerField(default=0, verbose_name=_("ترتيب العرض"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("قالب مرتبة")
        verbose_name_plural = _("قوالب المراتب")
        ordering = ['sort_order', '-is_featured', 'name']
    
    def __str__(self):
        return self.name
    
    def increment_usage(self):
        """زيادة عداد الاستخدام"""
        self.usage_count += 1
        self.save(update_fields=['usage_count'])


class BuilderSettings(models.Model):
    """إعدادات نظام بناء المراتب"""
    profit_margin_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('25'),
        verbose_name=_("هامش الربح الافتراضي %"),
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    auto_approval_threshold = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('5000'),
        verbose_name=_("حد الموافقة التلقائية"),
        help_text=_("الطلبات الأقل من هذا المبلغ توافق تلقائياً")
    )
    enable_auto_approval = models.BooleanField(
        default=False,
        verbose_name=_("تفعيل الموافقة التلقائية")
    )
    estimated_production_days = models.PositiveIntegerField(
        default=7,
        verbose_name=_("مدة الإنتاج المقدرة (أيام)")
    )
    max_designs_per_customer = models.PositiveIntegerField(
        default=10,
        verbose_name=_("الحد الأقصى للتصميمات لكل عميل")
    )
    enable_recommendations = models.BooleanField(
        default=True,
        verbose_name=_("تفعيل نظام الاقتراحات")
    )
    enable_gamification = models.BooleanField(
        default=True,
        verbose_name=_("تفعيل عناصر اللعب")
    )
    enable_ai_suggestions = models.BooleanField(
        default=True,
        verbose_name=_("تفعيل اقتراحات الذكاء الاصطناعي")
    )
    enable_feeling_detection = models.BooleanField(
        default=True,
        verbose_name=_("تفعيل كشف الإحساس التلقائي")
    )
    enable_feeling_selection = models.BooleanField(
        default=True,
        verbose_name=_("تفعيل اختيار الإحساس يدوياً")
    )
    max_ai_suggestions = models.PositiveIntegerField(
        default=5,
        verbose_name=_("الحد الأقصى للاقتراحات")
    )
    welcome_message = models.TextField(
        default="صمم مرتبتك الخاصة خطوة بخطوة!",
        verbose_name=_("رسالة الترحيب")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("إعدادات نظام البناء")
        verbose_name_plural = _("إعدادات نظام البناء")
    
    def __str__(self):
        return "إعدادات نظام بناء المراتب"
    
    designer_commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('10'),
        verbose_name=_("نسبة عمولة المصمم الافتراضية %"),
        help_text=_("النسبة المئوية التي يحصل عليها مصمم المرتبة عند بيع تصميمه")
    )
    enable_community_designs = models.BooleanField(
        default=True,
        verbose_name=_("تفعيل تصميمات المجتمع"),
        help_text=_("السماح للعملاء بنشر تصميماتهم وبيعها")
    )
    enable_duplicate_detection = models.BooleanField(
        default=True,
        verbose_name=_("تفعيل كشف التصميمات المكررة"),
        help_text=_("إخطار العميل إذا كان تصميمه موجود مسبقاً")
    )
    
    @classmethod
    def get_settings(cls):
        """الحصول على الإعدادات"""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings


class MattressOrder(models.Model):
    """طلبات شراء المراتب المخصصة"""
    STATUS_CHOICES = [
        ('pending_payment', _('في انتظار الدفع')),
        ('paid', _('مدفوع')),
        ('in_production', _('قيد الإنتاج')),
        ('quality_check', _('فحص الجودة')),
        ('ready', _('جاهز للتسليم')),
        ('shipped', _('تم الشحن')),
        ('delivered', _('تم التسليم')),
        ('cancelled', _('ملغي')),
        ('refunded', _('مسترجع')),
    ]
    
    PAYMENT_METHODS = [
        ('cash', _('كاش')),
        ('visa', _('فيزا')),
        ('instapay', _('إنستاباي')),
        ('vodafone_cash', _('فودافون كاش')),
        ('bank_transfer', _('تحويل بنكي')),
        ('online', _('دفع إلكتروني')),
    ]
    
    # رقم الطلب
    order_number = models.CharField(
        max_length=50, unique=True,
        verbose_name=_("رقم الطلب")
    )
    
    # العميل (المشتري)
    customer = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='mattress_orders',
        verbose_name=_("العميل")
    )
    
    # التصميم
    design = models.ForeignKey(
        CustomMattressDesign,
        on_delete=models.PROTECT,
        related_name='orders',
        verbose_name=_("التصميم")
    )
    
    # هل الشراء من تصميم عميل آخر (تصميمات المجتمع)
    is_community_purchase = models.BooleanField(
        default=False,
        verbose_name=_("شراء تصميم مجتمعي"),
        help_text=_("هل تم شراء هذا التصميم من تصميمات عملاء آخرين")
    )
    original_designer = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='designs_sold',
        verbose_name=_("المصمم الأصلي")
    )
    
    # بيانات العميل
    customer_name = models.CharField(max_length=200, verbose_name=_("اسم العميل"))
    customer_phone = models.CharField(max_length=20, verbose_name=_("رقم الهاتف"))
    customer_email = models.EmailField(blank=True, verbose_name=_("البريد الإلكتروني"))
    shipping_address = models.TextField(verbose_name=_("عنوان التسليم"))
    shipping_city = models.CharField(max_length=100, default='القاهرة', verbose_name=_("المدينة"))
    
    # المبالغ
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'), verbose_name=_("المجموع الفرعي"))
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'), verbose_name=_("تكلفة الشحن"))
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'), verbose_name=_("الخصم"))
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'), verbose_name=_("الضريبة"))
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'), verbose_name=_("الإجمالي"))
    
    # الدفع
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending_payment', verbose_name=_("الحالة"))
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, blank=True, verbose_name=_("طريقة الدفع"))
    payment_reference = models.CharField(max_length=200, blank=True, verbose_name=_("مرجع الدفع"))
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name=_("تاريخ الدفع"))
    
    # الإنتاج
    production_order = models.ForeignKey(
        'production.ProductionOrder',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='mattress_orders',
        verbose_name=_("أمر الإنتاج")
    )
    estimated_delivery_date = models.DateField(null=True, blank=True, verbose_name=_("تاريخ التسليم المتوقع"))
    actual_delivery_date = models.DateField(null=True, blank=True, verbose_name=_("تاريخ التسليم الفعلي"))
    
    # المحاسبة
    journal_entry = models.ForeignKey(
        'accounting.JournalEntry',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='mattress_orders',
        verbose_name=_("القيد المحاسبي")
    )
    
    # ملاحظات
    customer_notes = models.TextField(blank=True, verbose_name=_("ملاحظات العميل"))
    admin_notes = models.TextField(blank=True, verbose_name=_("ملاحظات الإدارة"))
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاريخ الإنشاء"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("آخر تحديث"))
    
    class Meta:
        verbose_name = _("طلب مرتبة")
        verbose_name_plural = _("طلبات المراتب")
        ordering = ['-created_at']
    
    def __str__(self):
        return f"طلب مرتبة #{self.order_number} - {self.customer_name}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            year = timezone.now().strftime('%Y')
            count = MattressOrder.objects.filter(
                order_number__startswith=f'MO-{year}'
            ).count() + 1
            self.order_number = f'MO-{year}-{count:06d}'
        super().save(*args, **kwargs)
    
    def mark_as_paid(self, payment_method='', payment_reference=''):
        """تأكيد الدفع وإنشاء القيد المحاسبي وأمر الإنتاج"""
        self.status = 'paid'
        self.payment_method = payment_method
        self.payment_reference = payment_reference
        self.paid_at = timezone.now()
        self.save()
        
        # تحديث حالة التصميم
        if self.design.status in ['draft', 'pending_approval', 'approved']:
            self.design.status = 'approved'
            self.design.save(update_fields=['status'])
        
        # إنشاء القيد المحاسبي
        self._create_journal_entry()
        
        # إنشاء أمر الإنتاج
        self._create_production_order()
        
        # عمولة المصمم (إذا كان تصميم مجتمعي)
        if self.is_community_purchase and self.original_designer:
            self._create_designer_commission()
    
    def _create_journal_entry(self):
        """إنشاء قيد محاسبي للبيع"""
        try:
            from accounting.models import JournalEntry, JournalEntryItem, Account
            
            # البحث عن الحسابات
            cash_account = Account.objects.filter(
                account_type='asset', name__icontains='صندوق'
            ).first() or Account.objects.filter(
                account_type='asset', code__startswith='1'
            ).first()
            
            revenue_account = Account.objects.filter(
                account_type='revenue', name__icontains='مبيعات'
            ).first() or Account.objects.filter(
                account_type='revenue'
            ).first()
            
            if not cash_account or not revenue_account:
                return None
            
            entry = JournalEntry.objects.create(
                date=timezone.now().date(),
                description=f'بيع مرتبة مخصصة - طلب #{self.order_number} - {self.customer_name}',
                entry_type='sales',
                reference=f'MO-{self.order_number}',
                is_posted=True,
                created_by=self.customer,
            )
            
            # مدين: النقدية/البنك
            JournalEntryItem.objects.create(
                journal_entry=entry,
                account=cash_account,
                type='debit',
                amount=self.total,
                description=f'بيع مرتبة مخصصة #{self.order_number}',
            )
            
            # دائن: إيراد المبيعات
            JournalEntryItem.objects.create(
                journal_entry=entry,
                account=revenue_account,
                type='credit',
                amount=self.total,
                description=f'إيراد بيع مرتبة مخصصة #{self.order_number}',
            )
            
            self.journal_entry = entry
            self.save(update_fields=['journal_entry'])
            return entry
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f'Error creating journal entry for MO-{self.order_number}: {e}')
            return None
    
    def _create_production_order(self):
        """إنشاء أمر إنتاج تلقائي"""
        try:
            from production.models import ProductionOrder
            from inventory.models import Product
            
            # البحث عن منتج المرتبة أو إنشاء واحد عام
            product = Product.objects.filter(
                name__icontains='مرتبة'
            ).first()
            
            if not product:
                product = Product.objects.create(
                    name=f'مرتبة مخصصة - {self.design.design_name}',
                    product_type='finished',
                )
            
            from production.models import BillOfMaterials
            bom = BillOfMaterials.objects.first()
            
            if not bom:
                return None
            
            start_date = timezone.now().date()
            end_date = start_date + timezone.timedelta(days=self.design.estimated_production_days or 7)
            
            prod_order = ProductionOrder.objects.create(
                product=product,
                bom=bom,
                planned_quantity=1,
                planned_start_date=start_date,
                planned_end_date=end_date,
                status='confirmed',
                priority='normal',
                notes=f'أمر إنتاج تلقائي - طلب مرتبة مخصصة #{self.order_number}\n'
                      f'التصميم: {self.design.design_name}\n'
                      f'العميل: {self.customer_name}\n'
                      f'المقاس: {self.design.mattress_size}\n'
                      f'الإحساس: {self.design.feeling_type or "غير محدد"}',
                created_by=self.customer,
            )
            
            self.production_order = prod_order
            self.design.production_order = prod_order
            self.design.status = 'in_production'
            self.design.save(update_fields=['production_order', 'status'])
            self.estimated_delivery_date = end_date
            self.status = 'in_production'
            self.save(update_fields=['production_order', 'estimated_delivery_date', 'status'])
            return prod_order
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f'Error creating production order for MO-{self.order_number}: {e}')
            return None
    
    def _create_designer_commission(self):
        """إنشاء عمولة للمصمم الأصلي"""
        if not self.is_community_purchase or not self.original_designer:
            return None
        commission_rate = self.design.designer_commission_rate or Decimal('10')
        commission_amount = self.total * (commission_rate / Decimal('100'))
        
        commission = DesignerCommission.objects.create(
            designer=self.original_designer,
            order=self,
            design=self.design,
            commission_rate=commission_rate,
            commission_amount=commission_amount,
        )
        
        # تحديث عداد مبيعات التصميم
        self.design.sales_count += 1
        self.design.save(update_fields=['sales_count'])
        
        return commission


class DesignerCommission(models.Model):
    """عمولات مصممي المراتب - 10% من كل بيعة"""
    STATUS_CHOICES = [
        ('pending', _('في الانتظار')),
        ('approved', _('مُعتمدة')),
        ('paid', _('مدفوعة')),
        ('cancelled', _('ملغاة')),
    ]
    
    designer = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='design_commissions',
        verbose_name=_("المصمم")
    )
    order = models.ForeignKey(
        MattressOrder, on_delete=models.CASCADE,
        related_name='commissions',
        verbose_name=_("الطلب")
    )
    design = models.ForeignKey(
        CustomMattressDesign, on_delete=models.CASCADE,
        related_name='commissions',
        verbose_name=_("التصميم")
    )
    
    commission_rate = models.DecimalField(
        max_digits=5, decimal_places=2,
        verbose_name=_("نسبة العمولة %")
    )
    commission_amount = models.DecimalField(
        max_digits=12, decimal_places=2,
        verbose_name=_("مبلغ العمولة")
    )
    
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='pending', verbose_name=_("الحالة")
    )
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name=_("تاريخ الدفع"))
    notes = models.TextField(blank=True, verbose_name=_("ملاحظات"))
    
    # القيد المحاسبي
    journal_entry = models.ForeignKey(
        'accounting.JournalEntry',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='designer_commissions',
        verbose_name=_("القيد المحاسبي")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("عمولة مصمم")
        verbose_name_plural = _("عمولات المصممين")
        ordering = ['-created_at']
    
    def __str__(self):
        return f"عمولة {self.designer.get_full_name() or self.designer.username} - {self.commission_amount} ج.م"
