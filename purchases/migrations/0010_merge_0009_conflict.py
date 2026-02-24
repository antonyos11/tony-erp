# Merge migration to resolve conflicting 0009 migrations
from django.db import migrations
from django.conf import settings

class Migration(migrations.Migration):
    # Transform this file into a no-op that simply chains after the
    # canonical merge migration 0010_merge_20250824_1943 to remove the
    # conflicting leaf nodes without deleting a file that might already
    # be referenced in some environments.
    dependencies = [
        ('purchases', '0010_merge_20250824_1943'),
    ]

    operations = []
