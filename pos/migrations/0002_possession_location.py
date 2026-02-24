from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ("pos", "0001_initial"),
        ("inventory", "0009_issue_inventory_i_status_e12400_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="possession",
            name="location",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='pos_sessions', to='inventory.location', verbose_name='الموقع / المعرض'),
        ),
    ]
