#!/usr/bin/env python
"""فحص مفصل لموديول المتجر الإلكتروني"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from django.urls import reverse, NoReverseMatch
from django.contrib.auth import get_user_model
from django.test import RequestFactory

# استيراد modules_config مباشرة
User = get_user_model()
user = User.objects.filter(is_superuser=True).first()

# إنشاء request وهمي
factory = RequestFactory()
request = factory.get('/')
request.user = user
request.session = {}

# نسخ الكود من context_processors
from django.conf import settings as django_settings

show_all = getattr(user, 'is_superuser', False)
print(f'show_all = {show_all}')

# فحص ecommerce module config
module_config = {
    'name': 'المتجر الإلكتروني',
    'icon': 'bi-shop',
    'perm_module': 'ecommerce',
    'permissions': ['view', 'add', 'change'],
    'items': [
        {'type': 'header', 'name': 'لوحة التحكم'},
        {'name': 'لوحة تحكم المتجر', 'url': 'ecommerce:admin_dashboard', 'permission': 'view'},
        {'type': 'divider'},
        {'name': 'الطلبات', 'url': 'ecommerce:admin_orders', 'permission': 'view'},
    ]
}

accessible_items = []
for item in module_config['items']:
    if item.get('type') in {'header', 'divider'}:
        accessible_items.append(item)
        continue
    
    # فحص الـ URL
    raw_url = item.get('url', '')
    try:
        resolved = reverse(raw_url)
        print(f'URL resolved: {raw_url} -> {resolved}')
        accessible_items.append(item)
    except NoReverseMatch as e:
        print(f'URL failed: {raw_url} - {e}')

visible_links = [i for i in accessible_items if 'url' in i]
print(f'accessible_items: {len(accessible_items)}')
print(f'visible_links: {len(visible_links)}')
print(f'Would show module: {bool(visible_links)}')
