from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0012_invoice_cached_total'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='is_tax_inclusive',
            field=models.BooleanField(default=False, help_text='السعر/الإجمالي يشمل ضريبة القيمة المضافة؟ (يتم استخدامه للفصل في العرض والحسابات اللاحقة)'),
        ),
        migrations.AddField(
            model_name='invoice',
            name='is_withholding_applied',
            field=models.BooleanField(default=False, help_text='هل تم تطبيق خصم/استقطاع من المنبع على هذه الفاتورة يدوياً؟'),
        ),
    ]
