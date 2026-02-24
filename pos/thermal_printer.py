# -*- coding: utf-8 -*-
"""
نظام الطباعة الحرارية المباشرة - XPrinter
Direct Thermal Printing System for XPrinter and ESC/POS printers
يدعم: Windows (win32print) و Linux (CUPS)
"""
import os
import sys
import logging
import subprocess
import tempfile
import platform

logger = logging.getLogger(__name__)

# تحديد نظام التشغيل
IS_LINUX = platform.system() == 'Linux'
IS_WINDOWS = platform.system() == 'Windows'

# محاولة استيراد المكتبات
WIN32_AVAILABLE = False
if IS_WINDOWS:
    try:
        import win32print
        import win32ui
        WIN32_AVAILABLE = True
    except ImportError:
        logger.warning("win32print غير متوفر - استخدم: pip install pywin32")

# التحقق من وجود CUPS على Linux
CUPS_AVAILABLE = False
if IS_LINUX:
    try:
        result = subprocess.run(['which', 'lp'], capture_output=True, text=True)
        CUPS_AVAILABLE = result.returncode == 0
        if CUPS_AVAILABLE:
            logger.info("CUPS متوفر للطباعة على Linux")
    except Exception:
        pass

try:
    from escpos.printer import Usb, Network, Serial
    if IS_WINDOWS:
        from escpos.printer import Win32Raw
    ESCPOS_AVAILABLE = True
except ImportError:
    ESCPOS_AVAILABLE = False
    logger.warning("python-escpos غير متوفر - استخدم: pip install python-escpos")


