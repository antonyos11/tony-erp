#!/usr/bin/env python3
"""
تنظيم ملفات التوثيق المتناثرة في المجلد الرئيسي
ينقل ملفات .md و .txt إلى مجلد docs/ منظم
"""
import os
import shutil
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCS_DIR = os.path.join(BASE_DIR, 'docs')

# تصنيف الملفات حسب الكلمات المفتاحية
CATEGORIES = {
    'guides': ['GUIDE', 'SETUP', 'QUICK_START', 'USER_GUIDE', 'README', 'INSTRUCTIONS'],
    'reports': ['REPORT', 'SUMMARY', 'ACHIEVEMENT', 'COMPLETION', 'CERTIFICATE', 'ANNOUNCEMENT'],
    'changelogs': ['CHANGELOG', 'FIX', 'IMPROVEMENTS', 'ENHANCEMENTS'],
    'deployment': ['DEPLOY', 'DOCKER', 'PRODUCTION', 'SERVER'],
    'api': ['API', 'ENDPOINT'],
    'features': ['FEATURE', 'CHECKLIST'],
}

# ملفات لا يجب نقلها
KEEP_FILES = {
    'README.md', 'CONTRIBUTING.md', 'LICENSE', 'LICENSE.md',
    'requirements.txt', 'Dockerfile', 'docker-compose.yml',
    'docker-compose.enterprise.yml', '.env', '.env.example',
    'manage.py', 'Makefile', 'Procfile',
}


def classify_file(filename):
    """تصنيف ملف حسب اسمه"""
    upper = filename.upper()
    for category, keywords in CATEGORIES.items():
        for kw in keywords:
            if kw in upper:
                return category
    return 'misc'


def scan_docs(base_dir):
    """البحث عن ملفات التوثيق في المجلد الرئيسي"""
    docs = []
    for f in os.listdir(base_dir):
        fpath = os.path.join(base_dir, f)
        if not os.path.isfile(fpath):
            continue
        if f in KEEP_FILES:
            continue
        ext = os.path.splitext(f)[1].lower()
        if ext in ('.md', '.txt') and f[0].isupper():
            category = classify_file(f)
            docs.append({'name': f, 'path': fpath, 'category': category})
    return docs


def main():
    check_only = '--check' in sys.argv
    do_fix = '--fix' in sys.argv

    print('=' * 70)
    print('📚 تنظيم ملفات التوثيق')
    print('=' * 70)

    docs = scan_docs(BASE_DIR)

    if not docs:
        print('\n✅ لا توجد ملفات توثيق متناثرة في المجلد الرئيسي!')
        return

    # تجميع حسب التصنيف
    by_category = {}
    for doc in docs:
        cat = doc['category']
        by_category.setdefault(cat, []).append(doc)

    print(f'\n📝 {len(docs)} ملف توثيق في المجلد الرئيسي:\n')
    for cat, files in sorted(by_category.items()):
        print(f'  📁 {cat}/ ({len(files)} ملف)')
        for f in files[:5]:
            print(f'      {f["name"]}')
        if len(files) > 5:
            print(f'      ... و {len(files) - 5} ملف آخر')

    if check_only:
        print(f'\n💡 استخدم --fix لنقل الملفات إلى docs/')
        return

    if do_fix:
        print(f'\n🔧 نقل الملفات إلى {DOCS_DIR}...')
        moved = 0
        for doc in docs:
            dest_dir = os.path.join(DOCS_DIR, doc['category'])
            os.makedirs(dest_dir, exist_ok=True)
            dest = os.path.join(dest_dir, doc['name'])
            if os.path.exists(dest):
                print(f'  ⚠️  موجود: {doc["name"]}')
                continue
            shutil.move(doc['path'], dest)
            moved += 1
            print(f'  ✅ {doc["name"]} → docs/{doc["category"]}/')

        print(f'\n✅ تم نقل {moved} ملف')
    else:
        print(f'\n💡 استخدم --check للفحص أو --fix للنقل')

    print('=' * 70)


if __name__ == '__main__':
    main()
