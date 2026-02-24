import os
import sys
import django
from django.test import Client
from django.urls import reverse, resolve

# Setup Django
sys.path.append('/var/www/tony_erp')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

modules_to_check = [
    'accounting', 'inventory', 'sales', 'purchases', 'hr', 'crm', 'production',
    'maintenance', 'fleet', 'pos', 'showrooms', 'approvals', 'notifications',
    'fixed_assets', 'contracting', 'shipping', 'eservices', 'projects',
    'home_services', 'quick_access', 'data_import', 'attendance', 'branches',
    'bank_reconciliation', 'bank_integration', 'budgeting', 'quality_control',
    'loyalty', 'helpdesk', 'smart_pricing', 'subscriptions', 'zatca',
    'sales_forecasting', 'marketing_campaigns', 'tender_bidding',
    'warranty_management', 'customer_profitability', 'energy_management',
    'complaint_management', 'license_management', 'competitive_intelligence',
    'compliance_management', 'risk_management', 'contract_management',
    'treasury_management', 'correspondence_management', 'intellectual_property',
    'advanced_crm', 'ai_assistant', 'business_intelligence', 'whatsapp_ai',
    'sound_notifications', 'theme_system', 'voice_assistant', 'custom_dashboard',
    'tasks', 'digital_signatures', 'report_builder', 'internal_chat',
    'cloud_backup', 'ai_analytics', 'video_calls', 'collaborative_docs', 'cms',
    'smartwatch'
]

client = Client()

# Create or get a superuser for testing
from django.contrib.auth import get_user_model
User = get_user_model()
user, created = User.objects.get_or_create(username='admin_test', defaults={'is_staff': True, 'is_superuser': True})
if created:
    user.set_password('pass123')
    user.save()
client.force_login(user)

print(f"{'Module':<30} | {'Status':<10} | {'URL'}")

print("-" * 60)

for module in modules_to_check:
    # Try common dashboard names
    names = [f'{module}:dashboard', f'{module}:home', f'{module}:dashboard_alt']
    found = False
    
    for name in names:
        try:
            url = reverse(name)
            response = client.get(url, follow=True)
            status = response.status_code
            print(f"{module:<30} | {status:<10} | {url}")
            found = True
            break
        except Exception:
            continue
            
    if not found:
        # Try manual path check from urls.py logic
        manual_path = f'/{module.replace("_", "-")}/dashboard/'
        try:
            response = client.get(manual_path, follow=True)
            status = response.status_code
            print(f"{module:<30} | {status:<10} | {manual_path} (Manual)")
        except Exception as e:
            print(f"{module:<30} | ERROR      | {str(e)}")
