"""
Pytest configuration and shared fixtures for Tony ERP test suite.

This module provides reusable fixtures that can be used across all tests,
reducing code duplication and ensuring consistent test setup.
"""

import os
import django
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client
from faker import Faker
from rest_framework.test import APIClient

# Configure Django settings for tests
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

User = get_user_model()
fake = Faker(['ar_SA', 'en_US'])  # Arabic and English locales


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """
    Grant database access to all tests automatically.
    This eliminates the need to mark every test with @pytest.mark.django_db
    """
    pass


# ============================================================================
# User and Authentication Fixtures
# ============================================================================

@pytest.fixture
def user():
    """Create a basic test user."""
    from tests.factories import UserFactory
    return UserFactory()


@pytest.fixture
def admin_user():
    """Create an admin/superuser for tests requiring elevated permissions."""
    from tests.factories import UserFactory
    return UserFactory(
        is_staff=True,
        is_superuser=True,
        username='admin',
        email='admin@test.com'
    )


@pytest.fixture
def accountant_user():
    """Create a user with accountant role."""
    from tests.factories import UserFactory, UserProfileFactory
    user = UserFactory(username='accountant')
    UserProfileFactory(
        user=user,
        arabic_name='محاسب اختبار',
        employee_id='ACC001'
    )
    return user


@pytest.fixture
def warehouse_user():
    """Create a user with warehouse manager role."""
    from tests.factories import UserFactory, UserProfileFactory
    user = UserFactory(username='warehouse_manager')
    UserProfileFactory(
        user=user,
        arabic_name='مدير مخزن',
        employee_id='WH001'
    )
    return user


@pytest.fixture
def authenticated_client(user):
    """
    Provide a Django test client with authenticated user.
    Use for testing views that require authentication.
    """
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def authenticated_api_client(user):
    """
    Provide a DRF APIClient with authenticated user.
    Use for testing REST API endpoints.
    """
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def admin_client(admin_user):
    """Django client authenticated as admin."""
    client = Client()
    client.force_login(admin_user)
    return client


@pytest.fixture
def admin_api_client(admin_user):
    """API client authenticated as admin."""
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


# ============================================================================
# Accounting Fixtures
# ============================================================================

@pytest.fixture
def fiscal_year(admin_user):
    """Create a fiscal year for 2026."""
    from accounting.models import FiscalYear
    return FiscalYear.objects.create(
        name='2026',
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_active=True,
        created_by=admin_user
    )


@pytest.fixture
def cost_center(admin_user):
    """Create a basic cost center."""
    from tests.factories import CostCenterFactory
    return CostCenterFactory(
        code='CC001',
        name='Main Cost Center',
        manager=admin_user
    )


@pytest.fixture
def sample_chart_of_accounts(admin_user):
    """
    Create a minimal chart of accounts for testing.
    
    Returns dict with commonly used accounts:
    - assets: Main asset account
    - cash: Cash account
    - receivables: Accounts receivable
    - inventory: Inventory account
    - liabilities: Main liability account
    - payables: Accounts payable
    - equity: Equity account
    - revenue: Sales revenue
    - expenses: Main expense account
    - cogs: Cost of goods sold
    """
    from tests.factories import AccountFactory
    
    # Create parent accounts
    assets = AccountFactory(
        code='1000',
        name='Assets',
        account_type='asset',
        is_group=True,
        parent=None
    )
    
    liabilities = AccountFactory(
        code='2000',
        name='Liabilities',
        account_type='liability',
        is_group=True,
        parent=None
    )
    
    equity = AccountFactory(
        code='3000',
        name='Equity',
        account_type='equity',
        is_group=True,
        parent=None
    )
    
    revenue = AccountFactory(
        code='4000',
        name='Revenue',
        account_type='revenue',
        is_group=True,
        parent=None
    )
    
    expenses = AccountFactory(
        code='5000',
        name='Expenses',
        account_type='expense',
        is_group=True,
        parent=None
    )
    
    # Create child accounts
    cash = AccountFactory(
        code='1001',
        name='Cash',
        account_type='asset',
        parent=assets,
        is_group=False,
        can_post=True
    )
    
    receivables = AccountFactory(
        code='1002',
        name='Accounts Receivable',
        account_type='asset',
        parent=assets,
        can_post=True
    )
    
    inventory = AccountFactory(
        code='1003',
        name='Inventory',
        account_type='asset',
        parent=assets,
        can_post=True
    )
    
    payables = AccountFactory(
        code='2001',
        name='Accounts Payable',
        account_type='liability',
        parent=liabilities,
        can_post=True
    )
    
    sales_revenue = AccountFactory(
        code='4001',
        name='Sales Revenue',
        account_type='revenue',
        parent=revenue,
        can_post=True
    )
    
    cogs = AccountFactory(
        code='5001',
        name='Cost of Goods Sold',
        account_type='expense',
        parent=expenses,
        can_post=True
    )
    
    return {
        'assets': assets,
        'cash': cash,
        'receivables': receivables,
        'inventory': inventory,
        'liabilities': liabilities,
        'payables': payables,
        'equity': equity,
        'revenue': sales_revenue,
        'expenses': expenses,
        'cogs': cogs,
    }


