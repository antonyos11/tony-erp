#!/usr/bin/env python
"""فحص تفصيلي لكل موديول"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from django.urls import reverse, NoReverseMatch
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.conf import settings
from django.utils.translation import gettext_lazy as _

User = get_user_model()
user = User.objects.filter(is_superuser=True).first()

factory = RequestFactory()
request = factory.get('/')
request.user = user
request.session = {}

show_all = True

# قائمة الموديولات للفحص
modules_to_check = ['woocommerce', 'ecommerce', 'maintenance']

for mod_key in modules_to_check:
    print(f'\n=== فحص {mod_key} ===')
    
    if mod_key == 'woocommerce':
        urls = [
            'woocommerce_integration:dashboard',
            'woocommerce_integration:config_list',
        ]
    elif mod_key == 'ecommerce':
        urls = [
            'ecommerce:admin_dashboard',
            'ecommerce:admin_orders',
            'ecommerce:store_home',
        ]
    elif mod_key == 'maintenance':
        urls = [
            'maintenance:dashboard',
            'maintenance:machine_list',
        ]
    
    for url_name in urls:
        try:
            resolved = reverse(url_name)
            print(f'  ✓ {url_name} -> {resolved}')
        except NoReverseMatch as e:
            print(f'  ✗ {url_name} - NoReverseMatch: {e}')
        except Exception as e:
            print(f'  ✗ {url_name} - Error: {type(e).__name__}: {e}')
