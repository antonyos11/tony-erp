from django.db import models
from django.utils.translation import gettext_lazy as _


class Employee(models.Model):
    first_name = models.CharField(_('الاسم الأول'), max_length=100)
    last_name = models.CharField(_('اسم العائلة'), max_length=100, blank=True)
    status = models.CharField(_('الحالة'), max_length=20, default='active')
    email = models.EmailField(_('البريد'), blank=True)

    class Meta:
        app_label = 'hr'

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
