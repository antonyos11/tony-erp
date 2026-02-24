from django.apps import AppConfig


class SalesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sales'

    def ready(self):
        """Register signals; defer DB-dependent permission creation until after migrations.

        Previous implementation executed a ContentType/Permission query during app
        initialization which triggers Django's RuntimeWarning about accessing the
        database before app registry is fully ready (especially with some DB backends
        or when running management commands like check/showmigrations).

        We now hook into the post_migrate signal so the permission is created only
        once the database schema is ensured.
        """
        from django.db.models.signals import post_migrate
        from django.dispatch import receiver

        @receiver(post_migrate, dispatch_uid='sales.ensure_print_customerstatement_perm')
        def _ensure_permission(sender, **kwargs):  # pragma: no cover (simple idempotent logic)
            if sender.name != 'sales':
                return
            try:
                from django.contrib.auth.models import Permission, ContentType
                from .models import Invoice
                ct = ContentType.objects.get_for_model(Invoice)
                Permission.objects.get_or_create(
                    codename='print_customerstatement',
                    content_type=ct,
                    defaults={'name': 'طباعة كشف حساب عميل'}
                )
            except Exception:
                # Swallow any exception silently to avoid impacting migrations; can be logged if needed.
                pass
