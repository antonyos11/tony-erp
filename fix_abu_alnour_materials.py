import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from inventory.models import Product, SupplierProductPrice
from partners.models import Supplier

def fix_materials():
    try:
        supplier = Supplier.objects.filter(name__icontains='ابو النور').first()
        if not supplier:
            print("Supplier 'ابو النور' not found.")
            return

        print(f"Found supplier: {supplier.name}")

        # Find all supplier prices for this supplier where product is not null
        prices = SupplierProductPrice.objects.filter(supplier=supplier, product__isnull=False)
        
        count = 0
        for price in prices:
            product = price.product
            # Only process if it's a raw material
            if product and product.product_type == 'raw_material':
                print(f"Processing: {product.name}")
                
                # 1. Save name to material_name
                price.material_name = product.name
                
                # 2. Unlink product
                price.product = None
                price.save()
                
                # 3. Delete the product
                product_name = product.name
                product.delete()
                
                print(f"  -> Converted '{product_name}' to standalone price and deleted the raw material product.")
                count += 1
                
        print(f"Successfully processed {count} materials.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    fix_materials()
