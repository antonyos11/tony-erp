"""Compatibility shim.

Historically the reporting API views lived in this module (report_views.py).
Due to a persistent phantom import / stale bytecode issue we migrated the
actual implementations to reporting_views.py. Some parts of the project or
cached .pyc files may still attempt to import api.report_views, which caused
spurious SyntaxError/ImportError during test collection.

To make the system robust regardless of which module name is imported, we
now simply re-export everything from reporting_views. This file should stay
lightweight and never contain executable top-level logic beyond the re-export
so that any stale cached version will still be safe.
"""

from .reporting_views import *  # noqa: F401,F403

# Explicit re-export list (optional; kept broad via wildcard for now). If we
# later want stricter control, we can define __all__ = [...].
