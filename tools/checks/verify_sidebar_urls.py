import os, re, json, sys
from pathlib import Path
BASE = Path(__file__).resolve().parent
CP_FILE = BASE/ 'core' / 'context_processors' / '__init__.py'
pattern = re.compile(r"'url':\s*'([^']+)'")
urls = []
text = CP_FILE.read_text(encoding='utf-8')
for m in pattern.finditer(text):
    val = m.group(1)
    if val.startswith('/'):
        continue
    if ':' in val:  # likely namespaced name
        urls.append(val)
# de-duplicate preserving order
seen = set(); ordered = []
for u in urls:
    if u not in seen:
        ordered.append(u); seen.add(u)
# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','accountant_pro.settings')
try:
    import django
    django.setup()
    from django.urls import reverse
except Exception as e:
    print(json.dumps({'error':'django_setup_failed','detail':str(e)}))
    sys.exit(1)
results = []
for name in ordered:
    try:
        resolved = reverse(name)
        ok = True
    except Exception as e:
        resolved = None; ok = False
    results.append({'name':name,'ok':ok,'resolved':resolved})
print(json.dumps(results, ensure_ascii=False, indent=2))
