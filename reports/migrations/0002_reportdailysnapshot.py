from django.db import migrations, models
import django.utils.timezone
from decimal import Decimal


class Migration(migrations.Migration):
    dependencies = [
        ('reports', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ReportDailySnapshot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(db_index=True)),
                ('created_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('net_revenue', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=18)),
                ('expenses', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=18)),
                ('cogs_approx', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=18)),
                ('cogs_fifo', models.DecimalField(blank=True, decimal_places=2, max_digits=18, null=True)),
                ('cogs_weighted', models.DecimalField(blank=True, decimal_places=2, max_digits=18, null=True)),
                ('closing_inventory_value', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=18)),
            ],
            options={
                'ordering': ['-date'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='reportdailysnapshot',
            unique_together={('date',)},
        ),
    ]
