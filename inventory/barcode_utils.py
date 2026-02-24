"""
أدوات الباركود - نظام الباركود المتكامل
مكتبة شاملة لتوليد وإدارة باركود المنتجات
"""

import barcode
from barcode.writer import ImageWriter
from PIL import Image, ImageDraw, ImageFont
import io
import base64
import os
from django.conf import settings
from django.http import HttpResponse
import qrcode
import arabic_reshaper
from bidi.algorithm import get_display


class BarcodeGenerator:
    """مولد الباركود المتقدم"""
    
    def __init__(self):
        self.barcode_types = {
            'code128': barcode.Code128,
            'code39': barcode.Code39,
            'ean13': barcode.EAN13,
            'upca': barcode.UPCA
        }
    
    @staticmethod
    def reshape_arabic(text):
        """
        معالجة النص العربي ليظهر بشكل صحيح في الصور
        """
        try:
            reshaped_text = arabic_reshaper.reshape(text)
            bidi_text = get_display(reshaped_text)
            return bidi_text
        except:
            return text
    
    def generate_barcode_image(self, code, barcode_type='code128', 
                              width=2.0, height=15.0, format='PNG', dpi=300):
        """
        توليد صورة باركود
        
        Args:
            code: رقم الباركود
            barcode_type: نوع الباركود (code128, code39, ean13)
            width: عرض الخطوط
            height: ارتفاع الباركود (بالملم)
            format: تنسيق الصورة (PNG, JPG)
        
        Returns:
            tuple: (image_buffer, base64_string)
        """
        try:
            # اختيار نوع الباركود
            barcode_class = self.barcode_types.get(barcode_type.lower(), barcode.Code128)
            
            # إنشاء الباركود
            # إعداد الكاتب مع DPI مخصص إن أمكن
            writer = ImageWriter()
            try:
                # بعض الإصدارات تدعم ضبط dpi مباشرة
                writer.dpi = dpi
            except Exception:
                pass
            barcode_instance = barcode_class(str(code), writer=writer)
            
            # إعدادات الباركود
            options = {
                'module_width': width,
                'module_height': height,
                'background': 'white',
                'foreground': 'black',
                'font_size': 10,
                'text_distance': 5.0,
                'quiet_zone': 6.5
            }
            
            # إنشاء buffer للصورة
            buffer = io.BytesIO()
            barcode_instance.write(buffer, options=options)
            buffer.seek(0)
            
            # تحويل لـ base64 للعرض في HTML
            image_data = buffer.getvalue()
            base64_string = base64.b64encode(image_data).decode('utf-8')
            
            return buffer, f"data:image/{format.lower()};base64,{base64_string}"
            
        except Exception as e:
            print(f"خطأ في توليد الباركود: {str(e)}")
            return None, None
    
    def generate_qr_code(self, data, size=10, border=4):
        """
        توليد QR Code
        
        Args:
            data: البيانات المراد تشفيرها
            size: حجم QR Code
            border: سُمك الحدود
        
        Returns:
            base64_string: صورة QR Code مُشفرة بـ base64
        """
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=size,
                border=border,
            )
            qr.add_data(str(data))
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            # تحويل لـ base64
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            
            image_data = buffer.getvalue()
            base64_string = base64.b64encode(image_data).decode('utf-8')
            
            return f"data:image/png;base64,{base64_string}"
            
        except Exception as e:
            print(f"خطأ في توليد QR Code: {str(e)}")
            return None
    
    def create_product_label(self, product, include_price=True, 
                           include_stock=True, label_size=(400, 200),
                           barcode_type='code128', dpi=203, currency_symbol=None,
                           barcode_only=False):
        """
        إنشاء ملصق منتج مع باركود
        - dpi يسمح بضبط دقة الملصق بما يتماشى مع طابعات الباركود (203 أو 300)
        - currency_symbol اختياري لعرض عملة مخصصة
        - barcode_only لملء الملصق بالباركود قدر الإمكان وتقليل النص
        """
        try:
            label_size = (int(label_size[0]), int(label_size[1]))
            label = Image.new('RGB', label_size, color='white')
            draw = ImageDraw.Draw(label)
            buffer, _ = self.generate_barcode_image(
                product.barcode,
                barcode_type=barcode_type,
                width=1.6,
                height=8.5,
                dpi=dpi,
            )
            currency_symbol = currency_symbol or getattr(settings, 'CURRENCY_SYMBOL', 'ر.س')
            scale = max(0.8, min(label_size[0] / 400, 1.8))
            if buffer:
                buffer.seek(0)
                barcode_img = Image.open(buffer)
                barcode_width = int(label_size[0] * 0.92)
                # في وضع barcode_only اجعل الارتفاع أكبر ليملأ الملصق
                if barcode_only:
                    barcode_height = int(label_size[1] * 0.75)
                else:
                    barcode_height = int(barcode_img.height * (barcode_width / barcode_img.width))
                    barcode_height = min(barcode_height, int(label_size[1] * 0.6))
                barcode_img = barcode_img.resize((barcode_width, barcode_height))
                x_offset = (label_size[0] - barcode_width) // 2
                y_offset = max(6, int(8 * scale))
                label.paste(barcode_img, (x_offset, y_offset))
                y_text_start = y_offset + barcode_height + (4 if barcode_only else 10)
                
                # محاولة استخدام خط عربي واضح
                try:
                    # محاولة خطوط عربية شائعة في Windows
                    font_large = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", int(22 * scale))
                    font_medium = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", int(17 * scale))
                    font_small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", int(14 * scale))
                    font_barcode = ImageFont.truetype("C:/Windows/Fonts/cour.ttf", int(12 * scale))  # Courier للباركود
                except:
                    try:
                        # خط احتياطي
                        font_large = ImageFont.truetype("arial.ttf", int(22 * scale))
                        font_medium = ImageFont.truetype("arial.ttf", int(17 * scale))
                        font_small = ImageFont.truetype("arial.ttf", int(14 * scale))
                        font_barcode = ImageFont.truetype("arial.ttf", int(12 * scale))
                    except:
                        font_large = ImageFont.load_default()
                        font_medium = ImageFont.load_default()
                        font_small = ImageFont.load_default()
                        font_barcode = ImageFont.load_default()
                
                # نص المنتج (يتخطى بالكامل إذا barcode_only)
                if not barcode_only:
                    product_name = product.name[:35] + "..." if len(product.name) > 35 else product.name
                    product_name = self.reshape_arabic(product_name)
                    bbox = draw.textbbox((0, 0), product_name, font=font_large)
                    text_width = bbox[2] - bbox[0]
                    x_text = (label_size[0] - text_width) // 2
                    draw.text((x_text, y_text_start), product_name, fill='black', font=font_large)
                    y_text_start += int(24 * scale)
                
                # كود المنتج - معالجة النص العربي
                if not barcode_only:
                    sku_text = self.reshape_arabic(f"كود: {product.sku}")
                    bbox = draw.textbbox((0, 0), sku_text, font=font_medium)
                    text_width = bbox[2] - bbox[0]
                    x_text = (label_size[0] - text_width) // 2
                    draw.text((x_text, y_text_start), sku_text, fill='black', font=font_medium)
                
                # السعر والمخزون - معالجة النص العربي
                if (include_price or include_stock) and not barcode_only:
                    y_text_start += int(22 * scale)
                    info_parts = []
                    if include_price:
                        info_parts.append(f"السعر: {product.price:.2f} {currency_symbol}")
                    if include_stock:
                        info_parts.append(f"متوفر: {product.current_stock}")
                    info_text = self.reshape_arabic(" | ".join(info_parts))
                    bbox = draw.textbbox((0, 0), info_text, font=font_small)
                    text_width = bbox[2] - bbox[0]
                    x_text = (label_size[0] - text_width) // 2
                    draw.text((x_text, y_text_start), info_text, fill='black', font=font_small)
                
                # رقم الباركود بخط Courier أوضح
                y_text_start += int(14 * scale)
                barcode_text = product.barcode
                bbox = draw.textbbox((0, 0), barcode_text, font=font_barcode)
                text_width = bbox[2] - bbox[0]
                x_text = (label_size[0] - text_width) // 2
                draw.text((x_text, y_text_start), barcode_text, fill='#333333', font=font_barcode)
            buffer = io.BytesIO()
            label.save(buffer, format='PNG')
            buffer.seek(0)
            image_data = buffer.getvalue()
            base64_string = base64.b64encode(image_data).decode('utf-8')
            return f"data:image/png;base64,{base64_string}"
        except Exception as e:
            print(f"خطأ في إنشاء ملصق المنتج: {str(e)}")
            return None

    def create_finished_unit_label(self, unit, label_mm=(100, 100), barcode_width=2.0, barcode_height=12.0):
        """
        إنشاء ملصق لقطعة منتَجة (متوافق مع طابعات Zebra):
        - يطبع اسم المنتج، المقاس، تاريخ الانتهاء (YYYY-MM-DD) والباركود فقط
        - label_mm: حجم الملصق بالملليميتر (مثال: (100,100) أو (100,50))
        - barcode_width/height: أبعاد وحدات الباركود (لملاءمة طابعات Zebra)
        """
        try:
            # تحويل المليمتر إلى بكسل تقريبياً (افتراض 8 px لكل مم ~ 203dpi/25.4)
            px_per_mm = 8
            size_px = (int(label_mm[0] * px_per_mm), int(label_mm[1] * px_per_mm))
            label = Image.new('RGB', size_px, color='white')
            draw = ImageDraw.Draw(label)

            # توليد صورة الباركود للوحدة
            buffer, _ = self.generate_barcode_image(
                unit.barcode,
                barcode_type='code128',
                width=barcode_width,
                height=barcode_height,
            )
            if buffer:
                buffer.seek(0)
                barcode_img = Image.open(buffer)
                # عرض الباركود 90% من عرض الملصق
                barcode_target_w = int(size_px[0] * 0.9)
                ratio = barcode_target_w / barcode_img.width
                barcode_target_h = int(barcode_img.height * ratio)
                barcode_img = barcode_img.resize((barcode_target_w, barcode_target_h))
                x_offset = (size_px[0] - barcode_target_w) // 2
                y_offset = 10
                label.paste(barcode_img, (x_offset, y_offset))
                y_text = y_offset + barcode_target_h + 8

                # خطوط
                try:
                    font_bold = ImageFont.truetype("arial.ttf", 22)
                    font_norm = ImageFont.truetype("arial.ttf", 18)
                    font_small = ImageFont.truetype("arial.ttf", 16)
                except:
                    font_bold = ImageFont.load_default()
                    font_norm = ImageFont.load_default()
                    font_small = ImageFont.load_default()

                # اسم المنتج
                name = unit.product.name
                name = name[:40] + '...' if len(name) > 40 else name
                x = (size_px[0] - draw.textlength(name, font=font_bold)) // 2
                draw.text((x, y_text), name, fill='black', font=font_bold)
                y_text += 26

                # المقاس (قابل للتعديل يدويًا: مخزون في unit.size_text)
                size_text = unit.size_text or ''
                if size_text:
                    x = (size_px[0] - draw.textlength(size_text, font=font_norm)) // 2
                    draw.text((x, y_text), size_text, fill='black', font=font_norm)
                    y_text += 22

                # تاريخ الانتهاء
                if unit.expiry_date:
                    exp_text = f"EXP: {unit.expiry_date.strftime('%Y-%m-%d')}"
                    x = (size_px[0] - draw.textlength(exp_text, font=font_small)) // 2
                    draw.text((x, y_text), exp_text, fill='black', font=font_small)
                    y_text += 20

                # كود الباركود نصيًا أسفل
                code_text = unit.barcode
                x = (size_px[0] - draw.textlength(code_text, font=font_small)) // 2
                draw.text((x, y_text), code_text, fill='gray', font=font_small)

            # مجددًا إلى base64
            out = io.BytesIO()
            label.save(out, format='PNG')
            out.seek(0)
            b64 = base64.b64encode(out.getvalue()).decode('utf-8')
            return f"data:image/png;base64,{b64}"
        except Exception as e:
            print(f"خطأ في إنشاء ملصق القطعة: {str(e)}")
            return None
    
    def batch_generate_labels(self, products, **kwargs):
        """
        توليد ملصقات متعددة للمنتجات
        
        Args:
            products: قائمة المنتجات
            **kwargs: معاملات إضافية لـ create_product_label
        
        Returns:
            list: قائمة بصور الملصقات مُشفرة بـ base64
        """
        labels = []
        for product in products:
            if product.barcode:
                label = self.create_product_label(product, **kwargs)
                if label:
                    labels.append({
                        'product': product,
                        'label_image': label
                    })
        return labels


