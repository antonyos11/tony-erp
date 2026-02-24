#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tony ERP - Local Print Agent
خدمة محلية للطباعة المباشرة على الطابعات الحرارية والعادية
"""

import asyncio
import json
import logging
import sys
import os
from datetime import datetime
from pathlib import Path

try:
    import websockets
    from websockets import serve
except ImportError:
    print("❌ يرجى تثبيت المكتبات: pip install websockets")
    sys.exit(1)

# إعداد السجلات
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('print_agent.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class PrintAgent:
    """وكيل الطباعة المحلي"""
    
    def __init__(self, host='localhost', port=9876):
        self.host = host
        self.port = port
        self.clients = set()
        self.printers = {}
        self.detect_printers()
        
    def detect_printers(self):
        """كشف الطابعات المتاحة"""
        if sys.platform == 'win32':
            self._detect_windows_printers()
        else:
            self._detect_unix_printers()
            
    def _detect_windows_printers(self):
        """كشف طابعات Windows"""
        try:
            import win32print
            printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
            
            for printer in printers:
                printer_name = printer[2]
                self.printers[printer_name] = {
                    'name': printer_name,
                    'type': 'windows',
                    'status': 'ready'
                }
            
            # الطابعة الافتراضية
            try:
                default = win32print.GetDefaultPrinter()
                if default:
                    self.printers['default'] = self.printers.get(default, {})
            except:
                pass
                
            logger.info(f"✓ تم اكتشاف {len(self.printers)} طابعة")
            for name in self.printers:
                logger.info(f"  • {name}")
                
        except ImportError:
            logger.warning("⚠ win32print غير متوفر - يرجى تثبيت: pip install pywin32")
            self._add_dummy_printer()
        except Exception as e:
            logger.error(f"❌ خطأ في كشف الطابعات: {e}")
            self._add_dummy_printer()
            
    def _detect_unix_printers(self):
        """كشف طابعات Linux/Mac"""
        try:
            import cups
            conn = cups.Connection()
            printers = conn.getPrinters()
            
            for name, details in printers.items():
                self.printers[name] = {
                    'name': name,
                    'type': 'cups',
                    'status': 'ready',
                    'info': details.get('printer-info', '')
                }
            
            logger.info(f"✓ تم اكتشاف {len(self.printers)} طابعة")
            
        except ImportError:
            logger.warning("⚠ pycups غير متوفر - يرجى تثبيت: pip install pycups")
            self._add_dummy_printer()
        except Exception as e:
            logger.error(f"❌ خطأ في كشف الطابعات: {e}")
            self._add_dummy_printer()
            
    def _add_dummy_printer(self):
        """إضافة طابعة وهمية للاختبار"""
        self.printers['dummy'] = {
            'name': 'Dummy Printer (للاختبار)',
            'type': 'dummy',
            'status': 'ready'
        }
        
    async def handle_client(self, websocket, path):
        """معالجة اتصال عميل جديد"""
        client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        self.clients.add(websocket)
        logger.info(f"✓ عميل جديد متصل: {client_id}")
        
        # إرسال قائمة الطابعات عند الاتصال
        await self.send_printers_list(websocket)
        
        try:
            async for message in websocket:
                await self.process_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"✗ العميل قطع الاتصال: {client_id}")
        except Exception as e:
            logger.error(f"❌ خطأ: {e}")
        finally:
            self.clients.remove(websocket)
            
    async def send_printers_list(self, websocket):
        """إرسال قائمة الطابعات"""
        response = {
            'event': 'printers_list',
            'printers': list(self.printers.values()),
            'timestamp': datetime.now().isoformat()
        }
        await websocket.send(json.dumps(response, ensure_ascii=False))
        
    async def process_message(self, websocket, message):
        """معالجة رسالة من العميل"""
        try:
            data = json.loads(message)
            action = data.get('action')
            
            if action == 'print':
                await self.handle_print(websocket, data)
            elif action == 'get_printers':
                await self.send_printers_list(websocket)
            elif action == 'test_print':
                await self.handle_test_print(websocket, data)
            else:
                await self.send_error(websocket, f"أمر غير معروف: {action}")
                
        except json.JSONDecodeError:
            await self.send_error(websocket, "خطأ في صيغة JSON")
        except Exception as e:
            logger.error(f"❌ خطأ في معالجة الرسالة: {e}")
            await self.send_error(websocket, str(e))
            
    async def handle_print(self, websocket, data):
        """معالجة طلب طباعة"""
        printer_name = data.get('printer', 'default')
        content_type = data.get('type', 'html')  # html, text, raw, pdf
        content = data.get('content', '')
        
        logger.info(f"📄 طلب طباعة على: {printer_name} - نوع: {content_type}")
        
        try:
            if content_type == 'html':
                result = await self.print_html(printer_name, content)
            elif content_type == 'text':
                result = await self.print_text(printer_name, content)
            elif content_type == 'raw':
                result = await self.print_raw(printer_name, content)
            elif content_type == 'pdf':
                result = await self.print_pdf(printer_name, content)
            else:
                raise ValueError(f"نوع غير مدعوم: {content_type}")
                
            response = {
                'event': 'print_success',
                'result': result,
                'timestamp': datetime.now().isoformat()
            }
            await websocket.send(json.dumps(response, ensure_ascii=False))
            logger.info("✓ تمت الطباعة بنجاح")
            
        except Exception as e:
            logger.error(f"❌ فشلت الطباعة: {e}")
            await self.send_error(websocket, f"فشلت الطباعة: {str(e)}")
            
    async def print_html(self, printer_name, html_content):
        """طباعة محتوى HTML"""
        # حفظ HTML مؤقتًا
        temp_file = Path('temp_print.html')
        temp_file.write_text(html_content, encoding='utf-8')
        
        if sys.platform == 'win32':
            # استخدام المتصفح للطباعة على Windows
            import win32api
            import win32print
            
            # تحويل HTML لـ PDF ثم طباعة
            # يمكن استخدام wkhtmltopdf أو مكتبة أخرى
            # هنا نستخدم طريقة مبسطة
            
            printer = printer_name if printer_name in self.printers else win32print.GetDefaultPrinter()
            
            # طباعة الملف
            win32api.ShellExecute(
                0,
                "print",
                str(temp_file.absolute()),
                f'/d:"{printer}"',
                ".",
                0
            )
            
            return {'status': 'sent', 'printer': printer}
        else:
            # على Linux استخدام wkhtmltopdf + lp
            import subprocess
            
            # تحويل لـ PDF
            subprocess.run(['wkhtmltopdf', str(temp_file), 'temp_print.pdf'])
            
            # طباعة
            subprocess.run(['lp', '-d', printer_name, 'temp_print.pdf'])
            
            return {'status': 'sent', 'printer': printer_name}
            
    async def print_text(self, printer_name, text_content):
        """طباعة نص عادي"""
        if sys.platform == 'win32':
            import win32print
            
            printer = printer_name if printer_name in self.printers else win32print.GetDefaultPrinter()
            
            # فتح الطابعة
            hPrinter = win32print.OpenPrinter(printer)
            try:
                # بدء مهمة طباعة
                hJob = win32print.StartDocPrinter(hPrinter, 1, ("Tony ERP Print", None, "RAW"))
                win32print.StartPagePrinter(hPrinter)
                
                # إرسال النص
                win32print.WritePrinter(hPrinter, text_content.encode('utf-8'))
                
                # إنهاء
                win32print.EndPagePrinter(hPrinter)
                win32print.EndDocPrinter(hPrinter)
            finally:
                win32print.ClosePrinter(hPrinter)
                
            return {'status': 'printed', 'printer': printer}
        else:
            import subprocess
            subprocess.run(['lp', '-d', printer_name], input=text_content.encode('utf-8'))
            return {'status': 'printed', 'printer': printer_name}
            
    async def print_raw(self, printer_name, raw_commands):
        """طباعة أوامر خام (ESC/POS للطابعات الحرارية)"""
        # raw_commands يجب أن يكون base64 أو hex
        import base64
        
        if isinstance(raw_commands, str):
            # تحويل من base64
            raw_bytes = base64.b64decode(raw_commands)
        else:
            raw_bytes = bytes(raw_commands)
            
        if sys.platform == 'win32':
            import win32print
            
            printer = printer_name if printer_name in self.printers else win32print.GetDefaultPrinter()
            
            hPrinter = win32print.OpenPrinter(printer)
            try:
                hJob = win32print.StartDocPrinter(hPrinter, 1, ("Tony ERP RAW", None, "RAW"))
                win32print.StartPagePrinter(hPrinter)
                win32print.WritePrinter(hPrinter, raw_bytes)
                win32print.EndPagePrinter(hPrinter)
                win32print.EndDocPrinter(hPrinter)
            finally:
                win32print.ClosePrinter(hPrinter)
                
            return {'status': 'printed', 'printer': printer, 'bytes': len(raw_bytes)}
        else:
            # على Linux - إرسال مباشر للطابعة
            with open(f'/dev/usb/lp0', 'wb') as printer_device:
                printer_device.write(raw_bytes)
            return {'status': 'printed', 'bytes': len(raw_bytes)}
            
    async def print_pdf(self, printer_name, pdf_data):
        """طباعة ملف PDF"""
        import base64
        
        # تحويل من base64
        pdf_bytes = base64.b64decode(pdf_data)
        
        # حفظ مؤقتًا
        temp_pdf = Path('temp_print.pdf')
        temp_pdf.write_bytes(pdf_bytes)
        
        if sys.platform == 'win32':
            import win32api
            import win32print
            
            printer = printer_name if printer_name in self.printers else win32print.GetDefaultPrinter()
            
            win32api.ShellExecute(
                0,
                "print",
                str(temp_pdf.absolute()),
                f'/d:"{printer}"',
                ".",
                0
            )
            
            return {'status': 'sent', 'printer': printer}
        else:
            import subprocess
            subprocess.run(['lp', '-d', printer_name, str(temp_pdf)])
            return {'status': 'sent', 'printer': printer_name}
            
    async def handle_test_print(self, websocket, data):
        """طباعة اختبارية"""
        printer_name = data.get('printer', 'default')
        
        test_content = f"""
