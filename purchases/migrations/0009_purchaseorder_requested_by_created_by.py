"""
Empty migration to resolve merge conflict with 0009_purchaseorder_created_by_purchaseorder_requested_by.
This migration intentionally performs no operations.
"""

from django.db import migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('purchases', '0008_alter_purchaseorder_status'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = []
