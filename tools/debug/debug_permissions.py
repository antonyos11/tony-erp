#!/usr/bin/env python
"""
سكريبت لاختبار الصلاحيات
"""
import os
import sys
import django

# إعداد Django
sys.path.append(r'd:\الشامل')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from django.contrib.auth.models import User
from users.models import user_has_permission
from core.context_processors import user_permissions
from django.http import HttpRequest


def test_user_permissions(username):
    """اختبار صلاحيات المستخدم"""
    try:
        user = User.objects.get(username=username)
        print(f"\n=== اختبار صلاحيات المستخدم: {username} ===")
        try:
            profile_role = getattr(user, 'profile', None)
            role_name = getattr(profile_role, 'role', None) if profile_role else None
            display_name = getattr(role_name, 'display_name', 'غير محدد') if role_name else 'غير محدد'
            print(f"الدور: {display_name}")
        except AttributeError:
            print("الدور: غير محدد")
        
        # اختبار مباشر للصلاحيات
        modules = ['accounting', 'inventory', 'sales', 'purchases', 'hr', 'crm']
        actions = ['view', 'add', 'change']
        
        print("\n--- فحص مباشر للصلاحيات ---")
        for module in modules:
            for action in actions:
                has_perm = user_has_permission(user, module, action)
                if has_perm:
                    print(f"{module} - {action}")
        
        # اختبار context processor
        print("\n--- فحص context processor ---")
        request = HttpRequest()
        request.user = user
        context = user_permissions(request)
        
        print("الوحدات المتاحة:")
        for module_key, module_data in context['user_modules'].items():
            print(f"{module_key}: {module_data['name']}")
            for item in module_data['items']:
                print(f"   - {item['name']}")
                
        print(f"\nعدد الوحدات المتاحة: {len(context['user_modules'])}")
        print(f"له صلاحيات: {context['has_any_permissions']}")
        
    except User.DoesNotExist:
        print(f"المستخدم {username} غير موجود")
    except Exception as e:
        print(f"خطأ: {e}")


if __name__ == '__main__':
    test_user_permissions('demo_user')
    print("\n" + "="*50)
    test_user_permissions('admin')