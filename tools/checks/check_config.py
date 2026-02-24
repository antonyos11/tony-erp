#!/usr/bin/env python
"""فحص عدد الموديولات في modules_config"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

# قراءة الملف مباشرة وحساب الموديولات
with open('core/context_processors.py', 'r', encoding='utf-8') as f:
    content = f.read()

# البحث عن بداية ونهاية modules_config
start_marker = "modules_config = {"
end_marker = "    # فحص صلاحيات المستخدم لكل وحدة"

if start_marker in content and end_marker in content:
    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker)
    config_section = content[start_idx:end_idx]
    
    # حساب عدد مفاتيح الموديولات
    import re
    module_keys = re.findall(r"^\s+'([a-z_]+)':\s*\{$", config_section, re.MULTILINE)
    
    print(f'عدد الموديولات في modules_config: {len(module_keys)}')
    print('الموديولات:')
    for i, key in enumerate(module_keys, 1):
        print(f'  {i}. {key}')
    
    # التحقق من وجود ecommerce
    if 'ecommerce' in module_keys:
        idx = module_keys.index('ecommerce')
        print(f'\necommerce في الموقع: {idx + 1}')
    else:
        print('\necommerce غير موجود في القائمة!')
else:
    print('لم يتم العثور على modules_config')
