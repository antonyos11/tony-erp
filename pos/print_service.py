"""
POS Print Service – generates ESC/POS receipt and sends to XPrinter.
خدمة طباعة نقطة البيع - إنشاء إيصال ESC/POS وإرساله للطابعة الحرارية.

Called when a POS transaction is completed (paid).
"""
import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional, Tuple

from printing.models import UnifiedPrintJob

logger = logging.getLogger(__name__)


def build_escpos_receipt(order) -> bytes:
    """
    Build ESC/POS binary data for a POS order receipt.
    Compatible with XP-80 and similar 80mm thermal printers.
    """
    ESC = b'\x1b'
    GS = b'\x1d'

    data = bytearray()

    # ── Initialize printer ──
    data += ESC + b'\x40'

    # ── Center align ──
    data += ESC + b'\x61\x01'

    # ── Double-height header ──
    data += GS + b'\x21\x11'
    try:
        data += 'صفا فوم\n'.encode('cp1256')
    except (UnicodeEncodeError, LookupError):
        data += b'Safa Foam\n'
    data += b'Safa Foam\n'
    data += GS + b'\x21\x00'  # Normal size

    data += b'================================\n'

    # ── Left align for details ──
    data += ESC + b'\x61\x00'

    # Order info
    order_number = getattr(order, 'number', '') or str(order.pk)
    data += f'Order: #{order_number}\n'.encode('ascii', errors='replace')
    data += f'Date:  {datetime.now().strftime("%Y-%m-%d %H:%M")}\n'.encode()

    # Cashier info
    cashier = ''
    if hasattr(order, 'session') and order.session:
        session = order.session
        if hasattr(session, 'cashier') and session.cashier:
            cashier = str(session.cashier)
        elif hasattr(session, 'user') and session.user:
            cashier = str(session.user)
    if not cashier and hasattr(order, 'created_by') and order.created_by:
        cashier = str(order.created_by)
    if cashier:
        data += f'Cashier: {cashier}\n'.encode('ascii', errors='replace')

    # Customer info
    customer = getattr(order, 'customer', None)
    if customer:
        data += f'Customer: {str(customer)[:25]}\n'.encode('ascii', errors='replace')

    # Location / showroom
    location = getattr(order, 'showroom', None) or getattr(order, 'location', None)
    if location:
        data += f'Branch: {str(location)[:25]}\n'.encode('ascii', errors='replace')

    data += b'--------------------------------\n'

    # ── Items ──
    items = order.lines.select_related('product').all()

    line_total_sum = Decimal('0')
    for item in items:
        name = str(item.product.name if item.product else '')[:22]
        qty = item.quantity
        price = float(item.price)
        line_total = float(qty * item.price)
        line_total_sum += item.price * qty

        # Product name line
        try:
            data += f'{name}\n'.encode('cp1256')
        except (UnicodeEncodeError, LookupError):
            data += f'{name}\n'.encode('ascii', errors='replace')

        # Qty x price = total  (right-aligned numbers)
        detail = f'  {qty} x {price:.2f} = {line_total:.2f}'
        data += detail.encode() + b'\n'

    data += b'================================\n'

    # ── Subtotal / Discount / Tax / Total ──
    data += ESC + b'\x61\x02'  # Right align

    subtotal = float(line_total_sum)
    data += f'Subtotal:     {subtotal:.2f}\n'.encode()

    discount = float(getattr(order, 'discount_amount', 0) or 0)
    if discount > 0:
        data += f'Discount:    -{discount:.2f}\n'.encode()

    tax = float(getattr(order, 'tax_amount', 0) or 0)
    if tax > 0:
        vat_rate = float(getattr(order, 'vat_rate', 0) or 0)
        data += f'VAT ({vat_rate:.0f}%):    +{tax:.2f}\n'.encode()

    shipping = float(getattr(order, 'shipping_cost', 0) or 0)
    if shipping > 0:
        data += f'Shipping:    +{shipping:.2f}\n'.encode()

    data += b'--------------------------------\n'

    # Total - bold, larger
    data += ESC + b'\x45\x01'  # Bold on
    data += GS + b'\x21\x01'  # Double width

    order_total = float(getattr(order, 'total', 0) or subtotal)
    data += f'TOTAL: {order_total:.2f}\n'.encode()

    data += GS + b'\x21\x00'  # Normal size
    data += ESC + b'\x45\x00'  # Bold off

    # ── Payments ──
    payments = order.payments.select_related('method').all()
    if payments.exists():
        data += ESC + b'\x61\x00'  # Left align
        data += b'\nPayments:\n'
        for pay in payments:
            method_name = str(pay.method) if pay.method else 'Cash'
            data += f'  {method_name}: {float(pay.amount):.2f}\n'.encode('ascii', errors='replace')

    # ── Footer ──
    data += ESC + b'\x61\x01'  # Center
    data += b'\n'
    data += b'--------------------------------\n'
    data += b'Thank you for your purchase!\n'
    try:
        data += 'شكراً لزيارتكم\n'.encode('cp1256')
    except (UnicodeEncodeError, LookupError):
        pass
    data += b'================================\n'

    # Feed and cut
    data += b'\n\n\n'
    data += GS + b'\x56\x00'  # Full cut

    return bytes(data)


def print_pos_receipt(
    order,
    copies: int = 1,
    printer_id=None,
    user=None,
) -> Tuple[bool, str, Optional[UnifiedPrintJob]]:
    """
    Generate and print a receipt for a POS order.
    Called from the POS payment view or the auto-print signal.
    """
    try:
        from printing.manager import PrintManager

        escpos_data = build_escpos_receipt(order)
        order_id = getattr(order, 'number', '') or str(order.pk)

        success, msg, job = PrintManager.print_receipt(
            escpos_data=escpos_data,
            title=f'Receipt #{order_id}',
            copies=copies,
            user=user,
            source_id=str(order.pk),
            printer_id=printer_id,
        )

        if success:
            logger.info(f"POS receipt printed for order {order_id}")
        else:
            logger.warning(f"POS receipt print failed for {order_id}: {msg}")

        return success, msg, job

    except Exception as e:
        logger.error(f"POS receipt error: {e}", exc_info=True)
        return False, str(e), None
