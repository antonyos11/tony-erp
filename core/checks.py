from __future__ import annotations
from django.core.checks import register, Error, Warning, Tags
from django.apps import apps


@register(Tags.templates)
def money_filter_registered(app_configs, **kwargs):  # pragma: no cover - lightweight diagnostic
    errors = []
    try:
        from django.template import engines
        eng = engines['django']
        filters = getattr(eng.engine, 'filters', {})
        if 'money' not in filters:
            errors.append(Warning(
                "Template filter 'money' not registered at startup.",
                hint="Ensure 'core.templatetags.money_tags' is listed under TEMPLATES[0]['OPTIONS']['builtins']",
                id='core.W001'
            ))
    except Exception as e:  # silent fail converted to warning
        errors.append(Warning(
            f"Could not verify money filter: {e}",
            id='core.W002'
        ))
    return errors


@register(Tags.database)
def inventory_location_min_stock_column(app_configs, **kwargs):  # pragma: no cover
    """Check that inventory_location has min_stock column to avoid OperationalError."""
    errors = []
    try:
        from django.db import connection
        with connection.cursor() as cur:
            cur.execute("PRAGMA table_info('inventory_location')")
            cols = {r[1] for r in cur.fetchall()}  # second field is column name in PRAGMA output
        if 'min_stock' not in cols:
            errors.append(Error(
                "Missing column inventory_location.min_stock",
                hint="Run migrations or create a data migration adding min_stock to inventory.Location model.",
                id='core.E001'
            ))
    except Exception as e:
        errors.append(Warning(
            f"Could not introspect inventory_location table: {e}",
            id='core.W003'
        ))
    return errors
