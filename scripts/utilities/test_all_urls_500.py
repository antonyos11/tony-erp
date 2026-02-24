#!/usr/bin/env python3
"""
سكريبت لاختبار جميع URLs في نظام Tony ERP
يفحص كل URL ويسجل الصفحات التي تعطي خطأ 500
"""
import os
import sys
import django

# Setup Django - نفس الطريقة من manage.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from django.urls import get_resolver, URLPattern, URLResolver
from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()

def get_all_urls(resolver=None, prefix=''):
    """استخراج جميع URLs من النظام"""
    if resolver is None:
        resolver = get_resolver()
    
    urls = []
    for pattern in resolver.url_patterns:
        if isinstance(pattern, URLResolver):
            # Nested URLconf
            namespace = pattern.namespace or ''
            urls.extend(get_all_urls(pattern, prefix + str(pattern.pattern)))
        elif isinstance(pattern, URLPattern):
            # URL pattern
            url_path = prefix + str(pattern.pattern)
            # تنظيف المسار من regex patterns
            url_path = url_path.replace('^', '').replace('$', '')
            # تخطي URLs التي تحتوي على parameters معقدة
            if '<' not in url_path and '(?P' not in url_path:
                urls.append({
                    'path': '/' + url_path.strip('/') + '/',
                    'name': pattern.name,
                    'namespace': getattr(pattern, 'namespace', None)
                })
    
    return urls

def test_urls():
    """اختبار جميع URLs"""
    # إنشاء مستخدم للاختبار
    try:
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            user = User.objects.create_superuser(
                username='test_admin',
                email='admin@test.com',
                password='test123'
            )
    except Exception as e:
        print(f"خطأ في إنشاء المستخدم: {e}")
        return
    
    client = Client()
    client.force_login(user)
    
    # جمع جميع URLs
    all_urls = get_all_urls()
    
    # تصنيف النتائج
    results = {
        'success': [],  # 200
        'redirect': [],  # 301, 302
        'client_error': [],  # 400, 404
        'server_error': [],  # 500
        'other': []
    }
    
    print(f"🔍 بدء اختبار {len(all_urls)} صفحة...\n")
    print("=" * 80)
    
    for idx, url_info in enumerate(all_urls, 1):
        url = url_info['path']
        name = url_info.get('name', 'N/A')
        
        try:
            response = client.get(url)
            status = response.status_code
            
            # تصنيف حسب كود الحالة
            if status == 200:
                results['success'].append((url, name, status))
                status_symbol = '✅'
            elif status in [301, 302, 303, 307]:
                results['redirect'].append((url, name, status))
                status_symbol = '↗️'
            elif status in [400, 404, 403]:
                results['client_error'].append((url, name, status))
                status_symbol = '⚠️'
            elif status >= 500:
                results['server_error'].append((url, name, status))
                status_symbol = '❌'
            else:
                results['other'].append((url, name, status))
                status_symbol = '❓'
            
            print(f"{status_symbol} [{idx}/{len(all_urls)}] {status} | {url} | {name}")
            
        except Exception as e:
            results['server_error'].append((url, name, f"Exception: {str(e)}"))
            print(f"❌ [{idx}/{len(all_urls)}] ERROR | {url} | {name} | {str(e)[:50]}")
    
    # طباعة التقرير النهائي
    print("\n" + "=" * 80)
    print("📊 تقرير النتائج:")
    print("=" * 80)
    print(f"✅ ناجحة (200): {len(results['success'])}")
    print(f"↗️  إعادة توجيه: {len(results['redirect'])}")
    print(f"⚠️  أخطاء العميل (404, 403): {len(results['client_error'])}")
    print(f"❌ أخطاء الخادم (500): {len(results['server_error'])}")
    print(f"❓ أخرى: {len(results['other'])}")
    
    # عرض تفاصيل أخطاء 500
    if results['server_error']:
        print("\n" + "=" * 80)
        print("🔥 الصفحات التي تحتاج إصلاح (أخطاء 500):")
        print("=" * 80)
        for url, name, status in results['server_error']:
            print(f"  • {url}")
            print(f"    الاسم: {name}")
            print(f"    الحالة: {status}")
            print()
    
    # حفظ التقرير في ملف
    with open('500_errors_report.txt', 'w', encoding='utf-8') as f:
        f.write("تقرير أخطاء 500 في نظام Tony ERP\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"إجمالي الصفحات المختبرة: {len(all_urls)}\n")
        f.write(f"الصفحات الناجحة: {len(results['success'])}\n")
        f.write(f"أخطاء الخادم (500): {len(results['server_error'])}\n\n")
        
        f.write("=" * 80 + "\n")
        f.write("الصفحات التي تحتاج إصلاح:\n")
        f.write("=" * 80 + "\n\n")
        
        for url, name, status in results['server_error']:
            f.write(f"URL: {url}\n")
            f.write(f"Name: {name}\n")
            f.write(f"Status: {status}\n")
            f.write("-" * 40 + "\n\n")
        
        f.write("\n" + "=" * 80 + "\n")
        f.write("أخطاء 404:\n")
        f.write("=" * 80 + "\n\n")
        
        for url, name, status in results['client_error']:
            if '404' in str(status):
                f.write(f"URL: {url}\n")
                f.write(f"Name: {name}\n")
                f.write("-" * 40 + "\n\n")
    
    print(f"\n💾 تم حفظ التقرير في: 500_errors_report.txt")
    
    return results

if __name__ == '__main__':
    results = test_urls()
