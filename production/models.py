from django.db import models
from django.utils.translation import gettext_lazy as _


class ProductionOrder(models.Model):
    number = models.CharField(_('رقم الأمر'), max_length=50, blank=True)
    status = models.CharField(_('الحالة'), max_length=20, default='draft')

    class Meta:
        app_label = 'production'

    def __str__(self):
        return self.number or str(self.pk)


class BillOfMaterials(models.Model):
    name = models.CharField(_('الاسم'), max_length=200, blank=True)

    class Meta:
        app_label = 'production'

    def __str__(self):
        return self.name or str(self.pk)
