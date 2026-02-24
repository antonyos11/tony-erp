#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tony ERP Print Agent v3.2 - Windows
وكيل الطباعة المحلي - يدعم 3 أنواع طابعات:
  1. Zebra ZD220 (ZPL - باركود/ملصقات)
  2. XPrinter XP-80 (ESC/POS - إيصالات حرارية)
  3. RICOH Aficio / أي A4 (PDF/HTML - فواتير/تقارير)

التشغيل:
  python agent_windows.py

التثبيت:
  pip install websockets pywin32 Pillow arabic-reshaper python-bidi
  python -m pywin32_postinstall -install
"""

import asyncio
import json
import logging
import sys
import os
import tempfile
import socket
import platform
import base64
import re
import time as _time
from datetime import datetime

AGENT_VERSION = '3.3'

try:
    import websockets
except ImportError:
    print("websockets not installed! Run: pip install websockets")
    sys.exit(1)

# Optional psutil for better process management
PSUTIL_AVAILABLE = False
psutil: object = None  # type: ignore[assignment]
try:
    import psutil  # type: ignore[no-redef]
    PSUTIL_AVAILABLE = True
except ImportError:
    pass

# Windows printing
WIN32_AVAILABLE = False
win32print: object = None  # type: ignore[assignment]
win32api: object = None  # type: ignore[assignment]
win32con: object = None  # type: ignore[assignment]
try:
    import win32print  # type: ignore[no-redef]
    import win32api  # type: ignore[no-redef]
    import win32con  # type: ignore[no-redef]
    WIN32_AVAILABLE = True
except ImportError:
    print("pywin32 not installed - some features won't work")

PIL_AVAILABLE = False
Image: object = None  # type: ignore[assignment]
ImageDraw: object = None  # type: ignore[assignment]
ImageFont: object = None  # type: ignore[assignment]
try:
    from PIL import Image, ImageDraw, ImageFont  # type: ignore[no-redef]
    PIL_AVAILABLE = True
except ImportError:
    print("Pillow not installed - image printing won't work")

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('print_agent.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

AGENT_PORT = int(os.environ.get('AGENT_PORT', '9876'))
AGENT_HOST = os.environ.get('AGENT_HOST', '0.0.0.0')

# ERP Server WebSocket URL — agent connects TO the server to register itself
ERP_WS_URL = os.environ.get('ERP_WS_URL', 'ws://72.62.176.249/ws/print-agent/')


def _kill_port_holders(port: int):
    """Kill any process occupying the given port. Prevents OSError 10048 on Windows."""
    import subprocess
    if platform.system() != 'Windows':
        # On Linux, try lsof
        try:
            result = subprocess.run(
                ['lsof', '-ti', f':{port}'],
                capture_output=True, text=True, timeout=5,
            )
            for pid_str in result.stdout.strip().split('\n'):
                pid_str = pid_str.strip()
                if pid_str and pid_str.isdigit():
                    pid = int(pid_str)
                    if pid != os.getpid():
                        os.kill(pid, 9)
                        logger.info(f"Killed PID {pid} occupying port {port}")
        except Exception:
            pass
        return

    try:
        result = subprocess.run(
            ['netstat', '-ano', '-p', 'TCP'],
            capture_output=True, text=True, timeout=10,
        )
        target = f':{port}'
        pids_to_kill = set()
        for line in result.stdout.splitlines():
            if target in line and ('LISTENING' in line or 'TIME_WAIT' in line):
                parts = line.split()
                if parts:
                    try:
                        pid = int(parts[-1])
                        if pid > 0 and pid != os.getpid():
                            pids_to_kill.add(pid)
                    except (ValueError, IndexError):
                        pass

        for pid in pids_to_kill:
            try:
                subprocess.run(
                    ['taskkill', '/F', '/PID', str(pid)],
                    capture_output=True, timeout=5,
                )
                logger.info(f"Killed PID {pid} occupying port {port}")
            except Exception as e:
                logger.warning(f"Could not kill PID {pid}: {e}")

        if pids_to_kill:
            _time.sleep(1)  # Allow OS to release the port

    except Exception as e:
        logger.warning(f"Port cleanup failed: {e}")


class WindowsPrintAgent:
    """Local print agent for Windows - supports Zebra + XPrinter + A4"""

    def __init__(self, host=AGENT_HOST, port=AGENT_PORT):
        self.host = host
        self.port = port
        self.clients = set()
        self.printers_cache = {'zebra': [], 'thermal': [], 'a4': [], 'all': []}
        self.default_printer = None

        # Machine identity — sent to ERP on connect
        self.machine_name = platform.node() or socket.gethostname()
        self.machine_ip = self._get_local_ip()
        self.os_platform = 'windows'

        # Auto-clear port before binding (fixes OSError 10048)
        _kill_port_holders(self.port)

        self._discover_printers()

    def _get_local_ip(self):
        """Get the local network IP (not 127.0.0.1)."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(1)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return '127.0.0.1'

    def _build_registration_message(self):
        """Build the registration payload sent to ERP on every connection."""
        printers_list = []
        for p in self.printers_cache.get('all', []):
            printers_list.append({
                'name': p.get('name', ''),
                'type': p.get('type', 'unknown'),
            })

        return {
            'type': 'register',
            'machine_name': self.machine_name,
            'machine_ip': self.machine_ip,
            'agent_version': AGENT_VERSION,
            'os_platform': self.os_platform,
            'agent_port': self.port,
            'printers': printers_list,
        }

    # ============================================
    # Printer Discovery
    # ============================================

    def _discover_printers(self):
        self.printers_cache = {'zebra': [], 'thermal': [], 'a4': [], 'all': []}

        if not WIN32_AVAILABLE:
            self._discover_printers_wmic()
            return

        zebra_kw = ['zebra', 'ze220', 'zd420', 'zd220', 'zpl', 'zt230', 'zt410', 'gk420']
        thermal_kw = ['xp-80', 'xp80', 'xprinter', 'thermal', 'pos-80', 'receipt',
                      'tm-t', 'rp80', 'pos80', 'xp-58', 'xp58', 'pos58', 'rongta']

        try:
            try:
                self.default_printer = win32print.GetDefaultPrinter()
            except Exception:
                pass

            flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
            for printer in win32print.EnumPrinters(flags):
                name = printer[2]
                name_lower = name.lower()

                info = {
                    'name': name,
                    'description': printer[1] or '',
                    'type': 'a4',
                    'is_default': name == self.default_printer
                }

                classified = False
                for kw in zebra_kw:
                    if kw in name_lower:
                        info['type'] = 'zebra'
                        self.printers_cache['zebra'].append(info)
                        classified = True
                        break

                if not classified:
                    for kw in thermal_kw:
                        if kw in name_lower:
                            info['type'] = 'thermal'
                            self.printers_cache['thermal'].append(info)
                            classified = True
                            break

                if not classified:
                    self.printers_cache['a4'].append(info)

                self.printers_cache['all'].append(info)

            logger.info("Printers discovered:")
            logger.info(f"  Zebra:   {[p['name'] for p in self.printers_cache['zebra']]}")
            logger.info(f"  Thermal: {[p['name'] for p in self.printers_cache['thermal']]}")
            logger.info(f"  A4:      {[p['name'] for p in self.printers_cache['a4']]}")

        except Exception as e:
            logger.error(f"Error discovering printers: {e}")
            self._discover_printers_wmic()

    def _discover_printers_wmic(self):
        try:
            import subprocess
            result = subprocess.run(
                ['wmic', 'printer', 'get', 'name,default'],
                capture_output=True, text=True, shell=True
            )
            lines = result.stdout.strip().split('\n')[1:]
            for line in lines:
                line = line.strip()
                if line:
                    is_default = 'TRUE' in line
                    name = line.replace('TRUE', '').replace('FALSE', '').strip()
                    if name:
                        info = {'name': name, 'type': 'a4', 'is_default': is_default}
                        self.printers_cache['all'].append(info)
                        self.printers_cache['a4'].append(info)
                        if is_default:
                            self.default_printer = name
        except Exception as e:
            logger.error(f"wmic failed: {e}")

    def _find_printer(self, printer_name=None, printer_type=None):
        """
        Find printer by exact name first, then by partial match, then by type.

        CRITICAL FIX: When the server sends printer_name='XP-80C (copy 2)',
        we must use EXACTLY that name, not fall back to copy 3.
        """
        if printer_name:
            # 1. Exact match (case-insensitive)
            for p in self.printers_cache.get('all', []):
                if p['name'].lower() == printer_name.lower():
                    logger.info(f"Printer exact match: '{printer_name}' -> '{p['name']}'")
                    return p['name']

            # 2. Partial match — but ONLY if there's exactly one match
            #    This prevents 'XP-80' from ambiguously matching
            #    'XP-80 (copy 2)' AND 'XP-80 (copy 3)'
            partial_matches = []
            for p in self.printers_cache.get('all', []):
                if printer_name.lower() in p['name'].lower():
                    partial_matches.append(p['name'])

            if len(partial_matches) == 1:
                logger.info(f"Printer partial match: '{printer_name}' -> '{partial_matches[0]}'")
                return partial_matches[0]
            elif len(partial_matches) > 1:
                logger.warning(
                    f"Ambiguous printer match for '{printer_name}': {partial_matches}. "
                    f"Using first match. Admin should set exact name in station mappings."
                )
                return partial_matches[0]

        # 3. Fall back to type-based selection
        if printer_type:
            printers = self.printers_cache.get(printer_type, [])
            if printers:
                logger.info(f"Printer type fallback: type={printer_type} -> '{printers[0]['name']}'")
                return printers[0]['name']

        # 4. Last resort — default printer
        if self.default_printer:
            return self.default_printer
        try:
            return win32print.GetDefaultPrinter()
        except Exception:
            return None

    def _send_raw_to_printer(self, printer_name, raw_data, doc_name="Tony ERP"):
        if not WIN32_AVAILABLE:
            raise RuntimeError("pywin32 not available")

        if isinstance(raw_data, str):
            raw_data = raw_data.encode('utf-8')

        hPrinter = win32print.OpenPrinter(printer_name)
        try:
            win32print.StartDocPrinter(hPrinter, 1, (doc_name, None, "RAW"))
            win32print.StartPagePrinter(hPrinter)
            win32print.WritePrinter(hPrinter, raw_data)
            win32print.EndPagePrinter(hPrinter)
            win32print.EndDocPrinter(hPrinter)
        finally:
            win32print.ClosePrinter(hPrinter)

    # ============================================
    # 1. Zebra ZE220 - ZPL (Barcode/Labels)
    # ============================================

    async def print_zebra_zpl(self, data):
        zpl_commands = data.get('zpl', '')
        printer_name = data.get('printer_name', '')
        ip = data.get('ip', '')
        port = int(data.get('port', 9100))

        if not zpl_commands:
            return {'success': False, 'error': 'No ZPL commands provided'}

        # Method 1: Network socket (fastest)
        if ip:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(10)
                sock.connect((ip, port))
                sock.sendall(zpl_commands.encode('utf-8'))
                sock.close()
                logger.info(f"ZPL -> Zebra Network {ip}:{port}")
                return {'success': True, 'method': 'network', 'ip': ip}
            except Exception as e:
                logger.warning(f"Network failed ({ip}): {e}, trying USB...")

        # Method 2: USB via win32print RAW
        printer = self._find_printer(printer_name, 'zebra')
        if not printer:
            return {'success': False, 'error': 'Zebra printer not found. Make sure driver is installed.'}

        try:
            self._send_raw_to_printer(printer, zpl_commands, "ZPL Label")
            logger.info(f"ZPL -> Zebra USB: {printer}")
            return {'success': True, 'method': 'usb', 'printer': printer}
        except Exception as e:
            logger.error(f"Zebra error: {e}")
            return {'success': False, 'error': str(e)}

    async def print_zebra_label(self, data):
        barcode_val = data.get('barcode', '')
        product_name = data.get('product_name', '')
        price = data.get('price', '')
        size_text = data.get('size_text', '')
        label_w = int(data.get('label_width_mm', 50))
        label_h = int(data.get('label_height_mm', 30))
        dpi = int(data.get('dpi', 203))
        copies = int(data.get('copies', 1))
        manufacture_date = data.get('manufacture_date', '')
        expiry_date = data.get('expiry_date', '')

        if not barcode_val:
            return {'success': False, 'error': 'No barcode value'}

        dots_per_mm = dpi / 25.4
        w = int(label_w * dots_per_mm)
        h = int(label_h * dots_per_mm)

        zpl = f"^XA\n^PW{w}\n^LL{h}\n^CI28\n"

        if product_name:
            fn_h = max(18, int(h * 0.12))
            zpl += f"^FO{int(w*0.05)},{int(h*0.05)}^A0N,{fn_h},{int(fn_h*0.85)}^FD{product_name[:30]}^FS\n"

        if size_text:
            fn_h = max(14, int(h * 0.08))
            zpl += f"^FO{int(w*0.05)},{int(h*0.20)}^A0N,{fn_h},{int(fn_h*0.85)}^FDSize: {size_text}^FS\n"

        y_price = 0.30
        if price:
            fn_h = max(16, int(h * 0.10))
            zpl += f"^FO{int(w*0.05)},{int(h*y_price)}^A0N,{fn_h},{int(fn_h*0.85)}^FD{price}^FS\n"
            y_price += 0.12

        if manufacture_date:
            fn_h = max(12, int(h * 0.06))
            zpl += f"^FO{int(w*0.05)},{int(h*y_price)}^A0N,{fn_h},{int(fn_h*0.85)}^FDMFG: {manufacture_date}^FS\n"

        if expiry_date:
            fn_h = max(12, int(h * 0.06))
            zpl += f"^FO{int(w*0.55)},{int(h*y_price)}^A0N,{fn_h},{int(fn_h*0.85)}^FDEXP: {expiry_date}^FS\n"

        barcode_x = int(w * 0.07)
        barcode_y = int(h * 0.52)
        barcode_h = max(30, int(h * 0.30))
        module_w = max(1, min(3, w // (len(barcode_val) * 12)))

        zpl += f"^FO{barcode_x},{barcode_y}^BY{module_w},3,{barcode_h}^BCN,,Y,N,N^FD{barcode_val}^FS\n"
        zpl += f"^PQ{copies}\n^XZ\n"

        data['zpl'] = zpl
        result = await self.print_zebra_zpl(data)
        if result.get('success'):
            result['label_size'] = f"{label_w}x{label_h}mm"
            result['copies'] = copies
        return result

    # ============================================
    # 2. XPrinter - Thermal (ESC/POS Receipts)
    # ============================================

    async def print_thermal_receipt(self, data):
        printer_name = data.get('printer_name', '')
        open_drawer = data.get('open_drawer', False)
        cut_paper = data.get('cut_paper', True)

        printer = self._find_printer(printer_name, 'thermal')
        if not printer:
            printer = self._find_printer(printer_name)
        if not printer:
            return {'success': False, 'error': 'Thermal printer (XPrinter) not found'}

        ESC = b'\x1b'
        GS = b'\x1d'
        raw_data = bytearray()
        raw_data += ESC + b'@'

        if open_drawer:
            raw_data += ESC + b'p\x00\x19\xfa'

        if data.get('raw_base64'):
            try:
                raw_data += base64.b64decode(data['raw_base64'])
            except Exception as e:
                return {'success': False, 'error': f'base64 decode error: {e}'}

        elif data.get('raw_commands'):
            raw_cmds = data['raw_commands']
            if isinstance(raw_cmds, str):
                try:
                    raw_data += base64.b64decode(raw_cmds)
                except Exception:
                    raw_data += raw_cmds.encode('utf-8', errors='replace')
            elif isinstance(raw_cmds, list):
                raw_data += bytes(raw_cmds)

        elif data.get('content'):
            content = data['content']
            try:
                import arabic_reshaper
                from bidi.algorithm import get_display
                for line in content.split('\n'):
                    if any('\u0600' <= c <= '\u06FF' for c in line):
                        reshaped = arabic_reshaper.reshape(line)
                        bidi_line = get_display(reshaped)
                        raw_data += bidi_line.encode('utf-8', errors='replace') + b'\n'
                    else:
                        raw_data += line.encode('utf-8', errors='replace') + b'\n'
            except ImportError:
                raw_data += content.encode('utf-8', errors='replace')

        elif data.get('html'):
            html = data['html']
            text = re.sub(r'<br\s*/?>', '\n', html, flags=re.IGNORECASE)
            text = re.sub(r'</p>', '\n', text, flags=re.IGNORECASE)
            text = re.sub(r'</tr>', '\n', text, flags=re.IGNORECASE)
            text = re.sub(r'</td>', '  ', text, flags=re.IGNORECASE)
            text = re.sub(r'<[^>]+>', '', text)
            text = re.sub(r'&amp;', '&', text)
            text = re.sub(r'&lt;', '<', text)
            text = re.sub(r'&gt;', '>', text)
            text = re.sub(r'&nbsp;', ' ', text)
            raw_data += text.encode('utf-8', errors='replace')
        else:
            return {'success': False, 'error': 'No content to print'}

        if cut_paper:
            raw_data += b'\n\n\n'
            raw_data += GS + b'V\x00'

        try:
            self._send_raw_to_printer(printer, bytes(raw_data), "Receipt")
            logger.info(f"Receipt -> XPrinter: {printer} ({len(raw_data)} bytes)")
            return {'success': True, 'printer': printer, 'bytes': len(raw_data)}
        except Exception as e:
            logger.error(f"XPrinter error: {e}")
            return {'success': False, 'error': str(e)}

    async def print_thermal_image(self, data):
        if not PIL_AVAILABLE:
            return {'success': False, 'error': 'Pillow not installed: pip install Pillow'}

        from io import BytesIO

        printer_name = data.get('printer_name', '')
        target_width = int(data.get('width', 384))

        try:
            if data.get('image_base64'):
                img_data = base64.b64decode(data['image_base64'])
                img = Image.open(BytesIO(img_data))
            elif data.get('image_path'):
                img = Image.open(data['image_path'])
            else:
                return {'success': False, 'error': 'No image provided'}
        except Exception as e:
            return {'success': False, 'error': f'Image load error: {e}'}

        img = img.convert('1')
        ratio = target_width / img.width
        img = img.resize((target_width, int(img.height * ratio)))

        raw_data = bytearray(b'\x1b@')
        width_bytes = (img.width + 7) // 8

        for y in range(img.height):
            row_data = bytearray(width_bytes)
            for x in range(img.width):
                if img.getpixel((x, y)) == 0:
                    row_data[x // 8] |= (0x80 >> (x % 8))
            raw_data += b'\x1dv0\x00'
            raw_data += bytes([width_bytes & 0xFF, (width_bytes >> 8) & 0xFF])
            raw_data += bytes([1, 0])
            raw_data += bytes(row_data)

        raw_data += b'\n\n\n\x1dV\x00'

        printer = self._find_printer(printer_name, 'thermal')
        if not printer:
            return {'success': False, 'error': 'Thermal printer not found'}

        try:
            self._send_raw_to_printer(printer, bytes(raw_data), "Receipt Image")
            logger.info(f"Image -> XPrinter: {printer} ({len(raw_data)} bytes)")
            return {'success': True, 'printer': printer, 'bytes': len(raw_data)}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    # ============================================
    # 3. A4 Printing - Invoices & Reports
    # ============================================

    async def print_a4_document(self, data):
        printer_name = data.get('printer_name', '')
        copies = int(data.get('copies', 1))

        printer = self._find_printer(printer_name, 'a4')
        if not printer:
            printer = self._find_printer(printer_name)
        if not printer:
            return {'success': False, 'error': 'A4 printer not found'}

        temp_path = None
        try:
            if data.get('pdf_base64'):
                pdf_data = base64.b64decode(data['pdf_base64'])
                fd, temp_path = tempfile.mkstemp(suffix='.pdf')
                with os.fdopen(fd, 'wb') as f:
                    f.write(pdf_data)

                for _ in range(copies):
                    win32api.ShellExecute(0, "printto", temp_path, f'"{printer}"', ".", 0)

                logger.info(f"PDF -> A4: {printer} ({copies} copies)")
                return {'success': True, 'printer': printer, 'copies': copies, 'method': 'pdf'}

            elif data.get('pdf_url'):
                import urllib.request
                fd, temp_path = tempfile.mkstemp(suffix='.pdf')
                os.close(fd)
                urllib.request.urlretrieve(data['pdf_url'], temp_path)

                for _ in range(copies):
                    win32api.ShellExecute(0, "printto", temp_path, f'"{printer}"', ".", 0)

                logger.info(f"PDF URL -> A4: {printer}")
                return {'success': True, 'printer': printer, 'method': 'pdf_url'}

            elif data.get('html'):
                fd, temp_path = tempfile.mkstemp(suffix='.html')
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    f.write(f"""<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head><meta charset="utf-8">
<style>body {{ font-family: Arial, sans-serif; direction: rtl; }}
@media print {{ body {{ margin: 0; }} }}</style></head>
<body>{data['html']}</body></html>""")

                for browser in [
                    r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
                    r'C:\Program Files\Google\Chrome\Application\chrome.exe',
                    r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
                ]:
                    if os.path.exists(browser):
                        import subprocess
                        cmd = f'"{browser}" --headless --disable-gpu --print-to-pdf-no-header --print-to-printer="{printer}" "file:///{temp_path}"'
                        subprocess.Popen(cmd, shell=True)
                        logger.info(f"HTML -> A4: {printer} (browser)")
                        return {'success': True, 'printer': printer, 'method': 'browser'}

                win32api.ShellExecute(0, "print", temp_path, None, ".", 0)
                return {'success': True, 'printer': printer, 'method': 'shell_print'}
            else:
                return {'success': False, 'error': 'No content (pdf_base64, pdf_url, or html)'}

        except Exception as e:
            logger.error(f"A4 error: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            if temp_path:
                async def _cleanup():
                    await asyncio.sleep(30)
                    try:
                        os.unlink(temp_path)
                    except OSError:
                        pass
                asyncio.ensure_future(_cleanup())

    # ============================================
    # Generic Print (backward compat)
    # ============================================

    async def print_generic(self, data):
        printer_name = data.get('printer', 'default')
        content_type = data.get('type', 'text')
        content = data.get('content', '')

        if content_type == 'raw':
            raw_bytes = base64.b64decode(content) if isinstance(content, str) else bytes(content)
            printer = self._find_printer(printer_name)
            if not printer:
                return {'success': False, 'error': 'Printer not found'}
            self._send_raw_to_printer(printer, raw_bytes, "Tony ERP RAW")
            return {'success': True, 'printer': printer, 'bytes': len(raw_bytes)}

        elif content_type == 'html':
            return await self.print_thermal_receipt({'html': content, 'printer_name': printer_name})
        else:
            return await self.print_thermal_receipt({'content': str(content), 'printer_name': printer_name})

    # ============================================
    # Test Print
    # ============================================

    async def handle_test_print(self, data):
        printer_type = data.get('printer_type', 'all')
        results = {}

        if printer_type in ('all', 'zebra') and self.printers_cache.get('zebra'):
            zpl_test = "^XA\n^PW400^LL300\n^FO30,30^A0N,40,40^FDTony ERP v3.0^FS\n^FO30,80^A0N,25,25^FDTest Print OK!^FS\n^FO30,130^BCN,80,Y,N,N^FD123456789012^FS\n^XZ"
            results['zebra'] = await self.print_zebra_zpl({
                'zpl': zpl_test,
                'printer_name': self.printers_cache['zebra'][0]['name']
            })

        if printer_type in ('all', 'thermal') and self.printers_cache.get('thermal'):
            results['thermal'] = await self.print_thermal_receipt({
                'content': '================================\n      Tony ERP v3.0\n      Test Print OK!\n================================\n   ' + datetime.now().strftime('%Y-%m-%d %H:%M') + '\n\n  Thermal Printer Working\n================================\n\n\n',
                'printer_name': self.printers_cache['thermal'][0]['name'],
                'cut_paper': True
            })

        if printer_type in ('all', 'a4') and self.printers_cache.get('a4'):
            results['a4'] = await self.print_a4_document({
                'html': '<div style="text-align:center;padding:50px;"><h1>Tony ERP v3.0</h1><h2>A4 Test Print - OK!</h2><p>' + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '</p></div>',
                'printer_name': self.printers_cache['a4'][0]['name']
            })

        return {'success': True, 'results': results}

    # ============================================
    # WebSocket Handler
    # ============================================

    async def handle_message(self, websocket, message):
        try:
            data = json.loads(message)
            action = data.get('action', '')
            request_id = data.get('request_id', '')

            logger.info(f"Request: {action}" + (f" [#{request_id}]" if request_id else ''))

            result = {}

            if action == 'print_zebra_zpl':
                result = await self.print_zebra_zpl(data)
            elif action == 'print_zebra_label':
                result = await self.print_zebra_label(data)
            elif action == 'print_thermal_receipt':
                result = await self.print_thermal_receipt(data)
            elif action == 'print_thermal_image':
                result = await self.print_thermal_image(data)
            elif action == 'print_a4':
                result = await self.print_a4_document(data)
            elif action == 'print':
                result = await self.print_generic(data)
            elif action == 'get_printers':
                self._discover_printers()
                result = {'success': True, 'printers': self.printers_cache}
            elif action == 'test_print':
                result = await self.handle_test_print(data)
            elif action == 'ping':
                result = {'success': True, 'status': 'pong', 'version': AGENT_VERSION,
                          'uptime': str(datetime.now() - self._start_time) if hasattr(self, '_start_time') else ''}
            elif action == 'get_status':
                result = {'success': True, 'connected': True, 'version': AGENT_VERSION,
                          'printers': self.printers_cache, 'clients': len(self.clients)}
            else:
                result = {'success': False, 'error': f'Unknown action: {action}'}

            if request_id:
                result['request_id'] = request_id

            await websocket.send(json.dumps(result, ensure_ascii=False))

        except json.JSONDecodeError:
            await websocket.send(json.dumps({'success': False, 'error': 'Invalid JSON'}))
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            resp = {'success': False, 'error': str(e)}
            try:
                if 'data' in dir() and data and data.get('request_id'):  # type: ignore[possibly-undefined]
                    resp['request_id'] = data['request_id']  # type: ignore[possibly-undefined]
            except Exception:
                pass
            await websocket.send(json.dumps(resp, ensure_ascii=False))

    async def _heartbeat_loop(self, websocket, interval=30):
        """Send periodic heartbeats so the server knows we're alive."""
        try:
            while True:
                await asyncio.sleep(interval)
                await websocket.send(json.dumps({
                    'type': 'heartbeat',
                    'machine_name': self.machine_name,
                    'timestamp': datetime.now().isoformat(),
                }))
        except (asyncio.CancelledError, Exception):
            pass

    async def handler(self, websocket, path=None):
        client = websocket.remote_address
        self.clients.add(websocket)
        logger.info(f"🔗 New connection: {client} (total: {len(self.clients)})")

        # Send initial handshake with printer info (legacy)
        await websocket.send(json.dumps({
            'type': 'connected',
            'agent_version': AGENT_VERSION,
            'printers': self.printers_cache,
            'default_printer': self.default_printer,
            'timestamp': datetime.now().isoformat()
        }, ensure_ascii=False))

        # Send station registration message
        reg_msg = self._build_registration_message()
        await websocket.send(json.dumps(reg_msg, ensure_ascii=False))
        logger.info(f"📋 Registered as '{self.machine_name}' ({self.machine_ip})")

        # Start heartbeat task
        heartbeat_task = asyncio.create_task(self._heartbeat_loop(websocket))

        try:
            async for message in websocket:
                await self.handle_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"🔌 Disconnected: {client}")
        except Exception as e:
            logger.error(f"Connection error: {e}")
        finally:
            heartbeat_task.cancel()
            self.clients.discard(websocket)
            logger.info(f"Clients remaining: {len(self.clients)}")

    # ============================================
    # Server Reporting — connect TO ERP server
    # ============================================

    async def _server_reporter(self):
        """
        Maintain a persistent WebSocket CLIENT connection to the ERP server.
        This lets the server know which station is online, what printers it has,
        and allows the server to push print jobs directly.
        """
        retry_delay = 3
        max_delay = 60

        while True:
            try:
                logger.info(f"🌐 Connecting to ERP server: {ERP_WS_URL}")
                async with websockets.connect(
                    ERP_WS_URL,
                    open_timeout=10,
                    ping_interval=20,
                    ping_timeout=20,
                    max_size=50 * 1024 * 1024,
                ) as ws:
                    logger.info("✅ Connected to ERP server!")
                    retry_delay = 3  # reset on success

                    # 1. Send registration
                    reg_msg = self._build_registration_message()
                    await ws.send(json.dumps(reg_msg, ensure_ascii=False))
                    logger.info(f"📋 Registered as '{self.machine_name}' with ERP server")

                    # 2. Wait for ack
                    try:
                        ack = await asyncio.wait_for(ws.recv(), timeout=10)
                        ack_data = json.loads(ack)
                        if ack_data.get('type') == 'register_ack':
                            logger.info(f"✅ Server acknowledged registration")
                        else:
                            logger.info(f"← Server response: {ack_data.get('type', 'unknown')}")
                    except asyncio.TimeoutError:
                        logger.warning("⚠️ No ack received from server (continuing)")

                    # 3. Start heartbeat + listen for server-pushed commands
                    heartbeat_task = asyncio.create_task(
                        self._server_heartbeat(ws)
                    )
                    try:
                        async for message in ws:
                            await self._handle_server_command(ws, message)
                    finally:
                        heartbeat_task.cancel()

            except (websockets.exceptions.ConnectionClosed, ConnectionError) as e:
                logger.warning(f"🔌 ERP connection lost: {e}")
            except Exception as e:
                logger.error(f"❌ ERP connection error: {e}")

            logger.info(f"🔄 Reconnecting to ERP in {retry_delay}s...")
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, max_delay)

    async def _server_heartbeat(self, ws, interval=30):
        """Send periodic heartbeats to the ERP server."""
        try:
            while True:
                await asyncio.sleep(interval)
                await ws.send(json.dumps({
                    'type': 'heartbeat',
                    'machine_name': self.machine_name,
                    'timestamp': datetime.now().isoformat(),
                }))
        except (asyncio.CancelledError, Exception):
            pass

    async def _handle_server_command(self, ws, raw_message):
        """
        Handle a print command pushed FROM the ERP server.
        The server sends the same actions as browser clients
        (print_zebra_zpl, print_thermal_receipt, print_a4, etc.)
        """
        data: dict = {}
        try:
            data = json.loads(raw_message)
            msg_type = data.get('type', '')
            action = data.get('action', '') or msg_type

            # Skip non-print messages (e.g. queue_replay, notifications, heartbeat ack)
            if msg_type in ('register_ack', 'pong', 'info', 'heartbeat_ack'):
                if msg_type == 'register_ack':
                    logger.info(f"✅ Server acknowledged registration")
                return

            logger.info(f"📥 Server command: {action}")

            # Reuse the same handler that browser clients use
            result = {}
            if action == 'print_zebra_zpl':
                result = await self.print_zebra_zpl(data)
            elif action == 'print_zebra_label':
                result = await self.print_zebra_label(data)
            elif action == 'print_thermal_receipt':
                result = await self.print_thermal_receipt(data)
            elif action == 'print_thermal_image':
                result = await self.print_thermal_image(data)
            elif action == 'print_a4':
                result = await self.print_a4_document(data)
            elif action == 'print':
                result = await self.print_generic(data)
            elif action == 'test_print':
                result = await self.handle_test_print(data)
            elif action == 'get_printers':
                self._discover_printers()
                result = {'success': True, 'printers': self.printers_cache}
            elif action == 'ping':
                result = {'success': True, 'status': 'pong', 'version': AGENT_VERSION}
            elif action == 'get_status':
                result = {'success': True, 'connected': True, 'version': AGENT_VERSION,
                          'printers': self.printers_cache}
            else:
                logger.debug(f"Ignoring unknown server message type: {action}")
                return

            # Send result back as print_result
            result['type'] = 'print_result'
            if data.get('request_id'):
                result['request_id'] = data['request_id']
            if data.get('job_id'):
                result['job_id'] = data['job_id']
            await ws.send(json.dumps(result, ensure_ascii=False))
            logger.info(f"  → Result: {'✅' if result.get('success') else '❌'}")

        except json.JSONDecodeError:
            logger.error("Invalid JSON from server")
        except Exception as e:
            logger.error(f"Server command error: {e}", exc_info=True)
            try:
                await ws.send(json.dumps({
                    'type': 'print_result',
                    'success': False,
                    'error': str(e),
                    'job_id': data.get('job_id', ''),
                }, ensure_ascii=False))
            except Exception:
                pass

    async def start(self):
        self._start_time = datetime.now()
        z = len(self.printers_cache.get('zebra', []))
        t = len(self.printers_cache.get('thermal', []))
        a = len(self.printers_cache.get('a4', []))

        print(f"\n  ✅ Agent running on ws://localhost:{self.port}")
        print(f"  �️  Machine: {self.machine_name} ({self.machine_ip})")
        print(f"  �📋 Discovered {z+t+a} printer(s):")
        for p in self.printers_cache.get('zebra', []):
            default = ' ⭐' if p.get('is_default') else ''
            print(f"     🏷️  [ZEBRA]   {p['name']}{default}")
        for p in self.printers_cache.get('thermal', []):
            default = ' ⭐' if p.get('is_default') else ''
            print(f"     🧾 [THERMAL] {p['name']}{default}")
        for p in self.printers_cache.get('a4', []):
            default = ' ⭐' if p.get('is_default') else ''
            print(f"     📄 [A4]      {p['name']}{default}")
        print(f"\n  Waiting for connections from browser...")
        print(f"  ERP at http://72.62.176.249 will connect automatically.")
        print(f"  Press Ctrl+C to stop.\n")

        logger.info(f"Agent v{AGENT_VERSION} on ws://{self.host}:{self.port} - {z+t+a} printers")

        async with websockets.serve(
            self.handler, self.host, self.port,
            origins=None,          # Allow ALL origins (CORS-safe)
            ping_interval=20,      # Built-in WebSocket ping every 20s
            ping_timeout=20,
            max_size=50 * 1024 * 1024,
        ):
            # Run server reporter in parallel — connects TO the ERP server
            reporter_task = asyncio.create_task(self._server_reporter())
            try:
                await asyncio.Future()  # run forever
            finally:
                reporter_task.cancel()


def _find_pids_on_port(port):
    """Find PIDs using a specific port via multiple methods."""
    pids = set()
    my_pid = os.getpid()

    # Method 1: psutil (most reliable)
    if PSUTIL_AVAILABLE:
        try:
            for conn in psutil.net_connections(kind='tcp'):
                if conn.laddr and conn.laddr.port == port:
                    if conn.pid and conn.pid != my_pid:
                        pids.add(conn.pid)
        except (psutil.AccessDenied, Exception):
            pass

    # Method 2: netstat fallback
    if not pids:
        try:
            import subprocess
            result = subprocess.run(
                ['netstat', '-ano', '-p', 'tcp'],
                capture_output=True, text=True, shell=True, timeout=10
            )
            for line in result.stdout.splitlines():
                if f':{port}' in line and ('LISTENING' in line or 'ESTABLISHED' in line):
                    parts = line.split()
                    pid_str = parts[-1].strip()
                    if pid_str.isdigit():
                        pid = int(pid_str)
                        if pid != my_pid and pid != 0:
                            pids.add(pid)
        except Exception:
            pass

    return list(pids)


def _kill_pid(pid):
    """Force-kill a process by PID."""
    if PSUTIL_AVAILABLE:
        try:
            proc = psutil.Process(pid)
            name = proc.name()
            print(f"    Killing PID {pid} ({name})")
            proc.kill()
            proc.wait(timeout=5)
            return True
        except Exception:
            pass
    # taskkill fallback
    try:
        import subprocess
        subprocess.run(['taskkill', '/F', '/PID', str(pid)],
                       capture_output=True, shell=True, timeout=10)
        return True
    except Exception:
        return False


def _port_in_use(port):
    """Check if a port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        try:
            s.connect(('127.0.0.1', port))
            return True
        except (ConnectionRefusedError, socket.timeout, OSError):
            pass
    # Also try binding
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('0.0.0.0', port))
            return False
        except OSError:
            return True


def _force_free_port(port, max_attempts=5):
    """Guarantee a port is free. Kill any process holding it."""
    for attempt in range(1, max_attempts + 1):
        if not _port_in_use(port):
            print(f"  ✅ Port {port} is free.")
            return True

        print(f"  ⚠️  Port {port} busy (attempt {attempt}/{max_attempts})")
        pids = _find_pids_on_port(port)
        if pids:
            print(f"    Found PIDs: {pids}")
            for pid in pids:
                _kill_pid(pid)
        else:
            print(f"    No PIDs found (TIME_WAIT state?) - will try SO_REUSEADDR")
            return True  # Let websockets try with SO_REUSEADDR

        _time.sleep(1.5)

    if not _port_in_use(port):
        return True

    print(f"  ❌ Could not free port {port}.")
    print(f"     Fix manually: netstat -ano | findstr :{port}")
    print(f"                   taskkill /F /PID <PID>")
    return False


def main():
    print(f"""
╔═══════════════════════════════════════════════════╗
║  Tony ERP - Print Agent v{AGENT_VERSION} (Windows)              ║
║  Zebra ZPL | XPrinter ESC/POS | A4 PDF           ║
╚═══════════════════════════════════════════════════╝
    """)

    if not WIN32_AVAILABLE:
        print("  ⚠️  pywin32 not installed - USB printing won't work")
        print("     pip install pywin32 && python -m pywin32_postinstall -install")
        print()

    # Port Watchdog - solve Error 10048 permanently
    print(f"  🔍 Checking port {AGENT_PORT}...")
    if not _force_free_port(AGENT_PORT):
        input("\n  Press Enter to close...")
        sys.exit(1)

    agent = WindowsPrintAgent()

    try:
        asyncio.run(agent.start())
    except KeyboardInterrupt:
        print("\n  🛑 Agent stopped by user.")
    except OSError as e:
        if getattr(e, 'errno', 0) == 10048 or 'address already in use' in str(e).lower():
            print(f"\n  ❌ Port {AGENT_PORT} grabbed during startup! Re-run to auto-fix.")
        else:
            logger.error(f"OS Error: {e}", exc_info=True)
        input("\n  Press Enter to close...")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal: {e}", exc_info=True)
        input("\n  Press Enter to close...")
        sys.exit(1)


if __name__ == '__main__':
    main()
