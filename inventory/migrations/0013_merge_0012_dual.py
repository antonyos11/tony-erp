from django.db import migrations

class Migration(migrations.Migration):
    """Merge placeholder for dual 0012 migrations (location_showroom / location_owning_showroom).
    Both are no-op placeholders; this resolves the graph conflict.
    """
    dependencies = [
        ('inventory', '0012_location_showroom'),
        ('inventory', '0012_location_owning_showroom'),
    ]
    operations = []
