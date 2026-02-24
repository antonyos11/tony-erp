#!/usr/bin/env python
"""فحص تفصيلي جداً مع تتبع الاستثناءات"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from django.urls import reverse, NoReverseMatch
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.conf import settings as django_settings
from django.utils.translation import gettext_lazy as _

User = get_user_model()
user = User.objects.filter(is_superuser=True).first()

factory = RequestFactory()
request = factory.get('/')
request.user = user
request.session = {}

# نسخ أجزاء من الكود لفهم ما يحدث
show_all = getattr(user, 'is_superuser', False) or getattr(django_settings, 'UI_SHOW_ALL_MODULES', False)
print(f'show_all = {show_all}')

# تعريف موديول ecommerce للفحص
module_config = {
    'name': _('المتجر الإلكتروني'),
    'icon': 'bi-shop',
    'perm_module': 'ecommerce',
    'permissions': ['view', 'add', 'change'],
    'items': [
        {'type': 'header', 'name': _('لوحة التحكم')},
        {'name': _('لوحة تحكم المتجر'), 'url': 'ecommerce:admin_dashboard', 'permission': 'view'},
        {'type': 'divider'},
        {'type': 'header', 'name': _('إدارة المتجر')},
        {'name': _('الطلبات'), 'url': 'ecommerce:admin_orders', 'permission': 'view'},
        {'name': _('المنتجات'), 'url': 'ecommerce:admin_products', 'permission': 'view'},
        {'name': _('عرض المتجر'), 'url': 'ecommerce:store_home', 'permission': 'view'},
    ]
}

perm_module = module_config.get('perm_module', 'ecommerce')
has_access = bool(show_all)
print(f'has_access = {has_access}')

accessible_items = []
current_path = '/'
current_view_name = ''

if has_access:
    for item in module_config['items']:
        print(f'  Processing item: {item}')
        # السماح بعناصر الرأس والفواصل بدون صلاحية
        if item.get('type') in {'header', 'divider'}:
            accessible_items.append(item)
            continue
        
        allowed = bool(show_all)
        print(f'    allowed = {allowed}')
        
        if allowed:
            item_active = False
            if 'url' in item:
                raw_url = item['url']
                if not raw_url.startswith('/'):
                    try:
                        resolved = reverse(raw_url)
                        print(f'    URL resolved: {raw_url} -> {resolved}')
                    except NoReverseMatch as e:
                        print(f'    URL FAILED: {raw_url} - {e}')
                        resolved = ''
                else:
                    resolved = raw_url
            accessible_items.append(item)

visible_links = [i for i in accessible_items if 'url' in i]
print(f'\naccessible_items: {len(accessible_items)}')
print(f'visible_links: {len(visible_links)}')

if visible_links:
    print('✅ سيتم إظهار الموديول!')
else:
    print('❌ لن يتم إظهار الموديول!')
