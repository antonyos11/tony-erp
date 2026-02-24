import os
import django
from django.conf import settings

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "accountant_pro.settings")
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

def verify_pricing_pages():
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

    urls = [
        '/smart-pricing/quote/calculate/cost-based/',
        '/smart-pricing/quote/calculate/ai-recommendation/'
    ]

    print("Checking Pricing Calculation Pages...")
    
    for url in urls:
        try:
            response = client.get(url)
            if response.status_code == 200:
                print(f"✅ Success: {url} loaded (200 OK)")
            else:
                print(f"❌ Failed: {url} returned {response.status_code}")
        except Exception as e:
            print(f"❌ Error checking {url}: {e}")

if __name__ == "__main__":
    verify_pricing_pages()
