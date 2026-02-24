#!/usr/bin/env python
"""
Test script for purchases quotations functionality
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from purchases.models_advanced import SupplierQuotation, RFQ, RFQItem
from partners.models import Partner
from inventory.models import Product
from decimal import Decimal

def test_quotation_list_view():
    """Test the quotation list view"""
    print("\n=== Testing Quotation List View ===")

    # Create a test user with admin privileges
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={'email': 'test@example.com', 'is_staff': True, 'is_superuser': True}
    )
    if created:
        user.set_password('testpass123')
        user.save()
    
    # Create a test client
    client = Client()
    client.login(username='testuser', password='testpass123')
    
    # Test the quotation list view
    response = client.get('/purchases/quotations/')
    
    print(f"Status Code: {response.status_code}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    # Check if the template was used
    assert 'purchases/quotation/list.html' in [t.name for t in response.templates]
    
    # Check context variables
    assert 'quotations' in response.context
    assert 'suppliers' in response.context
    assert 'rfqs' in response.context
    assert 'status_filter' in response.context
    assert 'supplier_filter' in response.context
    assert 'search' in response.context
    
    print("✓ Quotation list view works correctly")
    print(f"  - Status: {response.status_code}")
    print(f"  - Template: purchases/quotation/list.html")
    print(f"  - Context variables: quotations, suppliers, rfqs, filters")

def test_quotation_detail_view():
    """Test the quotation detail view"""
    print("\n=== Testing Quotation Detail View ===")
    
    # Get or create test data
    user, _ = User.objects.get_or_create(username='testuser')
    
    # Create a supplier
    supplier, _ = Partner.objects.get_or_create(
        name='Test Supplier',
        defaults={'partner_type': 'supplier'}
    )
    
    # Create an RFQ
    rfq, _ = RFQ.objects.get_or_create(
        number='RFQ-001',
        defaults={
            'title': 'Test RFQ',
            'deadline': '2026-12-31',
            'created_by': user
        }
    )
    
    # Create a quotation
    quotation, _ = SupplierQuotation.objects.get_or_create(
        number='QT-001',
        defaults={
            'rfq': rfq,
            'supplier': supplier,
            'valid_until': '2026-12-31'
        }
    )
    
    # Test the detail view
    client = Client()
    client.login(username='testuser', password='testpass123')
    
    response = client.get(f'/purchases/quotations/{quotation.pk}/')
    
    print(f"Status Code: {response.status_code}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    # Check context
    assert 'quotation' in response.context
    assert response.context['quotation'].pk == quotation.pk
    
    print("✓ Quotation detail view works correctly")
    print(f"  - Status: {response.status_code}")
    print(f"  - Quotation: {quotation.number}")

def main():
    """Run all tests"""
    print("=" * 50)
    print("PURCHASES QUOTATIONS TEST SUITE")
    print("=" * 50)
    
    try:
        test_quotation_list_view()
        test_quotation_detail_view()
        
        print("\n" + "=" * 50)
        print("✓ ALL TESTS PASSED!")
        print("=" * 50)
        return 0
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    exit(main())

