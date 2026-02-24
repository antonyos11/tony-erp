
import os
import django
import sys
from decimal import Decimal

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from django.contrib.auth.models import User
from partners.models import Customer, Supplier, Partner
from inventory.models import Product, Location, Category
from branches.models import Branch

def seed_data():
    print("🌱 Seeding test data...")
    
    # 1. Ensure 'boss' user exists
    user, created = User.objects.get_or_create(username='boss')
    if created:
        user.set_password('Mm02022006')
        user.is_staff = True
        user.is_superuser = True
        user.save()
        print(f"✅ Created user 'boss'")
    else:
        print(f"ℹ️ User 'boss' already exists")

    # 2. Ensure a Category exists
    category, created = Category.objects.get_or_create(name='Test Category')
    print(f"✅ Ensured Category exists")

    # 3. Ensure Products exist (ID 1 and 2)
    product1, created = Product.objects.get_or_create(id=1, defaults={
        'sku': 'P001',
        'name': 'Test Product 1',
        'category': category,
        'cost': Decimal('100.00'),
        'price': Decimal('150.00')
    })
    product2, created = Product.objects.get_or_create(id=2, defaults={
        'sku': 'P002',
        'name': 'Test Product 2',
        'category': category,
        'cost': Decimal('200.00'),
        'price': Decimal('250.00')
    })
    print(f"✅ Ensured Product IDs 1 and 2 exist")

    # 4. Ensure Location exists (ID 1)
    location, created = Location.objects.get_or_create(id=1, defaults={
        'name': 'Main Warehouse',
        'code': 'WH001',
        'type': 'raw'
    })
    print(f"✅ Ensured Location ID 1 exists")

    # 5. Ensure a Branch exists (ID 1) linked to Location
    branch, created = Branch.objects.get_or_create(id=1, defaults={
        'name': 'Main Branch', 
        'code': 'MAIN',
        'location': location
    })
    if not created and branch.location != location:
        branch.location = location
        branch.save()
    print(f"✅ Ensured Branch ID 1 exists")

    # 6. Ensure Partner/Customer exists (ID 1)
    partner_cust, created = Partner.objects.get_or_create(id=1, defaults={
        'name': 'Test Customer',
        'partner_type': 'customer',
        'phone': '123456789'
    })
    # If customer profile wasn't created by signal, create it
    if not hasattr(partner_cust, 'customer_profile'):
        customer, created = Customer.objects.get_or_create(id=1, defaults={
            'name': partner_cust.name,
            'phone': partner_cust.phone,
            'partner': partner_cust
        })
    else:
        customer = partner_cust.customer_profile
        if customer.id != 1:
            print(f"⚠️ Warning: Existing customer has ID {customer.id} instead of 1")
    print(f"✅ Ensured Customer exists")

    # 7. Ensure Partner/Supplier exists (ID 2)
    partner_supp, created = Partner.objects.get_or_create(id=2, defaults={
        'name': 'Test Supplier',
        'partner_type': 'supplier',
        'phone': '987654321'
    })
    if not hasattr(partner_supp, 'supplier_profile'):
        supplier, created = Supplier.objects.get_or_create(id=1, defaults={
            'name': partner_supp.name,
            'phone': partner_supp.phone,
            'partner': partner_supp
        })
    else:
        supplier = partner_supp.supplier_profile
        if supplier.id != 1:
            print(f"⚠️ Warning: Existing supplier has ID {supplier.id} instead of 1")
    print(f"✅ Ensured Supplier exists")

    print("✨ Seeding complete!")

if __name__ == "__main__":
    seed_data()
