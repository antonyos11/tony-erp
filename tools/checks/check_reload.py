#!/usr/bin/env python
"""فحص مباشر لتكوين الموديولات"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

# قراءة modules_config مباشرة من الملف
import importlib
import core.context_processors as cp

# إعادة تحميل الموديول
importlib.reload(cp)

from django.contrib.auth import get_user_model
from django.test import RequestFactory

User = get_user_model()
user = User.objects.filter(is_superuser=True).first()

factory = RequestFactory()
request = factory.get('/')
request.user = user
request.session = {}

# استدعاء الدالة
result = cp.user_permissions(request)
modules = result.get('user_modules', {})

print(f'عدد الموديولات: {len(modules)}')
print('الموديولات:')
for k in modules.keys():
    print(f'  - {k}')

if 'ecommerce' in modules:
    print('\n✅ ecommerce موجود!')
else:
    print('\n❌ ecommerce غير موجود!')
    
if 'woocommerce' in modules:
    print('✅ woocommerce موجود!')
else:
    print('❌ woocommerce غير موجود!')
