"""Debug script to check context_processors output"""
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from core.context_processors import user_permissions

User = get_user_model()

# Create a fake request
factory = RequestFactory()
request = factory.get('/')

# Get superadmin user
user = User.objects.filter(username='superadmin').first()
request.user = user

# Get context
context = user_permissions(request)

# Print showrooms module
if 'user_modules' in context:
    showrooms = context['user_modules'].get('showrooms')
    if showrooms:
        print("=" * 80)
        print(f"وحدة المعارض - عدد العناصر: {len(showrooms.get('items', []))}")
        print("=" * 80)
        for i, item in enumerate(showrooms.get('items', []), 1):
            item_type = item.get('type', 'link')
            if item_type == 'header':
                print(f"\n{i}. [رأس] {item.get('name')}")
            elif item_type == 'divider':
                print(f"{i}. [فاصل]")
            else:
                print(f"{i}. {item.get('name')} -> {item.get('url')}")
    else:
        print("❌ وحدة المعارض غير موجودة في user_modules")
        
    # Print CRM too
    crm = context['user_modules'].get('crm')
    if crm:
        print("\n" + "=" * 80)
        print(f"وحدة CRM - عدد العناصر: {len(crm.get('items', []))}")
        print("=" * 80)
        for i, item in enumerate(crm.get('items', []), 1):
            item_type = item.get('type', 'link')
            if item_type == 'header':
                print(f"\n{i}. [رأس] {item.get('name')}")
            elif item_type == 'divider':
                print(f"{i}. [فاصل]")
            else:
                print(f"{i}. {item.get('name')} -> {item.get('url')}")
    else:
        print("\n❌ وحدة CRM غير موجودة في user_modules")
else:
    print("❌ user_modules غير موجود في السياق!")

print("\n" + "=" * 80)
print("جميع الوحدات المتاحة:")
print("=" * 80)
if 'user_modules' in context:
    for key in context['user_modules'].keys():
        items_count = len(context['user_modules'][key].get('items', []))
        print(f"  - {key}: {items_count} عنصر")
