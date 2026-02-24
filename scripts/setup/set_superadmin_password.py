import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')

try:
    import django
    django.setup()
except Exception as e:
    print(f"Django setup failed: {e}")
    sys.exit(1)

from django.contrib.auth import get_user_model

User = get_user_model()

USERNAME = 'superadmin'
PASSWORD = 'Mm02022006'
EMAIL = 'admin@example.com'

u = User.objects.filter(username=USERNAME).first()
if not u:
    u = User.objects.create_superuser(username=USERNAME, email=EMAIL, password=PASSWORD)
else:
    u.set_password(PASSWORD)
    u.is_superuser = True
    u.is_staff = True
    u.save()

print('OK: superadmin password set')
