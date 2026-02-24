
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.db.models import Q
from inventory.models import Product
from partners.models import Customer
from sales.models import Invoice

@login_required
def global_search(request):
    query = request.GET.get('q', '').strip()
    results = []

    if not query:
        return JsonResponse({'results': []})

    # 1. Pages (Navigation)
    pages_config = [
        {'name': 'Dashboard', 'view': 'core:dashboard', 'category': 'Pages'},
        {'name': 'POS', 'view': 'pos:dashboard', 'category': 'Pages'},
        {'name': 'Inventory', 'view': 'inventory:product_list', 'category': 'Pages'},
        {'name': 'Accounting', 'view': 'accounting:dashboard', 'category': 'Pages'},
        {'name': 'Sales', 'view': 'sales:invoice_list', 'category': 'Pages'},
        {'name': 'Purchases', 'view': 'purchases:bill_list', 'category': 'Pages'},
        {'name': 'Smart Pricing', 'view': 'smart_pricing:dashboard', 'category': 'Pages'},
    ]
    
    for p_cfg in pages_config:
        if query.lower() in p_cfg['name'].lower():
            try:
                url = reverse(p_cfg['view'])
                results.append({'name': p_cfg['name'], 'url': url, 'category': p_cfg['category']})
            except Exception:
                pass # Skip invalid urls

    # 2. Products
    products = Product.objects.filter(
        Q(name__icontains=query) | Q(sku__icontains=query)
    )[:5]
    for p in products:
        results.append({
            'name': p.name,
            'url': f"/inventory/products/{p.id}/", # Assuming standard URL pattern, ideally check urls.py
            'category': 'Products',
            'meta': f"SKU: {p.sku}"
        })

    # 3. Customers
    customers = Customer.objects.filter(
        Q(name__icontains=query) | Q(phone__icontains=query)
    )[:5]
    for c in customers:
        results.append({
            'name': c.name,
            'url': f"/partners/customers/{c.id}/", # Assuming standard URL pattern
            'category': 'Customers',
            'meta': c.phone
        })

    # 4. Invoices
    # Search by ID usually
    if query.isdigit():
        invoices = Invoice.objects.filter(id=query)[:5]
        for inv in invoices:
            results.append({
                'name': f"Invoice #{inv.id}",
                'url': f"/sales/invoices/{inv.id}/", # Assuming standard URL pattern
                'category': 'Invoices',
                'meta': f"{inv.customer.name} - {inv.total}"
            })

    return JsonResponse({'results': results})
