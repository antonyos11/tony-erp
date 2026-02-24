from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hr', '0013_employeeloan_loaninstallment_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='attendance_exempt',
            field=models.BooleanField(default=False, verbose_name='مستثنى من إلزام الحضور'),
        ),
    ]
