"""Secondary merge to point to canonical merge and remove duplicate leaf."""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('purchases', '0010_merge_20250824_1943'),
    ]

    operations = []
