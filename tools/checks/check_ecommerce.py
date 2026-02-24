#!/usr/bin/env python
"""فحص ظهور موديول المتجر الإلكتروني"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from core.context_processors import user_permissions
from django.contrib.auth import get_user_model
from django.test import RequestFactory

User = get_user_model()
user = User.objects.filter(is_superuser=True).first()
print(f'المستخدم: {user.username}, is_superuser: {user.is_superuser}')

# إنشاء request وهمي
factory = RequestFactory()
request = factory.get('/')
request.user = user
request.session = {}

# الحصول على الموديولات
result = user_permissions(request)
modules = result.get('user_modules', {})
print(f'عدد الموديولات: {len(modules)}')
print('الموديولات المتاحة:')
for key in modules:
    print(f'  - {key}: {modules[key]["name"]}')

if 'ecommerce' in modules:
    print('المتجر الإلكتروني موجود!')
else:
    print('المتجر الإلكتروني غير موجود!')
