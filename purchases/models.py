from django.db import models
from django.utils.translation import gettext_lazy as _


class PurchaseBill(models.Model):
    number = models.CharField(_('رقم الفاتورة'), max_length=50, blank=True)
    supplier = models.ForeignKey('partners.Supplier', on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateField(_('التاريخ'), null=True, blank=True)
    total = models.DecimalField(_('الإجمالي'), max_digits=14, decimal_places=2, default=0)

    class Meta:
        verbose_name = _('فاتورة مشتريات')
        verbose_name_plural = _('فواتير المشتريات')
        app_label = 'purchases'

    def __str__(self):
        return self.number or str(self.pk)
