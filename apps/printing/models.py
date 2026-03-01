"""
نماذج تطبيق الطباعة والباركود — RITA ERP
"""
from django.db import models
from apps.core.models import AuditMixin


class PrintTemplate(AuditMixin):
    TEMPLATE_TYPES = [
        ('invoice',    'فاتورة بيع'),
        ('receipt',    'إيصال قبض'),
        ('purchase',   'أمر توريد'),
        ('production', 'أمر إنتاج'),
        ('barcode',    'باركود'),
    ]
    PAPER_SIZES = [
        ('thermal_80', 'حرارية 80mm'),
        ('a4',         'A4'),
        ('a5',         'A5'),
    ]

    name          = models.CharField(max_length=255, verbose_name='اسم القالب')
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPES, verbose_name='النوع')
    paper_size    = models.CharField(max_length=20, choices=PAPER_SIZES, verbose_name='حجم الورق')
    html_content  = models.TextField(verbose_name='محتوى HTML')
    is_default    = models.BooleanField(default=False, verbose_name='افتراضي')

    class Meta:
        verbose_name        = 'قالب طباعة'
        verbose_name_plural = 'قوالب الطباعة'
        ordering            = ['template_type', 'name']

    def __str__(self):
        return f'{self.name} ({self.get_template_type_display()})'

    def save(self, *args, **kwargs):
        """عند تعيين قالب افتراضي، ألغِ الافتراضي السابق من نفس النوع."""
        if self.is_default:
            PrintTemplate.objects.filter(
                template_type=self.template_type,
                is_default=True,
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)
