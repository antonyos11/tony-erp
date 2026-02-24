# Generated migration for supplier-specific product pricing

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0029_raw_materials_enhancements'),
        ('partners', '0001_initial'),
    ]

    operations = [
        # جدول أسعار المنتجات حسب المورد
        migrations.CreateModel(
            name='SupplierProductPrice',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('product', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='supplier_prices',
                    to='inventory.product',
                    verbose_name='المنتج'
                )),
                ('supplier', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='product_prices',
                    to='partners.supplier',
                    verbose_name='المورد'
                )),
                ('cost', models.DecimalField(
                    decimal_places=2,
                    max_digits=12,
                    verbose_name='التكلفة',
                    help_text='تكلفة وحدة الشراء من هذا المورد'
                )),
                ('currency', models.CharField(
                    max_length=3,
                    default='EGP',
                    verbose_name='العملة'
                )),
                ('min_order_qty', models.DecimalField(
                    decimal_places=4,
                    max_digits=12,
                    null=True,
                    blank=True,
                    verbose_name='الحد الأدنى للطلب'
                )),
                ('lead_time_days', models.PositiveIntegerField(
                    null=True,
                    blank=True,
                    verbose_name='مدة التوريد (أيام)'
                )),
                ('is_active', models.BooleanField(
                    default=True,
                    verbose_name='نشط'
                )),
                ('effective_date', models.DateField(
                    auto_now_add=True,
                    verbose_name='تاريخ السريان'
                )),
                ('notes', models.TextField(
                    blank=True,
                    verbose_name='ملاحظات'
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'سعر مورد',
                'verbose_name_plural': 'أسعار الموردين',
                'ordering': ['product', 'supplier', '-effective_date'],
                'unique_together': {('product', 'supplier', 'effective_date')},
            },
        ),
        
        # إضافة فهرس للبحث السريع
        migrations.AddIndex(
            model_name='supplierproductprice',
            index=models.Index(
                fields=['product', 'supplier', 'is_active'],
                name='spp_prod_supp_active_idx'
            ),
        ),
    ]

