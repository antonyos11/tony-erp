"""تحقق تفصيلي من الكتالوج"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from django.urls import reverse, NoReverseMatch

# تحقق من URL
print("=" * 60)
print("فحص URL الكتالوج:")
print("=" * 60)
try:
    url = reverse('inventory:catalog_list')
    print(f"✓ URL ناجح: {url}")
except NoReverseMatch as e:
    print(f"✗ فشل في حل URL: {e}")

# تحقق من السطر الفعلي في الملف
print("\n" + "=" * 60)
print("فحص الملف المصدري:")
print("=" * 60)

import importlib
import core.context_processors
# إجبار إعادة التحميل
importlib.reload(core.context_processors)

from core.context_processors import user_permissions

# فحص modules_config داخل الدالة
print("\nجاري فحص modules_config...")

# لا نستطيع الوصول للمتغير الداخلي مباشرة
# لكن نستطيع فحص ملف المصدر
import inspect
source = inspect.getsource(user_permissions)
if 'catalog_list' in source:
    print("✓ catalog_list موجود في كود الدالة")
    # عرض السطور المحتوية على catalog
    for i, line in enumerate(source.split('\n')):
        if 'catalog' in line.lower():
            print(f"   سطر {i}: {line.strip()}")
else:
    print("✗ catalog_list غير موجود في كود الدالة!")

# فحص من خلال request
print("\n" + "=" * 60)
print("محاكاة الطلب:")
print("=" * 60)

from django.test import RequestFactory
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.filter(is_superuser=True).first()
factory = RequestFactory()
request = factory.get('/')
request.user = user

result = user_permissions(request)
user_modules = result.get('user_modules', {})

if 'inventory' in user_modules:
    items = user_modules['inventory'].get('items', [])
    print(f"عدد عناصر المخزون: {len(items)}")
    
    # البحث عن catalog
    for item in items:
        url = item.get('url', '')
        name = item.get('name', '')
        if 'catalog' in url or 'كتالوج' in str(name):
            print(f"\n*** تم العثور على الكتالوج! ***")
            print(f"   {item}")
            break
    else:
        print("\n!!! لم يتم العثور على الكتالوج !!!")
        print("\nأول 3 عناصر:")
        for item in items[:3]:
            print(f"   {item}")
