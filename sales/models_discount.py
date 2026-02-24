from django.db import models
from django.utils.translation import gettext_lazy as _


class CustomerDiscountNote(models.Model):
    customer = models.ForeignKey('partners.Customer', on_delete=models.CASCADE, null=True, blank=True)
    amount = models.DecimalField(_('المبلغ'), max_digits=14, decimal_places=2, default=0)
    date = models.DateField(_('التاريخ'), null=True, blank=True)
    description = models.TextField(_('الوصف'), blank=True)

    class Meta:
        app_label = 'sales'
