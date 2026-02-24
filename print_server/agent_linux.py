#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tony ERP Print Agent v3.0 - Linux Server
=========================================
وكيل الطباعة على السيرفر - يعمل مع CUPS + الطباعة الشبكية

يدعم 3 أنواع طابعات:
  1. Zebra ZE220 (ZPL عبر TCP socket مباشرة لعنوان IP الطابعة)
  2. XPrinter (ESC/POS عبر TCP socket أو CUPS)
  3. أي طابعة A4 عبر CUPS (lp / lpr)

التشغيل:
  python3 agent_linux.py
  أو كخدمة systemd (انظر tony-print-agent.service)

المتطلبات:
  pip install websockets Pillow
  + CUPS مثبّت على السيرفر (sudo apt install cups)
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
import subprocess
import shutil
from datetime import datetime

AGENT_VERSION = '3.1'

try:
    import websockets
except ImportError:
    print("❌ websockets not installed! Run: pip install websockets")
    sys.exit(1)

PIL_AVAILABLE = False
Image = None
ImageDraw = None
ImageFont = None
try:
    from PIL import Image, ImageDraw, ImageFont  # type: ignore[assignment]
    PIL_AVAILABLE = True
except ImportError:
    pass

# Logging
LOG_DIR = os.path.dirname(os.path.abspath(__file__))
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(LOG_DIR, 'print_agent.log'), encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

AGENT_PORT = int(os.environ.get('AGENT_PORT', '9876'))
AGENT_HOST = os.environ.get('AGENT_HOST', '0.0.0.0')

# ERP Server WebSocket URL — agent connects TO the server to register itself
ERP_WS_URL = os.environ.get('ERP_WS_URL', 'ws://127.0.0.1:8001/ws/print-agent/')


