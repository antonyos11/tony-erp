import importlib, pathlib, sys, json, inspect
info = {}
for name in ['api.urls','api.report_views','api.reporting_views']:
    try:
        m = importlib.import_module(name)
        info[name] = {
            'file': getattr(m,'__file__', None),
            'attrs_sample': [a for a in dir(m) if 'Report' in a][:12]
        }
    except Exception as e:
        info[name] = {'error': repr(e)}
path_entries = []
for p in sys.path:
    ap = pathlib.Path(p,'api','urls.py')
    if ap.exists():
        path_entries.append(str(ap))
with open('debug_import_urls_output.json','w', encoding='utf-8') as f:
    json.dump({'modules': info, 'candidate_api_urls_files': path_entries}, f, ensure_ascii=False, indent=2)
print('Wrote debug_import_urls_output.json')
