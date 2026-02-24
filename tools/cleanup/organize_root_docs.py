#!/usr/bin/env python
"""
تنظيم ملفات root directory المبعثرة
الاستخدام:
    python tools/cleanup/organize_root_docs.py --check
    python tools/cleanup/organize_root_docs.py --move
"""
import os
import shutil
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# الملفات التي يجب أن تبقى في root
KEEP_IN_ROOT = {
    'README.md', 'LICENSE', 'LICENSE.md', 'CHANGELOG.md',
    'Makefile', 'Dockerfile', 'manage.py', 'conftest.py',
    'requirements.txt', 'requirements-dev.txt', 'setup.py', 'setup.cfg',
    'pyproject.toml', 'pytest.ini', 'Procfile', '.gitignore',
    '.env', '.env.example', '.env.production',
    '.env.enterprise.example', '.env.prod.example',
    '.pre-commit-config.yaml', '.coveragerc',
    'docker-compose.yml', 'docker-compose.prod.yml',
    'docker-compose.enterprise.yml',
    # db.sqlite3 removed - database files should NEVER be in version control
}


def categorize(fname):
    """Determine the destination directory for a file."""
    name = fname.upper()

    # Python scripts in root that aren't manage.py/conftest.py
    if name.endswith('.PY') and fname not in KEEP_IN_ROOT:
        return 'archive/scripts/'

    # fix reports
    if any(kw in name for kw in ['FIX_REPORT', '500_FIX', 'ALL_FIXES', 'URLS_FIX', '500_SCAN', '500_ERROR']):
        return 'archive/fix_reports/'

    # achievement / completion / success reports
    if any(kw in name for kw in ['ACHIEVEMENT', 'SUCCESS', 'COMPLETION', 'CERTIFICATE',
                                  'CONGRATULATIONS', 'ANNOUNCEMENT']):
        return 'archive/reports/'

    # implementation / development docs
    if any(kw in name for kw in ['IMPLEMENTATION', 'DEVELOPMENT', 'DEPLOYED', 'DEPLOYMENT']):
        return 'archive/reports/'

    # feature docs
    if any(kw in name for kw in ['FEATURE', 'ADVANCED_', 'NEW_FEATURES', 'USER_GUIDE',
                                  'QUICK_START', 'QUICK_REFERENCE']):
        return 'archive/features/'

    # test / UAT docs
    if any(kw in name for kw in ['TESTSPRITE', 'UAT_', 'UAT-', 'TESTING_REPORT', 'TEST_PLAN']):
        return 'archive/testing/'

    # sidebar / UI docs
    if any(kw in name for kw in ['SIDEBAR', 'DARK_THEME', 'CLICK_FIX', 'BROWSER_CACHE',
                                  'CLEAR_CACHE', 'CLEAR_BROWSER']):
        return 'archive/ui_docs/'

    # setup / instructions
    if any(kw in name for kw in ['INSTRUCTIONS', 'SETUP', 'APPLY_CHANGES']):
        return 'archive/setup/'

    # API docs
    if any(kw in name for kw in ['API_DOC', 'API_QUICK', 'API_SUCCESS']):
        return 'archive/api_docs/'

    # Misc markdown/text/json
    ext = os.path.splitext(fname)[1].lower()
    if ext in ('.md', '.txt') and fname not in KEEP_IN_ROOT:
        return 'archive/misc/'
    if ext == '.json' and fname not in KEEP_IN_ROOT:
        return 'archive/misc/'

    return None


def main():
    check_only = '--check' in sys.argv
    do_move = '--move' in sys.argv

    if not check_only and not do_move:
        print('Usage:')
        print('  python tools/cleanup/organize_root_docs.py --check')
        print('  python tools/cleanup/organize_root_docs.py --move')
        return

    print('=' * 60)
    print('Organize Root Directory')
    print('=' * 60)

    to_move = []
    for fname in sorted(os.listdir(BASE_DIR)):
        fpath = os.path.join(BASE_DIR, fname)
        if not os.path.isfile(fpath):
            continue
        if fname.startswith('.') and fname in KEEP_IN_ROOT:
            continue
        if fname in KEEP_IN_ROOT:
            continue
        dest = categorize(fname)
        if dest:
            to_move.append((fname, dest))

    if not to_move:
        print('\nNothing to move. Root is clean!')
        return

    print(f'\n{len(to_move)} file(s) can be organized:\n')
    for fname, dest in to_move:
        print(f'  {fname}  ->  {dest}')

    if check_only:
        print(f'\nRun with --move to actually move files.')
        return

    if do_move:
        moved = 0
        for fname, dest in to_move:
            src = os.path.join(BASE_DIR, fname)
            dst_dir = os.path.join(BASE_DIR, dest)
            dst = os.path.join(dst_dir, fname)
            try:
                os.makedirs(dst_dir, exist_ok=True)
                shutil.move(src, dst)
                print(f'  MOVED: {fname}')
                moved += 1
            except (IOError, OSError) as e:
                print(f'  FAIL: {fname}: {e}')
        print(f'\nMoved {moved} file(s)')


if __name__ == '__main__':
    main()
