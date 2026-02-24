"""Utility script to unify template inheritance.

Scans templates directory and replaces any of the legacy extends forms:
  {% extends 'base.html' %}
  {% extends "base.html" %}
  {% extends base_template|default:'base.html' %}
with the unified:
  {% extends BASE_TEMPLATE %}

Idempotent: running multiple times is safe.
Skips base.html (legacy wrapper) and base_v2.html.
"""
from __future__ import annotations
import pathlib
import re
import sys

TEMPLATES_DIR = pathlib.Path(__file__).resolve().parent.parent / 'templates'

PATTERNS = [
    re.compile(r"{\%\s*extends\s*'base\.html'\s*%}"),
    re.compile(r"{\%\s*extends\s*\"base\.html\"\s*%}"),
    re.compile(r"{\%\s*extends\s*base_template\|default:'base\.html'\s*%}"),
    re.compile(r"{\%\s*extends\s*base_template\|default:\"base\.html\"\s*%}"),
]

REPLACEMENT = "{% extends BASE_TEMPLATE %}"

def process_file(path: pathlib.Path) -> bool:
    if path.name in ("base.html", "base_v2.html"):
        return False
    try:
        text = path.read_text(encoding='utf-8')
    except Exception as e:
        print(f"Skip {path}: {e}")
        return False
    original = text
    for pat in PATTERNS:
        text = pat.sub(REPLACEMENT, text)
    if text != original:
        path.write_text(text, encoding='utf-8')
        return True
    return False

def main():
    if not TEMPLATES_DIR.exists():
        print(f"Templates directory not found: {TEMPLATES_DIR}", file=sys.stderr)
        return 1
    changed = 0
    total = 0
    for html_file in TEMPLATES_DIR.rglob('*.html'):
        total += 1
        if process_file(html_file):
            changed += 1
    print(f"Scanned {total} template files. Updated {changed} files.")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
