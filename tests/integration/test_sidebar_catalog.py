"""تحقق من ظهور الكتالوج في القائمة الجانبية"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from core.sidebar_processor import sidebar_menu
from core.context_processors import user_permissions

User = get_user_model()
user = User.objects.filter(is_superuser=True).first()
if not user:
    print("لا يوجد مستخدم superuser!")
    exit(1)

factory = RequestFactory()
request = factory.get('/')
request.user = user

# فحص user_permissions أولاً
print("=" * 60)
print("فحص user_permissions:")
print("=" * 60)
perm_result = user_permissions(request)
user_modules = perm_result.get('user_modules', {})
print(f"عدد الوحدات: {len(user_modules)}")

if 'inventory' in user_modules:
    inv_module = user_modules['inventory']
    print(f"\nوحدة المخزون موجودة!")
    print(f"  الاسم: {inv_module.get('name')}")
    print(f"  عدد العناصر: {len(inv_module.get('items', []))}")
    
    # البحث عن الكتالوج
    catalog_found = False
    for item in inv_module.get('items', []):
        if 'catalog' in item.get('url', '') or 'كتالوج' in item.get('name', ''):
            catalog_found = True
            print(f"\n  *** تم العثور على الكتالوج ***")
            print(f"      الاسم: {item.get('name')}")
            print(f"      URL: {item.get('url')}")
            print(f"      الأيقونة: {item.get('icon')}")
    
    if not catalog_found:
        print("\n  !!! الكتالوج غير موجود في عناصر المخزون !!!")
        print("  العناصر المتاحة:")
        for item in inv_module.get('items', [])[:10]:
            print(f"    - {item.get('name')} => {item.get('url')}")
else:
    print("وحدة المخزون غير موجودة!")

# فحص sidebar_menu
print("\n" + "=" * 60)
print("فحص sidebar_menu:")
print("=" * 60)
result = sidebar_menu(request)
sections = result.get('sidebar_sections', [])
print(f"عدد الأقسام: {len(sections)}")

for s in sections:
    section_id = s.get('id', '')
    section_label = s.get('label', '')
    if 'inventory' in section_id.lower() or 'مخ' in section_label:
        print(f"\nقسم المخزون موجود!")
        print(f"  ID: {section_id}")
        print(f"  Label: {section_label}")
        items = s.get('items', [])
        print(f"  عدد العناصر: {len(items)}")
        
        # البحث عن الكتالوج
        catalog_found = False
        for item in items:
            label = item.get('label', '')
            url = item.get('url', '')
            if 'catalog' in url or 'كتالوج' in label:
                catalog_found = True
                print(f"\n  *** تم العثور على الكتالوج في sidebar_sections ***")
                print(f"      Label: {label}")
                print(f"      URL: {url}")
        
        if not catalog_found:
            print("\n  !!! الكتالوج غير موجود في sidebar_sections !!!")
            print("  أول 5 عناصر:")
            for item in items[:5]:
                print(f"    - {item.get('label')} => {item.get('url')}")

print("\n" + "=" * 60)
print("انتهى الفحص")
print("=" * 60)
