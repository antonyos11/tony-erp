"""Dump the actually imported api.report_views module file path and its first 120 lines.
Creates file: report_views_runtime_dump.txt
Run: python dump_report_views_runtime.py
"""
import importlib, inspect, os, sys, traceback

OUT = 'report_views_runtime_dump.txt'

def main():
    try:
        mod = importlib.import_module('api.report_views')
    except Exception as e:
        with open(OUT, 'w', encoding='utf-8') as f:
            f.write('IMPORT ERROR:\n')
            traceback.print_exc(file=f)
        return
    path = getattr(mod, '__file__', 'NO_FILE')
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as fh:
            content = fh.readlines()
    except OSError as e:
        content = [f'Could not read file: {e}\n']
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write(f'PATH: {path}\n')
        for i, line in enumerate(content[:120], start=1):
            f.write(f'{i:03d}: {line}')
        f.write('\n--- EOF (truncated) ---\n')

if __name__ == '__main__':
    main()
