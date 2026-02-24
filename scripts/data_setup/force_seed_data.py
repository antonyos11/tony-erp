
import os
import django
from decimal import Decimal

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from django.contrib.auth.models import User
from partners.models import Customer, Supplier, Partner
from inventory.models import Product, Location, Category
from branches.models import Branch
from django.db import connection

def force_seed():
    print("🔥 Force seeding test data...")
    
    # 1. Clear tables (Order matters for FKs)
    with connection.cursor() as cursor:
        cursor.execute("TRUNCATE partners_customer, partners_supplier, partners_partner RESTART IDENTITY CASCADE;")
        cursor.execute("TRUNCATE branches_branch CASCADE;")
        cursor.execute("TRUNCATE inventory_stock, inventory_product, inventory_category, inventory_location RESTART IDENTITY CASCADE;")
    
    print("✅ Tables truncated and identities reset")

    # 2. Re-seed
    user, _ = User.objects.get_or_create(username='boss')
    user.set_password('Mm02022006')
    user.is_staff = True
    user.is_superuser = True
    user.save()

    category = Category.objects.create(id=1, name='Test Category')
    product1 = Product.objects.create(id=1, sku='P01', name='Test Product 1', category=category, cost=100, price=150)
    product2 = Product.objects.create(id=2, sku='P02', name='Test Product 2', category=category, cost=200, price=250)
    location = Location.objects.create(id=1, name='Main Warehouse', code='WH01', type='raw')
    branch = Branch.objects.create(id=1, name='Main Branch', code='MAIN', location=location)

    partner1 = Partner.objects.create(id=1, name='Test Customer', partner_type='customer', phone='123')
    # Signal creates customer, but let's check
    if not Customer.objects.filter(id=1).exists():
        # If signal didn't use ID 1, we might need to fix it
        Customer.objects.filter(partner=partner1).delete()
        Customer.objects.create(id=1, partner=partner1, name='Test Customer')

    partner2 = Partner.objects.create(id=2, name='Test Supplier', partner_type='supplier', phone='456')
    if not Supplier.objects.filter(id=1).exists():
        Supplier.objects.filter(partner=partner2).delete()
        Supplier.objects.create(id=1, partner=partner2, name='Test Supplier')

    print("✨ Force seeding complete! ID 1 should now be available for all.")

if __name__ == "__main__":
    force_seed()
