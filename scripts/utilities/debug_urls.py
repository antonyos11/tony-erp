
import os
import sys
import django
from django.urls import resolve, reverse

# Setup Django environment
sys.path.append('/var/www/tony_erp')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

def check_url(url):
    print(f"Checking URL: {url}")
    try:
        match = resolve(url)
        print(f"Match: {match.view_name} -> {match.func}")
    except Exception as e:
        print(f"Error resolving {url}: {e}")

urls_to_check = [
    '/dashboard/',
    '/api/token/',
    '/api/products/',
    '/accounts/login/',
    '/health/live/',
]

for url in urls_to_check:
    check_url(url)
