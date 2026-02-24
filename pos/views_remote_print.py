# -*- coding: utf-8 -*-
"""
API endpoint للطباعة المباشرة عن بُعد على الطابعة المحلية (XPrinter)

الفكرة:
- السيرفر يولّد بيانات ESC/POS كصورة عربية (مثل الطباعة المحلية تماماً)
- يرسلها للمتصفح كـ base64
- المتصفح يرسلها لوكيل الطباعة المحلي (print agent) عبر WebSocket محلي
- الوكيل المحلي يطبع مباشرة على XPrinter
"""
import base64
import json
import logging

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET
from django.shortcuts import get_object_or_404

from pos.models import POSOrder

logger = logging.getLogger(__name__)


@login_required
@require_GET
def generate_receipt_data(request, order_id):
    """
    توليد بيانات الإيصال كـ ESC/POS raw data بصيغة base64
    المتصفح يستقبلها ويرسلها للطابعة المحلية عبر print agent
    """
    try:
        order = get_object_or_404(POSOrder, pk=order_id)
        lines = order.lines.select_related('product').all()
        
        from .thermal_printer_arabic import ArabicThermalPrinter, PILLOW_AVAILABLE
        
        if not PILLOW_AVAILABLE:
            return JsonResponse({
                'success': False,
                'error': 'مكتبة Pillow غير متوفرة على السيرفر'
            }, status=500)
        
        # إنشاء كائن الطابعة (بدون اتصال فعلي - فقط لتوليد البيانات)
        printer = ArabicThermalPrinter(paper_width=576)
        
        # توليد بيانات الإيصال
        receipt_data = _generate_receipt_escpos(printer, order, lines)
        
        if receipt_data:
            # تحويل لـ base64
            b64_data = base64.b64encode(receipt_data).decode('ascii')
            
            return JsonResponse({
                'success': True,
                'data': b64_data,
                'order_id': order.id,
                'order_number': order.number,
                'size': len(receipt_data),
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'فشل في توليد بيانات الطباعة'
            }, status=500)
            
    except Exception as e:
        logger.error(f"خطأ في توليد بيانات الطباعة: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def _generate_receipt_escpos(printer, order, lines):
    """
    توليد بيانات ESC/POS للإيصال (بدون إرسال للطابعة)
    يستخدم نفس منطق print_receipt لكن يرجع البيانات فقط
    """
    from decimal import Decimal
    from PIL import Image
    
    # جلب بيانات الشركة
    company_name = 'Tony ERP'
    company_address = ''
    company_phone = ''
    company_vat = ''
    company_logo = None
    company = None
    
    try:
        from core.models import Company
        company = Company.objects.first()
        if company:
            company_name = company.name or 'Tony ERP'
            company_address = company.address or ''
            company_phone = company.phone or ''
            company_vat = company.tax_id or ''
            if company.logo:
                try:
                    company_logo = company.logo.path
                except:
                    pass
    except:
        pass
    
    # بيانات المعرض
    branch_name = ''
    branch_phone = ''
    branch_address = ''
    if order.location:
        branch_name = order.location.name
        try:
            from showrooms.models import Showroom
            showroom = Showroom.objects.filter(location=order.location).first()
            if showroom:
                branch_name = showroom.name_ar or showroom.name or order.location.name
                branch_phone = showroom.contact_phone or ''
                branch_address = showroom.address or ''
        except:
            pass
    
    # === طباعة اللوجو ===
    logo_data = bytearray()
    if company_logo:
        try:
            from PIL import ImageEnhance
            logo_img = Image.open(company_logo)
            target_width = 550
            ratio = target_width / logo_img.width
            new_height = int(logo_img.height * ratio)
            if new_height > 350:
                new_height = 350
                ratio = new_height / logo_img.height
                target_width = int(logo_img.width * ratio)
            
            logo_img = logo_img.resize((target_width, new_height), Image.Resampling.LANCZOS)
            
            if logo_img.mode == 'RGBA':
                background = Image.new('RGB', logo_img.size, (255, 255, 255))
                background.paste(logo_img, mask=logo_img.split()[3])
                logo_img = background
            
            if logo_img.mode != 'L':
                logo_img = logo_img.convert('L')
            
            enhancer = ImageEnhance.Contrast(logo_img)
            logo_img = enhancer.enhance(1.5)
            
            threshold = 200
            logo_img = logo_img.point(lambda p: 255 if p > threshold else 0).convert('1')
            
            full_width = 576
            centered_logo = Image.new('1', (full_width, new_height + 10), 1)
            paste_x = (full_width - target_width) // 2
            centered_logo.paste(logo_img, (paste_x, 5))
            
            logo_data.extend(printer._image_to_escpos(centered_logo))
            logo_data.extend(b'\n')
        except Exception as e:
            logger.warning(f"فشل تحميل اللوجو: {e}")
    
    # === بناء أسطر الإيصال ===
    receipt_lines = []
    bold_lines = []
    center_lines = []
    large_lines = []
    
    # بيانات الشركة
    receipt_lines.append(company_name)
    center_lines.append(0)
    large_lines.append(0)
    bold_lines.append(0)
    
    if company_address:
        receipt_lines.append(company_address)
        center_lines.append(len(receipt_lines) - 1)
    
    if company_phone:
        receipt_lines.append(f"هاتف: {company_phone}")
        center_lines.append(len(receipt_lines) - 1)
    
    if order.is_tax_invoice and company_vat:
        receipt_lines.append(f"الرقم الضريبي: {company_vat}")
        center_lines.append(len(receipt_lines) - 1)
    
    receipt_lines.append('=' * 48)
    center_lines.append(len(receipt_lines) - 1)
    
    # بيانات الفرع
    if branch_name:
        receipt_lines.append(f"الفرع: {branch_name}")
        center_lines.append(len(receipt_lines) - 1)
        bold_lines.append(len(receipt_lines) - 1)
        if branch_address:
            receipt_lines.append(branch_address)
            center_lines.append(len(receipt_lines) - 1)
        if branch_phone:
            receipt_lines.append(f"تليفون الفرع: {branch_phone}")
            center_lines.append(len(receipt_lines) - 1)
        receipt_lines.append('-' * 48)
        center_lines.append(len(receipt_lines) - 1)
    
    # نوع الفاتورة
    if order.is_tax_invoice:
        receipt_lines.append("*** فاتورة ضريبية ***")
        center_lines.append(len(receipt_lines) - 1)
        bold_lines.append(len(receipt_lines) - 1)
    
    # رقم الفاتورة
    receipt_lines.append(f"فاتورة رقم: {order.number}")
    bold_lines.append(len(receipt_lines) - 1)
    center_lines.append(len(receipt_lines) - 1)
    
    receipt_lines.append(f"التاريخ: {order.created_at.strftime('%Y-%m-%d')}  الوقت: {order.created_at.strftime('%H:%M')}")
    
    if hasattr(order, 'session') and order.session:
        cashier = order.session.user.first_name or order.session.user.username
        receipt_lines.append(f"الكاشير: {cashier}")
    
    if order.customer:
        receipt_lines.append(f"العميل: {order.customer}")
    
    receipt_lines.append('-' * 48)
    
    # === جدول المنتجات - يُرسم كصورة منفصلة ===
    # نجمع بيانات الجدول لرسمه لاحقاً
    table_headers = ['المنتج', 'الكمية', 'السعر', 'المجموع']
    table_rows = []
    for line in lines:
        name = str(line.product.name)
        qty = str(int(line.quantity))
        price = f"{line.price:,.0f}"
        total = f"{line.total:,.0f}"
        table_rows.append([name, qty, price, total])
    
    # placeholder - سيتم استبداله بالجدول المرسوم
    TABLE_MARKER = '__TABLE_HERE__'
    receipt_lines.append(TABLE_MARKER)
    
    receipt_lines.append('-' * 48)
    
    # المجاميع
    subtotal = getattr(order, 'subtotal', order.total)
    receipt_lines.append(f"المجموع:                              {subtotal:,.0f}")
    
    if order.discount_amount and order.discount_amount > 0:
        receipt_lines.append(f"الخصم:                               -{order.discount_amount:,.0f}")
    
    if order.is_tax_invoice and order.tax_amount and order.tax_amount > 0:
        vat_rate = order.vat_rate or 14
        receipt_lines.append(f"ضريبة القيمة المضافة ({vat_rate}%):          {order.tax_amount:,.0f}")
    
    if order.withholding_tax_amount and order.withholding_tax_amount > 0:
        rate = order.withholding_tax_rate or 0
        receipt_lines.append(f"ضريبة المنبع ({rate}%):               -{order.withholding_tax_amount:,.0f}")
    
    if order.shipping_cost and order.shipping_cost > 0:
        receipt_lines.append(f"مصاريف الشحن:                         {order.shipping_cost:,.0f}")
    
    receipt_lines.append('=' * 48)
    
    receipt_lines.append(f"الإجمالي:                         {order.total:,.0f} ج.م")
    bold_lines.append(len(receipt_lines) - 1)
    large_lines.append(len(receipt_lines) - 1)
    
    receipt_lines.append('=' * 48)
    
    if order.paid_amount:
        receipt_lines.append(f"المدفوع:                              {order.paid_amount:,.0f}")
        change = float(order.paid_amount) - float(order.total)
        if change > 0:
            receipt_lines.append(f"الباقي:                               {change:,.0f}")
    
    receipt_lines.append('')
    receipt_lines.append('-' * 48)
    center_lines.append(len(receipt_lines) - 1)
    
    receipt_lines.append('شكراً لزيارتكم')
    center_lines.append(len(receipt_lines) - 1)
    bold_lines.append(len(receipt_lines) - 1)
    
    # معلومات التواصل
    if company:
        receipt_lines.append('')
        if hasattr(company, 'phone') and company.phone:
            receipt_lines.append(f"هاتف: {company.phone}")
            center_lines.append(len(receipt_lines) - 1)
        if hasattr(company, 'mobile') and company.mobile:
            receipt_lines.append(f"موبايل: {company.mobile}")
            center_lines.append(len(receipt_lines) - 1)
        if hasattr(company, 'whatsapp') and company.whatsapp:
            receipt_lines.append(f"واتساب: {company.whatsapp}")
            center_lines.append(len(receipt_lines) - 1)
        if hasattr(company, 'email') and company.email:
            receipt_lines.append(f"إيميل: {company.email}")
            center_lines.append(len(receipt_lines) - 1)
        if hasattr(company, 'website') and company.website:
            receipt_lines.append(f"الموقع: {company.website}")
            center_lines.append(len(receipt_lines) - 1)
    
    # الفروع
    try:
        from showrooms.models import Showroom
        all_branches = Showroom.objects.filter(is_active=True).order_by('id')
        if all_branches.exists():
            receipt_lines.append('')
            receipt_lines.append('=' * 48)
            center_lines.append(len(receipt_lines) - 1)
            receipt_lines.append('فروعنا')
            center_lines.append(len(receipt_lines) - 1)
            bold_lines.append(len(receipt_lines) - 1)
            receipt_lines.append('=' * 48)
            center_lines.append(len(receipt_lines) - 1)
            
            for branch in all_branches:
                branch_display_name = branch.name_ar or branch.name
                receipt_lines.append(f"● {branch_display_name}")
                bold_lines.append(len(receipt_lines) - 1)
                
                location_parts = []
                if branch.country and branch.country != 'مصر':
                    location_parts.append(branch.country)
                if branch.governorate:
                    location_parts.append(branch.governorate)
                if branch.city:
                    location_parts.append(branch.city)
                if location_parts:
                    receipt_lines.append(' - '.join(location_parts))
                    center_lines.append(len(receipt_lines) - 1)
                
                if branch.address:
                    receipt_lines.append(branch.address)
                    center_lines.append(len(receipt_lines) - 1)
                if branch.contact_phone:
                    receipt_lines.append(f"تليفون: {branch.contact_phone}")
                    center_lines.append(len(receipt_lines) - 1)
                receipt_lines.append('-' * 32)
                center_lines.append(len(receipt_lines) - 1)
    except:
        pass
    
    receipt_lines.append('')
    receipt_lines.append('- - - - - - - - - - - - -')
    center_lines.append(len(receipt_lines) - 1)
    
    # === تحويل لصورة (مع الجدول) ===
    # نقسم الأسطر عند TABLE_MARKER ونرسم كل جزء
    from PIL import Image
    
    parts_before = []
    parts_after = []
    found_marker = False
    marker_bold_before = []
    marker_center_before = []
    marker_large_before = []
    marker_bold_after = []
    marker_center_after = []
    marker_large_after = []
    
    offset_after = 0
    for i, line in enumerate(receipt_lines):
        if line == '__TABLE_HERE__':
            found_marker = True
            offset_after = i + 1
            continue
        if not found_marker:
            parts_before.append(line)
            if i in bold_lines:
                marker_bold_before.append(len(parts_before) - 1)
            if i in center_lines:
                marker_center_before.append(len(parts_before) - 1)
            if i in large_lines:
                marker_large_before.append(len(parts_before) - 1)
        else:
            parts_after.append(line)
            new_idx = len(parts_after) - 1
            if i in bold_lines:
                marker_bold_after.append(new_idx)
            if i in center_lines:
                marker_center_after.append(new_idx)
            if i in large_lines:
                marker_large_after.append(new_idx)
    
    # رسم الجزء العلوي (قبل الجدول)
    img_before = printer._text_to_image(
        parts_before,
        font_size=22,
        bold_lines=marker_bold_before,
        center_lines=marker_center_before,
        large_lines=marker_large_before
    )
    
    # رسم جدول المنتجات
    col_widths = [240, 70, 110, 110]  # المنتج | الكمية | السعر | المجموع
    col_aligns = ['right', 'center', 'center', 'center']
    img_table = printer._table_to_image(
        table_headers, table_rows,
        font_size=20,
        col_widths=col_widths,
        col_aligns=col_aligns
    )
    
    # رسم الجزء السفلي (بعد الجدول)
    img_after = printer._text_to_image(
        parts_after,
        font_size=22,
        bold_lines=marker_bold_after,
        center_lines=marker_center_after,
        large_lines=marker_large_after
    )
    
    # دمج الصور الثلاثة
    total_h = 0
    if img_before: total_h += img_before.height
    if img_table: total_h += img_table.height
    if img_after: total_h += img_after.height
    
    img = Image.new('1', (printer.paper_width, total_h), color=1)
    y_offset = 0
    if img_before:
        img.paste(img_before, (0, y_offset))
        y_offset += img_before.height
    if img_table:
        img.paste(img_table, (0, y_offset))
        y_offset += img_table.height
    if img_after:
        img.paste(img_after, (0, y_offset))
    
    if img is None or total_h == 0:
        return None
    
    # === بناء بيانات ESC/POS ===
    data = bytearray()
    data.extend(printer.INIT)
    
    if logo_data:
        data.extend(logo_data)
    
    data.extend(printer._image_to_escpos(img))
    data.extend(printer.FEED_LINES)
    data.extend(printer.CUT_PARTIAL)  # قطع الورق
    
    return bytes(data)
