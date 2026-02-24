import sys, importlib, os, textwrap
print('Python:', sys.version)
print('CWD:', os.getcwd())
print('Sys.path entries (count=%d):' % len(sys.path))
for i,p in enumerate(sys.path):
    print('%2d:', i, p)
print('\nAttempting import of api.urls ...')
try:
    mod = importlib.import_module('api.urls')
    print('Imported api.urls OK. __file__ =', getattr(mod,'__file__',None))
    ident = getattr(mod,'API_URLS_IDENT', '<<NO IDENT ATTR>>')
    print('API_URLS_IDENT =', ident)
except Exception as e:
    print('Import api.urls FAILED:', e)

print('\nScanning sys.path for candidate api/urls.py files...')
found = []
for p in sys.path:
    candidate = os.path.join(p,'api','urls.py')
    if os.path.isfile(candidate):
        found.append(candidate)
print('Found %d candidate files:' % len(found))
for f in found:
    print(' -', f)

for f in found:
    try:
        print('\n---- BEGIN CONTENT (first 40 lines) of', f)
        with open(f,'r',encoding='utf-8', errors='replace') as fh:
            for idx,line in enumerate(fh):
                if idx>=40: break
                print('%03d:'% (idx+1), line.rstrip('\n'))
        print('---- END CONTENT of', f)
    except Exception as e:
        print('Could not read', f, e)
