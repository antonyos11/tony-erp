import os
import django
from django.conf import settings

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "accountant_pro.settings")
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

def verify_advanced_notifications():
    client = Client()
    User = get_user_model()
    try:
        user = User.objects.get(username='admin_test_url')
    except User.DoesNotExist:
        user = User.objects.create_superuser('admin_test_url', 'admin@test.com', 'password123')
    
    # Bypass password change enforcement
    if hasattr(user, 'profile'):
        profile = user.profile
        profile.must_change_password = False
        profile.is_approved = True
        profile.save()

    client.force_login(user)

    url = '/advanced-notifications/dashboard/'
    print(f"Checking {url} ...")

    try:
        response = client.get(url)
        if response.status_code == 200:
            print("✅ Success: Page loaded (200 OK)")
            if 'لوحة تحكم الإشعارات المتقدمة' in response.content.decode('utf-8'):
                 print("✅ Validation: Correct template rendered.")
            else:
                 print("⚠️ Warning: Page loaded but title not found.")
        else:
            print(f"❌ Failed: Status Code {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    verify_advanced_notifications()
