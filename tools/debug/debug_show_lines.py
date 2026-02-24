import pathlib, sys
p = pathlib.Path(r'd:\الشامل\fleet\views.py')
lines = p.read_text(encoding='utf-8', errors='replace').splitlines()
for i,l in enumerate(lines,1):
    if 80 <= i <= 140:
        print(f'{i:03d}: {repr(l)}')
