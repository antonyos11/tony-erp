#!/usr/bin/env python
"""
اختبار سريع لنقطة البيع - فحص الاتصال والصلاحيات
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from django.contrib.auth.models import User
from pos.models import POSOrder, POSOrderLine
from inventory.models import Product

def test_pos_connection():
    """اختبار الاتصال بنقطة البيع"""
    print("=" * 60)
    print("🧪 اختبار نقطة البيع - فحص الاتصال والصلاحيات")
    print("=" * 60)
    print()
    
    # 1. فحص المستخدمين
    print("1️⃣ فحص المستخدمين:")
    users = User.objects.all()
    print(f"   عدد المستخدمين: {users.count()}")
    
    for user in users[:5]:
        print(f"   - {user.username}:")
        print(f"     Staff: {user.is_staff}, Superuser: {user.is_superuser}")
        if hasattr(user, 'has_module_permission'):
            try:
                can_add = user.has_module_permission('pos', 'add')
                can_change = user.has_module_permission('pos', 'change')
                can_delete = user.has_module_permission('pos', 'delete')
                print(f"     POS Permissions - Add: {can_add}, Change: {can_change}, Delete: {can_delete}")
            except Exception as e:
                print(f"     ⚠️ خطأ في فحص الصلاحيات: {e}")
    print()
    
    # 2. فحص المنتجات
    print("2️⃣ فحص المنتجات:")
    products = Product.objects.all()
    print(f"   عدد المنتجات: {products.count()}")
    if products.exists():
        product = products.first()
        print(f"   مثال: {product.name} (ID: {product.id})")
        print(f"   السعر: {product.price}")
    else:
        print("   ⚠️ لا توجد منتجات في قاعدة البيانات!")
    print()
    
    # 3. فحص الطلبات
    print("3️⃣ فحص طلبات POS:")
    orders = POSOrder.objects.all()
    print(f"   عدد الطلبات: {orders.count()}")
    
    draft_orders = POSOrder.objects.filter(status='draft')
    print(f"   الطلبات المسودة: {draft_orders.count()}")
    
    if draft_orders.exists():
        order = draft_orders.first()
        print(f"   آخر طلب مسودة: #{order.id}")
        print(f"   الحالة: {order.status}")
        print(f"   الإجمالي: {order.total}")
        print(f"   عدد البنود: {order.lines.count()}")
    print()
    
    # 4. اختبار إضافة بند (محاكاة)
    print("4️⃣ اختبار إضافة بند:")
    if draft_orders.exists() and products.exists():
        order = draft_orders.first()
        product = products.first()
        
        try:
            # محاكاة إضافة بند
            line = POSOrderLine(
                order=order,
                product=product,
                quantity=1,
                price=product.price
            )
            print(f"   ✅ يمكن إنشاء بند: {product.name}")
            print(f"   المجموع سيكون: {line.total}")
            
            # لا نحفظ فعلياً لتجنب تغيير البيانات
            # line.save()
            print("   ℹ️ لم يتم الحفظ فعلياً (اختبار فقط)")
            
        except Exception as e:
            print(f"   ❌ خطأ في إضافة البند: {e}")
    else:
        print("   ⚠️ لا يمكن الاختبار - لا توجد طلبات مسودة أو منتجات")
    print()
    
    # 5. فحص CSRF في الإعدادات
    print("5️⃣ فحص إعدادات CSRF:")
    from django.conf import settings
    print(f"   CSRF_COOKIE_SECURE: {getattr(settings, 'CSRF_COOKIE_SECURE', False)}")
    print(f"   CSRF_COOKIE_HTTPONLY: {getattr(settings, 'CSRF_COOKIE_HTTPONLY', False)}")
    print(f"   CSRF_USE_SESSIONS: {getattr(settings, 'CSRF_USE_SESSIONS', False)}")
    print()
    
    # 6. التوصيات
    print("📋 التوصيات:")
    
    superuser_exists = User.objects.filter(is_superuser=True).exists()
    if not superuser_exists:
        print("   ⚠️ لا يوجد مستخدم superuser. أنشئ واحداً باستخدام:")
        print("      python manage.py createsuperuser")
    else:
        print("   ✅ يوجد مستخدم superuser")
    
    if not products.exists():
        print("   ⚠️ لا توجد منتجات. أضف منتجات من لوحة التحكم")
    else:
        print("   ✅ توجد منتجات متاحة")
    
    if not draft_orders.exists():
        print("   ℹ️ لا توجد طلبات مسودة. أنشئ طلباً جديداً من:")
        print("      /pos/order/new/")
    else:
        print("   ✅ توجد طلبات مسودة يمكن العمل عليها")
    
    print()
    print("=" * 60)
    print("✅ انتهى الاختبار")
    print("=" * 60)

if __name__ == '__main__':
    test_pos_connection()
