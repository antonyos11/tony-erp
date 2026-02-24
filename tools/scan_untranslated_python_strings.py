#!/usr/bin/env python
"""Scan Python source files for bare Arabic strings that are not wrapped
in gettext translation calls (_(), gettext(), pgettext(), npgettext()).

Heuristic rules:
- Target only files inside whitelisted app directories.
- Skip migrations, tests, and virtual environments.
- A bare Arabic string is a literal containing any Arabic letter (\u0600-\u06FF)
  that is not preceded (on same line before quotes) by one of allowed wrappers.
- Ignore lines with '# no-i18n' marker.

Exit codes:
0 => No potential issues
1 => Potential untranslated strings found

This is a lightweight heuristic; it may produce false positives, which can be
suppressed by adding the inline comment '# no-i18n'.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

APPS = ["api", "core", "sales", "inventory", "partners", "users"]
ALLOWED_WRAPPERS = re.compile(r"_(?:\.|\s*\(|$)|gettext\s*\(|pgettext\s*\(|npgettext\s*\(")
ARABIC_RE = re.compile(r"[\u0600-\u06FF]")
STRING_TOKEN_RE = re.compile(r"([rubfRUBF]*)(['\"])((?:\\.|(?!\2).)*)\2")

SKIP_DIR_NAMES = {"migrations", "tests", "__pycache__"}


def _safe_out(s: str):
    enc = getattr(sys.stdout, 'encoding', None) or 'utf-8'
    try:
        sys.stdout.write(s.encode(enc, 'replace').decode(enc, 'replace') + '\n')
    except Exception:
        sys.stdout.write(s.encode('ascii', 'replace').decode('ascii', 'replace') + '\n')


def is_python_file(path: Path) -> bool:
    return path.suffix == ".py"


def should_skip_dir(dirname: str) -> bool:
    return dirname in SKIP_DIR_NAMES or dirname.startswith('.')


def scan_file(path: Path) -> list[tuple[int, str]]:
    results: list[tuple[int, str]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:  # pragma: no cover - unlikely
        print(f"تعذر قراءة الملف {path}: {e}")
        return results
    for lineno, line in enumerate(text.splitlines(), 1):
        if "# no-i18n" in line:
            continue
        if not ARABIC_RE.search(line):  # quick reject
            continue
        # Skip translated wrappers
        if re.search(r"_(?:\s*\(|\s*\.)|_t\s*\(|gettext\s*\(|pgettext\s*\(|npgettext\s*\(", line):
            continue
        for m in STRING_TOKEN_RE.finditer(line):
            lit = m.group(3)
            if ARABIC_RE.search(lit):
                results.append((lineno, line.strip()))
                break
    return results


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    total = 0
    for app in APPS:
        app_path = root / app
        if not app_path.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(app_path):
            # prune
            dirnames[:] = [d for d in dirnames if not should_skip_dir(d)]
            for filename in filenames:
                if not filename.endswith('.py'):
                    continue
                file_path = Path(dirpath) / filename
                findings = scan_file(file_path)
                if findings:
                    _safe_out(f"ملف: {file_path}")
                    for lineno, snippet in findings[:5]:
                        _safe_out(f"  سطر {lineno}: {snippet}")
                    if len(findings) > 5:
                        _safe_out(f"  ... والمزيد ({len(findings)-5})")
                    total += len(findings)
    if total == 0:
        _safe_out("فحص النصوص العربية في بايثون: لا توجد سلاسل قد تحتاج ترجمة.")
        return 0
    strict = os.environ.get("STRICT_I18N") == "1"
    _safe_out(f"تم العثور على {total} سطر يحتوي على نص عربي محتمل بدون تغليف بالترجمة.")
    if strict:
        _safe_out("(وضع صارم) فشل الفحص لوجود نصوص غير مترجمة.")
        return 1
    else:
        _safe_out("(وضع تنبيهي فقط) لن يتم إيقاف العملية. أضف التغليف أو ضع # no-i18n عند الاقتضاء.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
