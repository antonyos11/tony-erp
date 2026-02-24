from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('fleet', '0004_driver_violation_advance_and_expense_driver'),
    ]

    operations = [
        migrations.AddField(
            model_name='trip',
            name='odometer_start',
            field=models.PositiveIntegerField(null=True, blank=True, verbose_name='قراءة العداد (بداية)'),
        ),
        migrations.AddField(
            model_name='trip',
            name='odometer_end',
            field=models.PositiveIntegerField(null=True, blank=True, verbose_name='قراءة العداد (نهاية)'),
        ),
    ]
