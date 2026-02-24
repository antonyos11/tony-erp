# Generated migration for advanced purchasing models

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('purchases', '0002_purchase_order'),
        ('inventory', '0001_initial'),
        ('partners', '0001_initial'),
    ]

    operations = [
        # =============================
        # طلبات الشراء (PR)
        # =============================
        migrations.CreateModel(
            name='PurchaseRequest',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('number', models.CharField(max_length=50, unique=True, verbose_name='رقم الطلب')),
                ('department', models.CharField(blank=True, max_length=100, verbose_name='القسم الطالب')),
                ('date', models.DateField(default=django.utils.timezone.now, verbose_name='تاريخ الطلب')),
                ('required_date', models.DateField(blank=True, null=True, verbose_name='تاريخ الحاجة')),
                ('status', models.CharField(
                    choices=[
                        ('draft', 'مسودة'),
                        ('pending', 'قيد المراجعة'),
                        ('approved', 'معتمد'),
                        ('rejected', 'مرفوض'),
                        ('converted', 'مُحوّل لأمر شراء'),
                        ('cancelled', 'ملغى'),
                    ],
                    default='draft',
                    max_length=20,
                    verbose_name='الحالة'
                )),
                ('priority', models.CharField(
                    choices=[
                        ('low', 'منخفضة'),
                        ('normal', 'عادية'),
                        ('high', 'عالية'),
                        ('urgent', 'عاجلة'),
                    ],
                    default='normal',
                    max_length=20,
                    verbose_name='الأولوية'
                )),
                ('notes', models.TextField(blank=True, verbose_name='ملاحظات')),
                ('justification', models.TextField(blank=True, verbose_name='التبرير/السبب')),
                ('approved_at', models.DateTimeField(blank=True, null=True, verbose_name='تاريخ الاعتماد')),
                ('approval_notes', models.TextField(blank=True, verbose_name='ملاحظات الاعتماد')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('requested_by', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='purchase_requests',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='طلب بواسطة'
                )),
                ('approved_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='approved_purchase_requests',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='اعتمد بواسطة'
                )),
                ('purchase_order', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='source_requests',
                    to='purchases.PurchaseOrder',
                    verbose_name='أمر الشراء المُحوّل'
                )),
            ],
            options={
                'verbose_name': 'طلب شراء',
                'verbose_name_plural': 'طلبات الشراء',
                'ordering': ['-date', '-id'],
            },
        ),
        migrations.CreateModel(
            name='PurchaseRequestItem',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('quantity', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='الكمية المطلوبة')),
                ('unit', models.CharField(blank=True, max_length=50, verbose_name='الوحدة')),
                ('estimated_price', models.DecimalField(
                    decimal_places=2,
                    default=Decimal('0'),
                    max_digits=12,
                    verbose_name='السعر التقديري'
                )),
                ('specifications', models.TextField(blank=True, verbose_name='المواصفات المطلوبة')),
                ('notes', models.TextField(blank=True, verbose_name='ملاحظات')),
                ('request', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='items',
                    to='purchases.PurchaseRequest',
                    verbose_name='طلب الشراء'
                )),
                ('product', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    to='inventory.Product',
                    verbose_name='المنتج'
                )),
            ],
            options={
                'verbose_name': 'بند طلب شراء',
                'verbose_name_plural': 'بنود طلبات الشراء',
            },
        ),
        
        # =============================
        # طلب عروض أسعار (RFQ)
        # =============================
        migrations.CreateModel(
            name='RFQ',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('number', models.CharField(max_length=50, unique=True, verbose_name='رقم RFQ')),
                ('title', models.CharField(max_length=200, verbose_name='العنوان')),
                ('date', models.DateField(default=django.utils.timezone.now, verbose_name='تاريخ الإصدار')),
                ('deadline', models.DateField(verbose_name='آخر موعد لتقديم العروض')),
                ('status', models.CharField(
                    choices=[
                        ('draft', 'مسودة'),
                        ('sent', 'مُرسل'),
                        ('received', 'استُلمت عروض'),
                        ('evaluated', 'تم التقييم'),
                        ('awarded', 'تم الترسية'),
                        ('cancelled', 'ملغى'),
                    ],
                    default='draft',
                    max_length=20,
                    verbose_name='الحالة'
                )),
                ('terms_conditions', models.TextField(blank=True, verbose_name='الشروط والأحكام')),
                ('payment_terms', models.TextField(blank=True, verbose_name='شروط الدفع')),
                ('delivery_terms', models.TextField(blank=True, verbose_name='شروط التسليم')),
                ('notes', models.TextField(blank=True, verbose_name='ملاحظات')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('purchase_request', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='rfqs',
                    to='purchases.PurchaseRequest',
                    verbose_name='طلب الشراء'
                )),
                ('created_by', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='created_rfqs',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='أنشئ بواسطة'
                )),
            ],
            options={
                'verbose_name': 'طلب عرض أسعار',
                'verbose_name_plural': 'طلبات عروض الأسعار',
                'ordering': ['-date', '-id'],
            },
        ),
        migrations.CreateModel(
            name='RFQItem',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('quantity', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='الكمية المطلوبة')),
                ('unit', models.CharField(blank=True, max_length=50, verbose_name='الوحدة')),
                ('specifications', models.TextField(blank=True, verbose_name='المواصفات')),
                ('target_price', models.DecimalField(
                    blank=True,
                    decimal_places=2,
                    max_digits=12,
                    null=True,
                    verbose_name='السعر المستهدف'
                )),
                ('rfq', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='items',
                    to='purchases.RFQ',
                    verbose_name='RFQ'
                )),
                ('product', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    to='inventory.Product',
                    verbose_name='المنتج'
                )),
            ],
            options={
                'verbose_name': 'بند طلب عرض أسعار',
                'verbose_name_plural': 'بنود طلبات عروض الأسعار',
            },
        ),
        migrations.CreateModel(
            name='RFQSupplier',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('invited_date', models.DateTimeField(default=django.utils.timezone.now, verbose_name='تاريخ الدعوة')),
                ('email_sent', models.BooleanField(default=False, verbose_name='تم إرسال البريد')),
                ('quotation_received', models.BooleanField(default=False, verbose_name='استلام العرض')),
                ('notes', models.TextField(blank=True, verbose_name='ملاحظات')),
                ('rfq', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='invited_suppliers',
                    to='purchases.RFQ'
                )),
                ('supplier', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    to='partners.Supplier',
                    verbose_name='المورد'
                )),
            ],
            options={
                'verbose_name': 'مورد مدعو',
                'verbose_name_plural': 'الموردون المدعوون',
                'unique_together': {('rfq', 'supplier')},
            },
        ),
        
        # =============================
        # عروض الموردين
        # =============================
        migrations.CreateModel(
            name='SupplierQuotation',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('number', models.CharField(max_length=50, unique=True, verbose_name='رقم العرض')),
                ('quotation_date', models.DateField(default=django.utils.timezone.now, verbose_name='تاريخ العرض')),
                ('valid_until', models.DateField(verbose_name='صالح حتى')),
                ('status', models.CharField(
                    choices=[
                        ('draft', 'مسودة'),
                        ('submitted', 'مُقدم'),
                        ('under_review', 'قيد المراجعة'),
                        ('accepted', 'مقبول'),
                        ('rejected', 'مرفوض'),
                        ('expired', 'منتهي'),
                    ],
                    default='draft',
                    max_length=20,
                    verbose_name='الحالة'
                )),
                ('payment_terms', models.TextField(blank=True, verbose_name='شروط الدفع')),
                ('delivery_time', models.IntegerField(default=0, verbose_name='مدة التوريد (أيام)')),
                ('warranty_period', models.CharField(blank=True, max_length=100, verbose_name='فترة الضمان')),
                ('shipping_cost', models.DecimalField(
                    decimal_places=2,
                    default=Decimal('0'),
                    max_digits=12,
                    verbose_name='تكلفة الشحن'
                )),
                ('tax_amount', models.DecimalField(
                    decimal_places=2,
                    default=Decimal('0'),
                    max_digits=12,
                    verbose_name='قيمة الضريبة'
                )),
                ('discount', models.DecimalField(
                    decimal_places=2,
                    default=Decimal('0'),
                    max_digits=12,
                    verbose_name='الخصم'
                )),
                ('notes', models.TextField(blank=True, verbose_name='ملاحظات')),
                ('attachments', models.FileField(
                    blank=True,
                    null=True,
                    upload_to='quotations/%Y/%m/',
                    verbose_name='المرفقات'
                )),
                ('evaluation_score', models.DecimalField(
                    blank=True,
                    decimal_places=2,
                    max_digits=5,
                    null=True,
                    verbose_name='درجة التقييم'
                )),
                ('evaluation_notes', models.TextField(blank=True, verbose_name='ملاحظات التقييم')),
                ('evaluated_at', models.DateTimeField(blank=True, null=True, verbose_name='تاريخ التقييم')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('rfq', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='quotations',
                    to='purchases.RFQ',
                    verbose_name='RFQ'
                )),
                ('supplier', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='quotations',
                    to='partners.Supplier',
                    verbose_name='المورد'
                )),
                ('evaluated_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='evaluated_quotations',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='قيّم بواسطة'
                )),
            ],
            options={
                'verbose_name': 'عرض سعر مورد',
                'verbose_name_plural': 'عروض أسعار الموردين',
                'ordering': ['-quotation_date', '-id'],
            },
        ),
        migrations.CreateModel(
            name='QuotationItem',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('quantity', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='الكمية')),
                ('unit_price', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='سعر الوحدة')),
                ('unit', models.CharField(blank=True, max_length=50, verbose_name='الوحدة')),
                ('brand', models.CharField(blank=True, max_length=100, verbose_name='الماركة/المصنع')),
                ('model', models.CharField(blank=True, max_length=100, verbose_name='الموديل')),
                ('specifications', models.TextField(blank=True, verbose_name='المواصفات')),
                ('notes', models.TextField(blank=True, verbose_name='ملاحظات')),
                ('quotation', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='items',
                    to='purchases.SupplierQuotation',
                    verbose_name='عرض السعر'
                )),
                ('rfq_item', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    to='purchases.RFQItem',
                    verbose_name='بند RFQ'
                )),
                ('product', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    to='inventory.Product',
                    verbose_name='المنتج'
                )),
            ],
            options={
                'verbose_name': 'بند عرض سعر',
                'verbose_name_plural': 'بنود عروض الأسعار',
            },
        ),
        
        # =============================
        # السجل التاريخي للأسعار
        # =============================
        migrations.CreateModel(
            name='ProductPriceHistory',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('price', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='السعر')),
                ('quantity', models.DecimalField(
                    decimal_places=2,
                    default=Decimal('1'),
                    max_digits=12,
                    verbose_name='الكمية'
                )),
                ('currency', models.CharField(default='EGP', max_length=10, verbose_name='العملة')),
                ('date', models.DateField(default=django.utils.timezone.now, verbose_name='التاريخ')),
                ('source', models.CharField(
                    choices=[
                        ('quotation', 'عرض سعر'),
                        ('purchase_bill', 'فاتورة شراء'),
                        ('purchase_order', 'أمر شراء'),
                        ('manual', 'إدخال يدوي'),
                    ],
                    max_length=20,
                    verbose_name='المصدر'
                )),
                ('notes', models.TextField(blank=True, verbose_name='ملاحظات')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('product', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='price_history',
                    to='inventory.Product',
                    verbose_name='المنتج'
                )),
                ('supplier', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='product_prices',
                    to='partners.Supplier',
                    verbose_name='المورد'
                )),
                ('quotation', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='price_records',
                    to='purchases.SupplierQuotation'
                )),
                ('purchase_bill', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='price_records',
                    to='purchases.PurchaseBill'
                )),
                ('purchase_order', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='price_records',
                    to='purchases.PurchaseOrder'
                )),
            ],
            options={
                'verbose_name': 'سجل سعر منتج',
                'verbose_name_plural': 'السجل التاريخي للأسعار',
                'ordering': ['-date', '-id'],
            },
        ),
        
        # =============================
        # جدول التسليم
        # =============================
        migrations.CreateModel(
            name='SupplierLeadTime',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('product_category', models.CharField(blank=True, max_length=100, verbose_name='فئة المنتج')),
                ('lead_time_days', models.IntegerField(verbose_name='مدة التوريد (أيام)')),
                ('min_order_quantity', models.DecimalField(
                    blank=True,
                    decimal_places=2,
                    max_digits=12,
                    null=True,
                    verbose_name='الحد الأدنى للطلب'
                )),
                ('max_order_quantity', models.DecimalField(
                    blank=True,
                    decimal_places=2,
                    max_digits=12,
                    null=True,
                    verbose_name='الحد الأقصى للطلب'
                )),
                ('is_active', models.BooleanField(default=True, verbose_name='نشط')),
                ('notes', models.TextField(blank=True, verbose_name='ملاحظات')),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('supplier', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='lead_times',
                    to='partners.Supplier',
                    verbose_name='المورد'
                )),
                ('product', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='supplier_lead_times',
                    to='inventory.Product',
                    verbose_name='المنتج'
                )),
            ],
            options={
                'verbose_name': 'جدول توريد مورد',
                'verbose_name_plural': 'جداول التوريد',
                'unique_together': {('supplier', 'product')},
            },
        ),
        
        # =============================
        # الشحنات
        # =============================
        migrations.CreateModel(
            name='Shipment',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('number', models.CharField(max_length=50, unique=True, verbose_name='رقم الشحنة')),
                ('shipping_method', models.CharField(blank=True, max_length=100, verbose_name='طريقة الشحن')),
                ('carrier', models.CharField(blank=True, max_length=100, verbose_name='شركة الشحن')),
                ('tracking_number', models.CharField(blank=True, max_length=100, verbose_name='رقم التتبع')),
                ('awb_bl_number', models.CharField(blank=True, max_length=100, verbose_name='رقم بوليصة الشحن')),
                ('shipped_date', models.DateField(blank=True, null=True, verbose_name='تاريخ الشحن')),
                ('estimated_arrival', models.DateField(blank=True, null=True, verbose_name='التاريخ المتوقع للوصول')),
                ('actual_arrival', models.DateField(blank=True, null=True, verbose_name='تاريخ الوصول الفعلي')),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'معلقة'),
                        ('in_transit', 'في الطريق'),
                        ('customs', 'في الجمارك'),
                        ('arrived', 'وصلت'),
                        ('received', 'استُلمت'),
                        ('delayed', 'متأخرة'),
                        ('cancelled', 'ملغاة'),
                    ],
                    default='pending',
                    max_length=20,
                    verbose_name='الحالة'
                )),
                ('shipping_cost', models.DecimalField(
                    decimal_places=2,
                    default=Decimal('0'),
                    max_digits=12,
                    verbose_name='تكلفة الشحن'
                )),
                ('customs_cost', models.DecimalField(
                    decimal_places=2,
                    default=Decimal('0'),
                    max_digits=12,
                    verbose_name='تكلفة الجمارك'
                )),
                ('insurance_cost', models.DecimalField(
                    decimal_places=2,
                    default=Decimal('0'),
                    max_digits=12,
                    verbose_name='تكلفة التأمين'
                )),
                ('notes', models.TextField(blank=True, verbose_name='ملاحظات')),
                ('attachments', models.FileField(
                    blank=True,
                    null=True,
                    upload_to='shipments/%Y/%m/',
                    verbose_name='المستندات'
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('purchase_order', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='shipments',
                    to='purchases.PurchaseOrder',
                    verbose_name='أمر الشراء'
                )),
                ('supplier', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='shipments',
                    to='partners.Supplier',
                    verbose_name='المورد'
                )),
            ],
            options={
                'verbose_name': 'شحنة',
                'verbose_name_plural': 'الشحنات',
                'ordering': ['-shipped_date', '-id'],
            },
        ),
        
        # =============================
        # استلام الواردات
        # =============================
        migrations.CreateModel(
            name='GoodsReceipt',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('number', models.CharField(max_length=50, unique=True, verbose_name='رقم سند الاستلام')),
                ('receipt_date', models.DateTimeField(default=django.utils.timezone.now, verbose_name='تاريخ الاستلام')),
                ('status', models.CharField(
                    choices=[
                        ('draft', 'مسودة'),
                        ('completed', 'مكتمل'),
                        ('with_variance', 'مع اختلافات'),
                        ('rejected', 'مرفوض'),
                    ],
                    default='draft',
                    max_length=20,
                    verbose_name='الحالة'
                )),
                ('quality_status', models.CharField(
                    choices=[
                        ('passed', 'مقبول'),
                        ('failed', 'مرفوض'),
                        ('partial', 'قبول جزئي'),
                        ('pending', 'قيد الفحص'),
                    ],
                    default='pending',
                    max_length=20,
                    verbose_name='حالة الجودة'
                )),
                ('inspection_date', models.DateTimeField(blank=True, null=True, verbose_name='تاريخ الفحص')),
                ('inspection_notes', models.TextField(blank=True, verbose_name='ملاحظات الفحص')),
                ('notes', models.TextField(blank=True, verbose_name='ملاحظات')),
                ('attachments', models.FileField(
                    blank=True,
                    null=True,
                    upload_to='receipts/%Y/%m/',
                    verbose_name='المرفقات'
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('purchase_order', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='goods_receipts',
                    to='purchases.PurchaseOrder',
                    verbose_name='أمر الشراء'
                )),
                ('shipment', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='goods_receipts',
                    to='purchases.Shipment',
                    verbose_name='الشحنة'
                )),
                ('location', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='goods_receipts',
                    to='inventory.Location',
                    verbose_name='الموقع'
                )),
                ('inspected_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='inspected_receipts',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='فُحص بواسطة'
                )),
                ('received_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='received_goods',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='استلم بواسطة'
                )),
            ],
            options={
                'verbose_name': 'سند استلام',
                'verbose_name_plural': 'سندات الاستلام',
                'ordering': ['-receipt_date', '-id'],
            },
        ),
        migrations.CreateModel(
            name='GoodsReceiptItem',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('ordered_quantity', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='الكمية المطلوبة')),
                ('received_quantity', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='الكمية المستلمة')),
                ('accepted_quantity', models.DecimalField(
                    decimal_places=2,
                    default=Decimal('0'),
                    max_digits=12,
                    verbose_name='الكمية المقبولة'
                )),
                ('rejected_quantity', models.DecimalField(
                    decimal_places=2,
                    default=Decimal('0'),
                    max_digits=12,
                    verbose_name='الكمية المرفوضة'
                )),
                ('quality_grade', models.CharField(
                    choices=[
                        ('excellent', 'ممتاز'),
                        ('good', 'جيد'),
                        ('acceptable', 'مقبول'),
                        ('poor', 'ضعيف'),
                        ('rejected', 'مرفوض'),
                    ],
                    default='good',
                    max_length=20,
                    verbose_name='تقييم الجودة'
                )),
                ('quality_notes', models.TextField(blank=True, verbose_name='ملاحظات الجودة')),
                ('variance_reason', models.TextField(blank=True, verbose_name='سبب الاختلاف')),
                ('rejection_reason', models.TextField(blank=True, verbose_name='سبب الرفض')),
                ('notes', models.TextField(blank=True, verbose_name='ملاحظات')),
                ('receipt', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='items',
                    to='purchases.GoodsReceipt',
                    verbose_name='سند الاستلام'
                )),
                ('purchase_order_item', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    to='purchases.PurchaseOrderItem',
                    verbose_name='بند أمر الشراء'
                )),
                ('product', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    to='inventory.Product',
                    verbose_name='المنتج'
                )),
            ],
            options={
                'verbose_name': 'بند سند استلام',
                'verbose_name_plural': 'بنود سندات الاستلام',
            },
        ),
        
        # =============================
        # الفهارس (Indexes)
        # =============================
        migrations.AddIndex(
            model_name='purchaserequest',
            index=models.Index(fields=['status', 'date'], name='pr_status_date_idx'),
        ),
        migrations.AddIndex(
            model_name='purchaserequest',
            index=models.Index(fields=['requested_by', 'date'], name='pr_reqby_date_idx'),
        ),
        migrations.AddIndex(
            model_name='supplierquotation',
            index=models.Index(fields=['rfq', 'supplier'], name='quot_rfq_supp_idx'),
        ),
        migrations.AddIndex(
            model_name='supplierquotation',
            index=models.Index(fields=['status', 'quotation_date'], name='quot_stat_date_idx'),
        ),
        migrations.AddIndex(
            model_name='productpricehistory',
            index=models.Index(fields=['product', 'supplier', 'date'], name='pph_prod_supp_date'),
        ),
        migrations.AddIndex(
            model_name='productpricehistory',
            index=models.Index(fields=['product', 'date'], name='pph_prod_date_idx'),
        ),
        migrations.AddIndex(
            model_name='supplierleadtime',
            index=models.Index(fields=['supplier', 'is_active'], name='slt_supp_active_idx'),
        ),
        migrations.AddIndex(
            model_name='shipment',
            index=models.Index(fields=['purchase_order', 'status'], name='ship_po_stat_idx'),
        ),
        migrations.AddIndex(
            model_name='shipment',
            index=models.Index(fields=['tracking_number'], name='ship_track_idx'),
        ),
        migrations.AddIndex(
            model_name='goodsreceipt',
            index=models.Index(fields=['purchase_order', 'status'], name='gr_po_stat_idx'),
        ),
        migrations.AddIndex(
            model_name='goodsreceipt',
            index=models.Index(fields=['receipt_date'], name='gr_date_idx'),
        ),
    ]
