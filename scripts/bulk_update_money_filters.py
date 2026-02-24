import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGETS = [
    ROOT / 'templates',
    ROOT / 'dist' / 'TonyERP' / 'app' / 'templates',
    ROOT / '_migration_package' / 'src' / 'templates',
]

# Patterns to transform
# 1) {{ var|floatformat:2 }} {% currency_symbol %} => {{ var|money }}
# 2) {{ var|floatformat:0 }} {% currency_symbol %} => {{ var|money:'|0' }}
# 3) Standalone {{ var|floatformat:2 }} in probable monetary contexts (heuristic) skipped for now.

pattern_pairs = [
    (re.compile(r"\{\{\s*([^{}|]+?)\|floatformat:2\s*\}\}\s*\{%\s*currency_symbol\s*%\}"), r"{{ \1|money }}"),
    (re.compile(r"\{\{\s*([^{}|]+?)\|floatformat:0\s*\}\}\s*\{%\s*currency_symbol\s*%\}"), r"{{ \1|money:'|0' }}"),
]

# Files changed counter
total_files = 0
total_changed = 0
for base in TARGETS:
    if not base.exists():
        continue
    changed = 0
    files = 0
    for html in base.rglob('*.html'):
        try:
            text = html.read_text(encoding='utf-8')
        except Exception:
            continue
        original = text
        for rx, repl in pattern_pairs:
            text = rx.sub(repl, text)
        if text != original:
            bak = html.with_suffix(html.suffix + '.bak')
            if not bak.exists():
                bak.write_text(original, encoding='utf-8')
            html.write_text(text, encoding='utf-8')
            changed += 1
        files += 1
    print(f"[money-fix] {base}: files={files} modified={changed}")
    total_files += files
    total_changed += changed

print(f"Summary: files={total_files} modified={total_changed}")
print("Done. You may safely delete *.bak after verification.")
