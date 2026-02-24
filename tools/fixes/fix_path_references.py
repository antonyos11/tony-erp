#!/usr/bin/env python3
"""
إصلاح مسارات Windows في ملفات المشروع
يبحث عن مسارات Windows مثل C:\\Users\\ ويحولها للنمط النسبي
"""
import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

WINDOWS_PATH_RE = re.compile(r'[A-Z]:\\\\?(?:Users|Program Files|Windows)[\\/][^\s\'",:]+', re.IGNORECASE)

SKIP_DIRS = {
    '.git', '__pycache__', 'node_modules', 'venv', 'env',
    '.venv', 'staticfiles', 'media', 'migrations',
}

EXTENSIONS = {'.py', '.html', '.js', '.css', '.json', '.yml', '.yaml', '.md', '.txt', '.conf'}


def scan_file(filepath):
    """فحص ملف واحد للبحث عن مسارات Windows"""
    findings = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                matches = WINDOWS_PATH_RE.findall(line)
                for match in matches:
                    findings.append({
                        'file': filepath,
                        'line': line_num,
                        'match': match,
                        'context': line.strip()[:120],
                    })
    except (OSError, IOError):
        pass
    return findings


def scan_project(base_dir):
    """فحص المشروع بالكامل"""
    all_findings = []
    scanned = 0

    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext not in EXTENSIONS:
                continue
            filepath = os.path.join(root, f)
            findings = scan_file(filepath)
            all_findings.extend(findings)
            scanned += 1

    return all_findings, scanned


def main():
    print('=' * 70)
    print('🔍 فحص مسارات Windows في المشروع')
    print('=' * 70)

    findings, scanned = scan_project(BASE_DIR)

    print(f'\n📂 تم فحص {scanned} ملف')

    if findings:
        print(f'\n🔴 تم العثور على {len(findings)} مسار Windows:')
        print('-' * 70)
        for f in findings:
            rel_path = os.path.relpath(f['file'], BASE_DIR)
            print(f'  📄 {rel_path}:{f["line"]}')
            print(f'     المسار: {f["match"]}')
            print(f'     السياق: {f["context"][:100]}')
            print()

        if '--fix' in sys.argv:
            print('🔧 الإصلاح التلقائي غير متاح لمسارات الملفات.')
            print('   يرجى مراجعة المسارات يدوياً واستخدام المسارات النسبية.')
    else:
        print('\n✅ لا توجد مسارات Windows في المشروع!')

    print('=' * 70)


if __name__ == '__main__':
    main()
