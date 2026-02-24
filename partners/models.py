from django.db import models
from django.utils.translation import gettext_lazy as _


class Partner(models.Model):
    """شريك تجاري عام"""
    PARTNER_TYPES = [
        ('customer', 'عميل'),
        ('supplier', 'مورد'),
        ('both', 'عميل ومورد'),
    ]
    name = models.CharField(_('الاسم'), max_length=200)
    partner_type = models.CharField(_('نوع الشريك'), max_length=20, choices=PARTNER_TYPES, default='customer')
    email = models.EmailField(_('البريد الإلكتروني'), blank=True)
    phone = models.CharField(_('الهاتف'), max_length=50, blank=True)
    address = models.TextField(_('العنوان'), blank=True)
    is_active = models.BooleanField(_('نشط'), default=True)

    class Meta:
        verbose_name = _('شريك')
        verbose_name_plural = _('الشركاء')

    def __str__(self):
        return self.name


class Customer(models.Model):
    """عميل"""
    name = models.CharField(_('الاسم'), max_length=200)
    first_name = models.CharField(_('الاسم الأول'), max_length=100, blank=True)
    last_name = models.CharField(_('اسم العائلة'), max_length=100, blank=True)
    company_name = models.CharField(_('اسم الشركة'), max_length=200, blank=True)
    email = models.EmailField(_('البريد الإلكتروني'), blank=True)
    phone = models.CharField(_('الهاتف'), max_length=50, blank=True)
    address = models.TextField(_('العنوان'), blank=True)
    is_active = models.BooleanField(_('نشط'), default=True)

    class Meta:
        verbose_name = _('عميل')
        verbose_name_plural = _('العملاء')
        ordering = ['name']

    def __str__(self):
        return self.company_name or self.name


class Supplier(models.Model):
    """مورد"""
    name = models.CharField(_('الاسم'), max_length=200)
    email = models.EmailField(_('البريد الإلكتروني'), blank=True)
    phone = models.CharField(_('الهاتف'), max_length=50, blank=True)
    address = models.TextField(_('العنوان'), blank=True)
    is_active = models.BooleanField(_('نشط'), default=True)

    class Meta:
        verbose_name = _('مورد')
        verbose_name_plural = _('الموردين')
        ordering = ['name']

    def __str__(self):
        return self.name
