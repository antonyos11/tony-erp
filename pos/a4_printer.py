# -*- coding: utf-8 -*-
"""
نظام الطباعة على ورق A4 - طابعات HP وغيرها
A4 Paper Printing System for HP and other printers
"""
import os
import io
import tempfile
import subprocess
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    import win32print
    import win32api
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
    logger.warning("pywin32 غير متوفر")


class A4Printer:
    """
    طابعة A4 للفواتير الكبيرة
    تدعم طابعات HP و Canon و Epson وغيرها
    """
    
    def __init__(self, printer_name=None):
        """
        تهيئة الطابعة
        
        Args:
            printer_name: اسم الطابعة (None = الافتراضية)
        """
        self.printer_name = printer_name
    
    def get_available_printers(self):
        """الحصول على قائمة الطابعات"""
        printers = []
        if WIN32_AVAILABLE:
            try:
                for printer in win32print.EnumPrinters(
                    win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
                ):
                    printers.append({
                        'name': printer[2],
                        'description': printer[1],
                        'is_default': printer[2] == win32print.GetDefaultPrinter()
                    })
            except Exception as e:
                logger.error(f"خطأ: {e}")
        return printers
    
    def get_default_printer(self):
        """الطابعة الافتراضية"""
        if WIN32_AVAILABLE:
            try:
                return win32print.GetDefaultPrinter()
            except:
                pass
        return None
    
    def _generate_invoice_html(self, order, lines, settings=None):
        """إنشاء HTML للفاتورة بحجم A4"""
        if settings is None:
            settings = {}
        
        shop_name = settings.get('shop_name', 'Tony ERP')
        shop_address = settings.get('shop_address', '')
        shop_phone = settings.get('shop_phone', '')
        shop_vat = settings.get('shop_vat', '')
        shop_logo = settings.get('shop_logo', '')
        branch_name = settings.get('branch_name', '')
        footer_text = settings.get('footer_text', 'شكراً لتعاملكم معنا')
        
        # حساب المجاميع
        subtotal = getattr(order, 'subtotal', order.total)
        discount = order.discount_amount or 0
        tax = order.tax_amount or 0
        withholding_tax = order.withholding_tax_amount or 0
        shipping_cost = order.shipping_cost or 0
        total = order.total
        paid = order.paid_amount or 0
        remaining = float(total) - float(paid) if paid else 0
        
        # الكاشير
        cashier = ''
        if hasattr(order, 'session') and order.session:
            cashier = order.session.user.first_name or order.session.user.username
        
        # بناء صفوف المنتجات
        items_html = ''
        for i, line in enumerate(lines, 1):
            items_html += f'''
            <tr>
                <td style="text-align: center;">{i}</td>
                <td>{line.product.name}</td>
                <td style="text-align: center;">{line.product.sku or '-'}</td>
                <td style="text-align: center;">{int(line.quantity)}</td>
                <td style="text-align: center;">{line.price:,.2f}</td>
                <td style="text-align: center; font-weight: bold;">{line.total:,.2f}</td>
            </tr>
            '''
        
        html = f'''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>فاتورة {order.number}</title>
    <style>
        @page {{
            size: A4 portrait;
            margin: 15mm;
        }}
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        html, body {{
            width: 100%;
            height: 100%;
        }}
        body {{
            font-family: 'Tahoma', 'Arial', sans-serif;
            font-size: 12pt;
            line-height: 1.4;
            color: #333;
            direction: rtl;
            background: white;
            margin: 0;
            padding: 0;
        }}
        .invoice {{
            width: 100%;
            max-width: 190mm;
            margin: 0 auto;
            padding: 5mm;
            page-break-inside: avoid;
        }}
        
        /* Header */
        .header {{
            display: flex;
            flex-direction: row;
            justify-content: space-between;
            align-items: flex-start;
            border-bottom: 3px solid #2c3e50;
            padding-bottom: 15px;
            margin-bottom: 20px;
            width: 100%;
        }}
        .company-info {{
            flex: 1;
            text-align: right;
        }}
        .company-logo {{
            max-height: 80px;
            max-width: 200px;
            margin-bottom: 10px;
            object-fit: contain;
        }}
        .company-name {{
            font-size: 24pt;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 5px;
        }}
        .company-details {{
            font-size: 10pt;
            color: #666;
        }}
        .invoice-info {{
            text-align: left;
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            min-width: 180px;
            flex-shrink: 0;
        }}
        .invoice-title {{
            font-size: 16pt;
            font-weight: bold;
            color: #e74c3c;
            margin-bottom: 10px;
        }}
        .invoice-number {{
            font-size: 12pt;
            font-weight: bold;
            color: #2c3e50;
        }}
        
        /* Customer Info */
        .customer-section {{
            display: flex;
            flex-direction: row;
            justify-content: space-between;
            margin-bottom: 20px;
            gap: 20px;
            width: 100%;
        }}
        .info-box {{
            flex: 1;
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            border-right: 4px solid #3498db;
        }}
        .info-box h3 {{
            font-size: 12pt;
            color: #2c3e50;
            margin-bottom: 10px;
            border-bottom: 1px solid #ddd;
            padding-bottom: 5px;
        }}
        .info-row {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 5px;
            font-size: 11pt;
        }}
        .info-label {{
            color: #666;
        }}
        .info-value {{
            font-weight: bold;
        }}
        
        /* Items Table */
        .items-table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }}
        .items-table th {{
            background: #2c3e50;
            color: white;
            padding: 12px 8px;
            font-size: 11pt;
            text-align: center;
        }}
        .items-table td {{
            padding: 10px 8px;
            border-bottom: 1px solid #ddd;
            font-size: 11pt;
        }}
        .items-table tr:nth-child(even) {{
            background: #f8f9fa;
        }}
        .items-table tr:hover {{
            background: #e8f4f8;
        }}
        
        /* Totals */
        .totals-section {{
            display: flex;
            justify-content: flex-end;
            margin-bottom: 20px;
        }}
        .totals-box {{
            width: 300px;
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
        }}
        .total-row {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #ddd;
            font-size: 12pt;
        }}
        .total-row:last-child {{
            border-bottom: none;
        }}
        .total-row.grand-total {{
            background: #2c3e50;
            color: white;
            margin: 10px -15px -15px;
            padding: 15px;
            border-radius: 0 0 8px 8px;
            font-size: 16pt;
            font-weight: bold;
        }}
        .total-row.remaining {{
            color: #e74c3c;
            font-weight: bold;
        }}
        
        /* Footer */
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 2px solid #ddd;
            text-align: center;
        }}
        .footer-text {{
            font-size: 14pt;
            color: #2c3e50;
            margin-bottom: 10px;
        }}
        .footer-note {{
            font-size: 10pt;
            color: #999;
        }}
        
        /* Signatures */
        .signatures {{
            display: flex;
            justify-content: space-between;
            margin-top: 40px;
            padding-top: 20px;
        }}
        .signature-box {{
            text-align: center;
            width: 200px;
        }}
        .signature-line {{
            border-top: 1px solid #333;
            margin-top: 50px;
            padding-top: 5px;
        }}
        
        @media print {{
            html, body {{
                width: 210mm;
                height: 297mm;
                margin: 0;
                padding: 0;
            }}
            body {{
                print-color-adjust: exact;
                -webkit-print-color-adjust: exact;
            }}
            .invoice {{
                width: 100%;
                max-width: 100%;
                padding: 0;
                margin: 0;
            }}
            .no-print {{
                display: none !important;
            }}
        }}
    </style>
</head>
<body>
    <div class="invoice">
        <!-- Header -->
        <div class="header">
            <div class="company-info">
                {f'<img src="{shop_logo}" alt="Logo" class="company-logo">' if shop_logo else ''}
                <div class="company-name">{shop_name}</div>
                <div class="company-details">
                    {f'<div>{shop_address}</div>' if shop_address else ''}
                    {f'<div>هاتف: {shop_phone}</div>' if shop_phone else ''}
                    {f'<div>الرقم الضريبي: {shop_vat}</div>' if shop_vat else ''}
                    {f'<div>الفرع: {branch_name}</div>' if branch_name else ''}
                </div>
            </div>
            <div class="invoice-info">
                <div class="invoice-title">فاتورة ضريبية</div>
                <div class="invoice-number">{order.number}</div>
                <div style="margin-top: 10px; font-size: 10pt;">
                    <div>التاريخ: {order.created_at.strftime('%Y-%m-%d')}</div>
                    <div>الوقت: {order.created_at.strftime('%H:%M')}</div>
                </div>
            </div>
        </div>
        
        <!-- Customer & Invoice Info -->
        <div class="customer-section">
            <div class="info-box">
                <h3>بيانات العميل</h3>
                <div class="info-row">
                    <span class="info-label">الاسم:</span>
                    <span class="info-value">{order.customer or 'عميل نقدي'}</span>
                </div>
                {f'<div class="info-row"><span class="info-label">الهاتف:</span><span class="info-value">{order.customer.phone if hasattr(order.customer, "phone") and order.customer else "-"}</span></div>' if order.customer else ''}
            </div>
            <div class="info-box">
                <h3>بيانات الفاتورة</h3>
                <div class="info-row">
                    <span class="info-label">الفرع:</span>
                    <span class="info-value">{order.location.name if order.location else '-'}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">الكاشير:</span>
                    <span class="info-value">{cashier or '-'}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">طريقة الدفع:</span>
                    <span class="info-value">{'نقدي' if not order.customer else 'آجل'}</span>
                </div>
            </div>
        </div>
        
        <!-- Items Table -->
        <table class="items-table">
            <thead>
                <tr>
                    <th style="width: 5%;">#</th>
                    <th style="width: 40%;">المنتج</th>
                    <th style="width: 15%;">الكود</th>
                    <th style="width: 10%;">الكمية</th>
                    <th style="width: 15%;">السعر</th>
                    <th style="width: 15%;">الإجمالي</th>
                </tr>
            </thead>
            <tbody>
                {items_html}
            </tbody>
        </table>
        
        <!-- Totals -->
        <div class="totals-section">
            <div class="totals-box">
                <div class="total-row">
                    <span>المجموع الفرعي:</span>
                    <span>{subtotal:,.2f} ج.م</span>
                </div>
                {f'<div class="total-row"><span>الخصم:</span><span style="color: #27ae60;">-{discount:,.2f} ج.م</span></div>' if discount else ''}
                {f'<div class="total-row"><span>ضريبة القيمة المضافة ({order.vat_rate or 14}%):</span><span>{tax:,.2f} ج.م</span></div>' if order.is_tax_invoice and tax else ''}
                {f'<div class="total-row"><span>ضريبة المنبع ({order.withholding_tax_rate or 0}%):</span><span style="color: #e74c3c;">-{withholding_tax:,.2f} ج.م</span></div>' if withholding_tax else ''}
                {f'<div class="total-row"><span>مصاريف الشحن:</span><span>{shipping_cost:,.2f} ج.م</span></div>' if shipping_cost else ''}
                <div class="total-row grand-total">
                    <span>الإجمالي:</span>
                    <span>{total:,.2f} ج.م</span>
                </div>
                {f'<div class="total-row"><span>المدفوع:</span><span>{paid:,.2f} ج.م</span></div>' if paid else ''}
                {f'<div class="total-row remaining"><span>المتبقي:</span><span>{remaining:,.2f} ج.م</span></div>' if remaining > 0 else ''}
            </div>
        </div>
        
        <!-- Signatures -->
        <div class="signatures">
            <div class="signature-box">
                <div class="signature-line">توقيع البائع</div>
            </div>
            <div class="signature-box">
                <div class="signature-line">توقيع المستلم</div>
            </div>
        </div>
        
        <!-- Footer -->
        <div class="footer">
            <div class="footer-text">{footer_text}</div>
            <div class="footer-note">
                تم إنشاء هذه الفاتورة بواسطة نظام Tony ERP - {datetime.now().strftime('%Y-%m-%d %H:%M')}
            </div>
        </div>
    </div>
</body>
</html>
'''
        return html
    
    def print_invoice(self, order, lines, settings=None, printer_name=None):
        """
        طباعة فاتورة A4
        
        Args:
            order: كائن الطلب
            lines: خطوط الطلب
            settings: إعدادات الفاتورة
            printer_name: اسم الطابعة
        """
        html = self._generate_invoice_html(order, lines, settings)
        
        # حفظ HTML مؤقتاً
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write(html)
            html_path = f.name
        
        try:
            # تحويل إلى PDF باستخدام WeasyPrint
            pdf_path = html_path.replace('.html', '.pdf')
            
            try:
                from weasyprint import HTML
                HTML(html_path).write_pdf(pdf_path)
            except ImportError:
                # إذا WeasyPrint غير متوفر، نطبع HTML مباشرة
                return self._print_html_direct(html_path, printer_name)
            except Exception as e:
                logger.error(f"خطأ WeasyPrint: {e}")
                # fallback to HTML printing
                return self._print_html_direct(html_path, printer_name)
            
            # طباعة PDF
            success = self._print_pdf(pdf_path, printer_name)
            
            # حذف الملفات المؤقتة
            try:
                os.unlink(pdf_path)
            except:
                pass
            
            return success
            
        finally:
            try:
                os.unlink(html_path)
            except:
                pass
    
    def _print_pdf(self, pdf_path, printer_name=None):
        """طباعة ملف PDF"""
        if not WIN32_AVAILABLE:
            return False
        
        printer = printer_name or self.printer_name or win32print.GetDefaultPrinter()
        
        try:
            # استخدام الأمر الافتراضي للطباعة
            win32api.ShellExecute(
                0,
                "print",
                pdf_path,
                f'/d:"{printer}"',
                ".",
                0
            )
            return True
        except Exception as e:
            logger.error(f"خطأ طباعة PDF: {e}")
            
            # محاولة بديلة باستخدام SumatraPDF أو Adobe Reader
            try:
                # محاولة مع SumatraPDF
                sumatra_paths = [
                    r"C:\Program Files\SumatraPDF\SumatraPDF.exe",
                    r"C:\Program Files (x86)\SumatraPDF\SumatraPDF.exe",
                ]
                for sumatra in sumatra_paths:
                    if os.path.exists(sumatra):
                        subprocess.run([
                            sumatra, 
                            "-print-to", printer,
                            "-silent",
                            pdf_path
                        ], check=True)
                        return True
            except:
                pass
            
            return False
    
    def _print_html_direct(self, html_path, printer_name=None):
        """طباعة HTML مباشرة عبر المتصفح"""
        try:
            import webbrowser
            # فتح HTML في المتصفح مع تنبيه للمستخدم للطباعة
            webbrowser.open(f'file:///{html_path.replace(os.sep, "/")}')
            return True
        except Exception as e:
            logger.error(f"خطأ: {e}")
            return False
    
    def print_with_notepad(self, html_path, printer_name=None):
        """طباعة باستخدام notepad (للنصوص)"""
        if not WIN32_AVAILABLE:
            return False
        try:
            printer = printer_name or self.printer_name or win32print.GetDefaultPrinter()
            # تحويل HTML لنص بسيط للطباعة
            subprocess.run([
                'notepad.exe', '/p', html_path
            ], check=True)
            return True
        except Exception as e:
            logger.error(f"خطأ: {e}")
            return False
    
    def print_with_browser(self, html_content, printer_name=None):
        """طباعة HTML عبر حفظ وفتح في المتصفح"""
        # حفظ HTML مع أوامر طباعة تلقائية
        html_with_print = html_content.replace(
            '</body>',
            '''<script>
                window.onload = function() {
                    window.print();
                };
            </script></body>'''
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write(html_with_print)
            html_path = f.name
        
        try:
            import webbrowser
            webbrowser.open(f'file:///{html_path.replace(os.sep, "/")}')
            return True
        except Exception as e:
            logger.error(f"خطأ: {e}")
            return False
    
    def get_invoice_html(self, order, lines, settings=None):
        """الحصول على HTML الفاتورة للعرض"""
        return self._generate_invoice_html(order, lines, settings)


def print_a4_invoice(order_id, printer_name=None, settings=None):
    """
    طباعة فاتورة A4
    
    Args:
        order_id: معرف الطلب
        printer_name: اسم الطابعة
        settings: إعدادات الفاتورة
    """
    from pos.models import POSOrder, POSOrderLine
    
    try:
        order = POSOrder.objects.get(id=order_id)
        lines = POSOrderLine.objects.filter(order=order).select_related('product')
        
        if settings is None:
            settings = {
                'shop_name': order.location.name if order.location else 'Tony ERP',
                'footer_text': 'شكراً لتعاملكم معنا',
            }
        
        printer = A4Printer(printer_name)
        success = printer.print_invoice(order, lines, settings, printer_name)
        
        return {
            'success': success,
            'order_number': order.number,
            'printer': printer_name or printer.get_default_printer()
        }
        
    except POSOrder.DoesNotExist:
        return {'success': False, 'error': 'الطلب غير موجود'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def get_invoice_preview(order_id, settings=None):
    """الحصول على HTML للمعاينة"""
    from pos.models import POSOrder, POSOrderLine
    
    try:
        order = POSOrder.objects.get(id=order_id)
        lines = POSOrderLine.objects.filter(order=order).select_related('product')
        
        if settings is None:
            settings = {
                'shop_name': order.location.name if order.location else 'Tony ERP',
                'footer_text': 'شكراً لتعاملكم معنا',
            }
        
        printer = A4Printer()
        html = printer.get_invoice_html(order, lines, settings)
        
        return {'success': True, 'html': html}
        
    except POSOrder.DoesNotExist:
        return {'success': False, 'error': 'الطلب غير موجود'}
    except Exception as e:
        return {'success': False, 'error': str(e)}
