"""
Production Pipeline → Automated Barcode Printing
تكامل خط الإنتاج → طباعة باركود تلقائية
Triggered when 'Packaging' stage is marked 'Complete'.
"""
import logging
from datetime import date
from typing import Tuple

logger = logging.getLogger(__name__)


def on_packaging_complete(stage_entry, user) -> Tuple[bool, str]:
    """
    Called when the Packaging stage is completed in the production pipeline.
    Generates warranty barcode labels and sends them to the Zebra printer.

    يُستدعى عند إكمال مرحلة التغليف في خط الإنتاج.
    """
    from printing.dispatch import PrintDispatcher

    order = stage_entry.board.production_order
    product = order.product
    units = list(order.finished_units.filter(
        status__in=['produced', 'in_stock']
    ).order_by('unit_serial'))

    if not units:
        return False, "لا توجد وحدات منتج نهائي نشطة لأمر الإنتاج هذا."

    zpl_commands = []

    for unit in units:
        # Build barcode: {SKU}-{Date}-{Serial}
        sku = product.sku if hasattr(product, 'sku') and product.sku else (
            product.barcode if hasattr(product, 'barcode') and product.barcode else f"P{product.pk}"
        )
        production_date = date.today().strftime('%y%m%d')
        serial = unit.unit_serial or f"{unit.pk:04d}"
        barcode_content = f"{sku}-{production_date}-{serial}"

        # Generate ZPL label
        zpl = _generate_warranty_zpl(
            barcode_content=barcode_content,
            product_name=product.name,
            sku=sku,
            serial=serial,
            production_date=date.today().strftime('%Y-%m-%d'),
            order_number=order.number,
            warranty_policy=getattr(unit, 'warranty_policy', None),
        )
        zpl_commands.append(zpl)

    combined_zpl = '\n'.join(zpl_commands)

    # Dispatch through unified system
    success, msg, job = PrintDispatcher.print_zpl(
        document_type='production_barcode',
        zpl_command=combined_zpl,
        title=f"باركود إنتاج - أمر #{order.number} ({len(units)} وحدة)",
        copies=1,
        user=user,
        source_app='production',
        source_model='ProductionOrder',
        source_id=str(order.pk),
    )

    if success:
        stage_entry.print_status = 'printing'
        stage_entry.save(update_fields=['print_status'])

    return success, msg


def _generate_warranty_zpl(
    barcode_content: str,
    product_name: str,
    sku: str,
    serial: str,
    production_date: str,
    order_number: str,
    warranty_policy=None,
    label_width_mm: int = 50,
    label_height_mm: int = 30,
    dpi: int = 203,
) -> str:
    """Generate a ZPL label for a warranty barcode."""
    dots_per_mm = dpi / 25.4
    w = int(label_width_mm * dots_per_mm)
    h = int(label_height_mm * dots_per_mm)

    zpl = f"^XA\n^PW{w}\n^LL{h}\n"

    # Product name (top, larger font)
    fn_h = max(20, int(h * 0.14))
    name_display = product_name[:28]
    zpl += f"^FO{int(w * 0.05)},{int(h * 0.05)}^A0N,{fn_h},{int(fn_h * 0.7)}^FD{name_display}^FS\n"

    # SKU line
    fn_small = max(14, int(h * 0.08))
    zpl += f"^FO{int(w * 0.05)},{int(h * 0.22)}^A0N,{fn_small},{int(fn_small * 0.7)}^FDSKU: {sku}  S/N: {serial}^FS\n"

    # Date & warranty
    zpl += f"^FO{int(w * 0.05)},{int(h * 0.35)}^A0N,{fn_small},{int(fn_small * 0.7)}^FDMFG: {production_date}^FS\n"
    if warranty_policy:
        policy_name = getattr(warranty_policy, 'name', str(warranty_policy))
        zpl += f"^FO{int(w * 0.55)},{int(h * 0.35)}^A0N,{fn_small},{int(fn_small * 0.7)}^FDWarranty: {policy_name}^FS\n"

    # Barcode (Code128)
    barcode_x = int(w * 0.07)
    barcode_y = int(h * 0.52)
    barcode_h = max(30, int(h * 0.30))
    module_w = max(1, min(3, w // (len(barcode_content) * 12)))
    zpl += f"^FO{barcode_x},{barcode_y}^BY{module_w},3,{barcode_h}^BCN,,Y,N,N^FD{barcode_content}^FS\n"

    # Order number (bottom-right, tiny)
    fn_tiny = max(10, int(h * 0.05))
    zpl += f"^FO{int(w * 0.65)},{int(h * 0.90)}^A0N,{fn_tiny},{int(fn_tiny * 0.7)}^FDOrd: {order_number}^FS\n"

    zpl += "^XZ\n"
    return zpl
