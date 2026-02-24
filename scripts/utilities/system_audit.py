import os
import sys
import django
from django.urls import get_resolver, URLPattern, URLResolver
from django.test import Client

# Setup Django environment
sys.path.append('/var/www/tony_erp')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

def list_urls(lis, acc=None):
    if acc is None:
        acc = []
    if not lis:
        return
    l = lis[0]
    if isinstance(l, URLPattern):
        yield acc + [str(l.pattern)]
    elif isinstance(l, URLResolver):
        yield from list_urls(l.url_patterns, acc + [str(l.pattern)])
    yield from list_urls(lis[1:], acc)

def get_all_urls():
    resolver = get_resolver()
    all_urls = []
    
    # Simple recursive walker (better than listing blindly)
    def trace_urls(resolver, prefix=''):
        for pattern in resolver.url_patterns:
            if hasattr(pattern, 'url_patterns'):
                # It's a resolver
                trace_urls(pattern, prefix + str(pattern.pattern))
            elif hasattr(pattern, 'pattern'):
                # It's a view
                url = prefix + str(pattern.pattern)
                # Filter out admin, auth, api, and complex regex parameters to keep it simple for now
                if 'admin/' in url or 'api/' in url or '<' in url:
                    continue
                all_urls.append(url)
    
    trace_urls(resolver)
    
    # Add manual ones
    dashboard_apps = [
        'sales-forecasting', 'marketing-campaigns', 'tender-bidding', 
        'warranty-management', 'customer-profitability', 'energy-management',
        'license-management', 'competitive-intelligence', 'compliance-management',
        'intellectual-property', 'contract-management', 'risk-management', 
        'treasury-management', 'whatsapp-ai', 'correspondence-management',
        'advanced-crm', 'ai-assistant', 'business-intelligence'
    ]
    for app in dashboard_apps:
        all_urls.append(f'{app}/dashboard/')
        all_urls.append(f'{app}/')

    return sorted(list(set(all_urls)))

print("Starting Comprehensive System Audit...")
print("="*60)

client = Client()
urls = get_all_urls()

broken_links = []
working_links = []
redirected_to_login = []

for url in urls:
    url_path = '/' + url.lstrip('/')
    
    try:
        # Don't follow redirects here to see where they go
        response = client.get(url_path, follow=False)
        status = response.status_code
        
        if status == 404:
            broken_links.append((url_path, status))
            print(f"[FAILED 404] : {url_path}")
        elif status == 302 or status == 301:
            location = response.get('Location', '')
            if 'login' in location:
                redirected_to_login.append(url_path)
            else:
                # Follow once to see if it's 404
                response2 = client.get(url_path, follow=True)
                if response2.status_code == 404:
                    broken_links.append((url_path, f"404 after redirect to {location}"))
                    print(f"[FAILED 404 AFTER REDIRECT] : {url_path} -> {location}")
                else:
                    working_links.append((url_path, status))
        elif status >= 400:
            broken_links.append((url_path, status))
            print(f"[FAILED {status}] : {url_path}")
        else:
            working_links.append((url_path, status))
            
    except Exception as e:
        broken_links.append((url_path, f"ERROR: {str(e)}"))
        print(f"[ERROR] {url_path} : {str(e)}")

print("="*60)
print(f"Audit Complete. Found {len(broken_links)} broken links.")
print(f"Working: {len(working_links)}")
print(f"Redirected to Login: {len(redirected_to_login)}")
print("-" * 20)
if broken_links:
    print("BROKEN LINKS INVENTORY:")
    for link, status in broken_links:
        print(f"- {link} (Status: {status})")
else:
    print("No broken links found!")


