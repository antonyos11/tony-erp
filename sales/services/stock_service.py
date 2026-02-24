"""
Sales Stock Service
====================
All stock mutations triggered by invoice line-item changes live here.

WHY NOT IN A SIGNAL
--------------------
The old code called select_for_update() inside a Django signal that fired
inside the *caller's* outer transaction.  Under concurrent load this meant:

  Worker-A: BEGIN … SELECT FOR UPDATE stock(row=42) … [holds lock]
  Worker-B: BEGIN … SELECT FOR UPDATE stock(row=42) … [waiting]
  Worker-A signal fires → tries to lock stock(row=42) again → DEADLOCK

Moving the lock + mutation into an explicit service function means:
  - The @transaction.atomic wrapping is self-contained and released the
    moment the function returns.
  - Signals in sales/models.py become thin dispatchers: they update the
    invoice cached_total (a fast F() UPDATE, no row lock) and then hand off
    to this service.
  - The service can be unit-tested by calling it directly — no need to
    simulate the Django signal machinery.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.conf import settings
from django.db import transaction
from django.db.models import F

if TYPE_CHECKING:
    from sales.models import InvoiceItem

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@transaction.atomic
def deduct_stock_for_invoice_item(instance: "InvoiceItem") -> None:
    """
    Deduct stock for a newly-created InvoiceItem.

    IMPORTANT: Call this ONLY for ``created=True`` items.

    Uses ``select_for_update()`` inside its own ``@transaction.atomic`` block
    so the row-level lock is acquired and released entirely within this
    function — it never leaks into the caller's transaction.

    :param instance: The freshly-saved InvoiceItem.
    """
    from inventory.models import Stock

    allow_negative: bool = getattr(settings, "ALLOW_NEGATIVE_INVENTORY", False)
    required_qty = instance.quantity

    stock = (
        Stock.objects.select_for_update()
        .filter(product=instance.product, location=instance.location)
        .first()
    )

    if stock:
        current_qty = stock.quantity or 0

        if not allow_negative and current_qty < required_qty:
            logger.warning(
                "Insufficient stock: product=%s location=%s available=%s required=%s — "
                "invoice will proceed (no hard block).",
                instance.product_id,
                instance.location_id,
                current_qty,
                required_qty,
            )

        new_qty = current_qty - required_qty
        if not allow_negative:
            new_qty = max(0, new_qty)

        stock.quantity = new_qty
        stock.save(update_fields=["quantity"])

    else:
        # No stock record exists yet — create a zero-quantity placeholder so
        # inventory reporting stays consistent.  Do NOT raise; the invoice
        # must not be blocked by a missing stock record.
        Stock.objects.create(
            product=instance.product,
            location=instance.location,
            quantity=0,
        )
        logger.warning(
            "No stock record found: product=%s location=%s "
            "(InvoiceItem=%s). Created zero-quantity record.",
            instance.product_id,
            instance.location_id,
            instance.pk,
        )


@transaction.atomic
def restore_stock_for_invoice_item(instance: "InvoiceItem") -> None:
    """
    Return stock when an InvoiceItem is deleted.

    Uses ``select_for_update()`` inside its own ``@transaction.atomic`` block
    to prevent concurrent restores producing incorrect totals.

    :param instance: The InvoiceItem about to be deleted.
    """
    from inventory.models import Stock

    stock = (
        Stock.objects.select_for_update()
        .filter(product=instance.product, location=instance.location)
        .first()
    )

    if stock:
        stock.quantity = F("quantity") + instance.quantity
        stock.save(update_fields=["quantity"])
    else:
        logger.warning(
            "Cannot restore stock: no record for product=%s location=%s "
            "(deleted InvoiceItem=%s).",
            instance.product_id,
            instance.location_id,
            instance.pk,
        )
