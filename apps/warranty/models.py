"""
نماذج تطبيق الضمان — RITA ERP
"""
import uuid
from django.db import models
from django.utils import timezone
from apps.core.models import AuditMixin


class WarrantyCard(AuditMixin):
    """بطاقة ضمان"""

    WARRANTY_STATUSES = [
        ('active',  'نشط'),
        ('expired', 'منتهي'),
        ('void',    'ملغي'),
    ]

    serial_number    = models.CharField(max_length=100, unique=True, verbose_name='رقم الضمان')
    invoice          = models.ForeignKey(
        'sales.SalesInvoice',
        on_delete=models.PROTECT,
        related_name='warranty_cards',
        verbose_name='الفاتورة',
    )
    invoice_line     = models.ForeignKey(
        'sales.SalesInvoiceLine',
        on_delete=models.PROTECT,
        related_name='warranty_cards',
        verbose_name='سطر الفاتورة',
    )
    customer         = models.ForeignKey(
        'sales.Customer',
        on_delete=models.PROTECT,
        related_name='warranty_cards',
        verbose_name='العميل',
    )
    product          = models.ForeignKey(
        'inventory.Product',
        on_delete=models.PROTECT,
        related_name='warranty_cards',
        verbose_name='المنتج',
    )
    purchase_date    = models.DateField(verbose_name='تاريخ الشراء')
    expiry_date      = models.DateField(verbose_name='تاريخ انتهاء الضمان')
    status           = models.CharField(max_length=20, choices=WARRANTY_STATUSES, default='active', verbose_name='الحالة')
    activated_by     = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='activated_warranties',
        verbose_name='فعّله',
    )
    activation_date  = models.DateTimeField(null=True, blank=True, verbose_name='تاريخ التفعيل')

    # بيانات العميل للضمان
    customer_name    = models.CharField(max_length=255, verbose_name='اسم العميل')
    customer_phone   = models.CharField(max_length=20, verbose_name='هاتف العميل')
    customer_address = models.TextField(blank=True, verbose_name='العنوان')

    class Meta:
        verbose_name        = 'بطاقة ضمان'
        verbose_name_plural = 'بطاقات الضمان'
        ordering            = ['-purchase_date']

    def __str__(self):
        return f'{self.serial_number} — {self.product}'

    @property
    def is_valid(self) -> bool:
        """هل الضمان ساري؟"""
        return self.status == 'active' and self.expiry_date >= timezone.now().date()

    def activate(self, user) -> None:
        """تفعيل بطاقة الضمان."""
        self.status          = 'active'
        self.activated_by    = user
        self.activation_date = timezone.now()
        self.save(update_fields=['status', 'activated_by', 'activation_date', 'updated_by'])

    def check_expiry(self) -> None:
        """تحديث الحالة إذا انتهت صلاحية الضمان."""
        if self.status == 'active' and self.expiry_date < timezone.now().date():
            self.status = 'expired'
            self.save(update_fields=['status'])

    @staticmethod
    def generate_serial() -> str:
        """توليد رقم ضمان فريد."""
        prefix = timezone.now().strftime('WR%Y%m%d')
        count  = WarrantyCard.objects.filter(
            serial_number__startswith=prefix
        ).count() + 1
        return f'{prefix}{count:04d}'


class WarrantyClaim(AuditMixin):
    """مطالبة ضمان"""

    CLAIM_STATUSES = [
        ('open',        'مفتوحة'),
        ('in_progress', 'جاري'),
        ('resolved',    'محلولة'),
        ('rejected',    'مرفوضة'),
    ]

    warranty          = models.ForeignKey(
        WarrantyCard,
        on_delete=models.PROTECT,
        related_name='claims',
        verbose_name='بطاقة الضمان',
    )
    claim_date        = models.DateField(verbose_name='تاريخ المطالبة')
    issue_description = models.TextField(verbose_name='وصف المشكلة')
    resolution        = models.TextField(blank=True, verbose_name='الحل')
    status            = models.CharField(
        max_length=20,
        choices=CLAIM_STATUSES,
        default='open',
        verbose_name='الحالة',
    )

    class Meta:
        verbose_name        = 'مطالبة ضمان'
        verbose_name_plural = 'مطالبات الضمان'
        ordering            = ['-claim_date']

    def __str__(self):
        return f'مطالبة #{self.pk} — {self.warranty.serial_number}'
