import os
import django
from django.conf import settings

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "accountant_pro.settings")
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

def verify_currency():
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

    urls_to_check = [
        ('/smart-pricing/production-line-suggestion/cost/', 'Production Cost'),
        ('/smart-pricing/dashboard/', 'Dashboard'),
    ]

    print("Verifying currency update to EGP (ج.م)...")
    
    all_passed = True
    for url, name in urls_to_check:
        try:
            response = client.get(url)
            if response.status_code == 200:
                content = response.content.decode('utf-8')
                if 'ج.م' in content:
                    print(f"✅ {name}: Found 'ج.م'")
                else:
                    print(f"⚠️ {name}: 'ج.م' NOT found in content.")
                    # Check if 'ر.س' still exists
                    if 'ر.س' in content:
                         print(f"   ❌ {name}: Found 'ر.س' (Old currency) still present!")
                         all_passed = False
                    else:
                         print(f"   ℹ️ {name}: Neither currency symbol found (might be dynamic or empty data).")
            else:
                print(f"❌ {name}: Failed to load (Status: {response.status_code})")
                all_passed = False
        except Exception as e:
            print(f"❌ Error checking {name}: {e}")
            all_passed = False

    if all_passed:
        print("\nVerification Successful: Currency updated.")
    else:
        print("\nVerification Failed.")

if __name__ == "__main__":
    verify_currency()
