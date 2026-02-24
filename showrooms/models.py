from django.db import models
from django.utils.translation import gettext_lazy as _


class Showroom(models.Model):
    name = models.CharField(_('الاسم'), max_length=200)
    code = models.CharField(_('الكود'), max_length=50, blank=True)
    address = models.TextField(_('العنوان'), blank=True)
    is_active = models.BooleanField(_('نشط'), default=True)

    class Meta:
        verbose_name = _('معرض')
        verbose_name_plural = _('المعارض')

    def __str__(self):
        return self.name
