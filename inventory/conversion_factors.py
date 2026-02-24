"""
نظام معاملات التحويل المحفوظة مسبقاً
للتحويل بين وحدات القياس المختلفة
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from decimal import Decimal


class ConversionFactor(models.Model):
    """معاملات التحويل المحفوظة بين الوحدات"""
    
    id = models.AutoField(primary_key=True)
    
    # الوحدات
    from_unit = models.CharField(
        max_length=20,
        verbose_name=_('من وحدة'),
        help_text=_('الوحدة المصدر')
    )
    to_unit = models.CharField(
        max_length=20,
        verbose_name=_('إلى وحدة'),
        help_text=_('الوحدة الهدف')
    )
    
    # المعامل
    factor = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        verbose_name=_('معامل التحويل'),
        help_text=_('1 من_وحدة = factor إلى_وحدة')
    )
    
    # نوع المادة (اختياري للتخصيص)
    MATERIAL_TYPE_CHOICES = [
        ('general', _('عام')),
        ('wood', _('خشب')),
        ('foam', _('إسفنج')),
        ('metal', _('معدن')),
        ('fabric', _('قماش')),
        ('liquid', _('سائل')),
        ('other', _('أخرى')),
    ]
    material_type = models.CharField(
        max_length=20,
        choices=MATERIAL_TYPE_CHOICES,
        default='general',
        verbose_name=_('نوع المادة'),
        help_text=_('تحديد نوع المادة لمعامل تحويل مخصص')
    )
    
    # الوصف
    description = models.TextField(
        blank=True,
        verbose_name=_('الوصف'),
        help_text=_('مثال: 1 متر مكعب خشب زان = 650 كجم')
    )
    
    # الحالة
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('نشط')
    )
    
    # التواريخ
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('معامل تحويل')
        verbose_name_plural = _('معاملات التحويل')
        unique_together = ['from_unit', 'to_unit', 'material_type']
        ordering = ['material_type', 'from_unit', 'to_unit']
        indexes = [
            models.Index(fields=['from_unit', 'to_unit']),
            models.Index(fields=['material_type', 'is_active']),
        ]
    
    def __str__(self):
        material_label = f"[{self.get_material_type_display()}] " if self.material_type != 'general' else ""
        return f"{material_label}1 {self.from_unit} = {self.factor} {self.to_unit}"
    
    @classmethod
    def get_factor(cls, from_unit, to_unit, material_type='general'):
        """الحصول على معامل التحويل"""
        # محاولة العثور على معامل خاص بنوع المادة
        try:
            cf = cls.objects.get(
                from_unit=from_unit,
                to_unit=to_unit,
                material_type=material_type,
                is_active=True
            )
            return cf.factor
        except cls.DoesNotExist:
            pass
        
        # محاولة العثور على معامل عام
        try:
            cf = cls.objects.get(
                from_unit=from_unit,
                to_unit=to_unit,
                material_type='general',
                is_active=True
            )
            return cf.factor
        except cls.DoesNotExist:
            return None
    
    @classmethod
    def convert(cls, value, from_unit, to_unit, material_type='general'):
        """تحويل قيمة من وحدة لأخرى"""
        if from_unit == to_unit:
            return value
        
        factor = cls.get_factor(from_unit, to_unit, material_type)
        if factor:
            return Decimal(str(value)) * factor
        
        # محاولة التحويل العكسي
        reverse_factor = cls.get_factor(to_unit, from_unit, material_type)
        if reverse_factor:
            return Decimal(str(value)) / reverse_factor
        
        return None


# معاملات التحويل الشائعة (للتحميل الأولي)
COMMON_CONVERSIONS = [
    # الوزن
    {'from_unit': 'ton', 'to_unit': 'kg', 'factor': '1000', 'material_type': 'general', 'description': '1 طن = 1000 كيلوجرام'},
    {'from_unit': 'kg', 'to_unit': 'g', 'factor': '1000', 'material_type': 'general', 'description': '1 كيلوجرام = 1000 جرام'},
    
    # الطول
    {'from_unit': 'm', 'to_unit': 'cm', 'factor': '100', 'material_type': 'general', 'description': '1 متر = 100 سنتيمتر'},
    {'from_unit': 'cm', 'to_unit': 'mm', 'factor': '10', 'material_type': 'general', 'description': '1 سنتيمتر = 10 مليمتر'},
    
    # المساحة
    {'from_unit': 'm2', 'to_unit': 'cm', 'factor': '10000', 'material_type': 'general', 'description': '1 متر مربع = 10000 سم²'},
    
    # الحجم → الوزن (خشب)
    {'from_unit': 'm3', 'to_unit': 'kg', 'factor': '650', 'material_type': 'wood', 'description': '1 م³ خشب زان = 650 كجم'},
    {'from_unit': 'm3', 'to_unit': 'kg', 'factor': '550', 'material_type': 'wood', 'description': '1 م³ خشب صنوبر = 550 كجم (استخدم نوع مادة مخصص)'},
    
    # الحجم → الوزن (إسفنج)
    {'from_unit': 'm3', 'to_unit': 'kg', 'factor': '25', 'material_type': 'foam', 'description': '1 م³ إسفنج كثافة 25 = 25 كجم'},
    {'from_unit': 'm3', 'to_unit': 'kg', 'factor': '30', 'material_type': 'foam', 'description': '1 م³ إسفنج كثافة 30 = 30 كجم'},
    {'from_unit': 'm3', 'to_unit': 'kg', 'factor': '35', 'material_type': 'foam', 'description': '1 م³ إسفنج كثافة 35 = 35 كجم'},
    
    # السوائل
    {'from_unit': 'liter', 'to_unit': 'kg', 'factor': '1', 'material_type': 'liquid', 'description': '1 لتر ماء = 1 كجم'},
    {'from_unit': 'gallon', 'to_unit': 'liter', 'factor': '3.785', 'material_type': 'liquid', 'description': '1 جالون = 3.785 لتر'},
    
    # التعبئة
    {'from_unit': 'carton', 'to_unit': 'piece', 'factor': '12', 'material_type': 'general', 'description': '1 كرتونة = 12 قطعة (افتراضي)'},
    {'from_unit': 'box', 'to_unit': 'piece', 'factor': '6', 'material_type': 'general', 'description': '1 صندوق = 6 قطع (افتراضي)'},
]


def load_common_conversions():
    """تحميل معاملات التحويل الشائعة"""
    created_count = 0
    for data in COMMON_CONVERSIONS:
        obj, created = ConversionFactor.objects.get_or_create(
            from_unit=data['from_unit'],
            to_unit=data['to_unit'],
            material_type=data['material_type'],
            defaults={
                'factor': Decimal(data['factor']),
                'description': data['description'],
                'is_active': True
            }
        )
        if created:
            created_count += 1
    
    return created_count
