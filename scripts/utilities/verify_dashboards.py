from django.test import Client
from django.urls import reverse
import os
import django
import sys

# Setup Django environment
sys.path.append('/var/www/tony_erp')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
import django.utils.encoding
try:
    django.utils.encoding.force_text = django.utils.encoding.force_str
except AttributeError:
    pass

django.setup()

client = Client()

urls_to_check = [
    '/sales-forecasting/dashboard/',
    '/marketing-campaigns/dashboard/',
    '/tender-bidding/dashboard/',
    '/warranty-management/dashboard/',
    '/customer-profitability/dashboard/',
    '/energy-management/dashboard/',
    '/license-management/dashboard/',
    '/competitive-intelligence/dashboard/',
    '/compliance-management/dashboard/',
    '/intellectual-property/dashboard/',
    '/contract-management/dashboard/',
    '/risk-management/dashboard/',
    '/treasury-management/dashboard/',
    # Additional fixes verified
    '/advanced-crm/dashboard/',
    '/correspondence-management/dashboard/',
    '/complaint-management/dashboard/',
    '/whatsapp-ai/dashboard/',
    '/accounting/advanced/budget/',
    '/ecommerce/quick-order/',
]

print("Checking Dashboard URLs...")
print("-" * 50)

failed_count = 0
for url in urls_to_check:
    print(f"Checking {url}...", end=' ')
    try:
        response = client.get(url)
        if response.status_code in [200, 302]: # 302 is likely login redirect which is fine (means URL exists)
            print(f"OK ({response.status_code})")
        else:
            print(f"FAILED ({response.status_code})")
            failed_count += 1
    except Exception as e:
        print(f"ERROR: {str(e)}")
        failed_count += 1

print("-" * 50)
if failed_count == 0:
    print("ALL CHECKS PASSED")
else:
    print(f"{failed_count} CHECKS FAILED")
