"""
نماذج تطبيق الشركاء (الموردين) — RITA ERP
"""
from django.db import models
from apps.core.models import AuditMixin


class Supplier(AuditMixin):
    """الموردون"""
    SUPPLIER_TYPE_CHOICES = [
        ('local', 'محلي'),
        ('international', 'دولي'),
    ]

    code = models.CharField(max_length=50, unique=True, verbose_name='الكود')
    name = models.CharField(max_length=300, verbose_name='الاسم')
    supplier_type = models.CharField(
        max_length=20, choices=SUPPLIER_TYPE_CHOICES,
        default='local', verbose_name='نوع المورد',
    )
    phone = models.CharField(max_length=20, blank=True, verbose_name='الهاتف')
    phone2 = models.CharField(max_length=20, blank=True, verbose_name='هاتف 2')
    address = models.TextField(blank=True, verbose_name='العنوان')
    country = models.CharField(max_length=100, default='مصر', verbose_name='الدولة')
    tax_number = models.CharField(max_length=50, blank=True, verbose_name='الرقم الضريبي')
    is_taxable = models.BooleanField(default=True, verbose_name='خاضع للضريبة')
    payment_terms = models.PositiveIntegerField(default=0, verbose_name='شروط الدفع (أيام)')
    account = models.ForeignKey(
        'accounts.Account', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='suppliers', verbose_name='الحساب المحاسبي',
    )
    contact_person = models.CharField(max_length=200, blank=True, verbose_name='جهة الاتصال')
    bank_name = models.CharField(max_length=200, blank=True, verbose_name='اسم البنك')
    bank_account = models.CharField(max_length=100, blank=True, verbose_name='رقم الحساب البنكي')
    is_active = models.BooleanField(default=True, verbose_name='نشط')

    class Meta:
        verbose_name = 'مورد'
        verbose_name_plural = 'الموردون'
        ordering = ['code']

    def __str__(self):
        return f'{self.code} - {self.name}'

