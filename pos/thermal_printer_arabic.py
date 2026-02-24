# -*- coding: utf-8 -*-
"""
نظام الطباعة الحرارية بالعربية - طباعة كصورة
Arabic Thermal Printing System - Image-based printing for XPrinter
"""
import os
import io
import logging
import subprocess
import platform
from pathlib import Path

logger = logging.getLogger(__name__)

# تحديد نظام التشغيل
IS_LINUX = platform.system() == 'Linux'
IS_WINDOWS = platform.system() == 'Windows'

# استيراد المكتبات
try:
    from PIL import Image, ImageDraw, ImageFont
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    logger.warning("Pillow غير متوفر - استخدم: pip install Pillow")

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    ARABIC_SUPPORT = True
except ImportError:
    ARABIC_SUPPORT = False
    logger.warning("arabic-reshaper/python-bidi غير متوفر")

# Windows printing
try:
    import win32print
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

# Linux CUPS printing
CUPS_AVAILABLE = False
if IS_LINUX:
    try:
        result = subprocess.run(['lpstat', '-v'], capture_output=True, text=True)
        CUPS_AVAILABLE = result.returncode == 0
    except:
        pass


class ArabicThermalPrinter:
    """
    طابعة حرارية تدعم العربية عبر طباعة الصور
    تعمل مع جميع طابعات ESC/POS بما فيها XPrinter
    """
    
    # أوامر ESC/POS
    ESC = b'\x1b'
    GS = b'\x1d'
    INIT = b'\x1b@'
    CUT_PARTIAL = b'\x1dV\x01'
    CUT_FULL = b'\x1dV\x00'
    CASH_DRAWER = b'\x1bp\x00\x19\xfa'
    FEED_LINES = b'\n\n\n'
    
    def __init__(self, printer_name=None, paper_width=576):
        """
        تهيئة الطابعة
        
        Args:
            printer_name: اسم الطابعة (None = الافتراضية)
            paper_width: عرض الورق بالبكسل (576 لـ 80mm كامل، 384 لـ 58mm)
        """
        self.printer_name = printer_name
        self.paper_width = paper_width  # 576 pixels for 80mm (72mm printable × 8 dpi)
        self.handle = None
        self.font_path = self._find_arabic_font()
        
    def _find_arabic_font(self):
        """البحث عن خط عربي مناسب"""
        # قائمة الخطوط العربية المحتملة
        font_paths = [
            # خطوط Linux
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
            "/usr/share/fonts/truetype/fonts-arabeyes/ae_AlArabiya.ttf",
            "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
            # خطوط Windows
            "C:/Windows/Fonts/tahoma.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/calibri.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/times.ttf",
            # خطوط عربية محتملة
            "C:/Windows/Fonts/tradbdo.ttf",  # Traditional Arabic Bold
            "C:/Windows/Fonts/trado.ttf",    # Traditional Arabic
            "C:/Windows/Fonts/simpbdo.ttf",  # Simplified Arabic Bold
            "C:/Windows/Fonts/simpo.ttf",    # Simplified Arabic
        ]
        
        for path in font_paths:
            if os.path.exists(path):
                return path
        
        # استخدام الخط الافتراضي
        return None
    
    def get_available_printers(self):
        """الحصول على قائمة الطابعات"""
        printers = []
        
        # Linux - CUPS
        if IS_LINUX and CUPS_AVAILABLE:
            try:
                result = subprocess.run(['lpstat', '-a'], capture_output=True, text=True)
                if result.returncode == 0:
                    for line in result.stdout.strip().split('\n'):
                        if line:
                            name = line.split()[0]
                            printers.append({
                                'name': name,
                                'description': line,
                                'is_default': self._is_default_printer_linux(name)
                            })
            except Exception as e:
                logger.error(f"خطأ Linux: {e}")
        
        # Windows
        elif WIN32_AVAILABLE:
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
    
    def _is_default_printer_linux(self, printer_name):
        """التحقق من الطابعة الافتراضية في Linux"""
        try:
            result = subprocess.run(['lpstat', '-d'], capture_output=True, text=True)
            if result.returncode == 0:
                return printer_name in result.stdout
        except:
            pass
        return False
    
    def get_default_printer(self):
        """الطابعة الافتراضية"""
        # Linux
        if IS_LINUX and CUPS_AVAILABLE:
            try:
                result = subprocess.run(['lpstat', '-d'], capture_output=True, text=True)
                if result.returncode == 0 and 'system default destination:' in result.stdout:
                    return result.stdout.split(':')[-1].strip()
            except:
                pass
        # Windows
        elif WIN32_AVAILABLE:
            try:
                return win32print.GetDefaultPrinter()
            except:
                pass
        return None
    
    def _find_thermal_printer(self):
        """البحث عن طابعة حرارية XPrinter"""
        thermal_keywords = ['xp-80', 'xp80', 'xprinter', 'thermal', 'pos', 'receipt', 'حرارية']
        
        # Linux
        if IS_LINUX and CUPS_AVAILABLE:
            try:
                result = subprocess.run(['lpstat', '-a'], capture_output=True, text=True)
                if result.returncode == 0:
                    for line in result.stdout.strip().split('\n'):
                        if line:
                            name = line.split()[0].lower()
                            for keyword in thermal_keywords:
                                if keyword in name:
                                    logger.info(f"تم العثور على طابعة حرارية: {name}")
                                    return line.split()[0]
            except Exception as e:
                logger.error(f"خطأ Linux: {e}")
        
        # Windows
        elif WIN32_AVAILABLE:
            try:
                for printer in win32print.EnumPrinters(
                    win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
                ):
                    name = printer[2]
                    name_lower = name.lower()
                    for keyword in thermal_keywords:
                        if keyword in name_lower:
                            logger.info(f"تم العثور على طابعة حرارية: {name}")
                            return name
            except Exception as e:
                logger.error(f"خطأ في البحث عن الطابعة: {e}")
        return None
    
    def connect(self):
        """الاتصال بالطابعة"""
        # Linux - لا نحتاج اتصال مستمر مع CUPS
        if IS_LINUX and CUPS_AVAILABLE:
            if not self.printer_name:
                self.printer_name = self._find_thermal_printer()
            if not self.printer_name:
                self.printer_name = self.get_default_printer()
            if self.printer_name:
                logger.info(f"تم تحديد الطابعة: {self.printer_name}")
                return True
            else:
                logger.warning("لم يتم العثور على طابعة - سيتم حفظ الملف للطباعة اليدوية")
                return True  # نعيد True لأننا سنحفظ ملف PDF
        
        # Windows
        if not WIN32_AVAILABLE:
            return False
        try:
            # إذا لم يتم تحديد طابعة، ابحث عن طابعة XP-80 أولاً
            if not self.printer_name:
                self.printer_name = self._find_thermal_printer()
            
            # إذا لم نجد طابعة حرارية، استخدم الافتراضية
            if not self.printer_name:
                self.printer_name = win32print.GetDefaultPrinter()
            
            self.handle = win32print.OpenPrinter(self.printer_name)
            logger.info(f"تم الاتصال بالطابعة: {self.printer_name}")
            return True
        except Exception as e:
            logger.error(f"خطأ الاتصال: {e}")
            return False
    
    def disconnect(self):
        """إغلاق الاتصال"""
        if self.handle:
            try:
                win32print.ClosePrinter(self.handle)
            except:
                pass
            self.handle = None
    
    def _send_raw(self, data):
        """إرسال بيانات للطابعة"""
        # Linux - استخدام lp
        if IS_LINUX:
            return self._send_raw_linux(data)
        
        # Windows
        if not self.handle:
            return False
        try:
            job = win32print.StartDocPrinter(self.handle, 1, ("Receipt", "", "RAW"))
            win32print.StartPagePrinter(self.handle)
            win32print.WritePrinter(self.handle, data)
            win32print.EndPagePrinter(self.handle)
            win32print.EndDocPrinter(self.handle)
            return True
        except Exception as e:
            logger.error(f"خطأ الإرسال: {e}")
            return False
    
    def _send_raw_linux(self, data):
        """إرسال بيانات خام للطابعة في Linux"""
        import tempfile
        try:
            # حفظ البيانات في ملف مؤقت
            with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as f:
                f.write(data)
                temp_file = f.name
            
            # إرسال للطابعة عبر lp
            cmd = ['lp', '-d', self.printer_name, '-o', 'raw', temp_file]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # حذف الملف المؤقت
            os.unlink(temp_file)
            
            if result.returncode == 0:
                logger.info(f"تم إرسال البيانات للطابعة: {self.printer_name}")
                return True
            else:
                logger.error(f"خطأ lp: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"خطأ Linux raw: {e}")
            return False
    
    def _has_arabic(self, text):
        """هل يحتوي على حروف عربية"""
        for char in str(text):
            if '\u0600' <= char <= '\u06FF' or '\u0750' <= char <= '\u077F' or '\uFB50' <= char <= '\uFDFF' or '\uFE70' <= char <= '\uFEFF':
                return True
        return False
    
    def _reshape_arabic(self, text):
        """إعادة تشكيل النص العربي للعرض الصحيح"""
        # Pillow 12+ مع raqm/fribidi/harfbuzz يعالج العربية تلقائياً
        # لا نحتاج arabic_reshaper أو bidi يدوياً
        return text
    
    def _text_to_image(self, lines, font_size=20, bold_lines=None, center_lines=None, large_lines=None):
        """
        تحويل نص لصورة
        
        Args:
            lines: قائمة أسطر النص
            font_size: حجم الخط
            bold_lines: أرقام الأسطر العريضة
            center_lines: أرقام الأسطر في المنتصف
            large_lines: أرقام الأسطر الكبيرة
        """
        if not PILLOW_AVAILABLE:
            return None
        
        bold_lines = bold_lines or []
        center_lines = center_lines or []
        large_lines = large_lines or []
        
        # تحميل الخط
        try:
            font = ImageFont.truetype(self.font_path, font_size) if self.font_path else ImageFont.load_default()
            font_large = ImageFont.truetype(self.font_path, font_size + 8) if self.font_path else font
            font_bold = ImageFont.truetype(self.font_path, font_size + 2) if self.font_path else font
        except Exception:
            font = ImageFont.load_default()
            font_large = font
            font_bold = font
        
        # حساب ارتفاع الصورة
        line_height = font_size + 8
        large_height = font_size + 16
        total_height = sum(large_height if i in large_lines else line_height for i in range(len(lines)))
        total_height += 20  # padding
        
        # إنشاء الصورة
        img = Image.new('1', (self.paper_width, total_height), color=1)  # 1-bit أبيض
        draw = ImageDraw.Draw(img)
        
        y = 10
        for i, line in enumerate(lines):
            display_text = str(line)
            
            # تحديد اتجاه النص - RTL للعربية، LTR للإنجليزية والرموز
            is_arabic = self._has_arabic(display_text)
            text_dir = 'rtl' if is_arabic else 'ltr'
            
            # اختيار الخط
            if i in large_lines:
                current_font = font_large
                current_height = large_height
            elif i in bold_lines:
                current_font = font_bold
                current_height = line_height
            else:
                current_font = font
                current_height = line_height
            
            # حساب موضع X
            try:
                bbox = draw.textbbox((0, 0), display_text, font=current_font, direction=text_dir)
                text_width = bbox[2] - bbox[0]
            except:
                try:
                    bbox = draw.textbbox((0, 0), display_text, font=current_font)
                    text_width = bbox[2] - bbox[0]
                except:
                    text_width = len(display_text) * (font_size // 2)
            
            if i in center_lines:
                x = (self.paper_width - text_width) // 2
            else:
                # محاذاة يمين للعربية
                x = self.paper_width - text_width - 10
            
            # رسم النص مع اتجاه RTL للعربية
            try:
                draw.text((x, y), display_text, font=current_font, fill=0, direction=text_dir)
            except:
                draw.text((x, y), display_text, font=current_font, fill=0)
            y += current_height
        
        return img
    
    def _wrap_text(self, text, font, max_width, draw, direction='ltr'):
        """
        تقسيم النص لعدة أسطر حسب عرض العمود
        يرجع قائمة أسطر
        """
        if not text.strip():
            return [text]
        
        # قياس النص الكامل
        try:
            bbox = draw.textbbox((0, 0), text, font=font, direction=direction)
            full_width = bbox[2] - bbox[0]
        except:
            full_width = len(text) * 10
        
        if full_width <= max_width:
            return [text]
        
        # تقسيم بالكلمات
        words = text.split()
        if not words:
            return [text]
        
        lines = []
        current_line = ''
        
        for word in words:
            test_line = f"{current_line} {word}".strip() if current_line else word
            try:
                bbox = draw.textbbox((0, 0), test_line, font=font, direction=direction)
                tw = bbox[2] - bbox[0]
            except:
                tw = len(test_line) * 10
            
            if tw <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        
        return lines if lines else [text]
    
    def _table_to_image(self, headers, rows, font_size=20, col_widths=None, col_aligns=None):
        """
        رسم جدول منسق كصورة مع دعم التفاف النص
        
        Args:
            headers: قائمة عناوين الأعمدة (من اليمين لليسار)
            rows: قائمة صفوف البيانات (كل صف = قائمة قيم)
            font_size: حجم الخط
            col_widths: عرض كل عمود بالبكسل (None = توزيع تلقائي)
            col_aligns: محاذاة كل عمود 'right'/'center'/'left'
        """
        if not PILLOW_AVAILABLE:
            return None
        
        num_cols = len(headers)
        padding = 6
        
        # تحميل الخطوط
        try:
            font = ImageFont.truetype(self.font_path, font_size) if self.font_path else ImageFont.load_default()
            font_bold = ImageFont.truetype(self.font_path, font_size + 2) if self.font_path else font
        except Exception:
            font = ImageFont.load_default()
            font_bold = font
        
        # حساب عرض الأعمدة تلقائياً
        if col_widths is None:
            available = self.paper_width - 20
            product_col_width = int(available * 0.42)
            other_col_width = (available - product_col_width) // (num_cols - 1) if num_cols > 1 else available
            col_widths = [product_col_width] + [other_col_width] * (num_cols - 1)
        
        if col_aligns is None:
            col_aligns = ['right'] * num_cols
        
        single_line_h = font_size + 8
        header_height = font_size + 14
        
        # === حساب ارتفاع كل صف مع التفاف النص ===
        # نحتاج صورة مؤقتة للقياسات
        tmp_img = Image.new('1', (self.paper_width, 10), color=1)
        tmp_draw = ImageDraw.Draw(tmp_img)
        
        # حساب أسطر كل خلية وارتفاع كل صف
        row_wrapped = []  # لكل صف: قائمة [col0_lines, col1_lines, ...]
        row_heights = []
        
        for row in rows:
            cell_lines_list = []
            max_lines = 1
            for col_idx in range(num_cols):
                text = str(row[col_idx]) if col_idx < len(row) else ''
                is_ar = self._has_arabic(text)
                text_dir = 'rtl' if is_ar else 'ltr'
                usable_width = col_widths[col_idx] - (padding * 2)
                wrapped = self._wrap_text(text, font, usable_width, tmp_draw, text_dir)
                cell_lines_list.append(wrapped)
                if len(wrapped) > max_lines:
                    max_lines = len(wrapped)
            row_wrapped.append(cell_lines_list)
            row_heights.append(max_lines * single_line_h + 4)
        
        # حساب الارتفاع الكلي
        total_height = 7 + header_height + 6 + sum(row_heights) + (len(rows) - 1) * 1 + 6
        
        # إنشاء الصورة
        img = Image.new('1', (self.paper_width, total_height), color=1)
        draw = ImageDraw.Draw(img)
        
        y = 4
        
        # === خط أفقي علوي ===
        draw.line([(10, y), (self.paper_width - 10, y)], fill=0, width=1)
        y += 3
        
        # === رسم عناوين الأعمدة ===
        header_y = y
        x_pos = self.paper_width - 10
        col_x_positions = []  # حفظ مواضع الأعمدة
        
        for col_idx in range(num_cols):
            col_w = col_widths[col_idx]
            x_start = x_pos - col_w
            col_x_positions.append((x_start, x_pos))
            
            text = str(headers[col_idx])
            is_ar = self._has_arabic(text)
            text_dir = 'rtl' if is_ar else 'ltr'
            
            try:
                bbox = draw.textbbox((0, 0), text, font=font_bold, direction=text_dir)
                tw = bbox[2] - bbox[0]
            except:
                tw = len(text) * (font_size // 2)
            
            tx = x_start + (col_w - tw) // 2
            try:
                draw.text((tx, y), text, font=font_bold, fill=0, direction=text_dir)
            except:
                draw.text((tx, y), text, font=font_bold, fill=0)
            
            # خط عمودي للعنوان
            if col_idx > 0:
                draw.line([(x_pos, header_y - 3), (x_pos, header_y + header_height - 3)], fill=0, width=1)
            
            x_pos = x_start
        
        y += header_height - 3
        
        # === خط فاصل تحت العناوين ===
        draw.line([(10, y), (self.paper_width - 10, y)], fill=0, width=2)
        y += 4
        
        # === رسم صفوف البيانات مع التفاف ===
        for row_idx, (row, cell_lines_list) in enumerate(zip(rows, row_wrapped)):
            row_h = row_heights[row_idx]
            row_top = y
            
            x_pos = self.paper_width - 10
            for col_idx in range(num_cols):
                col_w = col_widths[col_idx]
                x_start = x_pos - col_w
                align = col_aligns[col_idx] if col_idx < len(col_aligns) else 'right'
                wrapped_lines = cell_lines_list[col_idx]
                
                # عدد أسطر هذه الخلية
                num_cell_lines = len(wrapped_lines)
                # توسيط عمودي إذا الخلية أقل أسطر من الصف
                total_text_h = num_cell_lines * single_line_h
                vert_offset = (row_h - total_text_h) // 2
                
                for line_idx, line_text in enumerate(wrapped_lines):
                    is_ar = self._has_arabic(line_text)
                    text_dir = 'rtl' if is_ar else 'ltr'
                    
                    try:
                        bbox = draw.textbbox((0, 0), line_text, font=font, direction=text_dir)
                        tw = bbox[2] - bbox[0]
                    except:
                        tw = len(line_text) * (font_size // 2)
                    
                    if align == 'center':
                        tx = x_start + (col_w - tw) // 2
                    elif align == 'left':
                        tx = x_start + padding
                    else:  # right
                        tx = x_start + col_w - tw - padding
                    
                    ty = row_top + vert_offset + (line_idx * single_line_h)
                    try:
                        draw.text((tx, ty), line_text, font=font, fill=0, direction=text_dir)
                    except:
                        draw.text((tx, ty), line_text, font=font, fill=0)
                
                # خط عمودي
                if col_idx > 0:
                    draw.line([(x_pos, row_top - 2), (x_pos, row_top + row_h - 2)], fill=0, width=1)
                
                x_pos = x_start
            
            y += row_h
            
            # خط فاصل بين الصفوف
            if row_idx < len(rows) - 1:
                draw.line([(10, y - 2), (self.paper_width - 10, y - 2)], fill=0, width=1)
        
        # === خط أفقي سفلي ===
        draw.line([(10, y - 1), (self.paper_width - 10, y - 1)], fill=0, width=1)
        
        return img
    
    def _image_to_escpos(self, img):
        """تحويل صورة لأوامر ESC/POS"""
        if img is None:
            return b''
        
        # تحويل لـ 1-bit
        img = img.convert('1')
        width, height = img.size
        
        # تأكد أن العرض قابل للقسمة على 8
        if width % 8 != 0:
            new_width = (width // 8 + 1) * 8
            new_img = Image.new('1', (new_width, height), color=1)
            new_img.paste(img, (0, 0))
            img = new_img
            width = new_width
        
        # تحويل لبايتات
        pixels = list(img.getdata())
        bytes_per_row = width // 8
        
        data = bytearray()
        
        # GS v 0 - طباعة صورة raster
        # Format: GS v 0 m xL xH yL yH [data]
        data.extend(b'\x1dv0\x00')  # GS v 0 m (m=0 normal)
        data.append(bytes_per_row & 0xFF)  # xL
        data.append((bytes_per_row >> 8) & 0xFF)  # xH
        data.append(height & 0xFF)  # yL
        data.append((height >> 8) & 0xFF)  # yH
        
        # بيانات الصورة
        for y in range(height):
            for x in range(0, width, 8):
                byte = 0
                for bit in range(8):
                    if x + bit < width:
                        pixel_index = y * width + x + bit
                        if pixel_index < len(pixels) and pixels[pixel_index] == 0:  # أسود
                            byte |= (0x80 >> bit)
                data.append(byte)
        
        return bytes(data)
    
    def print_receipt(self, order, lines, settings=None):
        """
        طباعة إيصال بالعربية كصورة مع اللوجو
        """
        # جلب بيانات الشركة من قاعدة البيانات
        company_name = 'Tony ERP'
        company_address = ''
        company_phone = ''
        company_vat = ''
        company_logo = None
        try:
            from core.models import Company
            company = Company.objects.first()
            if company:
                company_name = company.name or 'Tony ERP'
                company_address = company.address or ''
                company_phone = company.phone or ''
                company_vat = company.tax_id or ''
                # جلب اللوجو
                if company.logo:
                    try:
                        company_logo = company.logo.path
                    except:
                        pass
        except:
            pass
        
        # بيانات المعرض/الفرع
        branch_name = ''
        branch_phone = ''
        branch_address = ''
        showroom = None
        if order.location:
            branch_name = order.location.name
            # جلب بيانات المعرض الكاملة
            try:
                from showrooms.models import Showroom
                showroom = Showroom.objects.filter(location=order.location).first()
                if showroom:
                    branch_name = showroom.name_ar or showroom.name or order.location.name
                    branch_phone = showroom.contact_phone or ''
                    branch_address = showroom.address or ''
            except:
                pass
        
        if settings is None:
            settings = {
                'footer_text': 'شكراً لزيارتكم',
                'cut_paper': True,
                'open_drawer': False,
            }
        
        # === طباعة اللوجو أولاً إذا وجد ===
        logo_data = bytearray()
        if company_logo:
            try:
                logo_img = Image.open(company_logo)
                
                # حجم كبير للإيصال (600 بكسل عرض)
                target_width = 550
                ratio = target_width / logo_img.width
                new_height = int(logo_img.height * ratio)
                # حد أقصى للارتفاع
                if new_height > 350:
                    new_height = 350
                    ratio = new_height / logo_img.height
                    target_width = int(logo_img.width * ratio)
                
                logo_img = logo_img.resize((target_width, new_height), Image.Resampling.LANCZOS)
                
                # تحويل لـ RGBA ثم معالجة الشفافية
                if logo_img.mode == 'RGBA':
                    # إنشاء خلفية بيضاء
                    background = Image.new('RGB', logo_img.size, (255, 255, 255))
                    background.paste(logo_img, mask=logo_img.split()[3])
                    logo_img = background
                
                # تحويل لـ grayscale
                if logo_img.mode != 'L':
                    logo_img = logo_img.convert('L')
                
                # تحسين التباين - جعل الخلفية بيضاء تماماً والشعار واضح
                from PIL import ImageEnhance
                enhancer = ImageEnhance.Contrast(logo_img)
                logo_img = enhancer.enhance(1.5)
                
                # تحويل للأبيض والأسود مع threshold مناسب
                threshold = 200  # قيمة أعلى = خلفية أكثر بياضاً
                
                def threshold_func(pixel_value: int) -> int:
                    return 255 if pixel_value > threshold else 0
                
                logo_img = logo_img.point(threshold_func).convert('1')
                
                # إنشاء صورة بعرض كامل مع اللوجو في الوسط
                full_width = 576
                centered_logo = Image.new('1', (full_width, new_height + 10), 1)  # 1 = أبيض
                paste_x = (full_width - target_width) // 2
                centered_logo.paste(logo_img, (paste_x, 5))
                
                logo_data.extend(self._image_to_escpos(centered_logo))
                logo_data.extend(b'\n')  # سطر فارغ بعد اللوجو
            except Exception as e:
                logger.warning(f"فشل تحميل اللوجو: {e}")
        
        # بناء أسطر الإيصال
        receipt_lines = []
        bold_lines = []
        center_lines = []
        large_lines = []
        
        # === 1. بيانات الشركة ===
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
        
        # الرقم الضريبي فقط إذا كانت فاتورة ضريبية
        if order.is_tax_invoice and company_vat:
            receipt_lines.append(f"الرقم الضريبي: {company_vat}")
            center_lines.append(len(receipt_lines) - 1)
        
        receipt_lines.append('=' * 48)
        center_lines.append(len(receipt_lines) - 1)
        
        # === 2. بيانات المعرض/الفرع ===
        if branch_name:
            receipt_lines.append(f"الفرع: {branch_name}")
            center_lines.append(len(receipt_lines) - 1)
            bold_lines.append(len(receipt_lines) - 1)
            
            # عنوان الفرع
            if branch_address:
                receipt_lines.append(branch_address)
                center_lines.append(len(receipt_lines) - 1)
            
            # هاتف الفرع
            if branch_phone:
                receipt_lines.append(f"تليفون الفرع: {branch_phone}")
                center_lines.append(len(receipt_lines) - 1)
            
            receipt_lines.append('-' * 48)
            center_lines.append(len(receipt_lines) - 1)
        
        # === 3. نوع الفاتورة ===
        if order.is_tax_invoice:
            receipt_lines.append("*** فاتورة ضريبية ***")
            center_lines.append(len(receipt_lines) - 1)
            bold_lines.append(len(receipt_lines) - 1)
        
        # === 4. رقم الفاتورة ===
        receipt_lines.append(f"فاتورة رقم: {order.number}")
        bold_lines.append(len(receipt_lines) - 1)
        center_lines.append(len(receipt_lines) - 1)
        
        # التاريخ والوقت
        receipt_lines.append(f"التاريخ: {order.created_at.strftime('%Y-%m-%d')}  الوقت: {order.created_at.strftime('%H:%M')}")
        
        # الكاشير
        if hasattr(order, 'session') and order.session:
            cashier = order.session.user.first_name or order.session.user.username
            receipt_lines.append(f"الكاشير: {cashier}")
        
        # العميل
        if order.customer:
            receipt_lines.append(f"العميل: {order.customer}")
        
        receipt_lines.append('-' * 48)
        
        # === عناوين الأعمدة ===
        receipt_lines.append("المنتج                      الكمية    السعر    المجموع")
        bold_lines.append(len(receipt_lines) - 1)
        receipt_lines.append('-' * 48)
        
        # === المنتجات ===
        for line in lines:
            # اسم المنتج كامل (حتى 28 حرف)
            name = str(line.product.name)[:28]
            qty = str(int(line.quantity))
            price = f"{line.price:,.0f}"
            total = f"{line.total:,.0f}"
            
            # تنسيق السطر - عرض أوسع
            item_line = f"{name:<28} {qty:>3} {price:>8} {total:>8}"
            receipt_lines.append(item_line)
        
        receipt_lines.append('-' * 48)
        
        # === المجاميع ===
        subtotal = getattr(order, 'subtotal', order.total)
        receipt_lines.append(f"المجموع:                              {subtotal:,.0f}")
        
        if order.discount_amount and order.discount_amount > 0:
            receipt_lines.append(f"الخصم:                               -{order.discount_amount:,.0f}")
        
        # ضريبة القيمة المضافة (فقط للفواتير الضريبية)
        if order.is_tax_invoice and order.tax_amount and order.tax_amount > 0:
            vat_rate = order.vat_rate or 14
            receipt_lines.append(f"ضريبة القيمة المضافة ({vat_rate}%):          {order.tax_amount:,.0f}")
        
        # ضريبة المنبع
        if order.withholding_tax_amount and order.withholding_tax_amount > 0:
            rate = order.withholding_tax_rate or 0
            receipt_lines.append(f"ضريبة المنبع ({rate}%):               -{order.withholding_tax_amount:,.0f}")
        
        # مصاريف الشحن
        if order.shipping_cost and order.shipping_cost > 0:
            receipt_lines.append(f"مصاريف الشحن:                         {order.shipping_cost:,.0f}")
        
        receipt_lines.append('=' * 48)
        
        # الإجمالي
        receipt_lines.append(f"الإجمالي:                         {order.total:,.0f} ج.م")
        bold_lines.append(len(receipt_lines) - 1)
        large_lines.append(len(receipt_lines) - 1)
        
        receipt_lines.append('=' * 48)
        
        # المدفوع
        if order.paid_amount:
            receipt_lines.append(f"المدفوع:                              {order.paid_amount:,.0f}")
            change = float(order.paid_amount) - float(order.total)
            if change > 0:
                receipt_lines.append(f"الباقي:                               {change:,.0f}")
        
        # التذييل
        receipt_lines.append('')
        receipt_lines.append('-' * 48)
        center_lines.append(len(receipt_lines) - 1)
        
        footer = settings.get('footer_text', 'شكراً لزيارتكم')
        receipt_lines.append(footer)
        center_lines.append(len(receipt_lines) - 1)
        bold_lines.append(len(receipt_lines) - 1)
        
        # معلومات التواصل - كل معلومة في سطر منفصل
        if company:
            receipt_lines.append('')
            
            # الهاتف
            if hasattr(company, 'phone') and company.phone:
                receipt_lines.append(f"هاتف: {company.phone}")
                center_lines.append(len(receipt_lines) - 1)
            
            # الموبايل
            if hasattr(company, 'mobile') and company.mobile:
                receipt_lines.append(f"موبايل: {company.mobile}")
                center_lines.append(len(receipt_lines) - 1)
            
            # واتساب
            if hasattr(company, 'whatsapp') and company.whatsapp:
                receipt_lines.append(f"واتساب: {company.whatsapp}")
                center_lines.append(len(receipt_lines) - 1)
            
            # البريد الإلكتروني
            if hasattr(company, 'email') and company.email:
                receipt_lines.append(f"إيميل: {company.email}")
                center_lines.append(len(receipt_lines) - 1)
            
            # الموقع
            if hasattr(company, 'website') and company.website:
                receipt_lines.append(f"الموقع: {company.website}")
                center_lines.append(len(receipt_lines) - 1)
            
            # مواقع التواصل الاجتماعي
            social_info = []
            if hasattr(company, 'facebook') and company.facebook:
                social_info.append("Facebook")
            if hasattr(company, 'instagram') and company.instagram:
                social_info.append("Instagram")
            if hasattr(company, 'tiktok') and company.tiktok:
                social_info.append("TikTok")
            if social_info:
                receipt_lines.append('')
                receipt_lines.append('تابعونا على: ' + ' - '.join(social_info))
                center_lines.append(len(receipt_lines) - 1)
                center_lines.append(len(receipt_lines) - 1)
        
        # === جميع فروع الشركة ===
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
                    
                    # البلد والمحافظة
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
                    
                    # العنوان
                    if branch.address:
                        receipt_lines.append(branch.address)
                        center_lines.append(len(receipt_lines) - 1)
                    
                    # الهاتف
                    if branch.contact_phone:
                        receipt_lines.append(f"تليفون: {branch.contact_phone}")
                        center_lines.append(len(receipt_lines) - 1)
                    
                    receipt_lines.append('-' * 32)
                    center_lines.append(len(receipt_lines) - 1)
        except Exception as e:
            pass  # تجاهل الأخطاء
        
        receipt_lines.append('')
        receipt_lines.append('- - - - - - - - - - - - -')
        center_lines.append(len(receipt_lines) - 1)
        
        # === تحويل لصورة ===
        img = self._text_to_image(
            receipt_lines,
            font_size=22,  # حجم خط أكبر لملء العرض
            bold_lines=bold_lines,
            center_lines=center_lines,
            large_lines=large_lines
        )
        
        if img is None:
            logger.error("فشل إنشاء الصورة")
            return False
        
        # === إرسال للطابعة ===
        data = bytearray()
        data.extend(self.INIT)
        
        # إضافة اللوجو إذا وجد
        if logo_data:
            data.extend(logo_data)
        
        data.extend(self._image_to_escpos(img))
        data.extend(self.FEED_LINES)
        
        if settings.get('open_drawer'):
            data.extend(self.CASH_DRAWER)
        
        if settings.get('cut_paper', True):
            data.extend(self.CUT_PARTIAL)
        
        return self._send_raw(bytes(data))
    
    def print_test(self):
        """طباعة اختبارية"""
        lines = [
            "=========== اختبار الطباعة ===========",
            "",
            "Tony ERP System - نظام إدارة الأعمال",
            "",
            "الطابعة تعمل بشكل صحيح",
            "تدعم اللغة العربية",
            "",
            "1234567890",
            "- - - - - - - - -",
        ]
        
        img = self._text_to_image(
            lines,
            font_size=20,
            bold_lines=[0, 2],
            center_lines=[0, 2, 3, 5, 6]
        )
        
        if img is None:
            return False
        
        data = bytearray()
        data.extend(self.INIT)
        data.extend(self._image_to_escpos(img))
        data.extend(self.FEED_LINES)
        data.extend(self.CUT_PARTIAL)
        
        return self._send_raw(bytes(data))
    
    def open_cash_drawer(self):
        """فتح درج النقود"""
        return self._send_raw(self.INIT + self.CASH_DRAWER)


def print_arabic_receipt(order_id, printer_name=None, open_drawer=False):
    """
    طباعة فاتورة بالعربية
    """
    from pos.models import POSOrder, POSOrderLine
    
    try:
        order = POSOrder.objects.get(id=order_id)
        lines = POSOrderLine.objects.filter(order=order)
        
        printer = ArabicThermalPrinter(printer_name)
        
        if not printer.connect():
            # في Linux بدون طابعة، لا نعيد خطأ - فقط تحذير
            if IS_LINUX and not printer.printer_name:
                logger.warning("لا توجد طابعة حرارية - يرجى الطباعة من المتصفح")
                return {
                    'success': False, 
                    'error': 'لا توجد طابعة حرارية متصلة. استخدم زر الطباعة في صفحة الإيصال.',
                    'fallback': 'browser'
                }
            return {'success': False, 'error': 'فشل الاتصال بالطابعة'}
        
        try:
            settings = {
                'shop_name': order.location.name if order.location else 'Tony ERP',
                'footer_text': 'شكراً لزيارتكم',
                'cut_paper': True,
                'open_drawer': open_drawer,
            }
            
            success = printer.print_receipt(order, lines, settings)
            
            if success:
                return {
                    'success': True,
                    'order_number': order.number,
                    'printer': printer.printer_name
                }
            else:
                return {
                    'success': False,
                    'error': 'فشلت الطباعة - تأكد من توصيل الطابعة',
                    'fallback': 'browser'
                }
        finally:
            printer.disconnect()
            
    except POSOrder.DoesNotExist:
        return {'success': False, 'error': 'الطلب غير موجود'}
    except Exception as e:
        logger.error(f"خطأ طباعة: {e}")
        return {'success': False, 'error': str(e)}
