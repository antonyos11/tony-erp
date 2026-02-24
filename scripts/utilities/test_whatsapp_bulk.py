#!/usr/bin/env python
"""
اختبار صفحة WhatsApp Bulk Create
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()

def test_whatsapp_bulk_page():
    """اختبار صفحة WhatsApp Bulk Create"""
    
    print("=" * 60)
    print("اختبار صفحة WhatsApp Bulk Create")
    print("=" * 60)
    
    # الحصول على مستخدم admin
    user = User.objects.filter(is_superuser=True).first()
    if not user:
        print("❌ No admin user found!")
        return False
    
    print(f"✅ Using admin user: {user.username}")
    
    # إنشاء client وتسجيل الدخول
    client = Client()
    client.force_login(user)
    
    # اختبار الـ URL
    try:
        url = reverse('crm:whatsapp_bulk_create')
        print(f"✅ URL resolved: {url}")
    except Exception as e:
        print(f"❌ Error resolving URL: {e}")
        return False
    
    # الوصول للصفحة
    print(f"\n🔍 Testing GET {url}...")
    try:
        response = client.get(url, follow=True)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Page loaded successfully!")
            
            # فحص المحتوى
            content = response.content.decode('utf-8', errors='ignore')
            
            if 'Server Error' in content or 'Server Error (500)' in content:
                print("❌ Page contains Server Error!")

                # استخراج الخطأ
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if 'Traceback' in line or 'Exception' in line or 'Error' in line:
                        error_context = '\n'.join(lines[max(0, i-5):min(len(lines), i+20)])
                        print("\n=== ERROR DETAILS ===")
                        print(error_context)
                        print("=== END ERROR ===\n")
                        break

                return False
            
            if 'NoReverseMatch' in content:
                print("❌ Page contains NoReverseMatch error!")
                # استخراج الخطأ
                for line in content.split('\n'):
                    if 'NoReverseMatch' in line or 'unit_create' in line:
                        print(f"  {line.strip()}")
                return False
            
            if 'Exception' in content and 'Traceback' in content:
                print("❌ Page contains Exception!")
                return False
            
            # فحص العناصر المهمة
            if 'WhatsApp' in content or 'whatsapp' in content:
                print("✅ Page contains WhatsApp content")
            
            print(f"✅ Page content length: {len(content)} bytes")
            return True
            
        elif response.status_code == 302:
            print(f"⚠️  Redirect to: {response.redirect_chain}")
            return True
            
        else:
            print(f"❌ Unexpected status code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Exception occurred: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_whatsapp_bulk_page()
    print("\n" + "=" * 60)
    if success:
        print("✅ TEST PASSED")
    else:
        print("❌ TEST FAILED")
    print("=" * 60)

