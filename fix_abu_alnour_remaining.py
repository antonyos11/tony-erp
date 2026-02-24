import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from inventory.models import Product, SupplierProductPrice
from partners.models import Supplier

def fix_remaining():
    try:
        supplier = Supplier.objects.filter(name__icontains='ابو النور').first()
        if not supplier:
            print("Supplier 'ابو النور' not found.")
            return

        products = Product.objects.filter(preferred_supplier=supplier)
        for p in products:
            print(f"Processing: {p.name}")
            
            # Create SupplierProductPrice
            SupplierProductPrice.objects.create(
                supplier=supplier,
                material_name=p.name,
                cost=p.cost,
                purchase_unit=p.purchase_uom
            )
            
            # Delete Product
            p.delete()
            print(f"  -> Converted '{p.name}' to standalone price and deleted the raw material product.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    fix_remaining()
