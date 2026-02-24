# Merge the duplicate 0010 leaves so Django sees a single head
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('purchases', '0010_merge_0009_conflict'),
        ('purchases', '0010_merge_0009_conflicts'),
    ]

    operations = []
