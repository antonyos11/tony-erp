"""Scan sys.path for any api/report_views.py copies and dump to scan_report_views_paths.txt"""
import os, sys
OUT = 'scan_report_views_paths.txt'

def main():
    hits = []
    for p in sys.path:
        try:
            candidate = os.path.join(p, 'api', 'report_views.py')
            if os.path.isfile(candidate):
                try:
                    size = os.path.getsize(candidate)
                except OSError:
                    size = -1
                hits.append((p, candidate, size))
        except Exception:
            continue
    with open(OUT, 'w', encoding='utf-8') as f:
        for base, path, size in hits:
            f.write(f'BASE:{base}\nFILE:{path}\nSIZE:{size}\n---\n')
    if not hits:
        with open(OUT, 'w', encoding='utf-8') as f:
            f.write('NO HITS')

if __name__ == '__main__':
    main()
