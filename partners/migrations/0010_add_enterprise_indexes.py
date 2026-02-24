# Generated migration for enterprise performance indexes
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    إضافة فهارس للأداء العالي في الشركات الكبيرة
    """

    dependencies = [
        ('partners', '0009_supplierdocument'),  # آخر migration
    ]

    operations = [
        # فهرس للبحث في اسم العميل
        migrations.AddIndex(
            model_name='customer',
            index=models.Index(fields=['name'], name='customer_name_idx'),
        ),
        # فهرس للبحث في الهاتف
        migrations.AddIndex(
            model_name='customer',
            index=models.Index(fields=['phone'], name='customer_phone_idx'),
        ),
        # فهرس للبحث في اسم المورد
        migrations.AddIndex(
            model_name='supplier',
            index=models.Index(fields=['name'], name='supplier_name_idx'),
        ),
        # فهرس للبحث في اسم الشريك
        migrations.AddIndex(
            model_name='partner',
            index=models.Index(fields=['name'], name='partner_name_idx'),
        ),
        # فهرس لنوع الشريك
        migrations.AddIndex(
            model_name='partner',
            index=models.Index(fields=['partner_type'], name='partner_type_idx'),
        ),
        # فهرس للشركاء النشطين
        migrations.AddIndex(
            model_name='partner',
            index=models.Index(fields=['is_active', 'partner_type'], name='partner_active_type_idx'),
        ),
    ]
