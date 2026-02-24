import os
import sys
import re

def _safe_out(text: str, *, error_prefix: str | None = None):
    """Print text safely even on narrow Windows consoles (cp1252).
    Falls back to ASCII replacement for unencodable characters.
    """
    try:
        print(text)
    except UnicodeEncodeError:
        cleaned = text.encode(sys.stdout.encoding or 'utf-8', errors='replace').decode(sys.stdout.encoding or 'utf-8', errors='ignore')
        try:
            print(cleaned)
        except Exception:
            # last resort: remove non-basic range
            fallback = ''.join(ch if ord(ch) < 128 else '?' for ch in text)
            print(fallback)

# Allowed basic Arabic letters, numbers, punctuation are fine; we only block emoji / symbols outside common ranges.
# We'll simply search for characters in the extended pictographic range or common emoji markers.
# Pattern targets surrogate pairs / extended symbols broadly.
EMOJI_PATTERN = re.compile(r"[\U0001F300-\U0001FAFF\U00002700-\U000027BF\U0001F1E6-\U0001F1FF]")

EXCLUDE_DIRS = {'.git', '.venv', '.venv_new', 'venv', 'node_modules', '__pycache__', 'migrations', 'static', 'media'}
ALLOWED_EXT = {'.py', '.md', '.txt', '.sh', '.bat', '.yml', '.yaml', '.json', '.cfg', '.ini'}


def scan_file(path):
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            for ln, line in enumerate(f, 1):
                if EMOJI_PATTERN.search(line):
                    yield ln, line.rstrip('\n')
    except Exception as e:
        print(f'تحذير: تعذر قراءة الملف {path}: {e}', file=sys.stderr)


def main():
    root = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    violations = []
    for dirpath, dirnames, filenames in os.walk(root):
        # تعديل قائمة الدلائل أثناء السير
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for name in filenames:
            ext = os.path.splitext(name)[1].lower()
            if ext and ext not in ALLOWED_EXT:
                continue
            full_path = os.path.join(dirpath, name)
            for ln, content in scan_file(full_path):
                violations.append((full_path, ln, content))

    if violations:
        _safe_out('تم العثور على استخدام رموز أو إيموجي غير مسموحة:')
        for path, ln, content in violations[:200]:  # حد للحجم
            _safe_out(f'- {path}:{ln}: {content}')
        _safe_out(f'الإجمالي: {len(violations)} سطر مخالف')
        sys.exit(1)
    else:
        _safe_out('فحص الترميز: لا توجد إيموجي أو رموز خاصة محظورة.')


if __name__ == '__main__':
    main()
