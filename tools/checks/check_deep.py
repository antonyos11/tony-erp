#!/usr/bin/env python
"""فحص مفصل جداً لموديول المتجر الإلكتروني"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from django.urls import reverse, NoReverseMatch
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.conf import settings

User = get_user_model()
user = User.objects.filter(is_superuser=True).first()

# إنشاء request وهمي
factory = RequestFactory()
request = factory.get('/')
request.user = user
request.session = {}

show_all = getattr(user, 'is_superuser', False) or getattr(settings, 'UI_SHOW_ALL_MODULES', False)
print(f'show_all = {show_all}')
print(f'user.is_superuser = {user.is_superuser}')

# الآن نفحص الموديول من context_processors
from core import context_processors as cp

# قراءة modules_config
import inspect
source = inspect.getsource(cp.user_permissions)

# طباعة عدد الموديولات
print("\nنفحص modules_config...")

# استدعاء الدالة
result = cp.user_permissions(request)
modules = result.get('user_modules', {})

print(f"\nعدد الموديولات المعروضة: {len(modules)}")
print("أسماء الموديولات:")
for k in modules.keys():
    print(f"  - {k}")

# البحث عن maintenance
if 'maintenance' in modules:
    print("\n✅ maintenance موجود")
else:
    print("\n❌ maintenance غير موجود")

if 'ecommerce' in modules:
    print("✅ ecommerce موجود")
else:
    print("❌ ecommerce غير موجود - نبحث عن السبب...")
    
    # نفحص إذا كان الموديول موجود في config
    # نحتاج طريقة للوصول إلى modules_config
