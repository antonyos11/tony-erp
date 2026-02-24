"""
Unit tests for Sales models.

Tests cover:
- Invoice model (number generation, totals, validation)
- InvoiceItem model (stock deduction signals)
- InvoicePayment model
- Tax calculations
- Discount logic

Priority: P0 - Critical (Revenue Tracking & Stock Management)
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.conf import settings

from sales.models import Invoice, InvoiceItem, InvoicePayment
from tests.factories import (
    InvoiceFactory, InvoiceItemFactory, InvoicePaymentFactory,
    CustomerFactory, ProductFactory, LocationFactory, StockFactory
)
from tests.utils import assert_decimal_equal, assert_stock_quantity


# ============================================================================
# Invoice Model Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.p0
class TestInvoiceModel:
    """Tests for Invoice model."""
    
    def test_create_invoice(self, customer):
        """Test creating a basic invoice."""
        invoice = InvoiceFactory(
            customer=customer,
            date=date.today(),
            discount=Decimal('0.00')
        )
        
        assert invoice.customer == customer
        assert invoice.date == date.today()
        assert invoice.discount == Decimal('0.00')
        assert invoice.is_posted is False
    
    def test_invoice_number_auto_generation(self):
        """Test that invoice numbers are auto-generated."""
        invoice1 = InvoiceFactory()
        invoice2 = InvoiceFactory()
        
        assert invoice1.number is not None
        assert invoice2.number is not None
        assert invoice1.number != invoice2.number
    
    def test_invoice_number_format(self):
        """Test invoice number format (INV-YYYYMM-NNNNNN)."""
        invoice = InvoiceFactory()
        
        assert invoice.number.startswith('INV-')
        year_month = date.today().strftime('%Y%m')
        assert year_month in invoice.number
    
    def test_invoice_number_uniqueness(self):
        """Test that invoice numbers are unique."""
        invoice1 = InvoiceFactory()
        
        # Try to create invoice with same number
        with pytest.raises(IntegrityError):
            Invoice.objects.create(
                number=invoice1.number,
                customer=CustomerFactory(),
                date=date.today()
            )
    
    @pytest.mark.slow
    def test_concurrent_invoice_number_generation(self):
        """Test invoice number generation under concurrent load."""
        from tests.utils import run_concurrent
        
        def create_invoice():
            return InvoiceFactory()
        
        # Create 20 invoices concurrently
        invoices, errors = run_concurrent(create_invoice, num_threads=20)
        
        # All should succeed
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(invoices) == 20
        
        # All numbers should be unique
        numbers = [inv.number for inv in invoices]
        assert len(numbers) == len(set(numbers)), "Duplicate invoice numbers generated!"
    
    def test_invoice_total_calculation(self, customer, product, location):
        """Test invoice total calculation from items."""
        # Create stock
        StockFactory(product=product, location=location, quantity=1000)
        
        invoice = InvoiceFactory(customer=customer, discount=Decimal('0.00'))
        
        # Add items
        InvoiceItemFactory(
            invoice=invoice,
            product=product,
            location=location,
            quantity=10,
            price=Decimal('100.00')
        )
        InvoiceItemFactory(
            invoice=invoice,
            product=ProductFactory(),
            location=location,
            quantity=5,
            price=Decimal('200.00')
        )
        
        # Update cached total (normally done by signal)
        invoice.refresh_from_db()
        
        # Total = (10 * 100) + (5 * 200) = 1000 + 1000 = 2000
        expected_total = Decimal('2000.00')
        assert_decimal_equal(invoice.total, expected_total)
    
    def test_invoice_total_with_discount(self, customer, product, location):
        """Test invoice total with discount applied."""
        StockFactory(product=product, location=location, quantity=1000)
        
        invoice = InvoiceFactory(customer=customer, discount=Decimal('100.00'))
        
        InvoiceItemFactory(
            invoice=invoice,
            product=product,
            location=location,
            quantity=10,
            price=Decimal('100.00')
        )
        
        invoice.refresh_from_db()
        
        # Total = (10 * 100) - 100 discount = 900
        expected_total = Decimal('900.00')
        assert_decimal_equal(invoice.total, expected_total)
    
    def test_invoice_remaining_calculation(self, customer, product, location):
        """Test invoice remaining amount calculation."""
        StockFactory(product=product, location=location, quantity=1000)
        
        invoice = InvoiceFactory(
            customer=customer,
            discount=Decimal('0.00'),
            paid=Decimal('0.00')
        )
        
        InvoiceItemFactory(
            invoice=invoice,
            product=product,
            location=location,
            quantity=10,
            price=Decimal('100.00')
        )
        
        invoice.refresh_from_db()
        
        # Remaining = Total - Paid = 1000 - 0 = 1000
        assert_decimal_equal(invoice.remaining, Decimal('1000.00'))
        
        # Record payment
        invoice.paid = Decimal('600.00')
        invoice.save()
        
        # Remaining = 1000 - 600 = 400
        assert_decimal_equal(invoice.remaining, Decimal('400.00'))
    
    def test_invoice_str_representation(self, customer):
        """Test string representation of invoice."""
        invoice = InvoiceFactory(customer=customer)
        
        assert invoice.number in str(invoice)
        assert customer.name in str(invoice)


# ============================================================================
# InvoiceItem Model Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.p0
class TestInvoiceItemModel:
    """Tests for InvoiceItem model."""
    
    def test_create_invoice_item(self, product, location):
        """Test creating an invoice item."""
        # Create stock
        StockFactory(product=product, location=location, quantity=1000)
        
        invoice = InvoiceFactory()
        item = InvoiceItemFactory(
            invoice=invoice,
            product=product,
            location=location,
            quantity=10,
            price=Decimal('100.00')
        )
        
        assert item.invoice == invoice
        assert item.product == product
        assert item.location == location
        assert item.quantity == 10
        assert_decimal_equal(item.price, Decimal('100.00'))
    
    def test_invoice_item_total_calculation(self, product, location):
        """Test item total calculation."""
        StockFactory(product=product, location=location, quantity=1000)
        
        item = InvoiceItemFactory(
            product=product,
            location=location,
            quantity=15,
            price=Decimal('50.00')
        )
        
        # Total = quantity * price = 15 * 50 = 750
        expected_total = Decimal('750.00')
        assert_decimal_equal(item.total, expected_total)
    
    def test_invoice_item_deducts_stock(self, product, location):
        """Test that creating invoice item deducts stock."""
        # Create initial stock
        initial_stock = 100
        StockFactory(product=product, location=location, quantity=initial_stock)
        
        # Create invoice item
        invoice = InvoiceFactory()
        quantity_sold = 10
        InvoiceItemFactory(
            invoice=invoice,
            product=product,
            location=location,
            quantity=quantity_sold
        )
        
        # Stock should be deducted
        expected_stock = initial_stock - quantity_sold
        assert_stock_quantity(product, location, expected_stock)
    
    def test_invoice_item_restores_stock_on_deletion(self, product, location):
        """Test that deleting invoice item restores stock."""
        # Create initial stock
        initial_stock = 100
        StockFactory(product=product, location=location, quantity=initial_stock)
        
        # Create invoice item
        quantity_sold = 10
        item = InvoiceItemFactory(
            invoice=InvoiceFactory(),
            product=product,
            location=location,
            quantity=quantity_sold
        )
        
        # Stock should be deducted
        assert_stock_quantity(product, location, initial_stock - quantity_sold)
        
        # Delete item
        item.delete()
        
        # Stock should be restored
        assert_stock_quantity(product, location, initial_stock)
    
    @pytest.mark.skipif(
        not getattr(settings, 'ALLOW_NEGATIVE_INVENTORY', False),
        reason="Negative inventory not allowed in settings"
    )
    def test_invoice_item_allows_negative_stock_if_enabled(self, product, location):
        """Test that negative stock is allowed if ALLOW_NEGATIVE_INVENTORY=True."""
        # Create minimal stock
        StockFactory(product=product, location=location, quantity=5)
        
        # Try to sell more than available (should succeed if allowed)
        InvoiceItemFactory(
            invoice=InvoiceFactory(),
            product=product,
            location=location,
            quantity=10  # More than available
        )
        
        # Should result in negative stock
        assert_stock_quantity(product, location, -5)
    
    @pytest.mark.skipif(
        getattr(settings, 'ALLOW_NEGATIVE_INVENTORY', True),
        reason="Negative inventory is allowed in settings"
    )
    def test_invoice_item_prevents_negative_stock_if_disabled(self, product, location):
        """Test that stock is clamped to zero if ALLOW_NEGATIVE_INVENTORY=False.
        
        The system logs a warning but does not raise an exception;
        instead it clamps the stock quantity to max(0, available - sold).
        """
        # Create minimal stock
        StockFactory(product=product, location=location, quantity=5)
        
        # Sell more than available — stock should be clamped to 0
        InvoiceItemFactory(
            invoice=InvoiceFactory(),
            product=product,
            location=location,
            quantity=10  # More than available
        )
        
        from inventory.models import Stock
        stock = Stock.objects.get(product=product, location=location)
        assert stock.quantity == 0, f"Stock should be clamped to 0, got {stock.quantity}"


# ============================================================================
# InvoicePayment Model Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.p0
class TestInvoicePaymentModel:
    """Tests for InvoicePayment model."""
    
    def test_create_invoice_payment(self):
        """Test creating an invoice payment."""
        invoice = InvoiceFactory()
        payment = InvoicePaymentFactory(
            invoice=invoice,
            amount=Decimal('500.00'),
            payment_method='cash',
            date=date.today()
        )
        
        assert payment.invoice == invoice
        assert_decimal_equal(payment.amount, Decimal('500.00'))
        assert payment.payment_method == 'cash'
        assert payment.date == date.today()
    
    def test_invoice_payment_updates_paid_amount(self, customer, product, location):
        """Test that payment updates invoice paid amount."""
        StockFactory(product=product, location=location, quantity=1000)
        
        invoice = InvoiceFactory(customer=customer, paid=Decimal('0.00'))
        InvoiceItemFactory(
            invoice=invoice,
            product=product,
            location=location,
            quantity=10,
            price=Decimal('100.00')
        )
        
        # Create payment
        payment_amount = Decimal('600.00')
        InvoicePaymentFactory(
            invoice=invoice,
            amount=payment_amount
        )
        
        # Refresh invoice
        invoice.refresh_from_db()
        
        # Paid amount should be updated
        assert_decimal_equal(invoice.paid, payment_amount)


# ============================================================================
# Tax Calculation Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.p0
class TestInvoiceTaxCalculations:
    """Tests for invoice tax calculations."""
    
    def test_invoice_tax_calculation_inclusive(self, customer, product, location):
        """Test tax calculation when tax is inclusive."""
        StockFactory(product=product, location=location, quantity=1000)
        
        invoice = InvoiceFactory(
            customer=customer,
            is_tax_inclusive=True,
            discount=Decimal('0.00')
        )
        
        # Price includes 14% VAT (Company default_vat_rate = 14%)
        InvoiceItemFactory(
            invoice=invoice,
            product=product,
            location=location,
            quantity=10,
            price=Decimal('114.00')  # Includes 14% VAT
        )
        
        invoice.refresh_from_db()
        
        # Total with tax = 10 * 114 = 1140
        # Tax = 1140 - (1140 / 1.14) = 1140 - 1000 = 140
        expected_tax = Decimal('140.00')
        assert_decimal_equal(invoice.tax, expected_tax)
    
    def test_invoice_tax_calculation_exclusive(self, customer, product, location):
        """Test tax calculation when tax is exclusive."""
        StockFactory(product=product, location=location, quantity=1000)
        
        invoice = InvoiceFactory(
            customer=customer,
            is_tax_inclusive=False,
            discount=Decimal('0.00')
        )
        
        # Price excludes 14% VAT (Company default_vat_rate = 14%)
        InvoiceItemFactory(
            invoice=invoice,
            product=product,
            location=location,
            quantity=10,
            price=Decimal('100.00')  # Excludes VAT
        )
        
        invoice.refresh_from_db()
        
        # Subtotal = 10 * 100 = 1000
        # Tax = 1000 * 0.14 = 140
        expected_tax = Decimal('140.00')
        assert_decimal_equal(invoice.tax, expected_tax)


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

@pytest.mark.unit
@pytest.mark.p0
class TestInvoiceEdgeCases:
    """Tests for invoice edge cases and error handling."""
    
    def test_invoice_with_zero_items(self, customer):
        """Test invoice with no items."""
        invoice = InvoiceFactory(customer=customer)
        
        # Should have zero total
        assert_decimal_equal(invoice.total, Decimal('0.00'))
    
    def test_invoice_with_100_percent_discount(self, customer, product, location):
        """Test invoice with 100% discount."""
        StockFactory(product=product, location=location, quantity=1000)
        
        invoice = InvoiceFactory(customer=customer)
        InvoiceItemFactory(
            invoice=invoice,
            product=product,
            location=location,
            quantity=10,
            price=Decimal('100.00')
        )
        
        invoice.refresh_from_db()
        
        # Apply 100% discount
        invoice.discount = invoice.total
        invoice.save()
        
        # Total after discount should be 0
        assert_decimal_equal(invoice.total - invoice.discount, Decimal('0.00'))
    
    def test_invoice_due_date_defaults(self, customer):
        """Test that due_date defaults to 30 days after invoice date."""
        invoice_date = date(2026, 1, 15)
        invoice = InvoiceFactory(
            customer=customer,
            date=invoice_date
        )
        
        # Default due date should be 30 days later
        expected_due_date = invoice_date + timedelta(days=30)
        assert invoice.due_date == expected_due_date
