from django.db import migrations, models
from decimal import Decimal
from django.db.models import Sum, F, ExpressionWrapper, DecimalField


def backfill_cached_total(apps, schema_editor):
    Invoice = apps.get_model('sales', 'Invoice')
    InvoiceItem = apps.get_model('sales', 'InvoiceItem')
    line_total = ExpressionWrapper(F('quantity') * F('price'), output_field=DecimalField(max_digits=12, decimal_places=2))
    sums = (InvoiceItem.objects.values('invoice_id')
            .annotate(total=Sum(line_total)))
    total_map = {row['invoice_id']: row['total'] for row in sums}
    batch = []
    for inv in Invoice.objects.all().only('id'):
        val = total_map.get(inv.id)
        if val:
            inv.cached_total = val
            batch.append(inv)
    if batch:
        Invoice.objects.bulk_update(batch, ['cached_total'])


class Migration(migrations.Migration):
    dependencies = [
        ('sales', '0011_cleanup_duplicate_print_permission'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='cached_total',
            field=models.DecimalField(default=Decimal('0'), max_digits=12, decimal_places=2, help_text='مجموع الفاتورة مخزن لتسريع التحقق تحت SQLite'),
        ),
        migrations.RunPython(backfill_cached_total, migrations.RunPython.noop),
    ]
