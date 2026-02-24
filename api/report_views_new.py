"""Alias copy of report_views for diagnostic import resolution.

If importing this module succeeds while the original triggers a phantom
SyntaxError, it indicates Python is loading a different physical file when
resolving 'api.report_views' (possibly due to path normalization / caching).
"""
from .report_views import *  # noqa
