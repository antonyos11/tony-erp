import os, sys
root = os.path.dirname(__file__)
removed = []
for dirpath, dirnames, filenames in os.walk(root):
    if '__pycache__' in dirpath or True:
        for f in filenames:
            if f.endswith('.pyc'):
                full = os.path.join(dirpath, f)
                try:
                    os.remove(full)
                    removed.append(full)
                except Exception as e:
                    print('Failed removing', full, e)
print('Removed', len(removed), 'pyc files')
