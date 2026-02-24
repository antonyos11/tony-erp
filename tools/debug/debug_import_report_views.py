import importlib, linecache, os, sys, pathlib, traceback
OUT_FILE = pathlib.Path('debug_import_report_views_output.txt')
with OUT_FILE.open('w', encoding='utf-8') as out:
    def w(*a):
        print(*a, file=out, flush=True)
    try:
        w('Python version:', sys.version)
        w('CWD:', os.getcwd())
        w('Sys.path:')
        for p in sys.path:
            w('  ', p)
        mod = importlib.import_module('api.report_views')
        w('Imported module file:', getattr(mod, '__file__', None))
        mod_file = getattr(mod, '__file__', None)
        if isinstance(mod_file, str):
            src_path = pathlib.Path(mod_file.replace('.pyc', '.py'))
        else:
            src_path = pathlib.Path('UNKNOWN_SOURCE')
        w('Derived source path:', src_path)
        if src_path.exists():
            data = src_path.read_bytes()
            w('Source size bytes:', len(data))
            w('First 64 raw bytes:', data[:64])
            text = data.decode('utf-8', errors='replace').splitlines()
            w('Total lines in source:', len(text))
            for i, l in enumerate(text[:120], 1):
                w(f'{i:03d}: {l}')
        else:
            w('Source path does not exist')
        if hasattr(mod, 'ReportsPermission'):
            code = mod.ReportsPermission.has_permission.__code__
            w('has_permission filename:', code.co_filename)
            w('has_permission firstlineno:', code.co_firstlineno)
        else:
            w('ReportsPermission class not found')
    except Exception:
        w('EXCEPTION DURING DEBUG IMPORT:')
        w(traceback.format_exc())
print('Debug output written to', OUT_FILE)
