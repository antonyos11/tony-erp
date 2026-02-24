"""Find spec for api.report_views without importing and dump path + first 60 lines.
Creates file: report_views_spec_dump.txt
Run: python find_report_views_spec.py
"""
import sys, os, importlib.machinery
OUT = 'report_views_spec_dump.txt'

def main():
    # Ensure project root on path
    root = os.path.dirname(__file__)
    if root not in sys.path:
        sys.path.insert(0, root)
    spec = importlib.machinery.PathFinder.find_spec('api.report_views', sys.path)
    with open(OUT, 'w', encoding='utf-8') as f:
        if not spec:
            f.write('NO SPEC FOUND\n')
            return
        f.write(f'ORIGIN: {spec.origin}\n')
        path = spec.origin
        if not path or not os.path.isfile(path):
            f.write('Origin not a file\n')
            return
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as fh:
                for i in range(60):
                    line = fh.readline()
                    if not line:
                        break
                    f.write(f'{i+1:03d}: {line}')
        except OSError as e:
            f.write(f'ERROR reading origin: {e}\n')

if __name__ == '__main__':
    main()
