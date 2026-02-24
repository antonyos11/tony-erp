from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0008_alter_modulepermission_id_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='managed_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='managed_users',
                to=settings.AUTH_USER_MODEL,
                verbose_name='المدير المباشر',
            ),
        ),
    ]
