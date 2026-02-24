#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
Quick Django diagnostics: prints environment, paths, and settings info,
then attempts django.setup() to catch early import errors.
Run from PowerShell:

  Set-Location d:\الشامل\الشامل\الشامل\app
  $env:ERP_STARTUP_DEBUG="1"
  python .\quick_diag.py

"""
import os
import sys
import unicodedata
import traceback

# Normalize and ensure project root in sys.path
PROJECT_ROOT = unicodedata.normalize('NFC', os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')

# Force UTF-8 where possible and provide a robust safe_print
try:
    if hasattr(sys.stdout, 'reconfigure') and callable(getattr(sys.stdout, 'reconfigure', None)):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # type: ignore
    if hasattr(sys.stderr, 'reconfigure') and callable(getattr(sys.stderr, 'reconfigure', None)):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')  # type: ignore
except Exception:
    pass

def safe_print(*args, **kwargs):
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        parts = []
        for a in args:
            try:
                s = str(a)
            except Exception:
                s = repr(a)
            try:
                s2 = s.encode('ascii', 'backslashreplace').decode('ascii')
            except Exception:
                s2 = ''.join(ch if ord(ch) < 128 else '?' for ch in s)
            parts.append(s2)
        try:
            print(*parts, **kwargs)
        except Exception:
            # Last resort: write to stderr as ascii-safe
            try:
                sys.stderr.write(' '.join(parts) + '\n')
            except Exception:
                pass

safe_print('[diag] Python:', sys.version)
safe_print('[diag] CWD:', os.getcwd())
safe_print('[diag] Script dir:', PROJECT_ROOT)
safe_print('[diag] First sys.path entries:', sys.path[:5])

# Mirror settings.py .env resolution
from pathlib import Path
base_dir = Path(__file__).resolve().parent
env_path = base_dir / '.env'
safe_print('[diag] Expect .env at:', str(env_path))
safe_print('[diag] .env exists?', env_path.exists())

# Try importing settings
try:
    from accountant_pro import settings as s
    safe_print('[diag] Settings import: OK')
    safe_print('[diag] BASE_DIR:', s.BASE_DIR)
    safe_print('[diag] DEBUG:', getattr(s, 'DEBUG', None))
    safe_print('[diag] ENVIRONMENT:', getattr(s, 'ENVIRONMENT', None))
    safe_print('[diag] ALLOWED_HOSTS (first 8):', getattr(s, 'ALLOWED_HOSTS', [])[:8])
    try:
        db = s.DATABASES.get('default', {})
    except Exception:
        db = {}
    safe_print('[diag] DB ENGINE:', db.get('ENGINE'))
    safe_print('[diag] DB NAME:', db.get('NAME'))
except SystemExit as e:
    safe_print('[diag] SystemExit during settings import, code=', getattr(e, 'code', None))
    raise
except Exception:
    safe_print('[diag] ERROR: Failed to import settings:')
    traceback.print_exc()
    sys.exit(2)

# Try full Django setup
try:
    import django
    safe_print('[diag] Django version:', django.get_version())
    django.setup()
    safe_print('[diag] django.setup(): OK')
except SystemExit as e:
    safe_print('[diag] SystemExit during django.setup(), code=', getattr(e, 'code', None))
    raise
except Exception:
    safe_print('[diag] ERROR during django.setup():')
    traceback.print_exc()
    sys.exit(3)

safe_print('[diag] All good. You can run the server now.')
