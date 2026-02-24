#!/usr/bin/env python3
"""
سكريبت إنشاء البيانات النموذجية للمشروع
الاستخدام: python create_sample_data.py
أو عبر: make seed-data
"""
import os
import sys
import django

# إعداد بيئة Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    try:
        django.setup()
    except Exception as e:
        print(f'❌ خطأ في إعداد Django: {e}')
        sys.exit(1)

    print('=' * 60)
    print('📦 إنشاء البيانات النموذجية للمشروع')
    print('=' * 60)

    from django.core.management import call_command
    try:
        call_command('load_sample_data', verbosity=2)
    except Exception as e:
        print(f'\n❌ خطأ: {e}')
        print('تأكد من تشغيل: python manage.py migrate أولاً')
        sys.exit(1)

    print('\n' + '=' * 60)
    print('✅ تم إنشاء البيانات النموذجية بنجاح!')
    print('=' * 60)
    print('\nلتشغيل السيرفر:')
    print('  python manage.py runserver')


if __name__ == '__main__':
    main()
