from django.contrib import admin

# Import advanced permissions and workflow admin registrations
try:
    from . import admin_permissions  # noqa: F401
except ImportError:
    pass
