# Generated migration for enterprise performance indexes
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    إضافة فهارس للأداء العالي للمخزون في الشركات الكبيرة
    """

    dependencies = [
        ('inventory', '0020_add_category_model'),
    ]

    operations = [
        # فهرس للباركود
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['barcode'], name='product_barcode_idx'),
        ),
        # فهرس للتصنيف
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['category'], name='product_category_idx'),
        ),
        # فهرس للمخزون - المنتج والموقع
        migrations.AddIndex(
            model_name='stock',
            index=models.Index(fields=['product', 'location'], name='stock_product_location_idx'),
        ),
        # فهرس للكميات المنخفضة
        migrations.AddIndex(
            model_name='stock',
            index=models.Index(fields=['quantity'], name='stock_quantity_idx'),
        ),
    ]
