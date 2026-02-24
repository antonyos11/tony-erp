from django.db import models
from django.utils.translation import gettext_lazy as _


class Customer(models.Model):
    name = models.CharField(_('الاسم'), max_length=200)
    first_name = models.CharField(_('الاسم الأول'), max_length=100, blank=True)
    last_name = models.CharField(_('اسم العائلة'), max_length=100, blank=True)
    company_name = models.CharField(_('اسم الشركة'), max_length=200, blank=True)
    email = models.EmailField(_('البريد'), blank=True)
    phone = models.CharField(_('الهاتف'), max_length=50, blank=True)

    class Meta:
        app_label = 'crm'

    def __str__(self):
        return self.name
