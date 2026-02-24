# -*- coding: utf-8 -*-
import os
import django
os.environ['DJANGO_SETTINGS_MODULE'] = 'accountant_pro.settings'
django.setup()

print('=' * 80)
print('CHECKING FOR ACTUAL MODEL NAMES')
print('=' * 80)

from django.apps import apps
all_models = sorted([f'{m._meta.app_label}.{m.__name__}' for m in apps.get_models()])

# Search for similar models
search_terms = ['Invoice', 'Transaction', 'Journal', 'Stock', 'Session', 'Order', 'Worker', 'Permission', 'Settings', 'Maintenance']

for term in search_terms:
    matches = [m for m in all_models if term in m]
    if matches:
        print(f'\nModels containing "{term}":')
        for m in matches[:15]:
            print(f'  - {m}')