class ThermalPrinter:
    """
    فئة الطباعة الحرارية المباشرة
    تدعم: XPrinter, Epson, Star, Bixolon وغيرها من طابعات ESC/POS
    """
    
    # أوامر ESC/POS الأساسية
    ESC = b'\x1b'
    GS = b'\x1d'
    
    # تهيئة الطابعة
    INIT = ESC + b'@'
    
    # محاذاة النص
    ALIGN_LEFT = ESC + b'a\x00'
    ALIGN_CENTER = ESC + b'a\x01'
    ALIGN_RIGHT = ESC + b'a\x02'
    
    # حجم الخط
    TEXT_NORMAL = GS + b'!\x00'
    TEXT_DOUBLE_HEIGHT = GS + b'!\x01'
    TEXT_DOUBLE_WIDTH = GS + b'!\x10'
    TEXT_DOUBLE = GS + b'!\x11'  # عرض وارتفاع مضاعف
    
    # تنسيق النص
    BOLD_ON = ESC + b'E\x01'
    BOLD_OFF = ESC + b'E\x00'
    UNDERLINE_ON = ESC + b'-\x01'
    UNDERLINE_OFF = ESC + b'-\x00'
    
    # قص الورق
    CUT_FULL = GS + b'V\x00'
    CUT_PARTIAL = GS + b'V\x01'
    
    # فتح درج النقود
    CASH_DRAWER = ESC + b'p\x00\x19\xfa'
    
    # تغذية الورق
    FEED_LINE = b'\n'
    FEED_3_LINES = b'\n\n\n'
    
    # صفحة الأكواد للعربية
    ARABIC_CODEPAGE = ESC + b't\x16'  # Windows-1256 (codepage 22)
    ARABIC_720 = ESC + b't\x1b'  # Arabic 720 (codepage 27)
    
    # تفعيل UTF-8 للطابعات الحديثة
    UTF8_MODE = ESC + b't\xff'  # UTF-8 mode
    
    # أمر تحديد مجموعة الأحرف الدولية (العربية)
    CHARSET_ARABIC = ESC + b'R\x08'  # Arabic character set
    
    # أوامر إضافية لـ XPrinter
    XPRINTER_UTF8 = b'\x1c\x26'  # FS & - تفعيل وضع الـ Kanji/UTF
    XPRINTER_STANDARD = b'\x1c\x2e'  # FS . - إلغاء وضع Kanji
    
    def __init__(self, printer_name=None, connection_type=None, use_utf8=True):
        """
        تهيئة الطابعة
        
        Args:
            printer_name: اسم الطابعة (None = الطابعة الافتراضية)
            connection_type: نوع الاتصال ('windows', 'linux', 'cups', 'usb', 'network', 'serial')
            use_utf8: استخدام UTF-8 (للطابعات الحديثة)
        """
        self.printer_name = printer_name
        # تحديد نوع الاتصال تلقائياً حسب نظام التشغيل
        if connection_type is None:
            if IS_LINUX:
                self.connection_type = 'cups'
            else:
                self.connection_type = 'windows'
        else:
            self.connection_type = connection_type
        self.use_utf8 = use_utf8
        self.printer = None
        self.handle = None
        
    def get_available_printers(self):
        """الحصول على قائمة الطابعات المتاحة"""
        printers = []
        
        # Linux - CUPS
        if IS_LINUX and CUPS_AVAILABLE:
            try:
                result = subprocess.run(['lpstat', '-p'], capture_output=True, text=True)
                if result.returncode == 0:
                    for line in result.stdout.strip().split('\n'):
                        if line.startswith('printer '):
                            parts = line.split()
                            if len(parts) >= 2:
                                name = parts[1]
                                printers.append({
                                    'name': name,
                                    'description': ' '.join(parts[2:]) if len(parts) > 2 else name,
                                    'is_default': False
                                })
                # التحقق من الطابعة الافتراضية
                default_result = subprocess.run(['lpstat', '-d'], capture_output=True, text=True)
                if default_result.returncode == 0 and 'destination:' in default_result.stdout:
                    default_printer = default_result.stdout.split('destination:')[-1].strip()
                    for p in printers:
                        if p['name'] == default_printer:
                            p['is_default'] = True
            except Exception as e:
                logger.error(f"خطأ في الحصول على طابعات CUPS: {e}")
        
        # Windows
        elif WIN32_AVAILABLE:
            try:
                for printer in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS):
                    printers.append({
                        'name': printer[2],
                        'description': printer[1],
                        'is_default': printer[2] == win32print.GetDefaultPrinter()
                    })
            except Exception as e:
                logger.error(f"خطأ في الحصول على الطابعات: {e}")
        return printers
    
    def get_default_printer(self):
        """الحصول على الطابعة الافتراضية"""
        # Linux - CUPS
        if IS_LINUX and CUPS_AVAILABLE:
            try:
                result = subprocess.run(['lpstat', '-d'], capture_output=True, text=True)
                if result.returncode == 0 and 'destination:' in result.stdout:
                    return result.stdout.split('destination:')[-1].strip()
            except Exception:
                pass
        # Windows
        elif WIN32_AVAILABLE:
            try:
                return win32print.GetDefaultPrinter()
            except Exception:
                pass
        return None
    
    def connect(self):
        """الاتصال بالطابعة"""
        try:
            if self.connection_type in ('cups', 'linux'):
                return self._connect_cups()
            elif self.connection_type == 'windows':
                return self._connect_windows()
            elif self.connection_type == 'usb' and ESCPOS_AVAILABLE:
                return self._connect_usb()
            elif self.connection_type == 'network' and ESCPOS_AVAILABLE:
                return self._connect_network()
            else:
                # تحديد تلقائي حسب النظام
                if IS_LINUX:
                    return self._connect_cups()
                return self._connect_windows()
        except Exception as e:
            logger.error(f"خطأ في الاتصال بالطابعة: {e}")
            return False
    
    def _connect_cups(self):
        """الاتصال عبر CUPS على Linux"""
        if not CUPS_AVAILABLE:
            logger.error("CUPS غير متوفر - قم بتثبيته: apt install cups")
            return False
        
        try:
            # التحقق من وجود الطابعة
            if self.printer_name:
                result = subprocess.run(['lpstat', '-p', self.printer_name], capture_output=True, text=True)
                if result.returncode != 0:
                    logger.error(f"الطابعة {self.printer_name} غير موجودة")
                    return False
            else:
                # استخدام الطابعة الافتراضية
                self.printer_name = self.get_default_printer()
            
            self.handle = 'cups'  # علامة أن الاتصال عبر CUPS
            return True
        except Exception as e:
            logger.error(f"خطأ في اتصال CUPS: {e}")
            return False
    
    def _connect_windows(self):
        """الاتصال عبر Windows Raw Printing"""
        if not WIN32_AVAILABLE:
            logger.error("pywin32 غير مثبت")
            return False
        
        try:
            printer_name = self.printer_name or win32print.GetDefaultPrinter()
            self.handle = win32print.OpenPrinter(printer_name)
            self.printer_name = printer_name
            return True
        except Exception as e:
            logger.error(f"خطأ في فتح الطابعة: {e}")
            return False
    
    def _connect_usb(self):
        """الاتصال عبر USB مباشرة"""
        try:
            # XPrinter USB IDs الشائعة
            # يمكن تعديلها حسب موديل الطابعة
            usb_ids = [
                (0x0483, 0x5743),  # XPrinter
                (0x0416, 0x5011),  # XPrinter XP-58
                (0x04b8, 0x0202),  # Epson TM-T88
                (0x0519, 0x0001),  # Star
            ]
            
            for vendor_id, product_id in usb_ids:
                try:
                    self.printer = Usb(vendor_id, product_id)
                    return True
                except Exception:
                    continue
            
            logger.error("لم يتم العثور على طابعة USB")
            return False
        except Exception as e:
            logger.error(f"خطأ في اتصال USB: {e}")
            return False
    
    def _connect_network(self, ip='192.168.1.100', port=9100):
        """الاتصال عبر الشبكة"""
        try:
            self.printer = Network(ip, port)
            return True
        except Exception as e:
            logger.error(f"خطأ في اتصال الشبكة: {e}")
            return False
    
    def disconnect(self):
        """إغلاق الاتصال"""
        try:
            if self.handle == 'cups':
                # CUPS لا يحتاج إغلاق صريح
                self.handle = None
            elif self.handle and WIN32_AVAILABLE:
                win32print.ClosePrinter(self.handle)
                self.handle = None
            if self.printer:
                self.printer.close()
                self.printer = None
        except Exception as e:
            logger.error(f"خطأ في إغلاق الطابعة: {e}")
    
    def _send_raw(self, data):
        """إرسال بيانات خام للطابعة"""
        if isinstance(data, str):
            data = data.encode('cp1256', errors='replace')
        
        # الطباعة عبر CUPS على Linux
        if self.handle == 'cups' and IS_LINUX:
            return self._send_raw_cups(data)
        
        # Windows
        if self.handle and WIN32_AVAILABLE:
            try:
                job = win32print.StartDocPrinter(self.handle, 1, ("POS Receipt", "", "RAW"))
                win32print.StartPagePrinter(self.handle)
                win32print.WritePrinter(self.handle, data)
                win32print.EndPagePrinter(self.handle)
                win32print.EndDocPrinter(self.handle)
                return True
            except Exception as e:
                logger.error(f"خطأ في الإرسال: {e}")
                return False
        elif self.printer:
            try:
                self.printer._raw(data)
                return True
            except Exception as e:
                logger.error(f"خطأ في الإرسال: {e}")
                return False
        return False
    
    def _send_raw_cups(self, data):
        """إرسال بيانات خام عبر CUPS"""
        try:
            # إنشاء ملف مؤقت للبيانات
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.raw', delete=False) as f:
                f.write(data)
                temp_file = f.name
            
            # إرسال للطابعة عبر lp
            cmd = ['lp', '-o', 'raw']
            if self.printer_name:
                cmd.extend(['-d', self.printer_name])
            cmd.append(temp_file)
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # حذف الملف المؤقت
            try:
                os.unlink(temp_file)
            except:
                pass
            
            if result.returncode == 0:
                logger.info(f"تم الإرسال للطابعة بنجاح: {result.stdout}")
                return True
            else:
                logger.error(f"فشل الطباعة: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"خطأ في إرسال CUPS: {e}")
            return False
    
    def print_receipt(self, order, lines, settings=None):
        """
        طباعة إيصال كامل
        
        Args:
            order: كائن الطلب POSOrder
            lines: خطوط الطلب
            settings: إعدادات الطباعة (اختياري)
        """
        if settings is None:
            settings = {
                'shop_name': 'Tony ERP',
                'header_text': '',
                'footer_text': 'شكراً لزيارتكم',
                'show_tax': True,
                'cut_paper': True,
                'open_drawer': False,
                'paper_width': 48,  # عدد الأحرف في السطر (80mm = 48, 58mm = 32)
            }
        
        width = settings.get('paper_width', 48)
        
        # بناء الإيصال
        receipt_data = bytearray()
        
        # تهيئة الطابعة
        receipt_data.extend(self.INIT)
        
        # تفعيل وضع UTF-8 للعربية
        if self.use_utf8:
            # تجربة عدة أوامر لدعم UTF-8 في XPrinter
            # 1. ESC t 0 - تعيين codepage 0 (PC437)
            receipt_data.extend(b'\x1b\x74\x00')
            # 2. FS & - تفعيل وضع الأحرف الصينية/اليونيكود  
            receipt_data.extend(b'\x1c\x26')
            # 3. ESC R 0 - تعيين مجموعة الأحرف الدولية
            receipt_data.extend(b'\x1b\x52\x00')
        else:
            receipt_data.extend(self.ARABIC_CODEPAGE)
        
        # --- الرأس ---
        receipt_data.extend(self.ALIGN_CENTER)
        receipt_data.extend(self.TEXT_DOUBLE)
        receipt_data.extend(self._encode(settings.get('shop_name', 'Tony ERP')))
        receipt_data.extend(b'\n')
        receipt_data.extend(self.TEXT_NORMAL)
        
        if settings.get('header_text'):
            receipt_data.extend(self._encode(settings['header_text']))
            receipt_data.extend(b'\n')
        
        # خط فاصل
        receipt_data.extend(self._encode('=' * width))
        receipt_data.extend(b'\n')
        
        # رقم الفاتورة
        receipt_data.extend(self.BOLD_ON)
        receipt_data.extend(self._encode(f"فاتورة رقم: {order.number}"))
        receipt_data.extend(b'\n')
        receipt_data.extend(self.BOLD_OFF)
        
        # معلومات الفاتورة
        receipt_data.extend(self.ALIGN_RIGHT)
        receipt_data.extend(self._encode(f"التاريخ: {order.created_at.strftime('%Y-%m-%d %H:%M')}"))
        receipt_data.extend(b'\n')
        
        if hasattr(order, 'session') and order.session:
            cashier = order.session.user.first_name or order.session.user.username
            receipt_data.extend(self._encode(f"الكاشير: {cashier}"))
            receipt_data.extend(b'\n')
        
        if order.customer:
            receipt_data.extend(self._encode(f"العميل: {order.customer}"))
            receipt_data.extend(b'\n')
        
        # خط فاصل
        receipt_data.extend(self._encode('-' * width))
        receipt_data.extend(b'\n')
        
        # --- عناوين الأعمدة ---
        header = self._format_item_line("المنتج", "الكمية", "السعر", "المجموع", width)
        receipt_data.extend(self.BOLD_ON)
        receipt_data.extend(self._encode(header))
        receipt_data.extend(b'\n')
        receipt_data.extend(self.BOLD_OFF)
        receipt_data.extend(self._encode('-' * width))
        receipt_data.extend(b'\n')
        
        # --- المنتجات ---
        for line in lines:
            product_name = line.product.name[:15] if len(line.product.name) > 15 else line.product.name
            qty = str(int(line.quantity))
            price = f"{line.price:,.0f}"
            total = f"{line.total:,.0f}"
            
            item_line = self._format_item_line(product_name, qty, price, total, width)
            receipt_data.extend(self._encode(item_line))
            receipt_data.extend(b'\n')
        
        # خط فاصل
        receipt_data.extend(self._encode('-' * width))
        receipt_data.extend(b'\n')
        
        # --- المجاميع ---
        receipt_data.extend(self.ALIGN_RIGHT)
        
        # المجموع الفرعي
        subtotal = getattr(order, 'subtotal', order.total)
        receipt_data.extend(self._encode(self._format_total_line("المجموع:", f"{subtotal:,.0f}", width)))
        receipt_data.extend(b'\n')
        
        # الخصم
        if order.discount_amount and order.discount_amount > 0:
            receipt_data.extend(self._encode(self._format_total_line("الخصم:", f"-{order.discount_amount:,.0f}", width)))
            receipt_data.extend(b'\n')
        
        # الضريبة
        if settings.get('show_tax') and order.tax_amount and order.tax_amount > 0:
            receipt_data.extend(self._encode(self._format_total_line("الضريبة:", f"{order.tax_amount:,.0f}", width)))
            receipt_data.extend(b'\n')
        
        # الإجمالي
        receipt_data.extend(self._encode('=' * width))
        receipt_data.extend(b'\n')
        receipt_data.extend(self.TEXT_DOUBLE)
        receipt_data.extend(self.BOLD_ON)
        receipt_data.extend(self._encode(self._format_total_line("الإجمالي:", f"{order.total:,.0f} ر.س", width)))
        receipt_data.extend(b'\n')
        receipt_data.extend(self.TEXT_NORMAL)
        receipt_data.extend(self.BOLD_OFF)
        receipt_data.extend(self._encode('=' * width))
        receipt_data.extend(b'\n')
        
        # المدفوع والباقي
        if order.paid_amount:
            receipt_data.extend(self._encode(self._format_total_line("المدفوع:", f"{order.paid_amount:,.0f}", width)))
            receipt_data.extend(b'\n')
            
            change = order.paid_amount - order.total
            if change > 0:
                receipt_data.extend(self._encode(self._format_total_line("الباقي:", f"{change:,.0f}", width)))
                receipt_data.extend(b'\n')
        
        # --- التذييل ---
        receipt_data.extend(b'\n')
        receipt_data.extend(self.ALIGN_CENTER)
        
        if settings.get('footer_text'):
            receipt_data.extend(self._encode(settings['footer_text']))
            receipt_data.extend(b'\n')
        
        receipt_data.extend(b'\n\n\n')
        
        # فتح درج النقود
        if settings.get('open_drawer'):
            receipt_data.extend(self.CASH_DRAWER)
        
        # قص الورق
        if settings.get('cut_paper'):
            receipt_data.extend(self.CUT_PARTIAL)
        
        # إرسال للطابعة
        return self._send_raw(bytes(receipt_data))
    
    def _encode(self, text):
        """تحويل النص للترميز المناسب - UTF-8 للعربية"""
        if isinstance(text, bytes):
            return text
        # استخدام UTF-8 للعربية - معظم طابعات XPrinter الحديثة تدعمه
        if self.use_utf8:
            return text.encode('utf-8', errors='replace')
        return text.encode('cp1256', errors='replace')
    
    def _format_item_line(self, name, qty, price, total, width):
        """تنسيق سطر منتج"""
        # تقسيم العرض: اسم المنتج (40%) | الكمية (15%) | السعر (20%) | المجموع (25%)
        name_width = int(width * 0.40)
        qty_width = int(width * 0.15)
        price_width = int(width * 0.20)
        total_width = width - name_width - qty_width - price_width
        
        name = name[:name_width].ljust(name_width)
        qty = qty.center(qty_width)
        price = price.rjust(price_width)
        total = total.rjust(total_width)
        
        return f"{name}{qty}{price}{total}"
    
    def _format_total_line(self, label, value, width):
        """تنسيق سطر مجموع"""
        label_width = int(width * 0.6)
        value_width = width - label_width
        return f"{label.ljust(label_width)}{value.rjust(value_width)}"
    
    def print_text(self, text, bold=False, double=False, align='right', cut=False):
        """طباعة نص بسيط"""
        data = bytearray()
        data.extend(self.INIT)
        
        # تفعيل UTF-8 للعربية
        if self.use_utf8:
            # FS & - تفعيل وضع الأحرف الصينية/اليونيكود  
            data.extend(b'\x1c\x26')
            data.extend(b'\x1b\x74\x00')
        else:
            data.extend(self.ARABIC_CODEPAGE)
        
        # المحاذاة
        if align == 'center':
            data.extend(self.ALIGN_CENTER)
        elif align == 'left':
            data.extend(self.ALIGN_LEFT)
        else:
            data.extend(self.ALIGN_RIGHT)
        
        # الحجم
        if double:
            data.extend(self.TEXT_DOUBLE)
        else:
            data.extend(self.TEXT_NORMAL)
        
        # Bold
        if bold:
            data.extend(self.BOLD_ON)
        
        # النص
        data.extend(self._encode(text))
        data.extend(b'\n\n\n')
        
        # القص
        if cut:
            data.extend(self.CUT_PARTIAL)
        
        return self._send_raw(bytes(data))
    
    def open_cash_drawer(self):
        """فتح درج النقود"""
        data = self.INIT + self.CASH_DRAWER
        return self._send_raw(data)
    
    def cut_paper(self):
        """قص الورق"""
        data = self.FEED_3_LINES + self.CUT_PARTIAL
        return self._send_raw(data)
    
    def test_print(self):
        """طباعة اختبارية"""
        return self.print_text(
            "*** اختبار الطباعة ***\nTony ERP System\nالطابعة تعمل بشكل صحيح",
            bold=True,
            align='center',
            cut=True
        )


def print_pos_order(order_id, printer_name=None, open_drawer=False):
    """
    دالة مساعدة لطباعة طلب POS
    
    Args:
        order_id: معرف الطلب
        printer_name: اسم الطابعة (None = الافتراضية)
        open_drawer: فتح درج النقود
    
    Returns:
        dict: نتيجة الطباعة
    """
    from pos.models import POSOrder, POSOrderLine
    
    try:
        order = POSOrder.objects.get(id=order_id)
        lines = POSOrderLine.objects.filter(order=order)
        
        printer = ThermalPrinter(printer_name)
        
        if not printer.connect():
            return {'success': False, 'error': 'فشل الاتصال بالطابعة'}
        
        try:
            settings = {
                'shop_name': order.location.name if order.location else 'Tony ERP',
                'footer_text': 'شكراً لزيارتكم',
                'show_tax': True,
                'cut_paper': True,
                'open_drawer': open_drawer,
                'paper_width': 48,
            }
            
            success = printer.print_receipt(order, lines, settings)
            
            return {
                'success': success,
                'order_number': order.number,
                'printer': printer.printer_name
            }
        finally:
            printer.disconnect()
            
    except POSOrder.DoesNotExist:
        return {'success': False, 'error': 'الطلب غير موجود'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def get_printers():
    """الحصول على قائمة الطابعات المتاحة"""
    printer = ThermalPrinter()
    return printer.get_available_printers()

def print_receipt_direct(order, lines, printer_name=None, open_drawer=False):
    """
    طباعة الإيصال مباشرة على الطابعة الحرارية
    
    Args:
        order: كائن الطلب POSOrder
        lines: بنود الطلب QuerySet
        printer_name: اسم الطابعة (None = الافتراضية)
        open_drawer: فتح درج النقود
    
    Returns:
        dict: نتيجة الطباعة
    """
    try:
        printer = ThermalPrinter(printer_name)
        
        if not printer.connect():
            return {'success': False, 'error': 'فشل الاتصال بالطابعة'}
        
        try:
            settings = {
                'shop_name': order.location.name if order.location else 'Tony ERP',
                'footer_text': 'شكراً لزيارتكم - نتمنى لكم يوماً سعيداً',
                'show_tax': False,
                'cut_paper': True,
                'open_drawer': open_drawer,
                'paper_width': 48,
            }
            
            success = printer.print_receipt(order, lines, settings)
            
            return {
                'success': success,
                'order_number': getattr(order, 'number', str(order.id)),
                'printer_name': printer.printer_name or 'default'
            }
        finally:
            printer.disconnect()
            
    except Exception as e:
        logger.error(f"Print error: {e}")
        return {'success': False, 'error': str(e)}