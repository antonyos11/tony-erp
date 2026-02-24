from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hr', '0007_alter_employeeidcard_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='leaverequest',
            name='replacement_employee',
            field=models.ForeignKey(
                to='hr.employee',
                on_delete=models.deletion.SET_NULL,
                null=True,
                blank=True,
                related_name='replacement_leave_requests',
                verbose_name='الموظف البديل أثناء الإجازة',
            ),
        ),
    ]
