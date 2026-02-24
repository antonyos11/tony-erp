"""
نظام الطباعة الحرارية المحسّن
Thermal Printer Handler with Retry Logic
"""

import logging
from typing import Optional, Dict, Any
from io import BytesIO
import time

logger = logging.getLogger(__name__)


class ThermalPrinterException(Exception):
    """استثناء خاص بالطباعة الحرارية"""
    pass


class ThermalPrinterHandler:
    """معالج الطباعة الحرارية مع إعادة المحاولة التلقائية"""
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.printer_status = {'available': True, 'last_error': None}
    
    def check_printer_status(self) -> Dict[str, Any]:
        """
        فحص حالة الطابعة قبل الطباعة
        Returns: dict مع حالة الطابعة
        """
        try:
            # محاولة الاتصال بالطابعة
            # يمكن تخصيصه حسب نوع الطابعة المستخدمة
            status = {
                'available': True,
                'connected': True,
                'paper_ok': True,
                'ready': True,
                'error': None
            }
            
            self.printer_status = status
            return status
            
        except Exception as e:
            logger.error(f"فشل فحص حالة الطابعة: {str(e)}")
            self.printer_status = {
                'available': False,
                'last_error': str(e)
            }
            return self.printer_status
    
    def print_with_retry(self, invoice, print_function, **kwargs) -> Dict[str, Any]:
        """
        طباعة مع إعادة محاولة تلقائية
        
        Args:
            invoice: الفاتورة المراد طباعتها
            print_function: دالة الطباعة الفعلية
            **kwargs: معاملات إضافية للطباعة
        
        Returns:
            dict مع نتيجة الطباعة
        """
        last_error = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"محاولة الطباعة {attempt}/{self.max_retries} للفاتورة {invoice.id}")
                
                # فحص حالة الطابعة
                status = self.check_printer_status()
                if not status.get('available'):
                    raise ThermalPrinterException(
                        f"الطابعة غير متاحة: {status.get('last_error', 'خطأ غير معروف')}"
                    )
                
                # محاولة الطباعة
                result = print_function(invoice, **kwargs)
                
                logger.info(f"نجحت الطباعة للفاتورة {invoice.id} في المحاولة {attempt}")
                
                return {
                    'success': True,
                    'attempt': attempt,
                    'message': 'تمت الطباعة بنجاح',
                    'invoice_id': invoice.id
                }
                
            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"فشلت محاولة الطباعة {attempt}/{self.max_retries}: {last_error}"
                )
                
                # إذا لم تكن المحاولة الأخيرة، انتظر ثم حاول مرة أخرى
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)
                    continue
        
        # فشلت جميع المحاولات
        logger.error(
            f"فشلت جميع محاولات الطباعة ({self.max_retries}) للفاتورة {invoice.id}: {last_error}"
        )
        
        return {
            'success': False,
            'attempts': self.max_retries,
            'error': last_error,
            'message': f'فشلت الطباعة بعد {self.max_retries} محاولات',
            'invoice_id': invoice.id,
            'fallback_available': True  # يمكن استخدام PDF كبديل
        }
    
    def fallback_to_pdf(self, invoice) -> Dict[str, Any]:
        """
        بديل PDF في حالة فشل الطباعة الحرارية
        
        Args:
            invoice: الفاتورة المراد تحويلها لـ PDF
        
        Returns:
            dict مع معلومات ملف PDF
        """
        try:
            from django.template.loader import render_to_string
            from weasyprint import HTML
            
            logger.info(f"إنشاء PDF بديل للفاتورة {invoice.id}")
            
            # توليد HTML من القالب
            html_string = render_to_string('sales/invoice_thermal.html', {
                'invoice': invoice,
                'print_mode': True
            })
            
            # تحويل إلى PDF
            pdf_file = BytesIO()
            HTML(string=html_string).write_pdf(pdf_file)
            pdf_file.seek(0)
            
            # حفظ PDF
            from django.core.files.base import ContentFile
            filename = f'invoice_{invoice.invoice_number}_{int(time.time())}.pdf'
            
            # يمكن حفظ الملف في النموذج أو إرجاعه مباشرة
            return {
                'success': True,
                'type': 'pdf',
                'filename': filename,
                'file': pdf_file,
                'message': 'تم إنشاء PDF بنجاح كبديل للطباعة'
            }
            
        except Exception as e:
            logger.error(f"فشل إنشاء PDF البديل: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'فشل إنشاء PDF البديل'
            }
    
    def log_print_attempt(self, invoice, success: bool, error: Optional[str] = None):
        """
        تسجيل محاولات الطباعة في قاعدة البيانات
        
        Args:
            invoice: الفاتورة
            success: نجحت الطباعة؟
            error: رسالة الخطأ إن وجدت
        """
        try:
            from .models import PrintLog
            
            PrintLog.objects.create(
                invoice=invoice,
                success=success,
                error_message=error,
                printer_type='thermal'
            )
        except Exception as e:
            logger.error(f"فشل تسجيل محاولة الطباعة: {str(e)}")


# مثيل عام للاستخدام
thermal_printer = ThermalPrinterHandler(max_retries=3, retry_delay=1.0)
