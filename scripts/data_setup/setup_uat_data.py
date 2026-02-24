#!/usr/bin/env python
"""
إعداد بيانات اختبار UAT
تشغيل: python setup_uat_data.py
"""

import os
import django
import sys

# إعداد Django
sys.path.insert(0, '/var/www/tony_erp')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tony_erp.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.db import transaction
from datetime import datetime, timedelta
from decimal import Decimal

User = get_user_model()

print("=" * 60)
print("🚀 بدء إعداد بيانات اختبار UAT")
print("=" * 60)

# الحسابات التجريبية
test_users = [
    {
        'username': 'ceo_test',
        'email': 'ceo@test.com',
        'first_name': 'أحمد',
        'last_name': 'المدير',
        'role': 'SUPER_ADMIN',
        'password': 'Test@123'
    },
    {
        'username': 'branch_manager_test',
        'email': 'branch@test.com',
        'first_name': 'محمد',
        'last_name': 'مدير الفرع',
        'role': 'BRANCH_MANAGER',
        'password': 'Test@123'
    },
    {
        'username': 'accountant_test',
        'email': 'accountant@test.com',
        'first_name': 'علي',
        'last_name': 'المحاسب',
        'role': 'ACCOUNTANT',
        'password': 'Test@123'
    },
    {
        'username': 'chief_accountant_test',
        'email': 'chief@test.com',
        'first_name': 'خالد',
        'last_name': 'مدير الحسابات',
        'role': 'SENIOR_ACCOUNTANT',
        'password': 'Test@123'
    },
    {
        'username': 'sales_test',
        'email': 'sales@test.com',
        'first_name': 'عمر',
        'last_name': 'المبيعات',
        'role': 'SALES',
        'password': 'Test@123'
    },
    {
        'username': 'inventory_test',
        'email': 'inventory@test.com',
        'first_name': 'ياسر',
        'last_name': 'المخزون',
        'role': 'INVENTORY_MANAGER',
        'password': 'Test@123'
    },
    {
        'username': 'purchasing_test',
        'email': 'purchasing@test.com',
        'first_name': 'سامي',
        'last_name': 'المشتريات',
        'role': 'PURCHASING',
        'password': 'Test@123'
    },
    {
        'username': 'production_test',
        'email': 'production@test.com',
        'first_name': 'فهد',
        'last_name': 'الإنتاج',
        'role': 'PRODUCTION',
        'password': 'Test@123'
    }
]

print("\n📝 إنشاء حسابات المستخدمين التجريبية...")
print("-" * 60)

created_users = []
for user_data in test_users:
    try:
        password = user_data.pop('password')
        user, created = User.objects.get_or_create(
            username=user_data['username'],
            defaults=user_data
        )
        if created:
            user.set_password(password)
            user.is_active = True
            user.save()
            print(f"✅ تم إنشاء: {user.username} ({user.first_name} {user.last_name})")
            created_users.append(user)
        else:
            print(f"⚠️  موجود مسبقاً: {user.username}")
    except Exception as e:
        print(f"❌ خطأ في إنشاء {user_data.get('username', 'unknown')}: {e}")

print(f"\n✅ تم إنشاء {len(created_users)} مستخدم جديد")

# إنشاء بيانات اختبارية
print("\n" + "=" * 60)
print("📦 جاري إنشاء بيانات اختبارية...")
print("=" * 60)

