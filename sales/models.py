from django.db import models
from django.utils.translation import gettext_lazy as _


class Invoice(models.Model):
    number = models.CharField(_('رقم الفاتورة'), max_length=50, blank=True)
    customer = models.ForeignKey('partners.Customer', on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    date = models.DateField(_('التاريخ'), null=True, blank=True)
    total = models.DecimalField(_('الإجمالي'), max_digits=14, decimal_places=2, default=0)
    description = models.TextField(_('الوصف'), blank=True)

    class Meta:
        verbose_name = _('فاتورة')
        verbose_name_plural = _('الفواتير')
        app_label = 'sales'

    def __str__(self):
        return self.number or str(self.pk)


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    description = models.CharField(_('الوصف'), max_length=200, blank=True)
    quantity = models.DecimalField(_('الكمية'), max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(_('سعر الوحدة'), max_digits=14, decimal_places=2, default=0)
    total = models.DecimalField(_('الإجمالي'), max_digits=14, decimal_places=2, default=0)

    class Meta:
        app_label = 'sales'


class InvoicePayment(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(_('المبلغ'), max_digits=14, decimal_places=2, default=0)
    date = models.DateField(_('التاريخ'), null=True, blank=True)

    class Meta:
        app_label = 'sales'
