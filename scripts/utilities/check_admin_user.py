import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tony_erp.settings')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

admins = User.objects.filter(is_superuser=True)
print(f"Admins count: {admins.count()}")
if admins.exists():
    print(f"First admin: {admins.first().username}")

from crm.models import Activity
# print activity fields
print([f.name for f in Activity._meta.fields])
