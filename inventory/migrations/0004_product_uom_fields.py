from django.db import migrations, models
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0003_location_is_active_location_is_default_location_type_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='purchase_uom',
            field=models.CharField(choices=[('unit', 'وحدة'), ('kg', 'كيلوجرام'), ('g', 'جرام'), ('m', 'متر'), ('cm', 'سنتيمتر')], default='unit', help_text='وحدة قياس الشراء (مثلاً: كجم، متر، وحدة)', max_length=10),
        ),
        migrations.AddField(
            model_name='product',
            name='usage_uom',
            field=models.CharField(choices=[('unit', 'وحدة'), ('kg', 'كيلوجرام'), ('g', 'جرام'), ('m', 'متر'), ('cm', 'سنتيمتر')], default='unit', help_text='الوحدة التي تُستهلك بها المادة في الإنتاج', max_length=10),
        ),
        migrations.AddField(
            model_name='product',
            name='conversion_factor',
            field=models.DecimalField(decimal_places=4, default=Decimal('1'), help_text='عامل التحويل: 1 من وحدة الشراء = هذا العدد من وحدة الاستخدام', max_digits=12),
        ),
    ]
