#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tony ERP - Local Print Agent for Windows
خدمة محلية للطباعة المباشرة على الطابعات الحرارية
نسخة مُحسّنة لـ Windows مع دعم XPrinter
"""

import asyncio
import json
import logging
import sys
import os
from datetime import datetime

try:
    import websockets
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


class WindowsPrintAgent:
    """وكيل الطباعة المحلي لـ Windows"""
    
    def __init__(self, host='localhost', port=9876):
        self.host = host
        self.port = port
        self.clients = set()
        self.printers = {}
        self.default_printer = None
        self.detect_printers()
        
    def detect_printers(self):
        """كشف الطابعات المتاحة على Windows"""
        try:
            import win32print
            
            # الطابعة الافتراضية
            try:
                self.default_printer = win32print.GetDefaultPrinter()
                logger.info(f"✓ الطابعة الافتراضية: {self.default_printer}")
            except:
                pass
            
            # كل الطابعات
            printers = win32print.EnumPrinters(
                win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
            )
            
            for flags, description, name, comment in printers:
                self.printers[name] = {
                    'name': name,
                    'type': 'windows',
                    'status': 'ready',
                    'description': description
                }
                logger.info(f"  • طابعة: {name}")
            
            logger.info(f"✓ تم اكتشاف {len(self.printers)} طابعة")
            
        except ImportError:
            logger.warning("⚠ win32print غير متوفر - جاري استخدام طريقة بديلة...")
            self._detect_printers_alternative()
        except Exception as e:
            logger.error(f"❌ خطأ في كشف الطابعات: {e}")
            self._detect_printers_alternative()
    
    def _detect_printers_alternative(self):
        """طريقة بديلة لكشف الطابعات باستخدام wmic"""
        try:
            import subprocess
            result = subprocess.run(
                ['wmic', 'printer', 'get', 'name,default'],
                capture_output=True,
                text=True,
                shell=True
            )
            
            lines = result.stdout.strip().split('\n')[1:]  # تجاهل العنوان
            for line in lines:
                line = line.strip()
                if line:
                    parts = line.split()
                    if len(parts) >= 1:
                        # اسم الطابعة قد يحتوي مسافات
                        if 'TRUE' in line:
                            name = line.replace('TRUE', '').strip()
                            self.default_printer = name
                        else:
                            name = line.replace('FALSE', '').strip()
                        
                        if name:
                            self.printers[name] = {
                                'name': name,
                                'type': 'windows',
                                'status': 'ready'
                            }
                            logger.info(f"  • طابعة: {name}")
            
            logger.info(f"✓ تم اكتشاف {len(self.printers)} طابعة (طريقة بديلة)")
            
        except Exception as e:
            logger.error(f"❌ فشل الكشف البديل: {e}")
            # إضافة طابعة وهمية للاختبار
            self.printers['XPrinter'] = {
                'name': 'XPrinter (تلقائي)',
                'type': 'thermal',
                'status': 'ready'
            }
            
    async def handle_client(self, websocket):
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
            self.clients.discard(websocket)
            
    async def send_printers_list(self, websocket):
        """إرسال قائمة الطابعات"""
        response = {
            'event': 'printers_list',
            'printers': list(self.printers.values()),
            'default_printer': self.default_printer,
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
        content_type = data.get('type', 'text')
        content = data.get('content', '')
        
        logger.info(f"📄 طلب طباعة - نوع: {content_type}")
        
        try:
            if content_type == 'text':
                result = await self.print_text_direct(printer_name, content)
            elif content_type == 'html':
                # تحويل HTML لنص بسيط وطباعته
                result = await self.print_html_as_text(printer_name, content)
            elif content_type == 'raw':
                result = await self.print_raw(printer_name, content)
            else:
                result = await self.print_text_direct(printer_name, str(content))
                
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
    
    async def print_text_direct(self, printer_name, text_content):
        """طباعة نص مباشرة على الطابعة - الطريقة الأساسية"""
        
        # محاولة 1: استخدام win32print
        try:
            import win32print
            import win32ui
            
            # اختيار الطابعة
            if printer_name == 'default' or printer_name not in self.printers:
                printer = self.default_printer or win32print.GetDefaultPrinter()
            else:
                printer = printer_name
            
            logger.info(f"🖨️ الطباعة على: {printer}")
            
            # فتح الطابعة
            hPrinter = win32print.OpenPrinter(printer)
            try:
                # بدء مهمة طباعة
                hJob = win32print.StartDocPrinter(hPrinter, 1, ("Tony ERP Receipt", "", "RAW"))
                win32print.StartPagePrinter(hPrinter)
                
                # تحويل النص لبايتات
                # للطابعات الحرارية نستخدم CP437 أو UTF-8
                try:
                    text_bytes = text_content.encode('cp437', errors='replace')
                except:
                    text_bytes = text_content.encode('utf-8', errors='replace')
                
                # إضافة أوامر ESC/POS
                init_printer = bytes([0x1B, 0x40])  # Initialize
                cut_paper = bytes([0x1D, 0x56, 0x00])  # Full cut
                
                # إرسال للطابعة
                win32print.WritePrinter(hPrinter, init_printer)
                win32print.WritePrinter(hPrinter, text_bytes)
                win32print.WritePrinter(hPrinter, b'\n\n\n')  # أسطر فارغة
                win32print.WritePrinter(hPrinter, cut_paper)
                
                # إنهاء
                win32print.EndPagePrinter(hPrinter)
                win32print.EndDocPrinter(hPrinter)
                
                return {'status': 'printed', 'printer': printer, 'method': 'win32print'}
                
            finally:
                win32print.ClosePrinter(hPrinter)
                
        except ImportError:
            logger.warning("win32print غير متوفر، جاري تجربة طريقة بديلة...")
            return await self.print_via_notepad(text_content)
        except Exception as e:
            logger.error(f"خطأ win32print: {e}")
            return await self.print_via_notepad(text_content)
    
    async def print_via_notepad(self, text_content):
        """طريقة بديلة: حفظ في ملف وطباعته"""
        import subprocess
        import tempfile
        
        # حفظ النص في ملف مؤقت
        temp_file = os.path.join(tempfile.gettempdir(), 'tony_receipt.txt')
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(text_content)
        
        # طباعة الملف
        try:
            # محاولة الطباعة مباشرة
            os.startfile(temp_file, 'print')  # type: ignore[attr-defined]
            return {'status': 'sent_to_print', 'method': 'startfile', 'file': temp_file}
        except Exception as e:
            logger.error(f"فشل startfile: {e}")
            # محاولة أخرى باستخدام notepad
            subprocess.Popen(['notepad', '/p', temp_file], shell=True)
            return {'status': 'sent_to_notepad', 'method': 'notepad', 'file': temp_file}
    
    async def print_html_as_text(self, printer_name, html_content):
        """تحويل HTML لنص وطباعته"""
        import re
        
        # إزالة تاجات HTML
        text = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL)
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
        text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</p>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</div>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</tr>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</td>', '  ', text, flags=re.IGNORECASE)
        text = re.sub(r'<[^>]+>', '', text)
        
        # تنظيف المسافات
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = text.strip()
        
        # إضافة خطوط فاصلة
        lines = text.split('\n')
        formatted_lines = []
        for line in lines:
            line = line.strip()
            if line:
                formatted_lines.append(line)
        
        formatted_text = '\n'.join(formatted_lines)
        
        return await self.print_text_direct(printer_name, formatted_text)
    
    async def print_raw(self, printer_name, raw_commands):
        """طباعة أوامر خام ESC/POS"""
        import base64
        
        try:
            import win32print
            
            # تحويل من base64
            if isinstance(raw_commands, str):
                raw_bytes = base64.b64decode(raw_commands)
            else:
                raw_bytes = bytes(raw_commands)
            
            # اختيار الطابعة
            if printer_name == 'default' or printer_name not in self.printers:
                printer = self.default_printer or win32print.GetDefaultPrinter()
            else:
                printer = printer_name
            
            hPrinter = win32print.OpenPrinter(printer)
            try:
                hJob = win32print.StartDocPrinter(hPrinter, 1, ("Tony ERP RAW", "", "RAW"))
                win32print.StartPagePrinter(hPrinter)
                win32print.WritePrinter(hPrinter, raw_bytes)
                win32print.EndPagePrinter(hPrinter)
                win32print.EndDocPrinter(hPrinter)
            finally:
                win32print.ClosePrinter(hPrinter)
                
            return {'status': 'printed', 'printer': printer, 'bytes': len(raw_bytes)}
            
        except Exception as e:
            logger.error(f"خطأ في طباعة RAW: {e}")
            raise
            
    async def handle_test_print(self, websocket, data):
        """طباعة اختبارية"""
        printer_name = data.get('printer', 'default')
        
        test_content = f"""
