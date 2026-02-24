# Generated manually for adding bank fields to InvoicePayment
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('sales', '0014_invoicepayment_journal_entry'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoicepayment',
            name='bank_name',
            field=models.CharField(verbose_name='اسم البنك (مخصص للدفعة)', max_length=120, blank=True),
        ),
        migrations.AddField(
            model_name='invoicepayment',
            name='bank_account',
            field=models.CharField(verbose_name='رقم / IBAN الحساب (مخصص للدفعة)', max_length=120, blank=True),
        ),
    ]
