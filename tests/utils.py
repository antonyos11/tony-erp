"""
Test utility functions and helpers for Tony ERP test suite.

This module provides common helper functions, assertion utilities,
and mock data generators used across multiple test files.
"""

from decimal import Decimal
from datetime import date, datetime, timedelta
from typing import Dict, List, Any, Optional
from django.contrib.auth import get_user_model
from django.test import Client
from django.db import transaction

User = get_user_model()


# ============================================================================
# Assertion Helpers
# ============================================================================

def assert_decimal_equal(actual: Decimal, expected: Decimal, precision: int = 2, msg: Optional[str] = None):
    """
    Assert that two Decimal values are equal within a given precision.
    
    Args:
        actual: The actual Decimal value
        expected: The expected Decimal value
        precision: Number of decimal places to compare (default: 2)
        msg: Optional custom error message
    
    Raises:
        AssertionError: If values are not equal within precision
    """
    factor = Decimal(10) ** precision
    actual_rounded = (actual * factor).quantize(Decimal('1'))
    expected_rounded = (expected * factor).quantize(Decimal('1'))
    
    default_msg = (
        f"Decimal values not equal: {actual} != {expected} "
        f"(rounded to {precision} places)"
    )
    assert actual_rounded == expected_rounded, msg or default_msg


def assert_journal_entry_balanced(journal_entry):
    """
    Assert that a journal entry is balanced (debits == credits).
    
    Args:
        journal_entry: JournalEntry instance
    
    Raises:
        AssertionError: If entry is not balanced
    """
    total_debit = sum(
        (item.amount for item in journal_entry.items.filter(type='debit')),
        Decimal('0')
    )
    total_credit = sum(
        (item.amount for item in journal_entry.items.filter(type='credit')),
        Decimal('0')
    )
    
    assert_decimal_equal(
        total_debit, 
        total_credit,
        msg=f"Journal entry not balanced: Debit={total_debit}, Credit={total_credit}"
    )


def assert_stock_quantity(product, location, expected_quantity):
    """
    Assert that stock quantity for a product at a location equals expected value.
    
    Args:
        product: Product instance
        location: Location instance
        expected_quantity: Expected stock quantity
    
    Raises:
        AssertionError: If stock quantity doesn't match
    """
    from inventory.models import Stock
    
    stock = Stock.objects.filter(product=product, location=location).first()
    actual_quantity = stock.quantity if stock else 0
    
    assert actual_quantity == expected_quantity, (
        f"Stock quantity mismatch for {product.sku} at {location.name}: "
        f"Expected {expected_quantity}, got {actual_quantity}"
    )


def assert_account_balance(account, expected_balance: Decimal):
    """
    Assert that an account's balance equals the expected value.
    
    Args:
        account: Account instance
        expected_balance: Expected account balance
    
    Raises:
        AssertionError: If balance doesn't match
    """
    actual_balance = account.balance
    assert_decimal_equal(
        actual_balance,
        expected_balance,
        msg=f"Account {account.code} balance mismatch: "
            f"Expected {expected_balance}, got {actual_balance}"
    )


# ============================================================================
# Data Generation Helpers
# ============================================================================

def generate_invoice_data(num_items: int = 3, customer=None) -> Dict[str, Any]:
    """
    Generate invoice data suitable for form submission or API calls.
    
    Args:
        num_items: Number of invoice items to include
        customer: Customer instance (creates one if None)
    
    Returns:
        Dict with invoice data
    """
    from tests.factories import CustomerFactory, ProductFactory, LocationFactory
    from tests.factories import StockFactory
    
    if customer is None:
        customer = CustomerFactory()
    
    location = LocationFactory()
    items = []
    
    for i in range(num_items):
        product = ProductFactory()
        StockFactory(product=product, location=location, quantity=1000)
        
        items.append({
            'product_id': product.id,
            'location_id': location.id,
            'quantity': 10,
            'price': float(product.price),
        })
    
    return {
        'customer_id': customer.id,
        'date': date.today().isoformat(),
        'due_date': (date.today() + timedelta(days=30)).isoformat(),
        'discount': 0.00,
        'is_tax_inclusive': True,
        'items': items,
    }


def generate_journal_entry_data(balanced: bool = True) -> Dict[str, Any]:
    """
    Generate journal entry data.
    
    Args:
        balanced: If True, creates balanced entry (debits == credits)
    
    Returns:
        Dict with journal entry data
    """
    from tests.factories import AccountFactory
    
    debit_account = AccountFactory(account_type='asset')
    credit_account = AccountFactory(account_type='revenue')
    amount = Decimal('1000.00')
    
    data = {
        'date': date.today().isoformat(),
        'entry_type': 'manual',
        'description': 'Test journal entry',
        'items': [
            {
                'account_id': debit_account.id,
                'type': 'debit',
                'amount': float(amount),
                'description': 'Debit entry',
            },
            {
                'account_id': credit_account.id,
                'type': 'credit',
                'amount': float(amount if balanced else amount * Decimal('0.5')),
                'description': 'Credit entry',
            },
        ],
    }
    
    return data


# ============================================================================
# Test Data Cleanup
# ============================================================================

def cleanup_test_files(directory: str = 'test_files'):
    """
    Clean up test files created during testing.
    
    Args:
        directory: Directory to clean up
    """
    import os
    import shutil
    
    if os.path.exists(directory):
        shutil.rmtree(directory)


# ============================================================================
# Database Transaction Helpers
# ============================================================================

