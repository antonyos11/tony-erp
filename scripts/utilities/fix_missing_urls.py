#!/usr/bin/env python3
"""
Script to add missing URL aliases to prevent NoReverseMatch errors
"""

import os
import sys

# إضافة المسار للمشروع
sys.path.insert(0, '/var/www/tony_erp')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django
django.setup()

from django.urls import get_resolver
from django.urls.resolvers import URLPattern, URLResolver
import re
from collections import defaultdict

def get_all_url_names(resolver=None, prefix=''):
    """Get all defined URL names"""
    if resolver is None:
        resolver = get_resolver()
    names = set()
    for pattern in resolver.url_patterns:
        if isinstance(pattern, URLResolver):
            ns = pattern.namespace or ''
            if ns:
                new_prefix = f'{prefix}{ns}:' if prefix else f'{ns}:'
            else:
                new_prefix = prefix
            names.update(get_all_url_names(pattern, new_prefix))
        elif isinstance(pattern, URLPattern):
            if pattern.name:
                names.add(f'{prefix}{pattern.name}')
    return names

def get_template_urls():
    """Extract URLs from templates"""
    template_urls = set()
    for root, dirs, files in os.walk('templates'):
        for file in files:
            if file.endswith('.html'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        urls = re.findall(r"{%\s*url\s+'([^']+)'", content)
                        for url in urls:
                            if ':' in url and '{{' not in url and 'object.' not in url and 'request.' not in url:
                                template_urls.add(url)
                except:
                    pass
    return template_urls

# معلومات التطابق المعروفة (URL المفقود -> URL موجود)
URL_ALIASES = {
    # Accounting
    'accounting:account_delete': 'accounting:account_edit',
    'accounting:asset_create': 'accounting:assets_overview',
    'accounting:bank_reconciliation': 'accounting:bank_reconcile',
    'accounting:cheque_edit': 'accounting:cheque_detail',
    'accounting:cost_allocation_create': 'accounting:cost_allocations_list',
    'accounting:cost_center_delete': 'accounting:cost_center_detail',
    'accounting:journal_drafts': 'accounting:journal_drafts_list',
    'accounting:journal_entry_edit': 'accounting:journal_entry_detail',
    'accounting:journal_entry_post': 'accounting:post_journal_entry',
    'accounting:journal_template_edit': 'accounting:journal_template_detail',
    'accounting:journal_templates': 'accounting:journal_templates_list',
    
    # Sales
    'sales:customer_list': 'sales:customers_list',
    
    # Purchases
    'purchases:po_edit': 'purchases:po_detail',
    'purchases:quotation_edit': 'purchases:quotation_detail',
    
    # HR
    'hr:department_delete': 'hr:department_detail',
    'hr:department_edit': 'hr:department_detail',
    'hr:position_edit': 'hr:position_detail',
    
    # CRM
    'crm:contact_create': 'crm:contacts_list',
    'crm:contact_edit': 'crm:contact_detail',
    
    # Inventory
    'inventory:analytics_dashboard': 'inventory:inventory_analytics_dashboard',
}

def main():
    print("=== فحص URLs المفقودة ===\n")
    
    defined_urls = get_all_url_names()
    template_urls = get_template_urls()
    
    missing = sorted(template_urls - defined_urls)
    
    if not missing:
        print("✅ لا توجد URLs مفقودة!")
        return
    
    # تصنيف حسب التطبيق
    missing_by_app = defaultdict(list)
    for url in missing:
        app = url.split(':')[0]
        missing_by_app[app].append(url)
    
    print(f"تم العثور على {len(missing)} URL مفقود:\n")
    
    for app, urls in sorted(missing_by_app.items()):
        print(f"\n{app}: ({len(urls)} URLs)")
        for url in sorted(urls)[:5]:
            alias = URL_ALIASES.get(url)
            if alias:
                print(f"  ❌ {url} → ✓ {alias}")
            else:
                print(f"  ❌ {url}")
        if len(urls) > 5:
            print(f"  ... و {len(urls) - 5} أخرى")
    
    print(f"\n\n=== الحلول الموصى بها ===")
    print(f"1. إضافة aliases في ملفات urls.py للـ URLs المتطابقة")
    print(f"2. إنشاء views جديدة للـ URLs المفقودة تماماً")
    print(f"3. تحديث القوالب لاستخدام الـ URL names الصحيحة")

if __name__ == '__main__':
    main()
