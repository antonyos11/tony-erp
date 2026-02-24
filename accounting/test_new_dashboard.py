"""
اختبار سريع للوحة المحاسبة الجديدة
========================================

لتشغيل هذا الاختبار:
python manage.py shell < test_new_dashboard.py
"""

from django.contrib.auth.models import User
from accounting.permissions import (
    AccountingRoles,
    create_accounting_roles,
    assign_user_to_role,
    get_user_accounting_role
)
from accounting.accounting_structure import (
    get_user_accounting_tabs,
    filter_items_by_user,
    ACCOUNTING_STRUCTURE
)

print("=" * 60)
print("🧪 اختبار لوحة المحاسبة الجديدة")
print("=" * 60)

# 1. إنشاء الأدوار
print("\n1️⃣ إنشاء الأدوار...")
result = create_accounting_roles()
print(f"   ✅ تم إنشاء: {len(result['created'])} أدوار")
print(f"   🔄 تم تحديث: {len(result['updated'])} أدوار")

# 2. إنشاء مستخدمين للاختبار
print("\n2️⃣ إنشاء مستخدمين للاختبار...")

# كاشير
cashier, created = User.objects.get_or_create(
    username='test_cashier',
    defaults={'email': 'cashier@test.com'}
)
if created:
    cashier.set_password('test123')
    cashier.save()
assign_user_to_role(cashier, AccountingRoles.CASHIER)
print(f"   💼 كاشير: {cashier.username}")

# محاسب
accountant, created = User.objects.get_or_create(
    username='test_accountant',
    defaults={'email': 'accountant@test.com'}
)
if created:
    accountant.set_password('test123')
    accountant.save()
assign_user_to_role(accountant, AccountingRoles.ACCOUNTANT)
print(f"   📊 محاسب: {accountant.username}")

# مدير مالي
cfo, created = User.objects.get_or_create(
    username='test_cfo',
    defaults={'email': 'cfo@test.com'}
)
if created:
    cfo.set_password('test123')
    cfo.save()
assign_user_to_role(cfo, AccountingRoles.CFO)
print(f"   👔 مدير مالي: {cfo.username}")

# 3. اختبار التبويبات المتاحة
print("\n3️⃣ اختبار التبويبات المتاحة...")

cashier_tabs = get_user_accounting_tabs(cashier)
print(f"   💼 كاشير - عدد التبويبات: {len(cashier_tabs)}")
print(f"      {cashier_tabs}")

accountant_tabs = get_user_accounting_tabs(accountant)
print(f"   📊 محاسب - عدد التبويبات: {len(accountant_tabs)}")
print(f"      {accountant_tabs}")

cfo_tabs = get_user_accounting_tabs(cfo)
print(f"   👔 مدير مالي - عدد التبويبات: {len(cfo_tabs)}")
print(f"      {cfo_tabs}")

# 4. اختبار تصفية العناصر
print("\n4️⃣ اختبار تصفية العناصر...")

# عد العناصر في التبويب الأول (الأساسيات اليومية)
tab_id = 'daily_basics'
if tab_id in ACCOUNTING_STRUCTURE:
    total_items = 0
    for group in ACCOUNTING_STRUCTURE[tab_id].get('groups', []):
        items = group.get('items', [])
        total_items += len(items)
    
    print(f"\n   التبويب: {tab_id}")
    print(f"   إجمالي العناصر: {total_items}")
    
    # تصفية للكاشير
    cashier_items = 0
    for group in ACCOUNTING_STRUCTURE[tab_id].get('groups', []):
        filtered = filter_items_by_user(group.get('items', []), cashier)
        cashier_items += len(filtered)
    print(f"   💼 كاشير يرى: {cashier_items} عنصر")
    
    # تصفية للمحاسب
    accountant_items = 0
    for group in ACCOUNTING_STRUCTURE[tab_id].get('groups', []):
        filtered = filter_items_by_user(group.get('items', []), accountant)
        accountant_items += len(filtered)
    print(f"   📊 محاسب يرى: {accountant_items} عنصر")
    
    # تصفية للمدير المالي
    cfo_items = 0
    for group in ACCOUNTING_STRUCTURE[tab_id].get('groups', []):
        filtered = filter_items_by_user(group.get('items', []), cfo)
        cfo_items += len(filtered)
    print(f"   👔 مدير مالي يرى: {cfo_items} عنصر")

# 5. اختبار الدور
print("\n5️⃣ اختبار الحصول على الدور...")

cashier_role = get_user_accounting_role(cashier)
print(f"   💼 {cashier.username} -> {cashier_role}")

accountant_role = get_user_accounting_role(accountant)
print(f"   📊 {accountant.username} -> {accountant_role}")

cfo_role = get_user_accounting_role(cfo)
print(f"   👔 {cfo.username} -> {cfo_role}")

# 6. معلومات الوصول
print("\n6️⃣ معلومات الوصول...")
print(f"""
   🌐 للوصول للوحة الجديدة:
   
   URL: http://localhost:8013/accounting/dashboard-new/
   
   📝 بيانات الاختبار:
   
   كاشير:
     username: test_cashier
     password: test123
   
   محاسب:
     username: test_accountant
     password: test123
   
   مدير مالي:
     username: test_cfo
     password: test123
""")

print("\n" + "=" * 60)
print("✅ انتهى الاختبار بنجاح!")
print("=" * 60)
