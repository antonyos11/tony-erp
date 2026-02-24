"""
النماذج الأساسية المشتركة (Abstract Base Models)
هذه النماذج توفر حقول وسلوكيات مشتركة لجميع نماذج النظام

الإصدار: 1.0
التاريخ: ديسمبر 2025
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from decimal import Decimal


class TimeStampedModel(models.Model):
    """
    نموذج أساسي لتتبع وقت الإنشاء والتحديث
    
    يوفر الحقول التالية:
    - created_at: تاريخ ووقت الإنشاء (تلقائي)
    - updated_at: تاريخ ووقت آخر تحديث (تلقائي)
    """
    created_at = models.DateTimeField(
        _('تاريخ الإنشاء'),
        auto_now_add=True,
        db_index=True
    )
    updated_at = models.DateTimeField(
        _('تاريخ التحديث'),
        auto_now=True
    )

    class Meta:
        abstract = True
        ordering = ['-created_at']


class UserTrackingModel(TimeStampedModel):
    """
    نموذج أساسي لتتبع المستخدم المسؤول
    
    يضيف إلى TimeStampedModel:
    - created_by: المستخدم الذي أنشأ السجل
    - updated_by: المستخدم الذي قام بآخر تحديث
    """
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(app_label)s_%(class)s_created',
        verbose_name=_('أنشئ بواسطة')
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(app_label)s_%(class)s_updated',
        verbose_name=_('حُدِّث بواسطة')
    )

    class Meta:
        abstract = True


class SoftDeleteManager(models.Manager):
    """مدير للنماذج ذات الحذف الناعم - يستثني السجلات المحذوفة افتراضياً"""
    
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)
    
    def with_deleted(self):
        """إرجاع جميع السجلات بما فيها المحذوفة"""
        return super().get_queryset()
    
    def deleted_only(self):
        """إرجاع السجلات المحذوفة فقط"""
        return super().get_queryset().filter(is_deleted=True)


class SoftDeleteModel(models.Model):
    """
    نموذج أساسي للحذف الناعم (Soft Delete)
    
    بدلاً من الحذف الفعلي، يتم تعليم السجل كمحذوف
    مما يسمح باستعادته لاحقاً
    """
    is_deleted = models.BooleanField(
        _('محذوف'),
        default=False,
        db_index=True
    )
    deleted_at = models.DateTimeField(
        _('تاريخ الحذف'),
        null=True,
        blank=True
    )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(app_label)s_%(class)s_deleted',
        verbose_name=_('حُذف بواسطة')
    )
    delete_reason = models.TextField(
        _('سبب الحذف'),
        blank=True
    )

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def soft_delete(self, user=None, reason=''):
        """حذف ناعم للسجل"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.delete_reason = reason
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by', 'delete_reason'])

    def restore(self):
        """استعادة سجل محذوف"""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.delete_reason = ''
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by', 'delete_reason'])


class StatusModel(models.Model):
    """
    نموذج أساسي للحالة والتفعيل
    """
    is_active = models.BooleanField(
        _('نشط'),
        default=True,
        db_index=True
    )

    class Meta:
        abstract = True


class OrderedModel(models.Model):
    """
    نموذج أساسي للترتيب
    """
    order = models.PositiveIntegerField(
        _('الترتيب'),
        default=0,
        db_index=True
    )

    class Meta:
        abstract = True
        ordering = ['order']


class CodedModel(models.Model):
    """
    نموذج أساسي للكيانات ذات الكود الفريد
    """
    code = models.CharField(
        _('الكود'),
        max_length=50,
        unique=True,
        db_index=True
    )

    class Meta:
        abstract = True


class NamedModel(models.Model):
    """
    نموذج أساسي للكيانات ذات الاسم والوصف
    """
    name = models.CharField(
        _('الاسم'),
        max_length=255
    )
    description = models.TextField(
        _('الوصف'),
        blank=True
    )

    class Meta:
        abstract = True

    def __str__(self):
        return self.name


