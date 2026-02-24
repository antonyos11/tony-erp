"""خدمات الطباعة الموحدة للباركود/QR والملصقات والإيصالات.
- ZPL للباركود/الملصقات
- ESC/POS للإيصالات الحرارية
- JSON/PDF كتمثيل تجميعي
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any
from datetime import datetime
import json


def _extract_qr_text(unit) -> str:
    """اختيار أفضل نص لإدخاله في QR على الملصق.

    - يفضل رابط تفعيل الضمان (URL)
    - يدعم بيانات قديمة مخزنة كـ JSON
    """
    raw = _safe(getattr(unit, 'qr_code_data', ''))
    if not raw:
        return _safe(getattr(unit, 'unit_serial', ''))

    # legacy JSON payload
    if raw.startswith('{'):
        try:
            obj = json.loads(raw)
            if isinstance(obj, dict):
                url = obj.get('url')
                if isinstance(url, str) and url.strip():
                    raw = url.strip()
                else:
                    sn = obj.get('sn')
                    if sn:
                        raw = str(sn).strip()
        except Exception:
            pass

    # make absolute if we have PUBLIC_SITE_URL and raw is a relative path
    try:
        from django.conf import settings
        public_base = (getattr(settings, 'PUBLIC_SITE_URL', '') or '').rstrip('/')
        if public_base and raw.startswith('/'):
            raw = f"{public_base}{raw}"
    except Exception:
        pass

    return _safe(raw)


@dataclass
class LabelPayload:
    data: Dict[str, Any]
    zpl: str
    escpos: str


def _safe(text: Any) -> str:
    return str(text or '').strip()


def build_warranty_label_payload(unit) -> LabelPayload:
    """إنشاء حمولة ملصق ضمان لوحدة منتج نهائي.
    يعتمد على minimal fields لتعمل بدون مكتبات خارجية.
    """
    product_name = _safe(getattr(unit, 'product', None) and unit.product.name)
    policy_name = _safe(getattr(unit, 'warranty_policy', None) and unit.warranty_policy.name)
    serial = _safe(getattr(unit, 'unit_serial', ''))
    barcode = _safe(getattr(unit, 'barcode', serial))
    qr_data = _extract_qr_text(unit)

    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M')

    # ZPL بسيط (حقول أساسية)
    zpl = f"""
^XA
^CF0,30
^FO30,30^FD{product_name}^FS
^CF0,25
^FO30,70^FDSerial: {serial}^FS
^FO30,110^FDBarcode: {barcode}^FS
^FO30,150^FDWarranty: {policy_name}^FS
^FO30,190^FDDatetime: {now}^FS
^BY2,2,70
^FO40,240^BCN,70,Y,N,N
^FD{barcode}^FS
^FO350,240^BQN,2,6
^FDQA,{qr_data}^FS
^XZ
""".strip()

    # ESC/POS نصي مبسط
    escpos = "\n".join([
        '*** WARRANTY LABEL ***',
        product_name,
        f"Serial: {serial}",
        f"Barcode: {barcode}",
        f"Warranty: {policy_name}",
        f"Generated: {now}",
        '[QR DATA]',
        qr_data,
        '*** END ***',
    ])

    data = {
        'product': product_name,
        'policy': policy_name,
        'serial': serial,
        'barcode': barcode,
        'qr_data': qr_data,
        'generated_at': now,
    }

    return LabelPayload(data=data, zpl=zpl, escpos=escpos)