class LinuxPrintAgent:
    """
    Server-side print agent for Linux.
    - Zebra: TCP socket to printer IP:9100 (ZPL)
    - XPrinter: TCP socket to printer IP:9100 (ESC/POS) or CUPS
    - A4: CUPS (lp command)
    """

    def __init__(self, host=AGENT_HOST, port=AGENT_PORT):
        self.host = host
        self.port = port
        self.clients = set()
        self.printers_cache = {'zebra': [], 'thermal': [], 'a4': [], 'all': []}
        self.default_printer = None

        # Machine identity — sent to ERP on connect
        self.machine_name = platform.node() or socket.gethostname()
        self.machine_ip = self._get_local_ip()
        self.os_platform = 'linux'

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
    #  Printer Discovery (CUPS + DB config)
    # ============================================

    def _discover_printers(self):
        """Discover printers from CUPS and Django PrinterConfiguration"""
        self.printers_cache = {'zebra': [], 'thermal': [], 'a4': [], 'all': []}
        self.default_printer = None

        # 1) CUPS printers
        self._discover_cups_printers()

        # 2) Django PrinterConfiguration (network printers)
        self._discover_db_printers()

        logger.info("Printers discovered:")
        logger.info(f"  Zebra:   {[p['name'] for p in self.printers_cache['zebra']]}")
        logger.info(f"  Thermal: {[p['name'] for p in self.printers_cache['thermal']]}")
        logger.info(f"  A4:      {[p['name'] for p in self.printers_cache['a4']]}")

    def _discover_cups_printers(self):
        """Discover CUPS-configured printers using lpstat"""
        try:
            # Get default printer
            result = subprocess.run(
                ['lpstat', '-d'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and 'system default destination:' in result.stdout:
                self.default_printer = result.stdout.split('system default destination:')[1].strip()

            # List all printers
            result = subprocess.run(
                ['lpstat', '-p', '-v'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                return

            # Parse printer names and URIs
            printer_info = {}
            for line in result.stdout.strip().split('\n'):
                line = line.strip()
                if not line:
                    continue
                if line.startswith('printer '):
                    # "printer MyPrinter is idle."
                    parts = line.split()
                    if len(parts) >= 2:
                        name = parts[1]
                        printer_info.setdefault(name, {})['name'] = name
                elif line.startswith('device for '):
                    # "device for MyPrinter: ipp://..."
                    match = re.match(r'device for (.+?):\s*(.+)', line)
                    if match:
                        name = match.group(1)
                        uri = match.group(2)
                        printer_info.setdefault(name, {})['name'] = name
                        printer_info.setdefault(name, {})['uri'] = uri

            zebra_kw = ['zebra', 'ze220', 'zd420', 'zd220', 'zpl', 'zt230', 'gk420']
            thermal_kw = ['xp-80', 'xp80', 'xprinter', 'thermal', 'pos-80', 'receipt',
                          'tm-t', 'rp80', 'pos80', 'xp-58', 'xp58', 'pos58', 'rongta']

            for name, info in printer_info.items():
                entry = {
                    'name': name,
                    'uri': info.get('uri', ''),
                    'type': 'a4',
                    'source': 'cups',
                    'is_default': name == self.default_printer
                }
                name_lower = name.lower()

                classified = False
                for kw in zebra_kw:
                    if kw in name_lower:
                        entry['type'] = 'zebra'
                        self.printers_cache['zebra'].append(entry)
                        classified = True
                        break
                if not classified:
                    for kw in thermal_kw:
                        if kw in name_lower:
                            entry['type'] = 'thermal'
                            self.printers_cache['thermal'].append(entry)
                            classified = True
                            break
                if not classified:
                    self.printers_cache['a4'].append(entry)

                self.printers_cache['all'].append(entry)

        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.warning(f"CUPS not available: {e}")

    def _discover_db_printers(self):
        """Load printers from Django PrinterConfiguration model"""
        try:
            # Setup Django if not already
            if 'DJANGO_SETTINGS_MODULE' not in os.environ:
                sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
                import django
                django.setup()

            from inventory.models import PrinterConfiguration
            configs = PrinterConfiguration.objects.filter(is_active=True)

            type_map = {
                'zebra': 'zebra',
                'xprinter': 'thermal',
                'hp_laserjet': 'a4',
                'generic': 'a4',
            }

            for conf in configs:
                ptype = type_map.get(conf.printer_type, 'a4')
                ip = str(conf.ip_address) if conf.ip_address else ''
                entry = {
                    'name': conf.name,
                    'type': ptype,
                    'source': 'db',
                    'db_id': conf.id,
                    'ip': ip,
                    'port': conf.port or (9100 if ptype in ('zebra', 'thermal') else 0),
                    'connection_type': conf.connection_type,
                    'paper_size': conf.paper_size,
                    'dpi': conf.dpi,
                    'label_width_mm': conf.label_width_mm,
                    'label_height_mm': conf.label_height_mm,
                    'shared_printer_name': conf.shared_printer_name or '',
                    'is_default': conf.is_default,
                }

                # Check if already in cache (from CUPS)
                existing = [p for p in self.printers_cache.get('all', []) if p['name'] == conf.name]
                if not existing:
                    self.printers_cache[ptype].append(entry)
                    self.printers_cache['all'].append(entry)
                else:
                    # Merge DB info into CUPS entry
                    existing[0].update({
                        'ip': ip,
                        'port': entry['port'],
                        'db_id': conf.id,
                        'dpi': conf.dpi,
                    })

        except Exception as e:
            logger.warning(f"Could not load DB printers: {e}")

    def _find_printer(self, printer_name=None, printer_type=None):
        """Find a printer by name or type, returns the printer dict"""
        if printer_name:
            for p in self.printers_cache.get('all', []):
                if p['name'].lower() == printer_name.lower():
                    return p
            for p in self.printers_cache.get('all', []):
                if printer_name.lower() in p['name'].lower():
                    return p

        if printer_type:
            printers = self.printers_cache.get(printer_type, [])
            # Prefer default
            for p in printers:
                if p.get('is_default'):
                    return p
            if printers:
                return printers[0]

        # Fallback to CUPS default
        if self.default_printer:
            for p in self.printers_cache.get('all', []):
                if p['name'] == self.default_printer:
                    return p

        # Return any available
        if self.printers_cache.get('all'):
            return self.printers_cache['all'][0]

        return None

    def _get_printer_ip(self, data, printer_info=None):
        """Get IP from request data or printer info"""
        ip = data.get('ip', '').strip()
        port = int(data.get('port', 9100))

        if not ip and printer_info:
            ip = printer_info.get('ip', '')
            port = int(printer_info.get('port', 0)) or port

        return ip, port

    # ============================================
    #  Raw TCP Socket Printing (Zebra / Thermal)
    # ============================================

    def _send_tcp(self, ip, port, raw_data, timeout=10):
        """Send raw data to a printer via TCP socket"""
        if isinstance(raw_data, str):
            raw_data = raw_data.encode('utf-8')

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            sock.connect((ip, port))
            sock.sendall(raw_data)
            logger.info(f"TCP -> {ip}:{port} ({len(raw_data)} bytes)")
            return True
        finally:
            sock.close()

    # ============================================
    #  CUPS Printing (lp command)
    # ============================================

    def _print_via_cups(self, printer_name, file_path, copies=1, options=None):
        """Print a file using CUPS lp command"""
        cmd = ['lp']
        if printer_name:
            cmd += ['-d', printer_name]
        if copies > 1:
            cmd += ['-n', str(copies)]
        if options:
            for key, val in options.items():
                cmd += ['-o', f'{key}={val}']
        cmd.append(file_path)

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise RuntimeError(f"lp failed: {result.stderr.strip()}")
        logger.info(f"CUPS -> {printer_name}: {file_path}")
        return result.stdout.strip()

    def _print_raw_via_cups(self, printer_name, raw_data, title="Tony ERP"):
        """Print raw data via CUPS (lp -o raw)"""
        if isinstance(raw_data, str):
            raw_data = raw_data.encode('utf-8')

        fd, tmp = tempfile.mkstemp(suffix='.raw')
        try:
            with os.fdopen(fd, 'wb') as f:
                f.write(raw_data)

            cmd = ['lp', '-o', 'raw', '-t', title]
            if printer_name:
                cmd += ['-d', printer_name]
            cmd.append(tmp)

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                raise RuntimeError(f"lp raw failed: {result.stderr.strip()}")
            logger.info(f"CUPS RAW -> {printer_name} ({len(raw_data)} bytes)")
        finally:
            try:
                os.unlink(tmp)
            except OSError:
                pass

    # ============================================
    #  1. Zebra ZE220 - ZPL (Barcode/Labels)
    # ============================================

    async def print_zebra_zpl(self, data):
        """Send ZPL commands to Zebra printer via TCP or CUPS"""
        zpl_commands = data.get('zpl', '')
        printer_name = data.get('printer_name', '')
        ip = data.get('ip', '').strip()
        port = int(data.get('port', 9100))

        if not zpl_commands:
            return {'success': False, 'error': 'No ZPL commands provided'}

        # Find printer config
        printer_info = self._find_printer(printer_name, 'zebra')
        if not ip and printer_info:
            ip = printer_info.get('ip', '')
            port = int(printer_info.get('port', 0)) or 9100

        # Method 1: TCP socket (for network Zebra printers)
        if ip:
            try:
                self._send_tcp(ip, port, zpl_commands)
                return {'success': True, 'method': 'network', 'ip': ip, 'port': port}
            except Exception as e:
                logger.warning(f"Zebra TCP failed ({ip}:{port}): {e}")
                # Fall through to CUPS

        # Method 2: CUPS raw mode
        cups_name = printer_name or (printer_info['name'] if printer_info and printer_info.get('source') == 'cups' else '')
        if cups_name:
            try:
                self._print_raw_via_cups(cups_name, zpl_commands, "ZPL Label")
                return {'success': True, 'method': 'cups', 'printer': cups_name}
            except Exception as e:
                return {'success': False, 'error': f'CUPS error: {e}'}

        return {'success': False, 'error': 'Zebra printer not found. Configure IP address in Admin > Printer Configuration or add a CUPS printer.'}

    async def print_zebra_label(self, data):
        """Generate ZPL from parameters and print to Zebra"""
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

        # Build ZPL
        zpl = f"^XA\n^PW{w}\n^LL{h}\n^CI28\n"

        # Product name (top)
        if product_name:
            fn_h = max(18, int(h * 0.12))
            zpl += f"^FO{int(w*0.05)},{int(h*0.05)}^A0N,{fn_h},{int(fn_h*0.85)}^FD{product_name[:30]}^FS\n"

        # Size text
        if size_text:
            fn_h = max(14, int(h * 0.08))
            zpl += f"^FO{int(w*0.05)},{int(h*0.20)}^A0N,{fn_h},{int(fn_h*0.85)}^FDSize: {size_text}^FS\n"

        # Price
        y_price = 0.30
        if price:
            fn_h = max(16, int(h * 0.10))
            zpl += f"^FO{int(w*0.05)},{int(h*y_price)}^A0N,{fn_h},{int(fn_h*0.85)}^FD{price}^FS\n"
            y_price += 0.12

        # Dates
        if manufacture_date:
            fn_h = max(12, int(h * 0.06))
            zpl += f"^FO{int(w*0.05)},{int(h*y_price)}^A0N,{fn_h},{int(fn_h*0.85)}^FDMFG: {manufacture_date}^FS\n"
        if expiry_date:
            fn_h = max(12, int(h * 0.06))
            zpl += f"^FO{int(w*0.55)},{int(h*y_price)}^A0N,{fn_h},{int(fn_h*0.85)}^FDEXP: {expiry_date}^FS\n"

        # Barcode
        barcode_x = int(w * 0.07)
        barcode_y = int(h * 0.52)
        barcode_h = max(30, int(h * 0.30))
        module_w = max(1, min(3, w // (len(barcode_val) * 12)))
        zpl += f"^FO{barcode_x},{barcode_y}^BY{module_w},3,{barcode_h}^BCN,,Y,N,N^FD{barcode_val}^FS\n"

        # Copies & end
        zpl += f"^PQ{copies}\n^XZ\n"

        data['zpl'] = zpl
        result = await self.print_zebra_zpl(data)
        if result.get('success'):
            result['label_size'] = f"{label_w}x{label_h}mm"
            result['copies'] = copies
        return result

    # ============================================
    #  2. XPrinter - Thermal (ESC/POS Receipts)
    # ============================================

    async def print_thermal_receipt(self, data):
        """Print receipt to thermal printer via TCP or CUPS"""
        printer_name = data.get('printer_name', '')
        open_drawer = data.get('open_drawer', False)
        cut_paper = data.get('cut_paper', True)

        ESC = b'\x1b'
        GS = b'\x1d'
        raw_data = bytearray()
        raw_data += ESC + b'@'  # Initialize printer

        # Open cash drawer
        if open_drawer:
            raw_data += ESC + b'p\x00\x19\xfa'

        # --- Content ---
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

        # Paper cut
        if cut_paper:
            raw_data += b'\n\n\n'
            raw_data += GS + b'V\x00'

        raw_bytes = bytes(raw_data)

        # Find printer
        printer_info = self._find_printer(printer_name, 'thermal')
        if not printer_info:
            printer_info = self._find_printer(printer_name)

        ip, port = '', 9100
        cups_name = ''
        if printer_info:
            ip = printer_info.get('ip', '')
            port = int(printer_info.get('port', 0)) or 9100
            cups_name = printer_info['name'] if printer_info.get('source') == 'cups' else ''

        # Also check request data for IP
        if not ip and data.get('ip'):
            ip = data['ip'].strip()
            port = int(data.get('port', 9100))

        # Method 1: TCP socket (network thermal printer)
        if ip:
            try:
                self._send_tcp(ip, port, raw_bytes)
                return {'success': True, 'method': 'network', 'ip': ip, 'bytes': len(raw_bytes)}
            except Exception as e:
                logger.warning(f"Thermal TCP failed ({ip}:{port}): {e}")

        # Method 2: CUPS
        if cups_name:
            try:
                self._print_raw_via_cups(cups_name, raw_bytes, "Receipt")
                return {'success': True, 'method': 'cups', 'printer': cups_name, 'bytes': len(raw_bytes)}
            except Exception as e:
                return {'success': False, 'error': f'CUPS error: {e}'}

        return {'success': False, 'error': 'Thermal printer not configured. Set IP address in Admin > Printer Configuration or add a CUPS printer.'}

    async def print_thermal_image(self, data):
        """Print image to thermal printer (ESC/POS raster)"""
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

        # Send to printer
        printer_info = self._find_printer(printer_name, 'thermal')
        ip = data.get('ip', '').strip()
        port = int(data.get('port', 9100))
        if not ip and printer_info:
            ip = printer_info.get('ip', '')
            port = int(printer_info.get('port', 0)) or 9100

        if ip:
            try:
                self._send_tcp(ip, port, bytes(raw_data))
                return {'success': True, 'method': 'network', 'bytes': len(raw_data)}
            except Exception as e:
                logger.warning(f"Image TCP failed: {e}")

        cups_name = printer_info['name'] if printer_info and printer_info.get('source') == 'cups' else ''
        if cups_name:
            try:
                self._print_raw_via_cups(cups_name, bytes(raw_data), "Receipt Image")
                return {'success': True, 'method': 'cups', 'bytes': len(raw_data)}
            except Exception as e:
                return {'success': False, 'error': str(e)}

        return {'success': False, 'error': 'Thermal printer not found'}

    # ============================================
    #  3. A4 Printing (CUPS)
    # ============================================

    async def print_a4_document(self, data):
        """Print PDF or HTML to A4 printer via CUPS"""
        printer_name = data.get('printer_name', '')
        copies = int(data.get('copies', 1))

        printer_info = self._find_printer(printer_name, 'a4')
        if not printer_info:
            printer_info = self._find_printer(printer_name)

        cups_name = ''
        if printer_info:
            cups_name = printer_info['name'] if printer_info.get('source') == 'cups' else ''
            if not cups_name:
                cups_name = printer_info.get('shared_printer_name', '') or printer_info.get('name', '')

        temp_path = None
        try:
            if data.get('pdf_base64'):
                pdf_data = base64.b64decode(data['pdf_base64'])
                fd, temp_path = tempfile.mkstemp(suffix='.pdf')
                with os.fdopen(fd, 'wb') as f:
                    f.write(pdf_data)

                self._print_via_cups(cups_name, temp_path, copies)
                return {'success': True, 'printer': cups_name, 'copies': copies, 'method': 'cups_pdf'}

            elif data.get('pdf_url'):
                import urllib.request
                fd, temp_path = tempfile.mkstemp(suffix='.pdf')
                os.close(fd)
                urllib.request.urlretrieve(data['pdf_url'], temp_path)

                self._print_via_cups(cups_name, temp_path, copies)
                return {'success': True, 'printer': cups_name, 'method': 'cups_pdf_url'}

            elif data.get('html'):
                fd, temp_path = tempfile.mkstemp(suffix='.html')
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    f.write(f"""<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head><meta charset="utf-8">
<style>body {{ font-family: Arial, sans-serif; direction: rtl; }}
@media print {{ body {{ margin: 0; }} }}</style></head>
<body>{data['html']}</body></html>""")

                # Try wkhtmltopdf to convert HTML→PDF then print
                if shutil.which('wkhtmltopdf'):
                    pdf_path = temp_path.replace('.html', '.pdf')
                    result = subprocess.run(
                        ['wkhtmltopdf', '--quiet', '--encoding', 'utf-8', temp_path, pdf_path],
                        capture_output=True, text=True, timeout=30
                    )
                    if result.returncode == 0 and os.path.exists(pdf_path):
                        self._print_via_cups(cups_name, pdf_path, copies)
                        os.unlink(pdf_path)
                        return {'success': True, 'printer': cups_name, 'method': 'wkhtmltopdf'}

                # Fallback: print HTML directly (CUPS can handle it with some setups)
                self._print_via_cups(cups_name, temp_path, copies)
                return {'success': True, 'printer': cups_name, 'method': 'cups_html'}

            else:
                return {'success': False, 'error': 'No content (pdf_base64, pdf_url, or html)'}

        except Exception as e:
            logger.error(f"A4 print error: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            if temp_path:
                def _cleanup():
                    import time
                    time.sleep(30)
                    try:
                        os.unlink(temp_path)
                    except OSError:
                        pass
                import threading
                threading.Thread(target=_cleanup, daemon=True).start()

    # ============================================
    #  Generic Print (backward compat)
    # ============================================

    async def print_generic(self, data):
        """Handle old format: {command:'print', type:'raw/html/text', content:'..'}"""
        printer_name = data.get('printer', 'default')
        content_type = data.get('type', 'text')
        content = data.get('content', '')

        if content_type == 'raw':
            raw_bytes = base64.b64decode(content) if isinstance(content, str) else bytes(content)
            printer_info = self._find_printer(printer_name, 'thermal')
            if printer_info:
                ip = printer_info.get('ip', '')
                port = int(printer_info.get('port', 0)) or 9100
                if ip:
                    self._send_tcp(ip, port, raw_bytes)
                    return {'success': True, 'method': 'network', 'bytes': len(raw_bytes)}
                if printer_info.get('source') == 'cups':
                    self._print_raw_via_cups(printer_info['name'], raw_bytes)
                    return {'success': True, 'method': 'cups', 'bytes': len(raw_bytes)}
            return {'success': False, 'error': 'No printer available'}

        elif content_type == 'html':
            return await self.print_thermal_receipt({'html': content, 'printer_name': printer_name})
        else:
            return await self.print_thermal_receipt({'content': str(content), 'printer_name': printer_name})

    # ============================================
    #  Test Print
    # ============================================

    async def handle_test_print(self, data):
        """Send test print to all configured printers"""
        printer_type = data.get('printer_type', 'all')
        results = {}
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if printer_type in ('all', 'zebra') and self.printers_cache.get('zebra'):
            zpl_test = f"^XA\n^PW400^LL300\n^FO30,30^A0N,40,40^FDTony ERP v3.0^FS\n^FO30,80^A0N,25,25^FDTest Print OK!^FS\n^FO30,120^A0N,20,20^FD{now}^FS\n^FO30,160^BCN,80,Y,N,N^FD123456789012^FS\n^XZ"
            results['zebra'] = await self.print_zebra_zpl({
                'zpl': zpl_test,
                'printer_name': self.printers_cache['zebra'][0].get('name', ''),
                'ip': self.printers_cache['zebra'][0].get('ip', ''),
                'port': self.printers_cache['zebra'][0].get('port', 9100),
            })

        if printer_type in ('all', 'thermal') and self.printers_cache.get('thermal'):
            results['thermal'] = await self.print_thermal_receipt({
                'content': (
                    '================================\n'
                    '      Tony ERP v3.0\n'
                    '      Test Print OK!\n'
                    '================================\n'
                    f'   {now}\n\n'
                    '  Thermal Printer Working\n'
                    '  الطابعة الحرارية تعمل\n'
                    '================================\n\n\n'
                ),
                'printer_name': self.printers_cache['thermal'][0].get('name', ''),
                'ip': self.printers_cache['thermal'][0].get('ip', ''),
                'port': self.printers_cache['thermal'][0].get('port', 9100),
                'cut_paper': True
            })

        if printer_type in ('all', 'a4') and self.printers_cache.get('a4'):
            results['a4'] = await self.print_a4_document({
                'html': f'<div style="text-align:center;padding:50px;"><h1>Tony ERP v3.0</h1><h2>A4 Test Print - OK!</h2><p>{now}</p></div>',
                'printer_name': self.printers_cache['a4'][0].get('name', ''),
            })

        if not results:
            return {'success': False, 'error': 'No printers configured. Add printers in Admin > Printer Configuration.'}

        return {'success': True, 'results': results}

    # ============================================
    #  WebSocket Handler
    # ============================================

    async def handle_message(self, websocket, message):
        """Process incoming WebSocket message"""
        data = {}
        try:
            data = json.loads(message)
            action = data.get('action', data.get('command', ''))
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
                result = {'success': True, 'status': 'pong', 'version': '3.0', 'platform': 'linux'}
            else:
                result = {'success': False, 'error': f'Unknown action: {action}'}

            if request_id:
                result['request_id'] = request_id

            await websocket.send(json.dumps(result, ensure_ascii=False))

        except json.JSONDecodeError:
            await websocket.send(json.dumps({'success': False, 'error': 'Invalid JSON'}))
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
            resp = {'success': False, 'error': str(e)}
            if data.get('request_id'):
                resp['request_id'] = data['request_id']
            try:
                await websocket.send(json.dumps(resp, ensure_ascii=False))
            except Exception:
                pass

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
                    retry_delay = 3

                    # 1. Send registration
                    reg_msg = self._build_registration_message()
                    await ws.send(json.dumps(reg_msg, ensure_ascii=False))
                    logger.info(f"📋 Registered as '{self.machine_name}' with ERP server")

                    # 2. Wait for ack
                    try:
                        ack = await asyncio.wait_for(ws.recv(), timeout=10)
                        ack_data = json.loads(ack)
                        if ack_data.get('type') == 'register_ack':
                            logger.info("✅ Server acknowledged registration")
                    except asyncio.TimeoutError:
                        logger.warning("⚠️ No ack received from server")

                    # 3. Start heartbeat + listen for server-pushed commands
                    hb_task = asyncio.create_task(self._server_heartbeat(ws))
                    try:
                        async for message in ws:
                            await self._handle_server_command(ws, message)
                    finally:
                        hb_task.cancel()

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
        """Handle a print command pushed FROM the ERP server."""
        data: dict = {}
        try:
            data = json.loads(raw_message)
            msg_type = data.get('type', '')
            action = data.get('action', '') or msg_type

            if msg_type in ('register_ack', 'pong', 'info', 'heartbeat_ack'):
                return

            logger.info(f"📥 Server command: {action}")

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
            else:
                logger.debug(f"Ignoring unknown server message type: {action}")
                return

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

    async def handler(self, websocket, path=None):
        """Handle a new WebSocket connection"""
        client = websocket.remote_address
        self.clients.add(websocket)
        logger.info(f"✅ New connection: {client}")

        # Send welcome message with printer list (legacy)
        welcome = {
            'type': 'connected',
            'agent_version': AGENT_VERSION,
            'platform': 'linux',
            'printers': self.printers_cache,
            'default_printer': self.default_printer,
            'timestamp': datetime.now().isoformat()
        }
        await websocket.send(json.dumps(welcome, ensure_ascii=False))

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
            logger.info(f"Disconnected: {client}")
        except Exception as e:
            logger.error(f"Connection error: {e}")
        finally:
            heartbeat_task.cancel()
            self.clients.discard(websocket)

    async def start(self):
        """Start the WebSocket server"""
        z = len(self.printers_cache.get('zebra', []))
        t = len(self.printers_cache.get('thermal', []))
        a = len(self.printers_cache.get('a4', []))

        logger.info(f"""
================================================
  Tony ERP Print Agent v{AGENT_VERSION} (Linux Server)
  ws://{self.host}:{self.port}
  Machine: {self.machine_name} ({self.machine_ip})
------------------------------------------------
  Zebra:   {z} printer(s)
  Thermal: {t} printer(s)
  A4:      {a} printer(s)
  Total:   {z+t+a} printer(s)
================================================
        """)

        async with websockets.serve(
            self.handler,
            self.host,
            self.port,
            ping_interval=20,
            ping_timeout=20,
            max_size=10 * 1024 * 1024,  # 10MB max message
        ):
            # Run server reporter in parallel — connects TO the ERP server
            reporter_task = asyncio.create_task(self._server_reporter())
            try:
                await asyncio.Future()  # Run forever
            finally:
                reporter_task.cancel()


def main():
    print(f"""
===================================================
  Tony ERP - Print Agent v{AGENT_VERSION} (Linux Server)
  Sends to: Zebra (TCP) | XPrinter (TCP) | A4 (CUPS)
===================================================
    """)

    agent = LinuxPrintAgent()

    try:
        asyncio.run(agent.start())
    except KeyboardInterrupt:
        print("\n🛑 Service stopped")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