try:
    from inventory.models import Product, Category, Warehouse
    from sales.models import Customer
    from purchasing.models import Supplier
    
    # الفئات
    print("\n📂 إنشاء فئات المنتجات...")
    categories_data = [
        {'name': 'مراتب', 'name_en': 'Mattresses'},
        {'name': 'أثاث', 'name_en': 'Furniture'},
        {'name': 'إسفنج', 'name_en': 'Foam'},
        {'name': 'أقمشة', 'name_en': 'Fabrics'},
        {'name': 'مواد خام', 'name_en': 'Raw Materials'}
    ]
    
    categories = []
    for cat_data in categories_data:
        cat, created = Category.objects.get_or_create(
            name=cat_data['name'],
            defaults=cat_data
        )
        categories.append(cat)
        if created:
            print(f"  ✅ {cat.name}")
    
    # المخازن
    print("\n🏪 إنشاء مخازن...")
    warehouses_data = [
        {'name': 'المخزن الرئيسي', 'code': 'MAIN'},
        {'name': 'مخزن الفرع 1', 'code': 'BR1'},
        {'name': 'مخزن الفرع 2', 'code': 'BR2'}
    ]
    
    warehouses = []
    for wh_data in warehouses_data:
        wh, created = Warehouse.objects.get_or_create(
            code=wh_data['code'],
            defaults=wh_data
        )
        warehouses.append(wh)
        if created:
            print(f"  ✅ {wh.name}")
    
    # المنتجات
    print("\n📦 إنشاء منتجات تجريبية...")
    products_count = 0
    for i in range(1, 51):
        product_data = {
            'name': f'منتج تجريبي {i}',
            'name_en': f'Test Product {i}',
            'sku': f'TST-{i:04d}',
            'barcode': f'1234567{i:05d}',
            'category': categories[i % len(categories)],
            'unit_price': Decimal(str(100 + (i * 10))),
            'cost_price': Decimal(str(50 + (i * 5))),
            'stock_quantity': 100 + i,
            'min_stock_level': 10,
            'is_active': True
        }
        
        product, created = Product.objects.get_or_create(
            sku=product_data['sku'],
            defaults=product_data
        )
        if created:
            products_count += 1
    
    print(f"  ✅ تم إنشاء {products_count} منتج")
    
    # العملاء
    print("\n👥 إنشاء عملاء تجريبيين...")
    customers_count = 0
    for i in range(1, 21):
        customer_data = {
            'name': f'عميل تجريبي {i}',
            'phone': f'05{i:08d}',
            'email': f'customer{i}@test.com',
            'credit_limit': Decimal('50000'),
            'is_active': True
        }
        
        customer, created = Customer.objects.get_or_create(
            phone=customer_data['phone'],
            defaults=customer_data
        )
        if created:
            customers_count += 1
    
    print(f"  ✅ تم إنشاء {customers_count} عميل")
    
    # الموردين
    print("\n🏭 إنشاء موردين تجريبيين...")
    suppliers_count = 0
    for i in range(1, 11):
        supplier_data = {
            'name': f'مورد تجريبي {i}',
            'phone': f'09{i:08d}',
            'email': f'supplier{i}@test.com',
            'credit_limit': Decimal('100000'),
            'is_active': True
        }
        
        supplier, created = Supplier.objects.get_or_create(
            phone=supplier_data['phone'],
            defaults=supplier_data
        )
        if created:
            suppliers_count += 1
    
    print(f"  ✅ تم إنشاء {suppliers_count} مورد")
    
except ImportError as e:
    print(f"⚠️  بعض النماذج غير متوفرة: {e}")
except Exception as e:
    print(f"❌ خطأ في إنشاء البيانات: {e}")

print("\n" + "=" * 60)
print("✅ اكتمل إعداد بيانات الاختبار بنجاح!")
print("=" * 60)

print("\n📋 ملخص الحسابات التجريبية:")
print("-" * 60)
print("الدور                    | اسم المستخدم          | كلمة المرور")
print("-" * 60)
for user_data in test_users:
    role = user_data.get('role', 'N/A')
    username = user_data.get('username', 'N/A')
    print(f"{role:25} | {username:20} | Test@123")

print("\n💡 للوصول:")
print("   الرابط: http://72.62.176.249/login/")
print("   كلمة المرور لجميع الحسابات: Test@123")

print("\n🎯 الخطوة التالية:")
print("   ابدأ الاختبارات باستخدام ملف UAT_TESTING_PLAN.md")
