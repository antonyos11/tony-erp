#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
import unicodedata

# --- Begin path normalization / de-dup to avoid shadow imports for 'api' package ---
PROJECT_ROOT = unicodedata.normalize('NFC', os.path.dirname(os.path.abspath(__file__)))

# Ensure project root is first
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Remove duplicate path entries that differ only by unicode normalization or case
_norm_map = {}
_new_sys_path = []
for p in sys.path:
    norm = unicodedata.normalize('NFC', os.path.abspath(p)).lower()
    if norm in _norm_map:
        continue
    _norm_map[norm] = p
    _new_sys_path.append(p)
sys.path[:] = _new_sys_path

os.environ.setdefault('API_SYS_PATH_CANON', ';'.join(sys.path[:10]))  # first few entries for debugging
# --- End path normalization block ---

# Force UTF-8 for stdio on Windows consoles to avoid UnicodeEncodeError
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')

# Improve console robustness on Windows (cp1252) by forcing UTF-8 when possible
try:  # pragma: no cover - environment dependent
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
            try:
                sys.stderr.write(' '.join(parts) + '\n')
            except Exception:
                pass


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
    if os.environ.get('ERP_STARTUP_DEBUG'):
        safe_print('[startup] manage.py beginning main()', flush=True)
        safe_print('[startup] Python:', sys.version, flush=True)
        safe_print('[startup] CWD:', os.getcwd(), flush=True)
        safe_print('[startup] DJANGO_SETTINGS_MODULE:', os.environ.get('DJANGO_SETTINGS_MODULE'), flush=True)
        safe_print('[startup] First sys.path entries:', sys.path[:5], flush=True)
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        if os.environ.get('ERP_STARTUP_DEBUG'):
            import traceback; traceback.print_exc()
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    try:
        from django.utils import encoding
        encoding.force_text = encoding.force_str
    except ImportError:
        pass

    try:
        execute_from_command_line(sys.argv)
    except SystemExit as e:  # capture early exits for diagnosis
        if os.environ.get('ERP_STARTUP_DEBUG'):
            safe_print(f'[startup] SystemExit caught (code={getattr(e, "code", None)})', flush=True)
        raise
    except Exception as e:  # pragma: no cover
        if os.environ.get('ERP_STARTUP_DEBUG'):
            import traceback; traceback.print_exc()
        raise


if __name__ == '__main__':
    main()