# إنشاء instance عام للاستخدام
barcode_generator = BarcodeGenerator()


def get_barcode_image(product, barcode_type='code128'):
    """
    دالة مساعدة للحصول على صورة الباركود
    
    Args:
        product: كائن المنتج
        barcode_type: نوع الباركود
    
    Returns:
        base64_string: صورة الباركود مُشفرة
    """
    if not product.barcode:
        return None
    
    buffer, base64_image = barcode_generator.generate_barcode_image(
        product.barcode, barcode_type
    )
    return base64_image


def get_product_qr_code(product):
    """
    دالة مساعدة للحصول على QR Code للمنتج
    
    Args:
        product: كائن المنتج
    
    Returns:
        base64_string: QR Code مُشفر
    """
    # إنشاء بيانات المنتج للـ QR Code
    product_data = {
        'sku': product.sku,
        'name': product.name,
        'barcode': product.barcode,
        'price': float(product.price),
    }
    
    # تحويل البيانات لـ JSON string
    import json
    data_string = json.dumps(product_data, ensure_ascii=False)
    
    return barcode_generator.generate_qr_code(data_string)


def validate_barcode(barcode_value):
    """
    التحقق من صحة رقم الباركود
    
    Args:
        barcode_value: رقم الباركود
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not barcode_value:
        return False, "رقم الباركود مطلوب"
    
    if not barcode_value.isdigit():
        return False, "رقم الباركود يجب أن يحتوي على أرقام فقط"
    
    if len(barcode_value) < 8 or len(barcode_value) > 20:
        return False, "طول رقم الباركود يجب أن يكون بين 8 و 20 رقم"
    
    return True, None


def resolve_label_dimensions(label_preset: str, width_mm_param: str = None, height_mm_param: str = None, px_per_mm: int = 8):
    """حساب أبعاد الملصق بالبكسل والملليمتر مع حماية الإدخال."""
    size_presets = {
        'small': {'px': (300, 150), 'mm': (30, 15)},
        'medium': {'px': (400, 200), 'mm': (40, 20)},
        'large': {'px': (600, 300), 'mm': (60, 30)},
    }

    label_px = size_presets.get(label_preset, size_presets['medium'])['px']
    label_mm = size_presets.get(label_preset, size_presets['medium'])['mm']

    if label_preset == 'custom' and width_mm_param and height_mm_param:
        try:
            width_mm = max(10.0, min(float(width_mm_param), 200.0))
            height_mm = max(10.0, min(float(height_mm_param), 200.0))
            label_px = (int(width_mm * px_per_mm), int(height_mm * px_per_mm))
            label_mm = (width_mm, height_mm)
        except ValueError:
            pass

    return label_px, label_mm


def search_products_by_barcode(barcode_value):
    """
    البحث عن المنتجات بالباركود
    
    Args:
        barcode_value: رقم الباركود
    
    Returns:
        QuerySet: المنتجات المطابقة
    """
    from .models import Product
    
    if not barcode_value:
        return Product.objects.none()
    
    # البحث الدقيق أولاً
    exact_match = Product.objects.filter(barcode=barcode_value)
    if exact_match.exists():
        return exact_match
    
    # البحث الجزئي كبديل
    partial_match = Product.objects.filter(barcode__icontains=barcode_value)
    return partial_match


# =====================
# نظام الطباعة المباشرة للطابعات
# =====================

def send_to_zebra_printer(zpl_commands, printer_config):
    """
    إرسال أوامر ZPL مباشرة لطابعة Zebra
    
    Args:
        zpl_commands: أوامر ZPL كنص
        printer_config: كائن PrinterConfiguration
    
    Returns:
        tuple: (success, message)
    """
    import socket
    
    try:
        if printer_config.connection_type == 'network':
            if not printer_config.ip_address or not printer_config.port:
                return False, "عنوان IP والمنفذ مطلوبان للاتصال الشبكي"
            
            # الاتصال عبر socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)  # 5 ثواني timeout
            
            try:
                sock.connect((printer_config.ip_address, printer_config.port))
                sock.sendall(zpl_commands.encode('utf-8'))
                sock.close()
                
                # تحديث إحصائيات الطباعة
                printer_config.increment_print_count()
                
                return True, "تمت الطباعة بنجاح"
            except socket.timeout:
                return False, "انتهت مهلة الاتصال بالطابعة"
            except ConnectionRefusedError:
                return False, "رفضت الطابعة الاتصال. تحقق من عنوان IP والمنفذ"
            except Exception as e:
                return False, f"خطأ في الاتصال: {str(e)}"
        
        elif printer_config.connection_type == 'usb':
            # الطباعة عبر USB (Windows)
            try:
                import win32print
                import win32ui
                
                if not printer_config.usb_device_path:
                    return False, "مسار USB مطلوب"
                
                # فتح الطابعة
                hPrinter = win32print.OpenPrinter(printer_config.usb_device_path)
                try:
                    # بدء مهمة طباعة
                    hJob = win32print.StartDocPrinter(hPrinter, 1, ("Barcode Label", None, "RAW"))
                    try:
                        win32print.StartPagePrinter(hPrinter)
                        win32print.WritePrinter(hPrinter, zpl_commands.encode('utf-8'))
                        win32print.EndPagePrinter(hPrinter)
                    finally:
                        win32print.EndDocPrinter(hPrinter)
                finally:
                    win32print.ClosePrinter(hPrinter)
                
                printer_config.increment_print_count()
                return True, "تمت الطباعة عبر USB بنجاح"
            
            except ImportError:
                return False, "مكتبة pywin32 غير مثبتة. استخدم: pip install pywin32"
            except Exception as e:
                return False, f"خطأ في الطباعة عبر USB: {str(e)}"
        
        else:
            return False, f"نوع اتصال غير مدعوم: {printer_config.connection_type}"
    
    except Exception as e:
        return False, f"خطأ عام: {str(e)}"


def generate_zpl_label(barcode_data, product_name, size_text, manufacture_date, expiry_date=None, 
                       label_width_mm=100, label_height_mm=100, dpi=203):
    """
    توليد أوامر ZPL لطباعة ليبل منتج تام الصنع
    
    Args:
        barcode_data: بيانات الباركود
        product_name: اسم المنتج
        size_text: المقاس
        manufacture_date: تاريخ التصنيع
        expiry_date: تاريخ الانتهاء (اختياري)
        label_width_mm: عرض الليبل بالملم
        label_height_mm: ارتفاع الليبل بالملم
        dpi: نقاط في البوصة (203 أو 300)
    
    Returns:
        str: أوامر ZPL
    """
    
    # تحويل الملم إلى dots
    dots_per_mm = dpi / 25.4
    label_width_dots = int(label_width_mm * dots_per_mm)
    label_height_dots = int(label_height_mm * dots_per_mm)
    
    # تنسيق التواريخ
    mfg_date_str = manufacture_date.strftime('%Y-%m-%d') if manufacture_date else ''
    exp_date_str = expiry_date.strftime('%Y-%m-%d') if expiry_date else ''
    
    # بناء أوامر ZPL
    zpl = f"""
