#!/usr/bin/env python3
"""
مدير النسخ الاحتياطية للمشروع
الاستخدام: python backup_manager.py [خيارات]
أو عبر: make backup
"""
import os
import sys
import argparse
import datetime
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKUP_DIR = os.path.join(BASE_DIR, 'backups')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
sys.path.insert(0, BASE_DIR)


def setup_django():
    try:
        import django
        django.setup()
        return True
    except Exception as e:
        print(f'❌ خطأ في إعداد Django: {e}')
        return False


def create_backup(backup_type='full'):
    if not setup_django():
        sys.exit(1)

    from django.core.management import call_command

    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

    print(f'\n💾 إنشاء نسخة احتياطية ({backup_type}) - {timestamp}')
    print('=' * 60)

    try:
        if backup_type in ('full', 'db'):
            # استخدام الأمر الموجود
            call_command('backup_now', verbosity=1)

        if backup_type in ('full', 'media'):
            media_dir = os.path.join(BASE_DIR, 'media')
            if os.path.exists(media_dir):
                dest = os.path.join(BACKUP_DIR, f'media_backup_{timestamp}')
                shutil.copytree(media_dir, dest, dirs_exist_ok=True)
                size_mb = sum(
                    os.path.getsize(os.path.join(r, f))
                    for r, _, files in os.walk(dest) for f in files
                ) / (1024 * 1024)
                print(f'✅ ملفات الميديا: {dest} ({size_mb:.1f} MB)')
            else:
                print('⚠️ مجلد media غير موجود')

        print('\n✅ اكتملت النسخة الاحتياطية!')

    except Exception as e:
        print(f'❌ خطأ: {e}')
        sys.exit(1)


def list_backups():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    items = []
    for name in os.listdir(BACKUP_DIR):
        path = os.path.join(BACKUP_DIR, name)
        mtime = datetime.datetime.fromtimestamp(os.path.getmtime(path))
        if os.path.isfile(path):
            size = os.path.getsize(path) / (1024 * 1024)
        else:
            size = sum(
                os.path.getsize(os.path.join(r, f))
                for r, _, files in os.walk(path) for f in files
            ) / (1024 * 1024)
        items.append((mtime, name, size))

    if not items:
        print('📭 لا توجد نسخ احتياطية في:', BACKUP_DIR)
        return

    items.sort(reverse=True)
    print(f'\n📋 النسخ الاحتياطية ({len(items)} نسخة) - {BACKUP_DIR}')
    print('-' * 70)
    for mtime, name, size in items:
        print(f'  {mtime.strftime("%Y-%m-%d %H:%M")}  {name:<45} {size:.1f} MB')


def restore_backup(backup_file):
    if not setup_django():
        sys.exit(1)

    if not os.path.exists(backup_file):
        # جرّب في مجلد backups
        alt = os.path.join(BACKUP_DIR, backup_file)
        if os.path.exists(alt):
            backup_file = alt
        else:
            print(f'❌ الملف غير موجود: {backup_file}')
            sys.exit(1)

    from django.core.management import call_command
    print(f'\n🔄 الاستعادة من: {backup_file}')
    try:
        call_command('restore_from', backup_file, verbosity=1)
        print('✅ اكتملت الاستعادة!')
    except Exception as e:
        # محاولة loaddata مباشرة
        try:
            call_command('loaddata', backup_file, verbosity=1)
            print('✅ تمت الاستعادة عبر loaddata!')
        except Exception as e2:
            print(f'❌ خطأ في الاستعادة: {e2}')
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='مدير النسخ الاحتياطية',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
أمثلة:
  python backup_manager.py                  # نسخة كاملة
  python backup_manager.py --type db        # قاعدة البيانات فقط
  python backup_manager.py --type media     # الميديا فقط
  python backup_manager.py --list           # عرض النسخ
  python backup_manager.py --restore FILE   # استعادة
        """
    )
    parser.add_argument('--type', choices=['full', 'db', 'media'],
                        default='full', help='نوع النسخة (افتراضي: full)')
    parser.add_argument('--list', action='store_true', help='عرض النسخ الاحتياطية')
    parser.add_argument('--restore', metavar='FILE', help='استعادة من ملف')

    args = parser.parse_args()

    print('=' * 60)
    print('💾 مدير النسخ الاحتياطية - Tony ERP')
    print('=' * 60)

    if args.list:
        list_backups()
    elif args.restore:
        restore_backup(args.restore)
    else:
        create_backup(args.type)


if __name__ == '__main__':
    main()
