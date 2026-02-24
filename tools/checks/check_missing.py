#!/usr/bin/env python
"""فحص تفصيلي لكل موديول وأسباب عدم ظهوره"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from django.urls import reverse, NoReverseMatch
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.conf import settings
from django.utils.translation import gettext_lazy as _
import importlib

# إعادة تحميل الموديول
import core.context_processors as cp
importlib.reload(cp)

User = get_user_model()
user = User.objects.filter(is_superuser=True).first()

factory = RequestFactory()
request = factory.get('/')
request.user = user
request.session = {}

# استدعاء الدالة مع تتبع
show_all = getattr(user, 'is_superuser', False) or getattr(settings, 'UI_SHOW_ALL_MODULES', False)

# نحتاج الوصول إلى modules_config
# سنقرأ الملف ونحلله
with open('core/context_processors.py', 'r', encoding='utf-8') as f:
    content = f.read()

# البحث عن الموديولات
import re
module_keys_in_file = re.findall(r"^\s+'([a-z_]+)':\s*\{$", content, re.MULTILINE)

# الحصول على النتيجة
result = cp.user_permissions(request)
modules_shown = set(result.get('user_modules', {}).keys())

print(f'الموديولات في الملف: {len(module_keys_in_file)}')
print(f'الموديولات المعروضة: {len(modules_shown)}')

# البحث عن الموديولات المفقودة
missing = []
for key in module_keys_in_file:
    if key not in modules_shown:
        missing.append(key)

print(f'\nالموديولات المفقودة ({len(missing)}):')
for m in missing:
    print(f'  - {m}')
