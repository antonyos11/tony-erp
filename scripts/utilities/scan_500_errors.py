#!/usr/bin/env python
"""
مسح شامل لجميع صفحات النظام لاكتشاف أخطاء 500
"""
import os
import sys
import django

# إعداد Django
sys.path.insert(0, '/var/www/tony_erp')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from django.urls import get_resolver, URLPattern, URLResolver
from django.test import Client
from django.contrib.auth import get_user_model
import json

def get_all_urls(resolver=None, prefix=''):
    """استخراج جميع URLs من النظام"""
    if resolver is None:
        resolver = get_resolver()
    
    urls = []
    for pattern in resolver.url_patterns:
        if isinstance(pattern, URLResolver):
            urls.extend(get_all_urls(pattern, prefix + str(pattern.pattern)))
        elif isinstance(pattern, URLPattern):
            url = prefix + str(pattern.pattern)
            # تنظيف URL من regex patterns
            url = url.replace('^', '').replace('$', '')
            # تجاهل URLs التي تحتوي على معاملات
            if '<' not in url and '(?P' not in url:
                if url and not url.startswith('__debug__'):
                    urls.append({
                        'url': '/' + url if not url.startswith('/') else url,
                        'name': pattern.name
                    })
    return urls

def test_urls():
    """اختبار جميع URLs"""
    print("🔍 جاري استخراج جميع URLs من النظام...")
    all_urls = get_all_urls()
    print(f"✅ تم العثور على {len(all_urls)} صفحة\n")
    
    # إنشاء مستخدم للاختبار
    User = get_user_model()
    user, created = User.objects.get_or_create(
        username='test_scanner',
        defaults={'is_staff': True, 'is_superuser': True}
    )
    if created:
        user.set_password('test123')
        user.save()
    
    client = Client()
    client.force_login(user)
    
    # إحصائيات
    stats = {
        'total': len(all_urls),
        'success': 0,
        'error_500': 0,
        'error_404': 0,
        'error_403': 0,
        'other': 0
    }
    
    errors_500 = []
    errors_404 = []
    
    print("🧪 جاري اختبار الصفحات...\n")
    
    for idx, url_info in enumerate(all_urls, 1):
        url = url_info['url']
        name = url_info.get('name', 'N/A')
        
        try:
            response = client.get(url, follow=False)
            status = response.status_code
            
            if status == 200:
                stats['success'] += 1
                print(f"✅ [{idx}/{len(all_urls)}] {url} - 200 OK")
            elif status == 500:
                stats['error_500'] += 1
                errors_500.append({
                    'url': url,
                    'name': name,
                    'status': status
                })
                print(f"❌ [{idx}/{len(all_urls)}] {url} - 500 ERROR")
            elif status == 404:
                stats['error_404'] += 1
                errors_404.append({
                    'url': url,
                    'name': name
                })
                print(f"⚠️  [{idx}/{len(all_urls)}] {url} - 404 NOT FOUND")
            elif status == 403:
                stats['error_403'] += 1
                print(f"🔒 [{idx}/{len(all_urls)}] {url} - 403 FORBIDDEN")
            elif status in [301, 302]:
                stats['success'] += 1
                print(f"↗️  [{idx}/{len(all_urls)}] {url} - {status} REDIRECT")
            else:
                stats['other'] += 1
                print(f"ℹ️  [{idx}/{len(all_urls)}] {url} - {status}")
                
        except Exception as e:
            stats['error_500'] += 1
            errors_500.append({
                'url': url,
                'name': name,
                'exception': str(e)
            })
            print(f"💥 [{idx}/{len(all_urls)}] {url} - EXCEPTION: {str(e)[:100]}")
    
    # طباعة التقرير النهائي
    print("\n" + "="*80)
    print("📊 تقرير النتائج")
    print("="*80)
    print(f"إجمالي الصفحات: {stats['total']}")
    print(f"✅ ناجحة: {stats['success']}")
    print(f"❌ أخطاء 500: {stats['error_500']}")
    print(f"⚠️  أخطاء 404: {stats['error_404']}")
    print(f"🔒 أخطاء 403: {stats['error_403']}")
    print(f"ℹ️  أخرى: {stats['other']}")
    print("="*80)
    
    # حفظ التقرير
    report = {
        'stats': stats,
        'errors_500': errors_500,
        'errors_404': errors_404
    }
    
    with open('/var/www/tony_erp/500_scan_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print("\n💾 تم حفظ التقرير في: 500_scan_report.json")
    
    if errors_500:
        print(f"\n⚠️  تحذير: تم اكتشاف {len(errors_500)} صفحة بها أخطاء 500!")
        print("\nالصفحات الرئيسية التي تحتاج إصلاح:")
        for error in errors_500[:10]:
            print(f"  - {error['url']} ({error.get('name', 'N/A')})")

if __name__ == '__main__':
    test_urls()
