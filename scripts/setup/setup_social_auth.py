#!/usr/bin/env python
"""
سكريبت إعداد مزودي تسجيل الدخول الاجتماعي
Setup Social Auth Providers Script

هذا السكريبت يضيف مزودي تسجيل الدخول الاجتماعي الافتراضيين
يمكنك تعديل الـ client_id و client_secret لكل مزود من لوحة التحكم

للتشغيل:
    python setup_social_auth.py
"""
import os
import sys
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from ecommerce.models import SocialAuthProvider


def setup_providers():
    """إعداد مزودي تسجيل الدخول الاجتماعي"""
    
    providers_data = [
        {
            'provider': 'google',
            'name': 'جوجل',
            'client_id': 'YOUR_GOOGLE_CLIENT_ID',
            'client_secret': 'YOUR_GOOGLE_CLIENT_SECRET',
            'is_active': False,  # يحتاج تفعيل بعد إضافة البيانات الحقيقية
            'sort_order': 1,
        },
        {
            'provider': 'facebook',
            'name': 'فيسبوك',
            'client_id': 'YOUR_FACEBOOK_APP_ID',
            'client_secret': 'YOUR_FACEBOOK_APP_SECRET',
            'is_active': False,
            'sort_order': 2,
        },
        {
            'provider': 'twitter',
            'name': 'تويتر / X',
            'client_id': 'YOUR_TWITTER_CLIENT_ID',
            'client_secret': 'YOUR_TWITTER_CLIENT_SECRET',
            'is_active': False,
            'sort_order': 3,
        },
        {
            'provider': 'apple',
            'name': 'Apple',
            'client_id': 'YOUR_APPLE_CLIENT_ID',
            'client_secret': 'YOUR_APPLE_CLIENT_SECRET',
            'is_active': False,
            'sort_order': 4,
        },
        {
            'provider': 'github',
            'name': 'GitHub',
            'client_id': 'YOUR_GITHUB_CLIENT_ID',
            'client_secret': 'YOUR_GITHUB_CLIENT_SECRET',
            'is_active': False,
            'sort_order': 5,
        },
        {
            'provider': 'microsoft',
            'name': 'Microsoft',
            'client_id': 'YOUR_MICROSOFT_CLIENT_ID',
            'client_secret': 'YOUR_MICROSOFT_CLIENT_SECRET',
            'is_active': False,
            'sort_order': 6,
        },
    ]
    
    print("=" * 60)
    print("🔐 إعداد مزودي تسجيل الدخول الاجتماعي")
    print("=" * 60)
    
    created_count = 0
    updated_count = 0
    
    for data in providers_data:
        provider, created = SocialAuthProvider.objects.update_or_create(
            provider=data['provider'],
            defaults={
                'name': data['name'],
                'client_id': data['client_id'],
                'client_secret': data['client_secret'],
                'is_active': data['is_active'],
                'sort_order': data['sort_order'],
            }
        )
        
        if created:
            created_count += 1
            print(f"✅ تم إنشاء: {provider.name} ({provider.provider})")
        else:
            updated_count += 1
            print(f"🔄 تم تحديث: {provider.name} ({provider.provider})")
    
    print("=" * 60)
    print(f"📊 النتيجة: {created_count} جديد | {updated_count} محدث")
    print("=" * 60)
    print()
    print("⚠️  ملاحظة مهمة:")
    print("   جميع المزودين معطلين افتراضياً")
    print("   يجب إضافة بيانات OAuth الحقيقية من:")
    print()
    print("   🔵 Google: https://console.developers.google.com/")
    print("   🔵 Facebook: https://developers.facebook.com/")
    print("   🔵 Twitter: https://developer.twitter.com/")
    print("   🔵 Apple: https://developer.apple.com/")
    print("   🔵 GitHub: https://github.com/settings/developers")
    print("   🔵 Microsoft: https://portal.azure.com/")
    print()
    print("   ثم فعّلها من لوحة تحكم المتجر:")
    print("   /store/admin/social-auth/")
    print("=" * 60)


def show_status():
    """عرض حالة المزودين"""
    providers = SocialAuthProvider.objects.all().order_by('sort_order')
    
    print("\n" + "=" * 60)
    print("📋 حالة مزودي تسجيل الدخول الاجتماعي")
    print("=" * 60)
    
    if not providers:
        print("❌ لا يوجد مزودين مسجلين")
        print("   شغّل الأمر: python setup_social_auth.py setup")
    else:
        for p in providers:
            status = "✅ مفعل" if p.is_active else "❌ معطل"
            has_creds = "🔑 بيانات موجودة" if p.client_id and 'YOUR_' not in p.client_id else "⚠️ بيانات وهمية"
            print(f"   {status} | {p.name:15} | {has_creds}")
    
    print("=" * 60)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'status':
        show_status()
    else:
        setup_providers()
        show_status()
