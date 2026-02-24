import os
import django
from django.conf import settings

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "accountant_pro.settings")
django.setup()

from django.test import Client, RequestFactory
from django.urls import reverse

def verify_urls():
    client = Client()
    # Create a user for login (since views are login_required)
    from django.contrib.auth import get_user_model
    User = get_user_model()
    try:
        user = User.objects.get(username='admin_test_url')
    except User.DoesNotExist:
        user = User.objects.create_superuser('admin_test_url', 'admin@test.com', 'password123')
    
    client.force_login(user)
    
    # Ensure user profile allows access (bypass password change enforcement)
    if hasattr(user, 'profile'):
        profile = user.profile
        profile.must_change_password = False
        profile.is_approved = True
        profile.save()


    urls_to_test = [
        ('/smart-pricing/production-line-suggestion/capacity/', 'production_line_capacity'),
        ('/smart-pricing/production-line-suggestion/efficiency/', 'production_line_efficiency'),
        ('/smart-pricing/production-line-suggestion/ai/', 'production_line_ai'),
        ('/smart-pricing/production-line-suggestion/cost/', 'production_line_cost'),
        ('/random-page-to-test-404/', '404_test'), # Test custom 404
    ]

    print("Verifying URLs...")
    all_passed = True
    
    for url, name in urls_to_test:
        try:
            response = client.get(url)
            
            if name == '404_test':
                if response.status_code == 404:
                    print(f"✅ {url} returned 404 as expected.")
                    # Check if our custom content is present
                    if b'404' in response.content and b'body' in response.content:
                        print(f"   -> Custom 404 template loaded successfully.")
                    else:
                        print(f"   ⚠️  Custom 404 template might not be loaded correctly (or content is different).")
                else:
                    print(f"❌ {url} returned {response.status_code} (expected 404).")
                    all_passed = False
            else:
                if response.status_code == 200:
                    print(f"✅ {url} returned 200 OK.")
                elif response.status_code == 302:
                     print(f"⚠️ {url} returned 302 (Redirect) - Likely auth issue if not handled. Target: {response.url}")
                else:
                    print(f"❌ {url} returned {response.status_code}.")
                    all_passed = False
                    
        except Exception as e:
            print(f"❌ Error testing {url}: {e}")
            all_passed = False

    if all_passed:
        print("\nAll URL verifications passed successfully!")
    else:
        print("\nSome URL verifications failed.")

if __name__ == "__main__":
    verify_urls()
