from django.db import migrations, models
import django.utils.timezone
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0002_alter_paymentmethod_type'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('sales', '0004_collectiontask_collection_status_idx_and_more'),
        ('partners', '__first__'),
    ]

    operations = [
        migrations.CreateModel(
            name='InvoicePayment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('receipt_number', models.CharField(blank=True, max_length=30, unique=True, verbose_name='رقم الإيصال')),
                ('date', models.DateTimeField(default=django.utils.timezone.now, verbose_name='التاريخ')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='المبلغ المدفوع')),
                ('reference', models.CharField(blank=True, max_length=100, verbose_name='مرجع (شيك/تحويل)')),
                ('description', models.TextField(blank=True, help_text='بيان توضيحي يظهر في الإيصال وكشف الحساب', verbose_name='وصف / بيان')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, related_name='created_invoice_payments', to=settings.AUTH_USER_MODEL, verbose_name='أنشئ بواسطة')),
                ('customer', models.ForeignKey(on_delete=models.deletion.PROTECT, related_name='invoice_payments', to='partners.customer', verbose_name='العميل')),
                ('invoice', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='payments', to='sales.invoice', verbose_name='الفاتورة')),
                ('payment_method', models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, to='payments.paymentmethod', verbose_name='طريقة الدفع')),
            ],
            options={
                'verbose_name': 'دفعة فاتورة',
                'verbose_name_plural': 'دفعات الفواتير',
                'ordering': ['-date', '-id'],
            },
        ),
        migrations.AddIndex(
            model_name='invoicepayment',
            index=models.Index(fields=['date'], name='invpay_date_idx'),
        ),
        migrations.AddIndex(
            model_name='invoicepayment',
            index=models.Index(fields=['receipt_number'], name='invpay_receipt_idx'),
        ),
    ]
