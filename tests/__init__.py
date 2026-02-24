"""Test package.

We set a default Django settings module so importing `tests.*` helpers doesn't
crash in environments where DJANGO_SETTINGS_MODULE isn't preconfigured.
"""

import os


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "accountant_pro.settings")