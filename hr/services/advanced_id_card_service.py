"""
خدمة متقدمة لإنشاء بطاقات التعريف
Advanced ID Card Generation Service

الميزات:
- دعم تصاميم أفقية وعمودية
- توليد QR Code و Barcode
- دعم مقاسات متعددة (PVC, A4, A6)
- طباعة دفعات
- تصدير PDF عالي الجودة
"""

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, portrait, A4, A6
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
from reportlab.lib.colors import HexColor
import barcode
from barcode.writer import ImageWriter
import qrcode
import json
from io import BytesIO
from PIL import Image
import os
import uuid
from datetime import date
from django.conf import settings
from django.utils import timezone


class AdvancedIDCardService:
    """خدمة متقدمة لإنشاء بطاقات التعريف"""
    
    # الأبعاد القياسية لبطاقة PVC (85.6mm × 53.98mm)
    PVC_WIDTH = 85.6 * mm
    PVC_HEIGHT = 53.98 * mm
    
    # أبعاد A6
    A6_WIDTH = 105 * mm
    A6_HEIGHT = 148 * mm
    
    def __init__(self, template=None):
        """
        تهيئة الخدمة
        
        Args:
            template: قالب التصميم (IDCardTemplate) أو None للافتراضي
        """
        self.template = template
        self._setup_fonts()
        self._load_template_settings()
    
    def _setup_fonts(self):
        """إعداد الخطوط العربية"""
        font_paths = [
            'C:/Windows/Fonts/arial.ttf',
            'C:/Windows/Fonts/tahoma.ttf',
            'C:/Windows/Fonts/calibri.ttf',
            os.path.join(settings.BASE_DIR, 'static', 'fonts', 'Arial.ttf'),
            os.path.join(settings.BASE_DIR, 'static', 'fonts', 'NotoSansArabic-Regular.ttf'),
        ]
        
        self.arabic_font = 'Helvetica'
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    font_name = f'ArabicFont_{os.path.basename(font_path).split(".")[0]}'
                    pdfmetrics.registerFont(TTFont(font_name, font_path))
                    self.arabic_font = font_name
                    break
                except Exception as e:
                    continue
    
    def _load_template_settings(self):
        """تحميل إعدادات القالب"""
        if self.template:
            self.orientation = self.template.orientation
            self.size = self.template.size
            self.primary_color = HexColor(self.template.primary_color)
            self.secondary_color = HexColor(self.template.secondary_color)
            self.text_color = HexColor(self.template.text_color)
            self.bg_color = HexColor(self.template.background_color)
            self.show_qr = self.template.show_qr_code
            self.show_barcode = self.template.show_barcode
            self.show_photo = self.template.show_photo
            self.show_department = self.template.show_department
            self.show_position = self.template.show_position
            self.show_employee_id = self.template.show_employee_id
            self.show_national_id = self.template.show_national_id
            self.show_issue_date = self.template.show_issue_date
            self.show_expiry_date = self.template.show_expiry_date
            self.name_font_size = self.template.name_font_size
            self.info_font_size = self.template.info_font_size
            self.back_instructions = self.template.back_instructions
            
            if self.size == 'custom' and self.template.custom_width and self.template.custom_height:
                self.card_width = float(self.template.custom_width) * mm
                self.card_height = float(self.template.custom_height) * mm
            elif self.size == 'a6':
                self.card_width = self.A6_WIDTH
                self.card_height = self.A6_HEIGHT
            else:
                self.card_width = self.PVC_WIDTH
                self.card_height = self.PVC_HEIGHT
        else:
            # الإعدادات الافتراضية
            self.orientation = 'horizontal'
            self.size = 'pvc'
            self.primary_color = HexColor('#0f172a')
            self.secondary_color = HexColor('#0ea5e9')
            self.text_color = HexColor('#ffffff')
            self.bg_color = HexColor('#f8fafc')
            self.show_qr = True
            self.show_barcode = True
            self.show_photo = True
            self.show_department = True
            self.show_position = True
            self.show_employee_id = True
            self.show_national_id = False
            self.show_issue_date = True
            self.show_expiry_date = True
            self.name_font_size = 14
            self.info_font_size = 10
            self.card_width = self.PVC_WIDTH
            self.card_height = self.PVC_HEIGHT
            self.back_instructions = '''• هذه البطاقة ملك للشركة ويجب إرجاعها عند انتهاء الخدمة
• يجب حمل البطاقة في جميع الأوقات داخل المنشأة
• في حالة الفقد يرجى الإبلاغ فوراً لقسم الموارد البشرية'''
        
        # تبديل الأبعاد للاتجاه العمودي
        if self.orientation == 'vertical':
            self.card_width, self.card_height = self.card_height, self.card_width
    
    def _format_arabic(self, text):
        """تنسيق النص العربي للعرض الصحيح"""
        try:
            from arabic_reshaper import reshape
            from bidi.algorithm import get_display
            reshaped = reshape(str(text))
            return get_display(reshaped)
        except ImportError:
            return str(text)
        except Exception:
            return str(text)
    
    def generate_qr_code(self, data):
        """توليد QR Code"""
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=10,
                border=2,
            )
            
            if isinstance(data, dict):
                qr.add_data(json.dumps(data, ensure_ascii=False))
            else:
                qr.add_data(str(data))
            
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            return ImageReader(buffer)
        except Exception as e:
            print(f"Error generating QR code: {e}")
            return None
    
    def generate_barcode(self, code):
        """توليد باركود Code128"""
        try:
            code128 = barcode.get_barcode_class('code128')
            barcode_instance = code128(str(code), writer=ImageWriter())
            buffer = BytesIO()
            barcode_instance.write(buffer, options={
                'write_text': False,
                'module_height': 8,
                'module_width': 0.4,
                'quiet_zone': 2,
            })
            buffer.seek(0)
            return ImageReader(buffer)
        except Exception as e:
            print(f"Error generating barcode: {e}")
            return None
    
    def _get_employee_photo(self, employee):
        """الحصول على صورة الموظف"""
        try:
            if employee.photo and os.path.exists(employee.photo.path):
                return employee.photo.path
        except:
            pass
        return None
    
    def _get_company_logo(self):
        """الحصول على شعار الشركة"""
        # أولاً: محاولة الحصول من القالب
        try:
            if self.template and self.template.company_logo:
                return self.template.company_logo.path
        except:
            pass
        
        # ثانياً: محاولة الحصول من بيانات الشركة في قاعدة البيانات
        try:
            from core.models import Company
            company = Company.objects.first()
            if company and company.logo and os.path.exists(company.logo.path):
                return company.logo.path
        except Exception as e:
            print(f"Error getting company logo: {e}")
        
        # ثالثاً: محاولة الحصول على الشعار من مسارات ثابتة
        logo_paths = [
            os.path.join(settings.MEDIA_ROOT, 'company', 'logo.png'),
            os.path.join(settings.STATIC_ROOT or settings.BASE_DIR, 'static', 'images', 'logo.png'),
            os.path.join(settings.BASE_DIR, 'static', 'images', 'logo.png'),
        ]
        
        for path in logo_paths:
            if os.path.exists(path):
                return path
        
        return None
    
    def _get_company_name(self):
        """الحصول على اسم الشركة"""
        try:
            from core.models import Company
            company = Company.objects.first()
            if company:
                return company.name
        except:
            pass
        return getattr(settings, 'COMPANY_NAME', 'شركتنا')
    
    def draw_front_horizontal(self, c, employee, card):
        """رسم الوجه الأمامي (أفقي)"""
        # الخلفية
        c.setFillColor(self.bg_color)
        c.rect(0, 0, self.card_width, self.card_height, fill=True, stroke=False)
        
        # الشريط العلوي
        c.setFillColor(self.primary_color)
        c.rect(0, self.card_height - 14*mm, self.card_width, 14*mm, fill=True, stroke=False)
        
        # شعار الشركة (أولاً)
        logo_path = self._get_company_logo()
        logo_width = 0
        if logo_path:
            try:
                c.drawImage(logo_path, 5*mm, self.card_height - 12*mm, 
                           width=10*mm, height=10*mm, preserveAspectRatio=True, mask='auto')
                logo_width = 12*mm  # مساحة الشعار
            except Exception as e:
                print(f"Error drawing logo: {e}")
        
        # اسم الشركة (بعد الشعار)
        company_name = self._get_company_name()
        c.setFillColor(self.text_color)
        c.setFont(self.arabic_font, 11)
        # رسم الاسم في وسط الشريط (مع مراعاة الشعار)
        text_x = (self.card_width + logo_width) / 2
        c.drawCentredString(text_x, self.card_height - 9*mm, self._format_arabic(company_name))
        
        # صورة الموظف
        if self.show_photo:
            photo_path = self._get_employee_photo(employee)
            if photo_path:
                try:
                    c.drawImage(photo_path, self.card_width - 27*mm, self.card_height - 38*mm,
                               width=22*mm, height=28*mm, preserveAspectRatio=True, mask='auto')
                    # إطار الصورة
                    c.setStrokeColor(self.secondary_color)
                    c.setLineWidth(1)
                    c.rect(self.card_width - 27*mm, self.card_height - 38*mm, 22*mm, 28*mm, fill=False, stroke=True)
                except:
                    pass
        
        # معلومات الموظف
        c.setFillColor(HexColor('#111827'))
        y_pos = self.card_height - 20*mm
        
        # الاسم
        name = employee.arabic_name or f"{employee.first_name} {employee.last_name}"
        c.setFont(self.arabic_font, self.name_font_size)
        c.drawRightString(self.card_width - 32*mm, y_pos, self._format_arabic(name))
        y_pos -= 5*mm
        
        # الوظيفة
        if self.show_position and employee.position:
            c.setFont(self.arabic_font, self.info_font_size)
            c.drawRightString(self.card_width - 32*mm, y_pos, self._format_arabic(str(employee.position)))
            y_pos -= 4*mm
        
        # القسم
        if self.show_department and employee.department:
            c.setFont(self.arabic_font, 8)
            c.drawRightString(self.card_width - 32*mm, y_pos, self._format_arabic(f"القسم: {employee.department}"))
            y_pos -= 4*mm
        
        # رقم الموظف
        if self.show_employee_id:
            c.setFont(self.arabic_font, 8)
            c.drawRightString(self.card_width - 32*mm, y_pos, self._format_arabic(f"الرقم: {employee.employee_id}"))
            y_pos -= 4*mm
        
        # الرقم القومي
        if self.show_national_id and employee.national_id:
            c.setFont(self.arabic_font, 7)
            c.drawRightString(self.card_width - 32*mm, y_pos, self._format_arabic(f"الهوية: {employee.national_id}"))
        
        # QR Code
        if self.show_qr:
            qr_data = {
                'card_number': card.card_number,
                'employee_id': employee.employee_id,
                'name': name,
                'issue_date': str(card.issue_date),
            }
            qr_img = self.generate_qr_code(qr_data)
            if qr_img:
                c.drawImage(qr_img, self.card_width - 18*mm, 3*mm, width=15*mm, height=15*mm)
        
        # الباركود
        if self.show_barcode:
            barcode_img = self.generate_barcode(card.card_number)
            if barcode_img:
                c.drawImage(barcode_img, 5*mm, 5*mm, width=40*mm, height=10*mm, preserveAspectRatio=True, mask='auto')
                c.setFont(self.arabic_font, 6)
                c.drawString(5*mm, 2*mm, card.card_number)
    
    def draw_front_vertical(self, c, employee, card):
        """رسم الوجه الأمامي (عمودي)"""
        # الخلفية
        c.setFillColor(self.bg_color)
        c.rect(0, 0, self.card_width, self.card_height, fill=True, stroke=False)
        
        # الشريط العلوي
        c.setFillColor(self.primary_color)
        c.rect(0, self.card_height - 18*mm, self.card_width, 18*mm, fill=True, stroke=False)
        
        # اسم الشركة
        company_name = getattr(settings, 'COMPANY_NAME', 'شركتنا')
        c.setFillColor(self.text_color)
        c.setFont(self.arabic_font, 10)
        c.drawCentredString(self.card_width / 2, self.card_height - 12*mm, self._format_arabic(company_name))
        
        # صورة الموظف (في الوسط)
        if self.show_photo:
            photo_path = self._get_employee_photo(employee)
            if photo_path:
                try:
                    c.drawImage(photo_path, (self.card_width - 25*mm) / 2, self.card_height - 50*mm,
                               width=25*mm, height=30*mm, preserveAspectRatio=True, mask='auto')
                    c.setStrokeColor(self.secondary_color)
                    c.setLineWidth(1)
                    c.rect((self.card_width - 25*mm) / 2, self.card_height - 50*mm, 25*mm, 30*mm, fill=False, stroke=True)
                except:
                    pass
        
        # معلومات الموظف
        c.setFillColor(HexColor('#111827'))
        y_pos = self.card_height - 55*mm
        
        # الاسم
        name = employee.arabic_name or f"{employee.first_name} {employee.last_name}"
        c.setFont(self.arabic_font, self.name_font_size)
        c.drawCentredString(self.card_width / 2, y_pos, self._format_arabic(name))
        y_pos -= 6*mm
        
        # الوظيفة
        if self.show_position and employee.position:
            c.setFont(self.arabic_font, self.info_font_size)
            c.drawCentredString(self.card_width / 2, y_pos, self._format_arabic(str(employee.position)))
            y_pos -= 5*mm
        
        # القسم
        if self.show_department and employee.department:
            c.setFont(self.arabic_font, 8)
            c.drawCentredString(self.card_width / 2, y_pos, self._format_arabic(f"القسم: {employee.department}"))
            y_pos -= 4*mm
        
        # رقم الموظف
        if self.show_employee_id:
            c.setFont(self.arabic_font, 8)
            c.drawCentredString(self.card_width / 2, y_pos, self._format_arabic(f"رقم الموظف: {employee.employee_id}"))
        
        # QR Code (أسفل)
        if self.show_qr:
            qr_data = {
                'card_number': card.card_number,
                'employee_id': employee.employee_id,
            }
            qr_img = self.generate_qr_code(qr_data)
            if qr_img:
                c.drawImage(qr_img, (self.card_width - 20*mm) / 2, 5*mm, width=20*mm, height=20*mm)
    
    def draw_back_side(self, c, employee, card):
        """رسم الوجه الخلفي"""
        # الخلفية
        c.setFillColor(HexColor('#f1f5f9'))
        c.rect(0, 0, self.card_width, self.card_height, fill=True, stroke=False)
        
        # الشريط العلوي
        c.setFillColor(self.primary_color)
        c.rect(0, self.card_height - 10*mm, self.card_width, 10*mm, fill=True, stroke=False)
        
        # العنوان
        c.setFillColor(self.text_color)
        c.setFont(self.arabic_font, 9)
        c.drawCentredString(self.card_width / 2, self.card_height - 6*mm, self._format_arabic("تعليمات مهمة"))
        
        # التعليمات
        c.setFillColor(HexColor('#374151'))
        c.setFont(self.arabic_font, 6)
        
        instructions = self.back_instructions.split('\n')
        y_pos = self.card_height - 15*mm
        for instruction in instructions:
            if instruction.strip():
                c.drawRightString(self.card_width - 3*mm, y_pos, self._format_arabic(instruction.strip()))
                y_pos -= 4*mm
        
        # تواريخ الصلاحية
        c.setFont(self.arabic_font, 7)
        c.setFillColor(HexColor('#1f2937'))
        
        if self.show_issue_date:
            c.drawCentredString(self.card_width / 2, 12*mm, 
                               self._format_arabic(f"تاريخ الإصدار: {card.issue_date}"))
        
        if self.show_expiry_date:
            c.drawCentredString(self.card_width / 2, 8*mm, 
                               self._format_arabic(f"تاريخ الانتهاء: {card.expiry_date}"))
        
        # خط التوقيع
        c.setStrokeColor(HexColor('#9ca3af'))
        c.line(15*mm, 3*mm, self.card_width - 15*mm, 3*mm)
    
    def generate_single_card_pdf(self, employee, card, output_buffer=None):
        """توليد PDF لبطاقة واحدة"""
        if output_buffer is None:
            output_buffer = BytesIO()
        
        # إنشاء PDF بحجم A4
        page_size = landscape(A4)
        c = canvas.Canvas(output_buffer, pagesize=page_size)
        
        page_width, page_height = page_size
        
        # حساب موضع البطاقات
        start_x = (page_width - (self.card_width * 2 + 15*mm)) / 2
        start_y = (page_height - self.card_height) / 2
        
        # الوجه الأمامي
        c.saveState()
        c.translate(start_x, start_y)
        
        if self.orientation == 'horizontal':
            self.draw_front_horizontal(c, employee, card)
        else:
            self.draw_front_vertical(c, employee, card)
        
        c.restoreState()
        
        # الوجه الخلفي
        c.saveState()
        c.translate(start_x + self.card_width + 15*mm, start_y)
        self.draw_back_side(c, employee, card)
        c.restoreState()
        
        # خطوط القص
        c.setStrokeColor(HexColor('#d1d5db'))
        c.setLineWidth(0.5)
        c.setDash(3, 3)
        
        c.rect(start_x, start_y, self.card_width, self.card_height, fill=False, stroke=True)
        c.rect(start_x + self.card_width + 15*mm, start_y, self.card_width, self.card_height, fill=False, stroke=True)
        
        # ملاحظة الطباعة
        c.setDash(1, 0)
        c.setFont("Helvetica", 8)
        c.setFillColor(HexColor('#9ca3af'))
        c.drawCentredString(page_width / 2, start_y - 10*mm, 
                           "Cut along the dotted lines - اقطع على طول الخطوط المنقطة")
        
        c.showPage()
        c.save()
        
        output_buffer.seek(0)
        return output_buffer
    
    def generate_batch_pdf(self, cards_with_employees, output_buffer=None):
        """توليد PDF لدفعة من البطاقات"""
        if output_buffer is None:
            output_buffer = BytesIO()
        
        # إنشاء PDF بحجم A4
        page_size = landscape(A4)
        c = canvas.Canvas(output_buffer, pagesize=page_size)
        
        page_width, page_height = page_size
        
        # عدد البطاقات في كل صفحة
        if self.size == 'pvc':
            cards_per_row = 2
            cards_per_col = 2
            gap = 10 * mm
        else:
            cards_per_row = 1
            cards_per_col = 1
            gap = 15 * mm
        
        # حساب المسافات
        total_width = (self.card_width * 2 + gap) * cards_per_row
        total_height = (self.card_height + gap) * cards_per_col
        
        start_x = (page_width - total_width) / 2 + gap
        start_y = page_height - (page_height - total_height) / 2 - self.card_height - gap
        
        current_col = 0
        current_row = 0
        
        for employee, card in cards_with_employees:
            # حساب الموضع
            x = start_x + current_col * (self.card_width * 2 + gap * 2)
            y = start_y - current_row * (self.card_height + gap)
            
            # الوجه الأمامي
            c.saveState()
            c.translate(x, y)
            
            if self.orientation == 'horizontal':
                self.draw_front_horizontal(c, employee, card)
            else:
                self.draw_front_vertical(c, employee, card)
            
            c.restoreState()
            
            # الوجه الخلفي
            c.saveState()
            c.translate(x + self.card_width + gap, y)
            self.draw_back_side(c, employee, card)
            c.restoreState()
            
            # خطوط القص
            c.setStrokeColor(HexColor('#e5e7eb'))
            c.setLineWidth(0.3)
            c.setDash(2, 2)
            c.rect(x, y, self.card_width, self.card_height, fill=False, stroke=True)
            c.rect(x + self.card_width + gap, y, self.card_width, self.card_height, fill=False, stroke=True)
            c.setDash(1, 0)
            
            current_col += 1
            if current_col >= cards_per_row:
                current_col = 0
                current_row += 1
                
                if current_row >= cards_per_col:
                    # صفحة جديدة
                    c.showPage()
                    current_row = 0
        
        if current_col > 0 or current_row > 0:
            c.showPage()
        
        c.save()
        output_buffer.seek(0)
        return output_buffer
    
    def generate_pvc_card_pdf(self, employee, card, output_buffer=None):
        """توليد PDF بحجم PVC للطباعة على طابعات البطاقات"""
        if output_buffer is None:
            output_buffer = BytesIO()
        
        # إنشاء PDF بحجم البطاقة
        c = canvas.Canvas(output_buffer, pagesize=(self.card_width, self.card_height))
        
        # الوجه الأمامي
        if self.orientation == 'horizontal':
            self.draw_front_horizontal(c, employee, card)
        else:
            self.draw_front_vertical(c, employee, card)
        
        c.showPage()
        
        # الوجه الخلفي
        self.draw_back_side(c, employee, card)
        
        c.showPage()
        c.save()
        
        output_buffer.seek(0)
        return output_buffer


