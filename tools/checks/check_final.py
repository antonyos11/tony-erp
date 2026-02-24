#!/usr/bin/env python
"""فحص تفصيلي لمعرفة سبب عدم ظهور الموديولات"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from django.urls import reverse, NoReverseMatch
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.conf import settings
from django.utils.translation import gettext_lazy as _

# إعادة تحميل الموديول بشكل كامل
import sys
if 'core.context_processors' in sys.modules:
    del sys.modules['core.context_processors']

import core.context_processors as cp

User = get_user_model()
user = User.objects.filter(is_superuser=True).first()

factory = RequestFactory()
request = factory.get('/')
request.user = user
request.session = {}

# الحصول على النتيجة
result = cp.user_permissions(request)
modules_shown = result.get('user_modules', {})

print(f'الموديولات المعروضة: {len(modules_shown)}')
for k, v in modules_shown.items():
    print(f'  - {k}: {v["name"]}')

# التحقق من الموديولات المفقودة
missing = ['e_shipping', 'fixed_assets', 'woocommerce', 'ecommerce']
print(f'\nالموديولات المفقودة:')
for m in missing:
    if m in modules_shown:
        print(f'  ✓ {m} موجود!')
    else:
        print(f'  ✗ {m} مفقود')
