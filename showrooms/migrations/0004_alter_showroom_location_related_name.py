from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('showrooms', '0003_posdevice_deviceauthtoken_attendance'),
    ]

    operations = [
        # No-op: only Python related_name change on OneToOneField (Showroom.location)
    ]
