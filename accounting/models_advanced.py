"""
النماذج المحاسبية المتقدمة
============================
الفترات المحاسبية
ملاحظة: FiscalYear, BankReconciliation, BudgetItem موجودين بالفعل في accounting.models
"""

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone


class AccountingPeriod(models.Model):
    """الفترة المحاسبية (شهرية عادةً)"""
    PERIOD_TYPE_CHOICES = [
        ('monthly', 'شهرية'),
        ('quarterly', 'ربع سنوية'),
        ('semi_annual', 'نصف سنوية'),
        ('annual', 'سنوية'),
        ('special', 'خاصة'),
    ]

    fiscal_year = models.ForeignKey(
        'accounting.FiscalYear',
        on_delete=models.CASCADE,
        related_name='periods',
        verbose_name='السنة المالية'
    )
    name = models.CharField(max_length=100, verbose_name='اسم الفترة')
    period_type = models.CharField(
        max_length=20,
        choices=PERIOD_TYPE_CHOICES,
        default='monthly',
        verbose_name='نوع الفترة'
    )
    start_date = models.DateField(verbose_name='تاريخ البداية')
    end_date = models.DateField(verbose_name='تاريخ النهاية')
    is_open = models.BooleanField(default=True, verbose_name='مفتوحة')
    is_adjustment_period = models.BooleanField(
        default=False,
        verbose_name='فترة تسوية',
        help_text='هل هذه فترة تسوية نهاية سنة؟'
    )
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='closed_accounting_periods',
        verbose_name='أُغلقت بواسطة'
    )
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name='تاريخ الإغلاق')
    notes = models.TextField(blank=True, verbose_name='ملاحظات')

    class Meta:
        verbose_name = 'فترة محاسبية'
        verbose_name_plural = 'الفترات المحاسبية'
        ordering = ['start_date']
        unique_together = ['fiscal_year', 'start_date']

    def __str__(self):
        status = '🔓' if self.is_open else '🔒'
        return f"{status} {self.name}"

    def clean(self):
        if self.start_date and self.end_date:
            if self.start_date >= self.end_date:
                raise ValidationError('تاريخ البداية يجب أن يكون قبل تاريخ النهاية')

    def close_period(self, user):
        """إقفال الفترة المحاسبية"""
        if not self.is_open:
            raise ValidationError('الفترة مغلقة بالفعل')

        from accounting.models import JournalEntry
        unposted = JournalEntry.objects.filter(
            date__gte=self.start_date,
            date__lte=self.end_date,
            is_posted=False
        )
        if unposted.exists():
            raise ValidationError(
                f'يوجد {unposted.count()} قيد غير مرحّل في هذه الفترة. '
                f'يجب ترحيل أو حذف جميع القيود قبل الإقفال.'
            )

        self.is_open = False
        self.closed_by = user
        self.closed_at = timezone.now()
        self.save(update_fields=['is_open', 'closed_by', 'closed_at'])

    def reopen_period(self, user):
        """إعادة فتح الفترة (فقط للمدير المالي)"""
        if self.is_open:
            raise ValidationError('الفترة مفتوحة بالفعل')
        self.is_open = True
        self.closed_by = None
        self.closed_at = None
        self.notes += f'\nتم إعادة الفتح بواسطة {user} في {timezone.now()}'
        self.save()

    @staticmethod
    def get_current_period():
        """الحصول على الفترة المحاسبية الحالية"""
        today = timezone.now().date()
        try:
            return AccountingPeriod.objects.get(
                start_date__lte=today,
                end_date__gte=today,
                is_open=True
            )
        except AccountingPeriod.DoesNotExist:
            return None
        except AccountingPeriod.MultipleObjectsReturned:
            return AccountingPeriod.objects.filter(
                start_date__lte=today,
                end_date__gte=today,
                is_open=True
            ).first()

    @staticmethod
    def is_date_in_open_period(date_value):
        """التحقق مما إذا كان التاريخ في فترة مفتوحة"""
        return AccountingPeriod.objects.filter(
            start_date__lte=date_value,
            end_date__gte=date_value,
            is_open=True
        ).exists()