^XA
^POI
^PW{label_width_dots}
^LL{label_height_dots}

^FO50,30^A0N,40,40^FD{product_name[:30]}^FS
^FO50,80^A0N,30,30^FDSize: {size_text}^FS
^FO50,120^A0N,25,25^FDMfg: {mfg_date_str}^FS
"""
    
    if exp_date_str:
        zpl += f"^FO50,150^A0N,25,25^FDExp: {exp_date_str}^FS\n"
    
    # إضافة الباركود
    barcode_y_pos = 200 if exp_date_str else 170
    zpl += f"""
^FO50,{barcode_y_pos}^BCN,100,Y,N,N^FD{barcode_data}^FS

^XZ
"""
    
    return zpl


def print_finished_unit_label_auto(finished_unit, printer_config=None):
    """
    طباعة ليبل لوحدة منتج تام الصنع تلقائياً
    
    Args:
        finished_unit: كائن FinishedGoodUnit
        printer_config: إعداد الطابعة (اختياري، سيستخدم الافتراضية)
    
    Returns:
        tuple: (success, message)
    """
    from .models import PrinterConfiguration
    
    # الحصول على إعداد الطابعة
    if not printer_config:
        printer_config = PrinterConfiguration.objects.filter(
            document_type='barcode',
            printer_type='zebra',
            is_active=True,
            is_default=True
        ).first()
        
        if not printer_config:
            return False, "لم يتم العثور على طابعة Zebra افتراضية للباركود"
    
    # توليد أوامر ZPL
    zpl_commands = generate_zpl_label(
        barcode_data=finished_unit.barcode,
        product_name=finished_unit.product.name,
        size_text=finished_unit.size_text or '',
        manufacture_date=finished_unit.manufacture_date,
        expiry_date=finished_unit.expiry_date,
        label_width_mm=printer_config.label_width_mm or 100,
        label_height_mm=printer_config.label_height_mm or 100,
        dpi=printer_config.dpi or 203
    )
    
    # إرسال للطابعة
    return send_to_zebra_printer(zpl_commands, printer_config)


def send_to_thermal_printer(document_html, printer_config, *, raw_text=False, title=None, line_width=None):
    """
    إرسال مستند (HTML أو نص) لطابعة حرارية (xprinter / ESC/POS)

    Args:
        document_html: محتوى HTML أو نص جاهز للطباعة
        printer_config: كائن PrinterConfiguration
        raw_text: عند True لن يتم تحويل HTML وسيُرسل النص كما هو
        title: عنوان اختياري يظهر أعلى الإيصال
        line_width: عرض السطر المرغوب (يُستنتج تلقائياً عند عدم التحديد)

    Returns:
        tuple: (success, message)
    """

    def _html_to_text(html_content: str) -> str:
        from html import unescape
        import re

        # الحفاظ على فواصل الأسطر قبل إزالة الوسوم
        normalized = re.sub(r'<\s*br\s*/?>', '\n', html_content, flags=re.IGNORECASE)
        normalized = re.sub(r'</p\s*>', '\n', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'<[^<]+?>', '', normalized)
        normalized = unescape(normalized)
        return normalized

    def _normalize_width(text: str) -> str:
        import textwrap

        width_hint = line_width or (48 if '80' in (printer_config.paper_size or '') else 32)
        wrapped_lines = []
        for ln in text.splitlines():
            if len(ln) <= width_hint:
                wrapped_lines.append(ln)
            else:
                wrapped_lines.extend(textwrap.wrap(ln, width=width_hint))
        return "\n".join(wrapped_lines).rstrip() + "\n"

    try:
        printable_text = document_html if raw_text else _html_to_text(document_html)
        printable_text = _normalize_width(printable_text)
        if title:
            printable_text = f"{title}\n{printable_text}"

        # محاولة استخدام python-escpos لطابعات الشبكة أو USB
        if printer_config.connection_type in ('network', 'usb'):
            try:
                from escpos.printer import Network, Usb

                if printer_config.connection_type == 'network':
                    if not printer_config.ip_address:
                        return False, "عنوان IP مطلوب"
                    printer = Network(printer_config.ip_address, port=printer_config.port or 9100, timeout=5)
                else:
                    # معرّفات USB غير متوفرة حالياً في التكوين، يمكن تمديدها لاحقاً
                    return False, "الطباعة عبر USB تحتاج تعريف vendor_id / product_id"

                try:
                    printer.charcode('CP864')  # دعم العربية في أغلب الطابعات الحرارية
                except Exception:
                    pass

                printer.text(printable_text)
                printer.cut()
                printer_config.increment_print_count()
                return True, "تمت الطباعة بنجاح"
            except ImportError:
                return False, "مكتبة python-escpos غير مثبتة. استخدم: pip install python-escpos"
            except Exception as e:
                return False, f"خطأ في الطباعة عبر ESC/POS: {str(e)}"

        # طابعات Windows المشاركة (اتصال shared)
        if printer_config.connection_type == 'shared':
            try:
                import win32print

                printer_name = printer_config.shared_printer_name or printer_config.name
                hPrinter = win32print.OpenPrinter(printer_name)
                try:
                    hJob = win32print.StartDocPrinter(hPrinter, 1, ("Thermal Document", None, "RAW"))
                    try:
                        win32print.StartPagePrinter(hPrinter)
                        raw_bytes = printable_text.encode('cp864', errors='ignore')
                        win32print.WritePrinter(hPrinter, raw_bytes)
                        # أمر قطع الورق في أغلب طابعات ESC/POS
                        win32print.WritePrinter(hPrinter, b"\x1dV\x00")
                        win32print.EndPagePrinter(hPrinter)
                    finally:
                        win32print.EndDocPrinter(hPrinter)
                finally:
                    win32print.ClosePrinter(hPrinter)

                printer_config.increment_print_count()
                return True, "تمت الطباعة عبر Windows Print Spooler"
            except ImportError:
                return False, "مكتبة pywin32 غير مثبتة. استخدم: pip install pywin32"
            except Exception as e:
                return False, f"خطأ في الطباعة عبر Windows: {str(e)}"

        return False, f"نوع اتصال غير مدعوم: {printer_config.connection_type}"

    except Exception as e:
        return False, f"خطأ في الطباعة: {str(e)}"


def send_to_laser_printer(pdf_file_path, printer_config):
    """
    إرسال ملف PDF لطابعة ليزر (HP LaserJet)
    
    Args:
        pdf_file_path: مسار ملف PDF
        printer_config: كائن PrinterConfiguration
    
    Returns:
        tuple: (success, message)
    """
    import platform
    
    try:
        if platform.system() == 'Windows':
            # استخدام Windows printing API
            try:
                import win32api
                import win32print
                
                printer_name = printer_config.shared_printer_name or printer_config.name
                
                # طباعة الملف
                win32api.ShellExecute(
                    0,
                    "print",
                    pdf_file_path,
                    f'/d:"{printer_name}"',
                    ".",
                    0
                )
                
                printer_config.increment_print_count()
                return True, "تم إرسال الملف للطباعة"
            
            except ImportError:
                return False, "مكتبة pywin32 غير مثبتة. استخدم: pip install pywin32"
        
        else:
            # Linux/Mac - استخدام CUPS
            try:
                import cups
                
                conn = cups.Connection()
                printer_name = printer_config.shared_printer_name or printer_config.name
                
                job_id = conn.printFile(printer_name, pdf_file_path, "Django Document", {})
                
                printer_config.increment_print_count()
                return True, f"تمت الطباعة - رقم المهمة: {job_id}"
            
            except ImportError:
                return False, "مكتبة pycups غير مثبتة. استخدم: pip install pycups"
    
    except Exception as e:
        return False, f"خطأ في الطباعة: {str(e)}"