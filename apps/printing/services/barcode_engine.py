"""
محرك توليد الباركود — RITA ERP
يدعم Code128 و QR Code
يتطلب: python-barcode و qrcode[pil]
"""
import io
import base64
from datetime import date


# ── Code128 via python-barcode ────────────────────────────────────────────────
def _barcode_to_base64(barcode_obj) -> str:
    """تحويل كائن barcode إلى صورة PNG مُرمَّزة Base64."""
    buffer = io.BytesIO()
    barcode_obj.write(buffer, options={'write_text': False})
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode('utf-8')


def generate_code128(
    product_code: str,
    production_date: date | None = None,
    production_order: str = '',
) -> str:
    """
    توليد باركود Code128 يحتوي على:
    - كود المنتج
    - تاريخ الإنتاج (YYYYMMDD)
    - رقم أمر الإنتاج

    إرجاع: صورة PNG مُرمَّزة Base64 (للتضمين في HTML/PDF).
    """
    try:
        import barcode
        from barcode.writer import ImageWriter
    except ImportError as exc:
        raise ImportError(
            "python-barcode غير مثبَّت. نفِّذ: pip install python-barcode"
        ) from exc

    prod_date_str = (production_date or date.today()).strftime('%Y%m%d')
    payload = f'{product_code}-{prod_date_str}-{production_order}'.strip('-')

    code128_cls = barcode.get_barcode_class('code128')
    code128_obj = code128_cls(payload, writer=ImageWriter())
    return _barcode_to_base64(code128_obj)


def generate_qr(
    product_code: str,
    production_date: date | None = None,
    production_order: str = '',
    extra_data: dict | None = None,
) -> str:
    """
    توليد QR Code يحتوي على بيانات منظَّمة للمنتج.

    إرجاع: صورة PNG مُرمَّزة Base64.
    """
    try:
        import qrcode
        from PIL import Image
    except ImportError as exc:
        raise ImportError(
            "qrcode أو Pillow غير مثبَّت. نفِّذ: pip install qrcode[pil]"
        ) from exc

    prod_date_str = (production_date or date.today()).strftime('%Y-%m-%d')
    data_lines = [
        f'Product: {product_code}',
        f'Date: {prod_date_str}',
        f'Order: {production_order}',
    ]
    if extra_data:
        for k, v in extra_data.items():
            data_lines.append(f'{k}: {v}')

    payload = '\n'.join(data_lines)

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=2,
    )
    qr.add_data(payload)
    qr.make(fit=True)

    img = qr.make_image(fill_color='black', back_color='white')
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode('utf-8')


def generate_barcode_html(
    product_code: str,
    product_name: str = '',
    production_date: date | None = None,
    production_order: str = '',
    barcode_type: str = 'code128',
    width: str = '150px',
    height: str = '60px',
) -> str:
    """
    إنشاء HTML جاهز لعرض/طباعة الباركود مع بيانات المنتج.
    barcode_type: 'code128' أو 'qr'
    """
    if barcode_type == 'qr':
        img_b64 = generate_qr(product_code, production_date, production_order)
        img_tag = f'<img src="data:image/png;base64,{img_b64}" style="width:{width};height:{height};">'
    else:
        img_b64 = generate_code128(product_code, production_date, production_order)
        img_tag = f'<img src="data:image/png;base64,{img_b64}" style="width:{width};height:{height};">'

    prod_date_str = (production_date or date.today()).strftime('%Y-%m-%d')
    html = f"""
<div style="text-align:center; font-family:Arial,sans-serif; display:inline-block; padding:4px; border:1px solid #ddd;">
    {img_tag}
    <div style="font-size:9px; margin-top:2px;">{product_code}</div>
    {"<div style='font-size:8px;'>" + product_name + "</div>" if product_name else ""}
    <div style="font-size:8px; color:#555;">{prod_date_str}</div>
</div>
"""
    return html