================================
   Tony ERP - طباعة اختبارية
================================

الطابعة: {printer_name}
التاريخ: {datetime.now().strftime('%Y-%m-%d')}
الوقت: {datetime.now().strftime('%H:%M:%S')}

--------------------------------

✓ الطابعة تعمل بشكل صحيح
✓ الاتصال سليم
✓ النظام جاهز للطباعة

--------------------------------
         شكراً لاستخدامكم
          Tony ERP System
================================


"""
        
        try:
            result = await self.print_text_direct(printer_name, test_content)
            
            response = {
                'event': 'print_success',
                'result': result,
                'timestamp': datetime.now().isoformat()
            }
            await websocket.send(json.dumps(response, ensure_ascii=False))
            logger.info("✓ تمت طباعة الاختبار بنجاح")
            
        except Exception as e:
            await self.send_error(websocket, str(e))
        
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
        if self.default_printer:
            logger.info(f"🖨️ الطابعة الافتراضية: {self.default_printer}")
        
        async with websockets.serve(self.handle_client, self.host, self.port):
            logger.info("✓ الخدمة جاهزة - في انتظار الاتصالات...")
            await asyncio.Future()  # تشغيل مستمر


def main():
    """النقطة الرئيسية للتشغيل"""
    print("""
╔═══════════════════════════════════════════════════════════╗
║       Tony ERP - Print Agent v2.0 (Windows)               ║
║       وكيل الطباعة المحلي - نسخة محسنة                   ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    # التحقق من win32print
    try:
        import win32print
        print("✓ win32print متوفر")
    except ImportError:
        print("⚠ win32print غير متوفر - جاري استخدام طريقة بديلة")
        print("  لتثبيته: pip install pywin32")
        print("  ثم: python -m pywin32_postinstall -install")
        print("")
    
    try:
        agent = WindowsPrintAgent()
        asyncio.run(agent.start())
    except KeyboardInterrupt:
        logger.info("\n👋 إيقاف الخدمة...")
    except Exception as e:
        logger.error(f"❌ خطأ فادح: {e}")
        import traceback
        traceback.print_exc()
        input("\nاضغط Enter للإغلاق...")
        sys.exit(1)


if __name__ == '__main__':
    main()
