#!/usr/bin/env python
"""فحص وجود ecommerce في الملف"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

# قراءة الملف مباشرة
with open('core/context_processors.py', 'r', encoding='utf-8') as f:
    content = f.read()

# البحث عن ecommerce
search_term = "'ecommerce':"
if search_term in content:
    print('ecommerce موجود في الملف')
    # طباعة السطر
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if search_term in line:
            print(f'السطر {i+1}: {line}')
else:
    print('ecommerce غير موجود في الملف!')

# طباعة عدد الموديولات
import re
matches = re.findall(r"'(\w+)':\s*\{\s*\n\s*'name':", content)
print(f'\nعدد الموديولات في الملف: {len(matches)}')
print('الموديولات:')
for m in matches:
    print(f'  - {m}')
