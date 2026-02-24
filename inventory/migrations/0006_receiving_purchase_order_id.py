
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0005_issue_issueitem_receiving_receivingitem_stockbatch_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='receiving',
            name='purchase_order_id',
            field=models.IntegerField(blank=True, null=True, help_text='معرّف أمر الشراء المرتبط (اختياري)'),
        ),
    ]