@transaction.atomic
def create_invoice_with_items(customer, products_data: List[Dict], location):
    """
    Create an invoice with items in a single transaction.
    
    Args:
        customer: Customer instance
        products_data: List of dicts with 'product', 'quantity', 'price'
        location: Location instance
    
    Returns:
        Invoice instance
    """
    from sales.models import Invoice, InvoiceItem
    
    invoice = Invoice.objects.create(
        customer=customer,
        date=date.today(),
        due_date=date.today() + timedelta(days=30),
    )
    
    for data in products_data:
        InvoiceItem.objects.create(
            invoice=invoice,
            product=data['product'],
            location=location,
            quantity=data['quantity'],
            price=data.get('price', data['product'].price),
        )
    
    return invoice


# ============================================================================
# Mock Data Generators
# ============================================================================

def generate_random_sku() -> str:
    """Generate a random SKU."""
    import random
    import string
    
    prefix = ''.join(random.choices(string.ascii_uppercase, k=3))
    number = ''.join(random.choices(string.digits, k=6))
    return f"{prefix}{number}"


def generate_random_barcode() -> str:
    """Generate a random barcode (EAN-13 format)."""
    import random
    return ''.join(random.choices('0123456789', k=13))


def generate_random_phone() -> str:
    """Generate a random Saudi phone number."""
    import random
    prefix = random.choice(['050', '053', '054', '055', '056', '058', '059'])
    number = ''.join(random.choices('0123456789', k=7))
    return f"{prefix}{number}"


# ============================================================================
# Time Manipulation Helpers
# ============================================================================

class FreezeTime:
    """
    Context manager for freezing time in tests.
    
    Usage:
        with FreezeTime('2026-01-22'):
            # Time is frozen
            assert date.today() == date(2026, 1, 22)
    """
    
    def __init__(self, frozen_time):
        from freezegun import freeze_time
        self.frozen_time = frozen_time
        self._freezer = freeze_time(frozen_time)
    
    def __enter__(self):
        return self._freezer.__enter__()
    
    def __exit__(self, *args):
        return self._freezer.__exit__(*args)


# ============================================================================
# API Testing Helpers
# ============================================================================

def get_jwt_token(username: str, password: str = 'testpass123') -> str:
    """
    Get JWT token for a user.
    
    Args:
        username: Username
        password: Password (default: testpass123)
    
    Returns:
        JWT access token
    """
    from rest_framework_simplejwt.tokens import RefreshToken
    
    user = User.objects.get(username=username)
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token)


def api_post_json(client, url: str, data: Dict, token: Optional[str] = None):
    """
    POST JSON data to API endpoint.
    
    Args:
        client: Test client
        url: URL path
        data: Data to post
        token: JWT token (optional)
    
    Returns:
        Response object
    """
    headers = {'HTTP_AUTHORIZATION': f'Bearer {token}'} if token else {}
    return client.post(
        url,
        data=data,
        content_type='application/json',
        **headers
    )


# ============================================================================
# Performance Testing Helpers
# ============================================================================

def measure_query_count(func, *args, **kwargs):
    """
    Measure number of database queries executed by a function.
    
    Args:
        func: Function to measure
        *args: Function arguments
        **kwargs: Function keyword arguments
    
    Returns:
        Tuple of (result, query_count)
    """
    from django.test.utils import override_settings
    from django.db import connection
    from django.test import TestCase
    
    with override_settings(DEBUG=True):
        connection.queries_log.clear()
        result = func(*args, **kwargs)
        query_count = len(connection.queries)
    
    return result, query_count


def assert_max_queries(max_queries: int):
    """
    Context manager to assert maximum number of queries.
    
    Usage:
        with assert_max_queries(5):
            # Code that should execute <= 5 queries
            MyModel.objects.all()
    """
    from django.test import TestCase
    return TestCase().assertNumQueries(max_queries)


# ============================================================================
# Concurrent Testing Helpers
# ============================================================================

def run_concurrent(func, num_threads: int = 10, *args, **kwargs):
    """
    Run a function concurrently in multiple threads.
    
    Useful for testing race conditions and thread safety.
    
    Args:
        func: Function to run
        num_threads: Number of concurrent threads
        *args: Function arguments
        **kwargs: Function keyword arguments
    
    Returns:
        List of results from each thread
    """
    import threading
    
    results = []
    errors = []
    
    def wrapper():
        try:
            result = func(*args, **kwargs)
            results.append(result)
        except Exception as e:
            errors.append(e)
    
    threads = []
    for _ in range(num_threads):
        thread = threading.Thread(target=wrapper)
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()
    
    return results, errors


# ============================================================================
# Cache Testing Helpers
# ============================================================================

def clear_all_caches():
    """Clear all Django caches."""
    from django.core.cache import caches
    
    for cache in caches.all():
        cache.clear()


def get_cache_key(key_pattern: str):
    """
    Get actual cache key from pattern.
    
    Args:
        key_pattern: Cache key pattern
    
    Returns:
        Actual cache key
    """
    from django.core.cache import cache
    return cache.make_key(key_pattern)


# ============================================================================
# Email Testing Helpers
# ============================================================================

def get_last_email():
    """Get the last email sent during testing."""
    from django.core import mail
    
    if mail.outbox:
        return mail.outbox[-1]
    return None


def assert_email_sent(subject: Optional[str] = None, to: Optional[List[str]] = None):
    """
    Assert that an email was sent with optional subject/recipient checking.
    
    Args:
        subject: Expected email subject (optional)
        to: Expected recipients (optional)
    """
    from django.core import mail
    
    assert len(mail.outbox) > 0, "No emails were sent"
    
    last_email = mail.outbox[-1]
    
    if subject:
        assert last_email.subject == subject, (
            f"Email subject mismatch: Expected '{subject}', got '{last_email.subject}'"
        )
    
    if to:
        assert set(last_email.to) == set(to), (
            f"Email recipients mismatch: Expected {to}, got {last_email.to}"
        )