╔═══════════════════════════════════════╗
║      Tony ERP - طباعة اختبارية       ║
╚═══════════════════════════════════════╝

الطابعة: {printer_name}
التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

✓ الطابعة تعمل بشكل صحيح
✓ الاتصال سليم
✓ النظام جاهز للطباعة

════════════════════════════════════════

        """
        
        await self.handle_print(websocket, {
            'printer': printer_name,
            'type': 'text',
            'content': test_content
        })
        
    async def send_error(self, websocket, error_message):
        """إرسال رسالة خطأ"""
        response = {
            'event': 'error',
            'error': error_message,
            'timestamp': datetime.now().isoformat()
        }
        await websocket.send(json.dumps(response, ensure_ascii=False))
        
    async def start(self):
        """تشغيل الخدمة"""
        logger.info(f"🚀 بدء خدمة الطباعة على {self.host}:{self.port}")
        logger.info(f"📊 الطابعات المتاحة: {len(self.printers)}")
        
        async with serve(self.handle_client, self.host, self.port):  # type: ignore[arg-type]
            logger.info("✓ الخدمة جاهزة - في انتظار الاتصالات...")
            await asyncio.Future()  # تشغيل مستمر


def main():
    """النقطة الرئيسية للتشغيل"""
    print("""
╔═══════════════════════════════════════════════════════════╗
║           Tony ERP - Print Agent v1.0                     ║
║           وكيل الطباعة المحلي                            ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    try:
        agent = PrintAgent()
        asyncio.run(agent.start())
    except KeyboardInterrupt:
        logger.info("\n👋 إيقاف الخدمة...")
    except Exception as e:
        logger.error(f"❌ خطأ فادح: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
