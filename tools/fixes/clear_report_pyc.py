"""Utility script to delete api/report_views.* pyc caches.
Run: python clear_report_pyc.py
"""
import os, glob

def main():
    base = os.path.dirname(__file__)
    pattern = os.path.join(base, 'api', '__pycache__', 'report_views.*.pyc')
    removed = []
    for path in glob.glob(pattern):
        try:
            os.remove(path)
            removed.append(path)
        except OSError:
            pass
    print('Removed:', removed)

if __name__ == '__main__':
    main()