class MonetaryModel(models.Model):
    """
    نموذج أساسي للحقول المالية
    يوفر حقول العملة والمبلغ
    """
    amount = models.DecimalField(
        _('المبلغ'),
        max_digits=15,
        decimal_places=2,
        default=Decimal('0')
    )
    currency = models.ForeignKey(
        'core.Currency',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_('العملة')
    )
    exchange_rate = models.DecimalField(
        _('سعر الصرف'),
        max_digits=18,
        decimal_places=6,
        default=Decimal('1'),
        help_text=_('سعر الصرف وقت العملية')
    )

    class Meta:
        abstract = True

    @property
    def amount_in_default_currency(self):
        """المبلغ بالعملة الافتراضية"""
        if self.currency and self.exchange_rate:
            return self.amount / self.exchange_rate
        return self.amount


class BranchAwareModel(models.Model):
    """
    نموذج أساسي للكيانات المرتبطة بالفروع
    """
    branch = models.ForeignKey(
        'core.Branch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('الفرع')
    )

    class Meta:
        abstract = True


class DocumentModel(UserTrackingModel):
    """
    نموذج أساسي للمستندات (فواتير، أوامر، إلخ)
    يجمع بين تتبع الوقت والمستخدم مع حقول المستند
    (UserTrackingModel يرث من TimeStampedModel بالفعل)
    """
    STATUS_CHOICES = [
        ('draft', _('مسودة')),
        ('pending', _('معلق')),
        ('approved', _('موافق عليه')),
        ('rejected', _('مرفوض')),
        ('completed', _('مكتمل')),
        ('cancelled', _('ملغي')),
    ]

    number = models.CharField(
        _('رقم المستند'),
        max_length=50,
        unique=True
    )
    date = models.DateField(
        _('التاريخ'),
        default=timezone.now
    )
    status = models.CharField(
        _('الحالة'),
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        db_index=True
    )
    notes = models.TextField(
        _('ملاحظات'),
        blank=True
    )

    class Meta:
        abstract = True
        ordering = ['-date', '-number']

    def __str__(self):
        return self.number


class FullAuditModel(UserTrackingModel, SoftDeleteModel, StatusModel):
    """
    نموذج شامل يجمع جميع ميزات التدقيق
    - تتبع الوقت (الإنشاء والتحديث)
    - تتبع المستخدم (من أنشأ ومن حدّث)
    - الحذف الناعم
    - حالة التفعيل
    """
    
    class Meta:
        abstract = True


# ============================================
# خدمات مساعدة للنماذج
# ============================================

def generate_document_number(prefix, model_class, field_name='number'):
    """
    توليد رقم مستند فريد
    
    Args:
        prefix: البادئة (مثل: INV, PO, SO)
        model_class: نموذج المستند
        field_name: اسم حقل الرقم
    
    Returns:
        رقم المستند الجديد
    """
    from django.db.models import Max
    from datetime import datetime
    
    year_month = datetime.now().strftime('%Y%m')
    prefix_pattern = f"{prefix}-{year_month}-"
    
    # البحث عن آخر رقم
    filter_kwargs = {f'{field_name}__startswith': prefix_pattern}
    last = model_class.objects.filter(**filter_kwargs).aggregate(
        max_num=Max(field_name)
    )['max_num']
    
    if last:
        try:
            last_seq = int(last.split('-')[-1])
            new_seq = last_seq + 1
        except (ValueError, IndexError):
            new_seq = 1
    else:
        new_seq = 1
    
    return f"{prefix_pattern}{new_seq:04d}"


def get_next_code(model_class, prefix, code_field='code', padding=4):
    """
    توليد كود فريد تسلسلي
    
    Args:
        model_class: النموذج
        prefix: البادئة
        code_field: اسم حقل الكود
        padding: عدد الخانات
    
    Returns:
        الكود الجديد
    """
    from django.db.models import Max
    import re
    
    filter_kwargs = {f'{code_field}__startswith': prefix}
    last = model_class.objects.filter(**filter_kwargs).aggregate(
        max_code=Max(code_field)
    )['max_code']
    
    if last:
        match = re.search(r'(\d+)$', last)
        if match:
            new_seq = int(match.group(1)) + 1
        else:
            new_seq = 1
    else:
        new_seq = 1
    
    return f"{prefix}{new_seq:0{padding}d}"
