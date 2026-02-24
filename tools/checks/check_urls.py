#!/usr/bin/env python
"""فحص URLs موديول المتجر الإلكتروني"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from django.urls import reverse, NoReverseMatch

urls_to_check = [
    'ecommerce:admin_dashboard',
    'ecommerce:admin_orders',
    'ecommerce:admin_products',
    'ecommerce:admin_categories',
    'ecommerce:admin_reviews',
    'ecommerce:admin_coupons',
    'ecommerce:admin_settings_menu',
    'ecommerce:admin_settings',
    'ecommerce:admin_header_settings',
    'ecommerce:admin_footer_settings',
    'ecommerce:admin_payment_gateways',
    'ecommerce:admin_shipping_companies',
    'ecommerce:admin_shipping_costs',
    'ecommerce:admin_social_media',
    'ecommerce:admin_banners',
    'ecommerce:admin_page_content',
    'ecommerce:admin_flash_sales',
    'ecommerce:admin_homepage_sections',
    'ecommerce:admin_newsletter',
    'ecommerce:store_home',
]

print('فحص URLs المتجر الإلكتروني:')
for url_name in urls_to_check:
    try:
        url = reverse(url_name)
        print(f'  OK: {url_name} -> {url}')
    except NoReverseMatch as e:
        print(f'  FAIL: {url_name} - {e}')
    except Exception as e:
        print(f'  ERROR: {url_name} - {e}')
