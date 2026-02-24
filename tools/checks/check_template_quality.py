# -*- coding: utf-8 -*-
"""
فحص جودة القوالب - تحديد القوالب التي تحتاج تطوير
"""
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path

templates_dir = Path('templates')

def analyze_template(file_path):
    try:
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        content_lower = content.lower()
        lines = content.strip().split('\n')
        size = len(content.strip())
        
        stub_indicators = [
            'stub template', 'placeholder', 'todo:', 'coming soon',
            'under construction'
        ]
        is_stub = any(ind in content_lower for ind in stub_indicators)
        
        has_form = '<form' in content_lower
        has_table = '<table' in content_lower
        has_list = '<ul' in content_lower or '<ol' in content_lower
        has_cards = 'card' in content_lower
        has_content = has_form or has_table or has_list or has_cards
        
        extends_base = '{% extends' in content
        has_bootstrap = 'class=' in content and ('btn' in content or 'form-' in content or 'table' in content)
        
        return {
            'path': str(file_path.relative_to(templates_dir)),
            'size': size,
            'lines': len(lines),
            'is_stub': is_stub,
            'has_content': has_content,
            'extends_base': extends_base,
            'has_styling': has_bootstrap,
        }
    except Exception as e:
        return None

results = []
for html_file in templates_dir.rglob('*.html'):
    rel_path = str(html_file.relative_to(templates_dir))
    if rel_path.startswith('_') or '/emails/' in rel_path or 'partials/' in rel_path or 'components/' in rel_path:
        continue
    result = analyze_template(html_file)
    if result:
        results.append(result)

stub_templates = [r for r in results if r.get('is_stub')]
minimal_templates = [r for r in results if r['size'] < 500 and not r.get('is_stub')]
no_content_templates = [r for r in results if not r.get('has_content') and r['size'] < 2000 and r.get('extends_base')]

print('='*80)
print('Template Quality Report')
print('='*80)
print(f'Total templates checked: {len(results)}')
print(f'Stub templates: {len(stub_templates)}')
print(f'Minimal content (<500 chars): {len(minimal_templates)}')
print(f'No real content: {len(no_content_templates)}')

if stub_templates:
    print('\n' + '='*80)
    print(f'STUB TEMPLATES ({len(stub_templates)}):')
    for t in sorted(stub_templates, key=lambda x: x['path'])[:30]:
        print(f"  {t['path']} ({t['size']} chars)")

if minimal_templates:
    print('\n' + '='*80)
    print(f'MINIMAL TEMPLATES ({len(minimal_templates)}):')
    for t in sorted(minimal_templates, key=lambda x: x['size'])[:30]:
        print(f"  {t['path']} ({t['size']} chars)")

if no_content_templates:
    print('\n' + '='*80)
    print(f'NO REAL CONTENT TEMPLATES ({len(no_content_templates)}):')
    for t in sorted(no_content_templates, key=lambda x: x['path'])[:30]:
        print(f"  {t['path']} ({t['size']} chars)")

print('\n' + '='*80)
print('Done!')
