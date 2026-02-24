"""
خدمة إنشاء وتوليد بطاقات التعريف
ID Card Service for generating employee ID cards
"""

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
import barcode
from barcode.writer import ImageWriter
import qrcode
import json
from io import BytesIO
from PIL import Image
import os
from django.conf import settings


class IDCardService:
    """خدمة إنشاء بطاقات التعريف"""
    
    # الأبعاد القياسية (85.6mm × 53.98mm - حجم بطاقة الائتمان)
    CARD_WIDTH = 85.6 * mm
    CARD_HEIGHT = 53.98 * mm
    
    # الألوان
    COLOR_PRIMARY = (0.2, 0.4, 0.8)  # أزرق
    COLOR_SECONDARY = (0.95, 0.95, 1.0)  # أزرق فاتح جداً
    COLOR_TEXT = (0, 0, 0)  # أسود
    COLOR_LIGHT_GRAY = (0.98, 0.98, 0.98)  # رمادي فاتح
    
    def __init__(self, employee, card_data):
        self.employee = employee
        self.card_data = card_data
        self._setup_arabic_font()
    
    def _setup_arabic_font(self):
        """إعداد الخط العربي"""
        # استخدام خط Arial Unicode MS من Windows
        try:
            # مسارات محتملة للخطوط العربية في Windows
            font_paths = [
                'C:/Windows/Fonts/arial.ttf',
                'C:/Windows/Fonts/tahoma.ttf',
                'C:/Windows/Fonts/calibri.ttf',
                os.path.join(settings.BASE_DIR, 'static', 'fonts', 'Arial.ttf'),
            ]
            
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont('ArabicFont', font_path))
                        self.arabic_font = 'ArabicFont'
                        return
                    except:
                        continue
            
            # إذا فشل كل شيء، استخدم Helvetica
            self.arabic_font = 'Helvetica'
        except:
            self.arabic_font = 'Helvetica'
    
    def generate_barcode(self, card_number):
        """توليد باركود Code128"""
        try:
            code128 = barcode.get_barcode_class('code128')
            barcode_instance = code128(card_number, writer=ImageWriter())
            buffer = BytesIO()
            barcode_instance.write(buffer, options={'write_text': False})
            buffer.seek(0)
            return ImageReader(buffer)
        except Exception as e:
            print(f"Error generating barcode: {e}")
            return None
    
    def generate_qrcode(self, data):
        """توليد QR Code"""
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=2,
            )
            qr.add_data(json.dumps(data, ensure_ascii=False))
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            return ImageReader(buffer)
        except Exception as e:
            print(f"Error generating QR code: {e}")
            return None
    
    def create_front_side(self, c):
        """إنشاء الوجه الأمامي للبطاقة"""
        from arabic_reshaper import reshape
        from bidi.algorithm import get_display
        
        def format_arabic(text):
            """تنسيق النص العربي للعرض الصحيح"""
            try:
                reshaped = reshape(text)
                return get_display(reshaped)
            except:
                return text
        
        # خلفية ملونة
        c.setFillColorRGB(*self.COLOR_SECONDARY)
        c.rect(0, 0, self.CARD_WIDTH, self.CARD_HEIGHT, fill=True, stroke=False)
        
        # شريط علوي ملون
        c.setFillColorRGB(*self.COLOR_PRIMARY)
        c.rect(0, self.CARD_HEIGHT - 12*mm, self.CARD_WIDTH, 12*mm, fill=True, stroke=False)
        
        # اسم الشركة (في الشريط العلوي)
        c.setFillColorRGB(1, 1, 1)  # أبيض
        c.setFont(self.arabic_font, 12)
        company_name = getattr(settings, 'COMPANY_NAME', 'شركة البلاستيك')
        c.drawCentredString(self.CARD_WIDTH / 2, self.CARD_HEIGHT - 8*mm, format_arabic(company_name))
        
        # صورة الموظف (أعلى يمين)
        if self.employee.photo:
            try:
                photo_path = self.employee.photo.path
                c.drawImage(photo_path, self.CARD_WIDTH - 25*mm, 
                           self.CARD_HEIGHT - 35*mm, 
                           width=20*mm, height=25*mm, 
                           preserveAspectRatio=True, mask='auto')
                
                # إطار للصورة
                c.setStrokeColorRGB(*self.COLOR_PRIMARY)
                c.setLineWidth(0.5)
                c.rect(self.CARD_WIDTH - 25*mm, self.CARD_HEIGHT - 35*mm, 
                      20*mm, 25*mm, fill=False, stroke=True)
            except Exception as e:
                print(f"Error adding photo: {e}")
        
        # المعلومات الأساسية
        c.setFillColorRGB(*self.COLOR_TEXT)
        
        # الاسم
        c.setFont(self.arabic_font, 14)
        name = self.employee.arabic_name or f"{self.employee.first_name} {self.employee.last_name}"
        c.drawRightString(self.CARD_WIDTH - 30*mm, self.CARD_HEIGHT - 38*mm, format_arabic(name))
        
        # الوظيفة
        c.setFont(self.arabic_font, 10)
        job_title = str(self.employee.position.title) if self.employee.position else "موظف"
        c.drawRightString(self.CARD_WIDTH - 30*mm, self.CARD_HEIGHT - 43*mm, format_arabic(job_title))
        
        # القسم
        c.setFont(self.arabic_font, 8)
        department = str(self.employee.department.name) if self.employee.department else ""
        if department:
            c.drawRightString(self.CARD_WIDTH - 30*mm, self.CARD_HEIGHT - 47*mm, format_arabic(f"القسم: {department}"))
        
        # رقم الموظف
        c.setFont(self.arabic_font, 8)
        c.drawRightString(self.CARD_WIDTH - 30*mm, self.CARD_HEIGHT - 51*mm, 
                         format_arabic(f"الرقم: {self.employee.employee_id}"))
        
        # الباركود (أسفل يسار)
        barcode_img = self.generate_barcode(self.card_data.card_number)
        if barcode_img:
            c.drawImage(barcode_img, 5*mm, 8*mm, width=35*mm, height=8*mm, 
                       preserveAspectRatio=True, mask='auto')
        
        # رقم البطاقة أسفل الباركود
        c.setFont(self.arabic_font, 7)
        c.drawString(5*mm, 6*mm, self.card_data.card_number)
        
        # QR Code (أسفل يمين)
        qr_data = {
            'card_number': self.card_data.card_number,
            'employee_id': self.employee.employee_id,
            'name': name,
            'department': department,
            'issue_date': str(self.card_data.issue_date),
        }
        qr_img = self.generate_qrcode(qr_data)
        if qr_img:
            c.drawImage(qr_img, self.CARD_WIDTH - 20*mm, 5*mm, 
                       width=15*mm, height=15*mm)
    
    def create_back_side(self, c):
        """إنشاء الوجه الخلفي للبطاقة"""
        from arabic_reshaper import reshape
        from bidi.algorithm import get_display
        
        def format_arabic(text):
            """تنسيق النص العربي للعرض الصحيح"""
            try:
                reshaped = reshape(text)
                return get_display(reshaped)
            except:
                return text
        
        # خلفية
        c.setFillColorRGB(*self.COLOR_LIGHT_GRAY)
        c.rect(0, 0, self.CARD_WIDTH, self.CARD_HEIGHT, fill=True, stroke=False)
        
        # شريط علوي
        c.setFillColorRGB(*self.COLOR_PRIMARY)
        c.rect(0, self.CARD_HEIGHT - 8*mm, self.CARD_WIDTH, 8*mm, fill=True, stroke=False)
        
        # عنوان
        c.setFillColorRGB(1, 1, 1)
        c.setFont(self.arabic_font, 10)
        c.drawCentredString(self.CARD_WIDTH / 2, self.CARD_HEIGHT - 5*mm, format_arabic("تعليمات مهمة"))
        
        # التعليمات بالعربية
        c.setFillColorRGB(*self.COLOR_TEXT)
        c.setFont(self.arabic_font, 6)
        
        instructions = [
            "• هذه البطاقة ملك للشركة ويجب إرجاعها عند انتهاء الخدمة",
            "• يجب حمل البطاقة في جميع الأوقات داخل المصنع",
            "• في حالة الفقد يرجى الإبلاغ فوراً لقسم الموارد البشرية",
            "• عدم إساءة استخدام البطاقة أو إعارتها للغير",
            "• البطاقة صالحة للدخول والخروج من جميع مباني الشركة",
        ]
        
        y_pos = self.CARD_HEIGHT - 13*mm
        for instruction in instructions:
            c.drawRightString(self.CARD_WIDTH - 3*mm, y_pos, format_arabic(instruction))
            y_pos -= 3.5*mm
        
        # معلومات الإصدار والانتهاء
        c.setFont(self.arabic_font, 7)
        y_pos = 15*mm
        c.drawCentredString(self.CARD_WIDTH / 2, y_pos, 
                           format_arabic(f"تاريخ الإصدار: {self.card_data.issue_date}"))
        y_pos -= 4*mm
        c.drawCentredString(self.CARD_WIDTH / 2, y_pos, 
                           format_arabic(f"تاريخ الانتهاء: {self.card_data.expiry_date}"))
        
        # معلومات الاتصال للطوارئ
        y_pos -= 5*mm
        c.setFont(self.arabic_font, 6)
        emergency_contact = getattr(self.employee, 'emergency_contact_phone', '')
        if emergency_contact:
            c.drawCentredString(self.CARD_WIDTH / 2, y_pos, 
                               format_arabic(f"للطوارئ: {emergency_contact}"))
        
        # خط أسفل للتوقيع
        y_pos = 3*mm
        c.line(10*mm, y_pos, self.CARD_WIDTH - 10*mm, y_pos)
        c.setFont(self.arabic_font, 6)
        c.drawCentredString(self.CARD_WIDTH / 2, y_pos - 2*mm, format_arabic("توقيع حامل البطاقة"))
    
    def generate_pdf(self, output_path):
        """توليد ملف PDF للبطاقة (وجهين جنباً إلى جنب)"""
        # إنشاء PDF بحجم A4 أفقي
        c = canvas.Canvas(output_path, pagesize=landscape(A4))
        
        # حساب موضع البطاقات (في وسط الصفحة)
        page_width, page_height = landscape(A4)
        start_x = (page_width - (self.CARD_WIDTH * 2 + 10*mm)) / 2
        start_y = (page_height - self.CARD_HEIGHT) / 2
        
        # الوجه الأمامي
        c.saveState()
        c.translate(start_x, start_y)
        self.create_front_side(c)
        c.restoreState()
        
        # الوجه الخلفي (بجانب الأمامي)
        c.saveState()
        c.translate(start_x + self.CARD_WIDTH + 10*mm, start_y)
        self.create_back_side(c)
        c.restoreState()
        
        # إضافة خطوط القص (اختياري)
        c.setStrokeColorRGB(0.7, 0.7, 0.7)
        c.setLineWidth(0.5)
        c.setDash(2, 2)
        
        # خطوط حول البطاقة الأمامية
        c.rect(start_x, start_y, self.CARD_WIDTH, self.CARD_HEIGHT, fill=False, stroke=True)
        
        # خطوط حول البطاقة الخلفية
        c.rect(start_x + self.CARD_WIDTH + 10*mm, start_y, 
              self.CARD_WIDTH, self.CARD_HEIGHT, fill=False, stroke=True)
        
        # ملاحظة للطباعة
        c.setDash(1, 0)
        c.setFont("Helvetica", 8)
        c.setFillColorRGB(0.5, 0.5, 0.5)
        c.drawCentredString(page_width / 2, start_y - 10*mm, 
                           "Cut along the dotted lines - اقطع على طول الخطوط المنقطة")
        
        c.showPage()
        c.save()
        
        return output_path
    
    def generate_single_card_pdf(self, output_path, side='front'):
        """توليد PDF لوجه واحد فقط (لطابعات البطاقات الخاصة)"""
        # حجم البطاقة القياسي
        c = canvas.Canvas(output_path, pagesize=(self.CARD_WIDTH, self.CARD_HEIGHT))
        
        if side == 'front':
            self.create_front_side(c)
        else:
            self.create_back_side(c)
        
        c.showPage()
        c.save()
        
        return output_path

