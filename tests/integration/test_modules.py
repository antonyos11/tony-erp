#!/usr/bin/env python
"""
اختبار شامل لجميع وحدات النظام
"""
import os
import sys
import django
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from django.urls import reverse, NoReverseMatch

def test_all_modules():
    """اختبار جميع الوحدات"""
    
    # Setup client and user
    client = Client()
    superuser = User.objects.get(username='superadmin')
    client.force_login(superuser)
    
    # Test URLs
    test_urls = {
        'الصفحة الرئيسية': '/',
        'الإدارة': '/admin/',
        'المستخدمين': '/users/',
        'المخزون': '/inventory/',
        'المبيعات': '/sales/', 
        'المشتريات': '/purchases/',
        'التقارير': '/reports/',
        'المحاسبة': '/accounting/',
        'الموارد البشرية': '/hr/',
        'CRM': '/crm/',
        'الإنتاج': '/production/',
    }
    
    print("بدء اختبار وحدات النظام...")
    print("=" * 50)
    
    results = {}
    
    for name, url in test_urls.items():
        try:
            response = client.get(url)
            if response.status_code == 200:
                status = "يعمل بشكل صحيح"
                results[name] = True
            elif response.status_code == 302:
                status = "يعمل (إعادة توجيه)"
                results[name] = True
            elif response.status_code == 403:
                status = "يحتاج صلاحيات"
                results[name] = True
            else:
                status = f"خطأ {response.status_code}"
                results[name] = False

        except Exception as e:
            status = f"خطأ: {str(e)[:30]}..."
            results[name] = False

        print(f"{name:20} : {status}")
    
    # Summary
    working = sum(results.values())
    total = len(results)
    
    print("\n" + "=" * 50)
    print(f"النتائج: {working}/{total} وحدة تعمل بشكل صحيح")
    
    if working == total:
        print("جميع الوحدات تعمل بشكل ممتاز!")
        return True
    else:
        failed = [name for name, result in results.items() if not result]
        print(f"الوحدات التي تحتاج إصلاح: {', '.join(failed)}")
        return False

if __name__ == "__main__":
    test_all_modules()