import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from crm.models import Customer

print("Checking customer codes...")
customers = Customer.objects.all().order_by('-id')[:10]
for c in customers:
    print(f"ID: {c.id}, Code: {c.customer_code}")
