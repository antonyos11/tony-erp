from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ('reports', '0002_reportdailysnapshot'),
    ]

    operations = [
        migrations.CreateModel(
            name='ReportVarianceIncident',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, db_index=True)),
                ('report', models.CharField(max_length=120, db_index=True)),
                ('percent', models.FloatField(help_text='Variance percent magnitude (absolute value).')),
                ('threshold_used', models.FloatField(help_text='Effective threshold that triggered warning.')),
                ('global_min_applied', models.BooleanField(default=False)),
                ('date_from', models.DateField(null=True, blank=True, db_index=True)),
                ('date_to', models.DateField(null=True, blank=True, db_index=True)),
                ('extra', models.JSONField(null=True, blank=True)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='reportvarianceincident',
            index=models.Index(fields=['report', '-created_at'], name='reports_variance_report_created_idx'),
        ),
    ]
