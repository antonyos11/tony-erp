"""Deprecated migration placeholder to avoid conflict; original 0012_location_showroom removed in favor of 0012_location_owning_showroom.

This file is intentionally left without operations. Safe to keep for existing databases that may
have applied the old migration name locally. New deployments should only apply 0012_location_owning_showroom.
"""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('inventory', '0011_product_internal_code_product_is_third_party'),
    ]

    operations = []
