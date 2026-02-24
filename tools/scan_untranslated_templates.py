import re, os, sys, pathlib

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / 'templates'

ARABIC_RE = re.compile(r'[\u0600-\u06FF]+')
TRANS_TAG_RE = re.compile(r"\{%(?:-|)\s*trans\s+'([^']+)'\s*%}|\{%(?:-|)\s*blocktrans[\s%}]")

ignored_dirs = {'static', 'locale', 'node_modules'}

issues = []
for root, dirs, files in os.walk(TEMPLATES_DIR):
    dirs[:] = [d for d in dirs if d not in ignored_dirs]
    for f in files:
        if not f.endswith(('.html', '.txt')):
            continue
        path = pathlib.Path(root) / f
        text = path.read_text(encoding='utf-8', errors='ignore')
        # Remove existing trans blocks content markers to avoid false positives
        cleaned = re.sub(r'\{%.+?%\}', '', text, flags=re.DOTALL)
        for i, line in enumerate(text.splitlines(), start=1):
            if '{% trans' in line or '{% blocktrans' in line:
                continue
            if ARABIC_RE.search(line):
                # Heuristic: skip HTML comments
                if line.strip().startswith('<!--'):
                    continue
                issues.append((path.relative_to(BASE_DIR), i, line.strip()[:160]))

if not issues:
    print('No potential untranslated Arabic strings found.')
else:
    print('Potential untranslated Arabic strings:')
    for rel, ln, snippet in issues[:200]:
        print(f"{rel}:{ln}: {snippet}")
    if len(issues) > 200:
        print(f"... {len(issues)-200} more lines omitted")
    sys.exit(1)