# ============================================================================
# Inventory Fixtures
# ============================================================================

@pytest.fixture
def category():
    """Create a product category."""
    from tests.factories import CategoryFactory
    return CategoryFactory(name='Test Category')


@pytest.fixture
def location():
    """Create a warehouse location."""
    from tests.factories import LocationFactory
    return LocationFactory(name='Main Warehouse')


@pytest.fixture
def product(category):
    """Create a basic product."""
    from tests.factories import ProductFactory
    return ProductFactory(
        sku='PROD001',
        name='Test Product',
        category=category,
        price=Decimal('100.00'),
        cost=Decimal('60.00')
    )


@pytest.fixture
def raw_material(category):
    """Create a raw material product."""
    from tests.factories import ProductFactory
    return ProductFactory(
        sku='RAW001',
        name='Raw Material',
        category=category,
        product_type='raw_material',
        price=Decimal('50.00'),
        cost=Decimal('30.00')
    )


@pytest.fixture
def base_products(category):
    """
    Create a set of base products for testing.
    Returns list of 5 products with varying prices.
    """
    from tests.factories import ProductFactory
    
    products = []
    for i in range(1, 6):
        product = ProductFactory(
            sku=f'PROD{i:03d}',
            name=f'Product {i}',
            category=category,
            price=Decimal(f'{i * 100}.00'),
            cost=Decimal(f'{i * 60}.00')
        )
        products.append(product)
    
    return products


@pytest.fixture
def stock_item(product, location):
    """Create stock for a product at a location."""
    from tests.factories import StockFactory
    return StockFactory(
        product=product,
        location=location,
        quantity=100
    )


# ============================================================================
# Sales Fixtures
# ============================================================================

@pytest.fixture
def customer():
    """Create a customer."""
    from tests.factories import CustomerFactory
    return CustomerFactory(
        name='Test Customer',
        phone='0501234567'
    )


@pytest.fixture
def supplier():
    """Create a supplier."""
    from tests.factories import SupplierFactory
    return SupplierFactory(
        name='Test Supplier',
        phone='0507654321'
    )


# ============================================================================
# Production Fixtures
# ============================================================================

@pytest.fixture
def work_center():
    """Create a production work center."""
    from tests.factories import ProductionWorkCenterFactory
    return ProductionWorkCenterFactory(
        code='WC001',
        name='Assembly Line 1',
        hourly_rate=Decimal('50.00')
    )


@pytest.fixture
def bom(product, raw_material):
    """Create a Bill of Materials."""
    from tests.factories import BOMFactory, BOMItemFactory
    
    bom = BOMFactory(
        product=product,
        version='1.0',
        base_quantity=1
    )
    
    # Add raw material to BOM
    BOMItemFactory(
        bom=bom,
        material=raw_material,
        item_type='material',
        quantity=2,
        unit_cost=raw_material.cost
    )
    
    return bom


# ============================================================================
# Time and Date Fixtures
# ============================================================================

@pytest.fixture
def freeze_time():
    """
    Fixture to freeze time for testing date/time dependent functionality.
    
    Usage:
        def test_something(freeze_time):
            with freeze_time('2026-01-22'):
                # Time is frozen at 2026-01-22
                pass
    """
    from freezegun import freeze_time as _freeze_time
    return _freeze_time


@pytest.fixture
def today():
    """Get today's date."""
    return date.today()


@pytest.fixture
def yesterday():
    """Get yesterday's date."""
    return date.today() - timedelta(days=1)


@pytest.fixture
def tomorrow():
    """Get tomorrow's date."""
    return date.today() + timedelta(days=1)


# ============================================================================
# Utility Fixtures
# ============================================================================

@pytest.fixture
def faker_instance():
    """Provide Faker instance for generating test data."""
    return fake


@pytest.fixture
def settings_override():
    """
    Fixture to temporarily override Django settings.
    
    Usage:
        def test_something(settings_override):
            with settings_override(ALLOW_NEGATIVE_INVENTORY=False):
                # ALLOW_NEGATIVE_INVENTORY is False here
                pass
    """
    from django.test import override_settings
    return override_settings


# ============================================================================
# Cleanup Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def clear_cache():
    """Clear Django cache before each test."""
    from django.core.cache import cache
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def reset_sequences():
    """Reset database sequences after each test."""
    yield
    # Sequences will be reset automatically by Django test framework
    pass
