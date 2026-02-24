from django.db import models
from django.utils.translation import gettext_lazy as _


class Product(models.Model):
    name = models.CharField(_('الاسم'), max_length=200)
    code = models.CharField(_('الكود'), max_length=50, blank=True)
    price = models.DecimalField(_('السعر'), max_digits=14, decimal_places=2, default=0)

    class Meta:
        app_label = 'inventory'

    def __str__(self):
        return self.name
