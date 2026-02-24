"""
Unit tests — sales.services.stock_service
==========================================

Phase 1 / Step 2: Verifies that the stock service functions (previously
embedded inside Django signals) behave correctly in isolation.

Notes on test setup
--------------------
InvoiceItemFactory.save() fires the post_save signal which already calls
deduct_stock_for_invoice_item().  To test the service in isolation the helper
_make_item() disconnects both signals before saving.

DB constraint
-------------
inventory.Stock has a CHECK constraint stock_quantity_nonnegative (quantity >= 0).
ALLOW_NEGATIVE_INVENTORY cannot override the DB constraint, so negative-stock
tests would raise IntegrityError and are not included.

Run:
    pytest tests/unit/test_stock_service.py -v
"""

import threading

import pytest
from django.db.models.signals import post_save, pre_delete

from sales.models import InvoiceItem, invoice_item_added, invoice_item_deleted
from tests.factories import (
    InvoiceFactory,
    InvoiceItemFactory,
    LocationFactory,
    ProductFactory,
    StockFactory,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_item(quantity=10, stock_qty=None, product=None, location=None):
    """
    Create and save an InvoiceItem WITHOUT triggering post_save / pre_delete
    signals so that the service can be tested in isolation.
    """
    if product is None:
        product = ProductFactory()
    if location is None:
        location = LocationFactory()

    if stock_qty is not None:
        StockFactory(product=product, location=location, quantity=stock_qty)

    post_save.disconnect(invoice_item_added, sender=InvoiceItem)
    pre_delete.disconnect(invoice_item_deleted, sender=InvoiceItem)
    try:
        item = InvoiceItemFactory.build(
            product=product, location=location, quantity=quantity
        )
        item.invoice = InvoiceFactory()
        item.save()
    finally:
        post_save.connect(invoice_item_added, sender=InvoiceItem)
        pre_delete.connect(invoice_item_deleted, sender=InvoiceItem)

    return item


# ---------------------------------------------------------------------------
# deduct_stock_for_invoice_item
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
class TestDeductStock:

    def test_normal_deduction(self):
        """Stock is reduced by the item quantity."""
        from inventory.models import Stock
        from sales.services.stock_service import deduct_stock_for_invoice_item

        item = _make_item(quantity=10, stock_qty=50)
        deduct_stock_for_invoice_item(item)

        stock = Stock.objects.get(product=item.product, location=item.location)
        assert stock.quantity == 40

    def test_exact_deduction_reaches_zero(self):
        """Deducting exactly available qty floors at zero."""
        from inventory.models import Stock
        from sales.services.stock_service import deduct_stock_for_invoice_item

        item = _make_item(quantity=30, stock_qty=30)
        deduct_stock_for_invoice_item(item)

        stock = Stock.objects.get(product=item.product, location=item.location)
        assert stock.quantity == 0

    def test_insufficient_stock_no_negative(self, settings):
        """With ALLOW_NEGATIVE_INVENTORY=False, quantity floors at 0, no exception."""
        from inventory.models import Stock
        from sales.services.stock_service import deduct_stock_for_invoice_item

        settings.ALLOW_NEGATIVE_INVENTORY = False
        item = _make_item(quantity=100, stock_qty=5)
        deduct_stock_for_invoice_item(item)

        stock = Stock.objects.get(product=item.product, location=item.location)
        assert stock.quantity == 0

    def test_no_stock_record_creates_zero_placeholder(self):
        """If no Stock row exists, a zero-quantity placeholder is created; no exception."""
        from inventory.models import Stock
        from sales.services.stock_service import deduct_stock_for_invoice_item

        item = _make_item(quantity=5, stock_qty=None)
        Stock.objects.filter(product=item.product, location=item.location).delete()

        deduct_stock_for_invoice_item(item)  # must not raise

        assert Stock.objects.filter(
            product=item.product, location=item.location
        ).exists()

    def test_warning_logged_on_insufficient_stock(self, settings, caplog):
        """A WARNING is emitted when stock is insufficient."""
        import logging
        from sales.services.stock_service import deduct_stock_for_invoice_item

        settings.ALLOW_NEGATIVE_INVENTORY = False
        item = _make_item(quantity=999, stock_qty=1)

        with caplog.at_level(logging.WARNING, logger="sales.services.stock_service"):
            deduct_stock_for_invoice_item(item)

        assert "Insufficient stock" in caplog.text

    def test_two_sequential_deductions_accumulate(self):
        """Two sequential service calls properly accumulate deductions."""
        from inventory.models import Stock
        from sales.services.stock_service import deduct_stock_for_invoice_item

        product = ProductFactory()
        location = LocationFactory()
        StockFactory(product=product, location=location, quantity=80)

        item1 = _make_item(quantity=10, product=product, location=location)
        item2 = _make_item(quantity=20, product=product, location=location)

        deduct_stock_for_invoice_item(item1)
        deduct_stock_for_invoice_item(item2)

        stock = Stock.objects.get(product=product, location=location)
        assert stock.quantity == 50  # 80 - 10 - 20


# ---------------------------------------------------------------------------
# restore_stock_for_invoice_item
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
class TestRestoreStock:

    def test_normal_restore(self):
        """Restoring adds the item quantity back to stock."""
        from inventory.models import Stock
        from sales.services.stock_service import restore_stock_for_invoice_item

        item = _make_item(quantity=10, stock_qty=20)
        restore_stock_for_invoice_item(item)

        stock = Stock.objects.get(product=item.product, location=item.location)
        assert stock.quantity == 30

    def test_restore_to_zero_stock(self):
        """Restoring against a zero-quantity stock record gives the full item qty."""
        from inventory.models import Stock
        from sales.services.stock_service import restore_stock_for_invoice_item

        item = _make_item(quantity=15, stock_qty=0)
        restore_stock_for_invoice_item(item)

        stock = Stock.objects.get(product=item.product, location=item.location)
        assert stock.quantity == 15

    def test_restore_no_stock_record_logs_warning(self, caplog):
        """restore_stock logs a WARNING when no stock record exists (no exception raised)."""
        import logging
        from inventory.models import Stock
        from sales.services.stock_service import restore_stock_for_invoice_item

        item = _make_item(quantity=5, stock_qty=None)
        Stock.objects.filter(product=item.product, location=item.location).delete()

        with caplog.at_level(logging.WARNING, logger="sales.services.stock_service"):
            restore_stock_for_invoice_item(item)  # must not raise

        assert "Cannot restore stock" in caplog.text

    def test_deduct_then_restore_returns_to_original(self):
        """deduct followed by restore leaves stock unchanged."""
        from inventory.models import Stock
        from sales.services.stock_service import (
            deduct_stock_for_invoice_item,
            restore_stock_for_invoice_item,
        )

        item = _make_item(quantity=25, stock_qty=100)
        deduct_stock_for_invoice_item(item)
        restore_stock_for_invoice_item(item)

        stock = Stock.objects.get(product=item.product, location=item.location)
        assert stock.quantity == 100


# ---------------------------------------------------------------------------
# Concurrency regression
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
class TestConcurrentDeductions:

    def test_five_parallel_deductions_serialised(self):
        """
        Five threads each deducting 10 from stock=100 must leave exactly 50.

        The OLD code ran select_for_update inside the *caller's* transaction,
        creating deadlock/lost-update risk under concurrent load.

        With each service call owning its own @transaction.atomic, the lock is
        acquired and released per-call, serialising all five writes correctly.
        """
        from inventory.models import Stock
        from sales.services.stock_service import deduct_stock_for_invoice_item

        product = ProductFactory()
        location = LocationFactory()
        StockFactory(product=product, location=location, quantity=100)

        invoice = InvoiceFactory()
        items = []

        # Create items without triggering signal (avoid double-deduction)
        post_save.disconnect(invoice_item_added, sender=InvoiceItem)
        pre_delete.disconnect(invoice_item_deleted, sender=InvoiceItem)
        try:
            for _ in range(5):
                item = InvoiceItemFactory.build(
                    product=product, location=location, quantity=10
                )
                item.invoice = invoice
                item.save()
                items.append(item)
        finally:
            post_save.connect(invoice_item_added, sender=InvoiceItem)
            pre_delete.connect(invoice_item_deleted, sender=InvoiceItem)

        errors = []

        def _run(item):
            try:
                deduct_stock_for_invoice_item(item)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_run, args=(item,)) for item in items]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Thread errors: {errors}"

        stock = Stock.objects.get(product=product, location=location)
        assert stock.quantity == 50, (
            f"Expected 50 after 5×10 deductions from 100, got {stock.quantity}"
        )
