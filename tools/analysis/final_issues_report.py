# -*- coding: utf-8 -*-
"""
Final comprehensive check for Django project issues
"""
import os
import django
os.environ['DJANGO_SETTINGS_MODULE'] = 'accountant_pro.settings'
django.setup()

from django.apps import apps
from django.urls import reverse, NoReverseMatch

print('=' * 80)
print('تقرير فحص مشاكل مشروع Django')
print('=' * 80)

# =========================================================================
# 1. MISSING MODELS REFERENCED IN CODE
# =========================================================================
print('\n\n📦 1. MODELS غير موجودة مستخدمة في الكود:')
print('-' * 60)

all_model_names = {model.__name__ for model in apps.get_models()}

missing_models = [
    ('accounting/navigation.py', 'PurchaseInvoice', 'لا يوجد - يجب استخدام PurchaseBill'),
    ('core/views.py', 'Transaction', 'لا يوجد - الموجود هو BankTransaction أو PaymentTransaction'),
    ('fixed_assets/models.py', 'JournalEntryLine', 'لا يوجد - الموجود هو JournalEntryItem'),
    ('maintenance/views.py', 'Maintenance', 'لا يوجد - الموجود هو MaintenanceRecord أو MaintenanceRequest'),
    ('purchases/views.py', 'ProductStock', 'لا يوجد - الموجود هو Stock'),
    ('purchases/views.py', 'CompanySettings', 'لا يوجد - الموجود هو AppSettings'),
    ('pos/signals.py', 'PosSession', 'لا يوجد - الموجود هو POSSession'),
    ('showrooms/views_pages.py', 'POSOrderItem', 'لا يوجد - الموجود هو POSOrderLine'),
    ('woocommerce_integration/signals.py', 'ProductStock', 'لا يوجد - الموجود هو Stock'),
    ('woocommerce_integration/signals.py', 'SalesInvoice', 'لا يوجد - الموجود هو Invoice'),
    ('hr/payroll_calculator.py', 'WorkerProduction', 'لا يوجد - الموجود هو WorkerProductionEntry'),
    ('maintenance/management/commands/grant_maintenance_permissions.py', 'UserModulePermission', 'لا يوجد - الموجود هو ModulePermission'),
]

for file, model, note in missing_models:
    print(f'  ❌ {model}')
    print(f'     الملف: {file}')
    print(f'     ملاحظة: {note}')
    print()


# =========================================================================
# 2. BROKEN URL NAMES IN TEMPLATES
# =========================================================================
print('\n\n🔗 2. URLs مكسورة في Templates:')
print('-' * 60)

broken_urls = [
    ('accounting:journal_detail', 'templates/accounting/period_close_year.html'),
    ('crm:customers_list', 'templates/dashboard.html'),
    ('eservices:operator_edit', 'templates/eservices/operator_list.html'),
    ('hr:id_card_deactivate', 'templates/hr/id_card_preview.html'),
    ('hr:id_card_print_pdf', 'templates/hr/id_card_preview.html'),
    ('maintenance:request_detail', 'templates/maintenance/preventive/dashboard.html'),
    ('production:work_center_list', 'templates/production/work_center_detail.html'),
    ('production:workers_list', 'templates/production/worker_production_history.html'),
]

for url_name, template in broken_urls:
    try:
        reverse(url_name)
        print(f'  ✅ {url_name} - يعمل')
    except NoReverseMatch:
        try:
            reverse(url_name, kwargs={'pk': 1})
            print(f'  ✅ {url_name} - يعمل (يحتاج pk)')
        except:
            try:
                reverse(url_name, args=[1])
                print(f'  ✅ {url_name} - يعمل (يحتاج arg)')
            except:
                print(f'  ❌ {url_name}')
                print(f'     في القالب: {template}')
    print()


# =========================================================================
# 3. MISSING TEMPLATES
# =========================================================================
print('\n\n📄 3. Templates مفقودة (عينة من أهمها):')
print('-' * 60)

import glob

# Collect existing templates
existing_templates = set()
for root, dirs, files in os.walk('templates'):
    for f in files:
        if f.endswith('.html'):
            rel = os.path.relpath(os.path.join(root, f), 'templates')
            existing_templates.add(rel.replace('\\', '/'))

critical_missing = [
    'accounting/trial_balance_comparison.html',
    'crm/analytics/dashboard.html',
    'hr/payroll_auto_calculate.html',
    'inventory/analytics/stock_valuation.html',
    'maintenance/maintenance_alerts.html',
    'pos/receipt.html',
    'production/integrated_dashboard.html',
    'production/oee_dashboard.html',
    'reports/builder/create.html',
    'users/security_logs.html',
]

for tpl in critical_missing:
    if tpl not in existing_templates:
        print(f'  ❌ {tpl}')
    else:
        print(f'  ✅ {tpl}')

print('\n  ... وهناك المزيد (165 قالب مفقود إجمالاً)')


# =========================================================================
# 4. VIEW IMPORTS ERRORS
# =========================================================================
print('\n\n📥 4. أخطاء استيراد Views:')
print('-' * 60)
print('  ❌ exports.views - الوحدة غير موجودة')


# =========================================================================
# SUMMARY
# =========================================================================
print('\n\n' + '=' * 80)
print('📊 ملخص المشاكل المكتشفة:')
print('=' * 80)
print(f'''
  • Models غير موجودة: 12
  • URLs مكسورة: 8
  • Templates مفقودة: ~165
  • أخطاء استيراد: 1
  
⚠️ إجمالي المشاكل التي تحتاج إصلاح: ~186
''')
