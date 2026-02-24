from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('sales', '0006_invoicepayment_print_tracking'),
    ]

    operations = [
        # No schema changes: added runtime validation + monthly sequence + post_delete recalculation.
    ]
