import os
import django
import sys
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from crm.serializers import QuotationSerializer
from rest_framework.exceptions import ValidationError

payload = {
    "customer": 1, 
    "items": [
        {
            "product": 1,
            "quantity": 2,
            "unit_price": 100.0
        }
    ],
    "valid_until": "2026-12-31"
}

print("Checking Serializer Validation...")
serializer = QuotationSerializer(data=payload)
if serializer.is_valid():
    print("✅ VALID")
else:
    print("❌ INVALID")
    print(serializer.errors)

from crm.serializers import QuotationItemSerializer
print("\nQuotationItemSerializer Meta.read_only_fields:", QuotationItemSerializer.Meta.read_only_fields)
