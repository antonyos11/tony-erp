# Generated migration for Invoice Enhanced Features

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('partners', '0001_initial'),
        ('payments', '0001_initial'),
        ('sales', '0026_add_showroom_field'),  # استبدل برقم آخر migration
    ]

    operations = [
        # InvoiceTemplate
        migrations.CreateModel(
            name='InvoiceTemplate',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='اسم النموذج')),
                ('description', models.TextField(blank=True, verbose_name='الوصف')),
                ('discount', models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='الخصم')),
                ('is_tax_inclusive', models.BooleanField(default=False, verbose_name='السعر شامل الضريبة')),
                ('items_data', models.JSONField(default=list, help_text='قائمة الأصناف بصيغة JSON', verbose_name='بيانات الأصناف')),
                ('notes', models.TextField(blank=True, verbose_name='ملاحظات')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')),
                ('is_active', models.BooleanField(default=True, verbose_name='نشط')),
                ('usage_count', models.PositiveIntegerField(default=0, verbose_name='عدد مرات الاستخدام')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='invoice_templates', to=settings.AUTH_USER_MODEL, verbose_name='أنشأه')),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='partners.customer', verbose_name='العميل')),
                ('payment_method', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='payments.paymentmethod', verbose_name='طريقة الدفع')),
            ],
            options={
                'verbose_name': 'نموذج فاتورة',
                'verbose_name_plural': 'نماذج الفواتير',
                'ordering': ['-usage_count', '-created_at'],
            },
        ),
        
        # InvoiceAutosave
        migrations.CreateModel(
            name='InvoiceAutosave',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('session_key', models.CharField(db_index=True, max_length=100, verbose_name='مفتاح الجلسة')),
                ('form_data', models.JSONField(default=dict, verbose_name='بيانات النموذج')),
                ('items_data', models.JSONField(default=list, verbose_name='بيانات الأصناف')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')),
                ('expires_at', models.DateTimeField(blank=True, null=True, verbose_name='تاريخ الانتهاء')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='المستخدم')),
            ],
            options={
                'verbose_name': 'حفظ تلقائي',
                'verbose_name_plural': 'الحفظ التلقائي',
                'ordering': ['-updated_at'],
                'unique_together': {('user', 'session_key')},
            },
        ),
        
        # InvoiceAttachment
        migrations.CreateModel(
            name='InvoiceAttachment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to='invoices/attachments/%Y/%m/', verbose_name='الملف')),
                ('original_filename', models.CharField(max_length=255, verbose_name='اسم الملف الأصلي')),
                ('file_type', models.CharField(blank=True, max_length=50, verbose_name='نوع الملف')),
                ('file_size', models.PositiveIntegerField(default=0, verbose_name='حجم الملف (بايت)')),
                ('description', models.CharField(blank=True, max_length=200, verbose_name='الوصف')),
                ('uploaded_at', models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الرفع')),
                ('invoice', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attachments', to='sales.invoice', verbose_name='الفاتورة')),
                ('uploaded_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='رفعه')),
            ],
            options={
                'verbose_name': 'مرفق فاتورة',
                'verbose_name_plural': 'مرفقات الفواتير',
                'ordering': ['-uploaded_at'],
            },
        ),
        
        # InvoiceHistory
        migrations.CreateModel(
            name='InvoiceHistory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('created', 'إنشاء'), ('updated', 'تحديث'), ('deleted', 'حذف'), ('restored', 'استعادة'), ('item_added', 'إضافة صنف'), ('item_removed', 'حذف صنف'), ('payment_added', 'إضافة دفعة')], max_length=20, verbose_name='الإجراء')),
                ('timestamp', models.DateTimeField(auto_now_add=True, verbose_name='الوقت')),
                ('changes', models.JSONField(default=dict, verbose_name='التغييرات')),
                ('previous_data', models.JSONField(blank=True, default=dict, verbose_name='البيانات السابقة')),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True, verbose_name='عنوان IP')),
                ('user_agent', models.CharField(blank=True, max_length=255, verbose_name='متصفح المستخدم')),
                ('invoice', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='history', to='sales.invoice', verbose_name='الفاتورة')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='المستخدم')),
            ],
            options={
                'verbose_name': 'سجل تغيير فاتورة',
                'verbose_name_plural': 'سجل تغييرات الفواتير',
                'ordering': ['-timestamp'],
            },
        ),
        
        # CustomerCreditLimit
        migrations.CreateModel(
            name='CustomerCreditLimit',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('credit_limit', models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='حد الائتمان')),
                ('current_balance', models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='الرصيد الحالي')),
                ('payment_days', models.PositiveIntegerField(default=0, help_text='عدد الأيام المسموح بها للدفع', verbose_name='أيام الدفع')),
                ('is_blocked', models.BooleanField(default=False, verbose_name='محظور')),
                ('block_reason', models.TextField(blank=True, verbose_name='سبب الحظر')),
                ('last_transaction_date', models.DateField(blank=True, null=True, verbose_name='تاريخ آخر معاملة')),
                ('last_payment_date', models.DateField(blank=True, null=True, verbose_name='تاريخ آخر دفعة')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')),
                ('customer', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='credit_limit_info', to='partners.customer', verbose_name='العميل')),
            ],
            options={
                'verbose_name': 'حد ائتمان عميل',
                'verbose_name_plural': 'حدود ائتمان العملاء',
            },
        ),
        
        # Indexes
        migrations.AddIndex(
            model_name='invoicetemplate',
            index=models.Index(fields=['customer', 'is_active'], name='sales_invoi_custome_idx'),
        ),
        migrations.AddIndex(
            model_name='invoicetemplate',
            index=models.Index(fields=['created_by', 'is_active'], name='sales_invoi_created_idx'),
        ),
        migrations.AddIndex(
            model_name='invoiceautosave',
            index=models.Index(fields=['user', 'updated_at'], name='sales_invoi_user_up_idx'),
        ),
        migrations.AddIndex(
            model_name='invoiceautosave',
            index=models.Index(fields=['expires_at'], name='sales_invoi_expires_idx'),
        ),
        migrations.AddIndex(
            model_name='invoicehistory',
            index=models.Index(fields=['invoice', '-timestamp'], name='sales_invoi_invoice_idx'),
        ),
        migrations.AddIndex(
            model_name='invoicehistory',
            index=models.Index(fields=['user', '-timestamp'], name='sales_invoi_user_ti_idx'),
        ),
    ]