def create_employee_id_card_advanced(employee, template=None, expiry_months=12):
    """
    إنشاء بطاقة هوية جديدة للموظف مع دعم القوالب
    
    Args:
        employee: كائن Employee
        template: قالب التصميم (اختياري)
        expiry_months: عدد أشهر الصلاحية
    
    Returns:
        EmployeeIDCard: كائن البطاقة
    """
    from hr.models import EmployeeIDCard, IDCardTemplate
    from datetime import timedelta
    
    # استخدام القالب الافتراضي إن لم يُحدد
    if template is None:
        template = IDCardTemplate.objects.filter(is_default=True, is_active=True).first()
    
    # إنهاء صلاحية البطاقات القديمة
    EmployeeIDCard.objects.filter(
        employee=employee,
        status='active'
    ).update(status='replaced')
    
    # رقم بطاقة فريد
    card_number = f"EMP-{employee.id:05d}-{uuid.uuid4().hex[:8].upper()}"
    
    # تواريخ الصلاحية
    issue_date = date.today()
    expiry_date = issue_date + timedelta(days=expiry_months * 30)
    
    # توليد QR Code data
    qr_data = {
        'card_number': card_number,
        'employee_id': employee.employee_id,
        'name': employee.arabic_name or f"{employee.first_name} {employee.last_name}",
        'issue_date': str(issue_date),
        'expiry_date': str(expiry_date),
    }
    
    # إنشاء البطاقة
    card = EmployeeIDCard.objects.create(
        employee=employee,
        card_number=card_number,
        qr_code_data=json.dumps(qr_data, ensure_ascii=False),
        issue_date=issue_date,
        expiry_date=expiry_date,
        status='active'
    )
    
    # توليد صورة QR Code
    try:
        service = AdvancedIDCardService(template)
        qr_img = service.generate_qr_code(qr_data)
        if qr_img:
            from django.core.files.base import ContentFile
            buffer = BytesIO()
            # حفظ QR كـ PNG
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=10,
                border=2,
            )
            qr.add_data(json.dumps(qr_data, ensure_ascii=False))
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            img.save(buffer, format='PNG')
            
            card.qr_code_image.save(
                f'qr_{card.card_number}.png',
                ContentFile(buffer.getvalue()),
                save=True
            )
    except Exception as e:
        print(f"Error generating QR image: {e}")
    
    return card
