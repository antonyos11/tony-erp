#!/usr/bin/env python3
"""
أداة تنظيف المستندات المكررة والملفات التسويقية غير الضرورية
تفحص مجلد docs/ وتحذف الملفات المتكررة أو ذات المحتوى التسويقي فقط
"""
import os
import sys
import hashlib
from collections import defaultdict
from pathlib import Path


# الأنماط التسويقية المكررة (عناوين عامة بدون محتوى تقني)
MARKETING_KEYWORDS = [
    'نظام متكامل ومتطور',
    'مميزات النظام',
    'لماذا تختار',
    'أفضل نظام',
    'الحل الشامل',
    'تواصل معنا',
    'احصل على عرض',
    'نسخة تجريبية مجانية',
]


def get_file_hash(filepath):
    """حساب hash للملف"""
    h = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def is_marketing_only(filepath):
    """فحص إذا كان الملف يحتوي فقط على محتوى تسويقي"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except (UnicodeDecodeError, IOError):
        return False

    if len(content) < 100:
        return False  # ملف قصير جداً، ربما مفيد

    marketing_count = sum(1 for kw in MARKETING_KEYWORDS if kw in content)
    # إذا كان أكثر من 3 عبارات تسويقية وملف قصير نسبياً
    if marketing_count >= 3 and len(content) < 5000:
        return True

    return False


def find_duplicates(docs_dir):
    """البحث عن الملفات المكررة بناءً على المحتوى"""
    hash_map = defaultdict(list)
    for root, dirs, files in os.walk(docs_dir):
        for fname in files:
            fpath = os.path.join(root, fname)
            fhash = get_file_hash(fpath)
            hash_map[fhash].append(fpath)

    duplicates = {h: paths for h, paths in hash_map.items() if len(paths) > 1}
    return duplicates


def analyze_docs(base_dir):
    """تحليل مجلد المستندات"""
    docs_dir = os.path.join(base_dir, 'docs')
    if not os.path.isdir(docs_dir):
        print("مجلد docs/ غير موجود")
        return

    total_files = 0
    marketing_files = []
    empty_files = []
    backup_files = []

    for root, dirs, files in os.walk(docs_dir):
        for fname in files:
            fpath = os.path.join(root, fname)
            total_files += 1

            # ملفات النسخ الاحتياطي
            if any(pat in fname for pat in ['.backup', '.bak', '.old', '~', '.orig']):
                backup_files.append(fpath)
                continue

            # ملفات فارغة
            if os.path.getsize(fpath) == 0:
                empty_files.append(fpath)
                continue

            # ملفات تسويقية فقط
            if fname.endswith('.md') and is_marketing_only(fpath):
                marketing_files.append(fpath)

    # البحث عن المكررات
    duplicates = find_duplicates(docs_dir)

    # === التقرير ===
    print(f"\n{'='*60}")
    print(f"  تقرير تنظيف المستندات - Tony ERP")
    print(f"{'='*60}\n")
    print(f"  إجمالي الملفات: {total_files}")
    print(f"  ملفات النسخ الاحتياطي: {len(backup_files)}")
    print(f"  ملفات فارغة: {len(empty_files)}")
    print(f"  ملفات تسويقية فقط: {len(marketing_files)}")
    print(f"  مجموعات مكررة: {len(duplicates)}")

    total_to_clean = len(backup_files) + len(empty_files)
    # من كل مجموعة مكررة، نحتفظ بواحد فقط
    for paths in duplicates.values():
        total_to_clean += len(paths) - 1

    print(f"\n  إجمالي الملفات القابلة للحذف: {total_to_clean}")

    if backup_files:
        print(f"\n  --- ملفات النسخ الاحتياطي ---")
        for f in backup_files[:10]:
            print(f"    🗑️  {os.path.relpath(f, base_dir)}")
        if len(backup_files) > 10:
            print(f"    ... و {len(backup_files) - 10} ملف آخر")

    if duplicates:
        print(f"\n  --- مجموعات مكررة ---")
        for h, paths in list(duplicates.items())[:5]:
            print(f"    📄 مكرر ({len(paths)} نسخ):")
            for p in paths:
                print(f"       {os.path.relpath(p, base_dir)}")

    if marketing_files:
        print(f"\n  --- ملفات تسويقية ---")
        for f in marketing_files[:10]:
            print(f"    📢 {os.path.relpath(f, base_dir)}")

    return {
        'backup_files': backup_files,
        'empty_files': empty_files,
        'marketing_files': marketing_files,
        'duplicates': duplicates,
    }


def cleanup(base_dir, dry_run=True):
    """تنظيف الملفات غير الضرورية"""
    result = analyze_docs(base_dir)
    if not result:
        return

    to_delete = []
    to_delete.extend(result['backup_files'])
    to_delete.extend(result['empty_files'])

    # من المكررات، نحتفظ بأول ملف فقط
    for paths in result['duplicates'].values():
        sorted_paths = sorted(paths)
        to_delete.extend(sorted_paths[1:])  # حذف كل النسخ عدا الأولى

    if not to_delete:
        print("\n✅ لا توجد ملفات تحتاج تنظيف")
        return

    if dry_run:
        print(f"\n⚠️  وضع المعاينة: سيتم حذف {len(to_delete)} ملف")
        print("   أعد التشغيل مع --execute للتنفيذ الفعلي")
    else:
        deleted = 0
        for fpath in to_delete:
            try:
                os.remove(fpath)
                deleted += 1
            except OSError as e:
                print(f"  ❌ خطأ في حذف {fpath}: {e}")
        print(f"\n✅ تم حذف {deleted}/{len(to_delete)} ملف")


if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    execute = '--execute' in sys.argv

    if execute:
        print("🔴 وضع التنفيذ الفعلي - سيتم حذف الملفات")
        cleanup(base_dir, dry_run=False)
    else:
        print("🔵 وضع المعاينة - لن يتم حذف أي ملف")
        cleanup(base_dir, dry_run=True)
