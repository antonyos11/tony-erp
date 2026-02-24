from django.db import migrations

class Migration(migrations.Migration):
    """No-op migration documenting earlier duplicate numbering (0002 variants).

    This migration intentionally does nothing; it serves as an anchor so that
    future migrations have a clear, monotonically increasing sequence after
    resolving historical duplicate numbering in the repository. DO NOT REMOVE.
    """
    dependencies = [
        ('core', '0014_set_egp_default_currency'),
    ]
    operations = []
