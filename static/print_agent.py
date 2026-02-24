#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tony ERP - Local Print Agent
=============================

Runs on the local cashier machine (Windows/Linux).
Receives print commands from the browser via local WebSocket
and prints directly to XPrinter or any thermal printer.

Install:
    pip install websockets

Run:
    python print_agent.py

After starting:
    - Agent listens on port 9100 locally
    - Browser connects to ws://localhost:9100
    - Sends print data as base64
"""

import asyncio
import base64
import json
import logging
import os
import platform
import subprocess
import sys
import tempfile

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('PrintAgent')

# ===================== SETTINGS =====================
AGENT_PORT = 9100          # Local WebSocket port
PRINTER_NAME = None        # None = auto-detect / default
# ====================================================

IS_WINDOWS = platform.system() == 'Windows'
IS_LINUX = platform.system() == 'Linux'

# Import websockets
try:
    import websockets
    from websockets.server import serve as ws_serve
except ImportError:
    print("[ERROR] 'websockets' library not installed!")
    print("  Run: python -m pip install websockets")
    print()
    input("Press Enter to exit...")
    sys.exit(1)

# Windows printing via win32print (optional)
WIN32_AVAILABLE = False
if IS_WINDOWS:
    try:
        import win32print
        WIN32_AVAILABLE = True
        logger.info("win32print available - using native Windows printing")
    except ImportError:
        logger.warning("pywin32 not installed - will use fallback printing method")
        logger.warning("For better results: python -m pip install pywin32")


class LocalPrinter:
    """Manage local printer"""

    def __init__(self, printer_name=None):
        self.printer_name = printer_name or self._find_thermal_printer() or self._get_default()

    def _get_default(self):
        """Get default printer"""
        if WIN32_AVAILABLE:
            try:
                return win32print.GetDefaultPrinter()
            except:
                pass
        elif IS_WINDOWS:
            # Fallback: use wmic to get default printer
            try:
                result = subprocess.run(
                    ['wmic', 'printer', 'where', 'Default=TRUE', 'get', 'Name', '/value'],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0 and 'Name=' in result.stdout:
                    name = result.stdout.split('Name=')[1].strip()
                    if name:
                        return name
            except:
                pass
            # Try PowerShell
            try:
                result = subprocess.run(
                    ['powershell', '-Command',
                     '(Get-WmiObject Win32_Printer | Where-Object {$_.Default -eq $true}).Name'],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip()
            except:
                pass
        elif IS_LINUX:
            try:
                result = subprocess.run(['lpstat', '-d'], capture_output=True, text=True)
                if result.returncode == 0 and ':' in result.stdout:
                    return result.stdout.split(':')[-1].strip()
            except:
                pass
        return None

    def _find_thermal_printer(self):
        """Find XPrinter or thermal printer"""
        keywords = ['xp-80', 'xp80', 'xprinter', 'xp-58', 'thermal', 'pos', 'receipt', 'xp-']

        if WIN32_AVAILABLE:
            try:
                for p in win32print.EnumPrinters(
                    win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
                ):
                    name = p[2].lower()
                    for kw in keywords:
                        if kw in name:
                            return p[2]
            except:
                pass
        elif IS_WINDOWS:
            # Fallback: use wmic to list printers
            try:
                result = subprocess.run(
                    ['wmic', 'printer', 'get', 'Name', '/value'],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if line.startswith('Name='):
                            name = line.split('=', 1)[1].strip()
                            for kw in keywords:
                                if kw in name.lower():
                                    return name
            except:
                pass
        elif IS_LINUX:
            try:
                result = subprocess.run(['lpstat', '-a'], capture_output=True, text=True)
                if result.returncode == 0:
                    for line in result.stdout.strip().split('\n'):
                        name = line.split()[0].lower() if line.strip() else ''
                        for kw in keywords:
                            if kw in name:
                                return line.split()[0]
            except:
                pass
        return None

    def get_printers(self):
        """List available printers"""
        printers = []
        default = self._get_default()

        if WIN32_AVAILABLE:
            try:
                for p in win32print.EnumPrinters(
                    win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
                ):
                    printers.append({
                        'name': p[2],
                        'is_default': p[2] == default
                    })
            except:
                pass
        elif IS_WINDOWS:
            # Fallback: use wmic
            try:
                result = subprocess.run(
                    ['wmic', 'printer', 'get', 'Name,Default', '/value'],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    current_name = None
                    current_default = False
                    for line in result.stdout.split('\n'):
                        line = line.strip()
                        if line.startswith('Default='):
                            current_default = line.split('=', 1)[1].strip().upper() == 'TRUE'
                        elif line.startswith('Name='):
                            current_name = line.split('=', 1)[1].strip()
                        if current_name is not None and line == '':
                            printers.append({'name': current_name, 'is_default': current_default})
                            current_name = None
                            current_default = False
                    if current_name:
                        printers.append({'name': current_name, 'is_default': current_default})
            except:
                pass
        elif IS_LINUX:
            try:
                result = subprocess.run(['lpstat', '-a'], capture_output=True, text=True)
                if result.returncode == 0:
                    for line in result.stdout.strip().split('\n'):
                        name = line.split()[0] if line.strip() else None
                        if name:
                            printers.append({
                                'name': name,
                                'is_default': name == default
                            })
            except:
                pass
        return printers

    def print_raw(self, data: bytes):
        """Send raw (ESC/POS) data to printer"""
        if not self.printer_name:
            raise Exception("No printer found! Make sure your printer is connected and drivers are installed.")

        logger.info(f"Printing {len(data)} bytes to: {self.printer_name}")

        if IS_WINDOWS:
            if WIN32_AVAILABLE:
                return self._print_windows_native(data)
            else:
                return self._print_windows_fallback(data)
        elif IS_LINUX:
            return self._print_linux(data)
        else:
            raise Exception(f"Unsupported OS: {platform.system()}")

    def _print_windows_native(self, data: bytes):
        """Print on Windows using win32print (best method)"""
        handle = win32print.OpenPrinter(self.printer_name)
        try:
            win32print.StartDocPrinter(handle, 1, ("Tony ERP Receipt", None, "RAW"))
            win32print.StartPagePrinter(handle)
            win32print.WritePrinter(handle, data)
            win32print.EndPagePrinter(handle)
            win32print.EndDocPrinter(handle)
            return True
        finally:
            win32print.ClosePrinter(handle)

    def _print_windows_fallback(self, data: bytes):
        """Print on Windows without pywin32 - uses file copy to printer port"""
        # Write data to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.bin', mode='wb') as f:
            f.write(data)
            temp_path = f.name

        try:
            # Method 1: Try to find printer port via wmic and copy directly
            try:
                result = subprocess.run(
                    ['wmic', 'printer', 'where', f'Name="{self.printer_name}"',
                     'get', 'PortName', '/value'],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0 and 'PortName=' in result.stdout:
                    port = result.stdout.split('PortName=')[1].strip()
                    if port:
                        logger.info(f"Printing via port: {port}")
                        copy_result = subprocess.run(
                            f'copy /b "{temp_path}" "{port}"',
                            capture_output=True, text=True, shell=True, timeout=15
                        )
                        if copy_result.returncode == 0:
                            return True
                        logger.warning(f"Direct port copy failed: {copy_result.stderr}")
            except Exception as e:
                logger.warning(f"Port detection failed: {e}")

            # Method 2: Try to copy to printer share name
            try:
                share_name = f"\\\\localhost\\{self.printer_name}"
                logger.info(f"Trying printer share: {share_name}")
                share_result = subprocess.run(
                    f'copy /b "{temp_path}" "{share_name}"',
                    capture_output=True, text=True, shell=True, timeout=15
                )
                if share_result.returncode == 0:
                    return True
                logger.warning(f"Share copy failed: {share_result.stderr}")
            except Exception as e:
                logger.warning(f"Share copy failed: {e}")

            # Method 3: Try PowerShell raw printing
            try:
                logger.info("Trying PowerShell raw print...")
                ps_script = (
                    f'$p = Get-WmiObject Win32_Printer | Where-Object {{$_.Name -eq "{self.printer_name}"}}; '
                    f'$port = $p.PortName; '
                    f'if ($port) {{ Copy-Item "{temp_path}" "\\\\.\\"$port -Force }}'
                )
                ps_result = subprocess.run(
                    ['powershell', '-Command', ps_script],
                    capture_output=True, text=True, timeout=15
                )
                if ps_result.returncode == 0:
                    return True
                logger.warning(f"PowerShell print failed: {ps_result.stderr}")
            except Exception as e:
                logger.warning(f"PowerShell print failed: {e}")

            raise Exception(
                f"Could not print to '{self.printer_name}'. "
                f"Install pywin32 for reliable printing: python -m pip install pywin32"
            )
        finally:
            try:
                os.unlink(temp_path)
            except:
                pass

    def _print_linux(self, data: bytes):
        """Print on Linux"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as f:
            f.write(data)
            temp_path = f.name

        try:
            result = subprocess.run(
                ['lp', '-d', self.printer_name, '-o', 'raw', temp_path],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                raise Exception(f"lp error: {result.stderr}")
            return True
        finally:
            os.unlink(temp_path)


class PrintAgentServer:
    """Local WebSocket server for receiving print commands"""

    def __init__(self):
        self.printer = LocalPrinter(PRINTER_NAME)
        self.print_count = 0

    async def handle_connection(self, websocket):
        """Handle browser connection"""
        remote = websocket.remote_address
        logger.info(f"New connection from: {remote}")

        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    response = await self.handle_command(data)
                    await websocket.send(json.dumps(response))
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        'success': False,
                        'error': 'Invalid message format'
                    }))
        except Exception as e:
            logger.error(f"Connection error: {e}")

    async def handle_command(self, data: dict):
        """Handle print command"""
        cmd = data.get('command', '')

        if cmd == 'print':
            return await self._handle_print(data)
        elif cmd == 'status':
            return self._handle_status()
        elif cmd == 'test':
            return await self._handle_test()
        elif cmd == 'printers':
            return self._handle_printers()
        else:
            return {'success': False, 'error': f'Unknown command: {cmd}'}

    async def _handle_print(self, data: dict):
        """Print ESC/POS data"""
        try:
            b64_data = data.get('data', '')
            if not b64_data:
                return {'success': False, 'error': 'No print data provided'}

            # Decode base64
            raw_data = base64.b64decode(b64_data)

            # Print
            self.printer.print_raw(raw_data)
            self.print_count += 1

            order_id = data.get('order_id', '?')
            logger.info(f"[OK] Receipt #{order_id} printed (total: {self.print_count})")

            return {
                'success': True,
                'message': 'Printed successfully',
                'printer': self.printer.printer_name,
                'print_count': self.print_count
            }
        except Exception as e:
            logger.error(f"[ERROR] Print failed: {e}")
            return {'success': False, 'error': str(e)}

    def _handle_status(self):
        """Agent status"""
        return {
            'success': True,
            'agent': 'Tony ERP Print Agent',
            'printer': self.printer.printer_name,
            'print_count': self.print_count,
            'platform': platform.system(),
            'win32': WIN32_AVAILABLE,
        }

    async def _handle_test(self):
        """Test print"""
        try:
            # Simple ESC/POS test commands
            test_data = bytearray()
            test_data.extend(b'\x1b\x40')  # Initialize
            test_data.extend(b'\x1b\x61\x01')  # Center
            test_data.extend(b'\x1d\x21\x11')  # Double size
            test_data.extend('Tony ERP\n'.encode('cp1256', errors='replace'))
            test_data.extend(b'\x1d\x21\x00')  # Normal
            test_data.extend(b'\x1b\x61\x01')  # Center
            test_data.extend('================================\n'.encode())
            test_data.extend('Print Agent Test\n'.encode())
            test_data.extend('================================\n'.encode())
            test_data.extend('Printer is working!\n'.encode())
            test_data.extend(b'\n\n\n')
            test_data.extend(b'\x1d\x56\x01')  # Cut

            self.printer.print_raw(bytes(test_data))
            self.print_count += 1

            return {
                'success': True,
                'message': 'Test page printed',
                'printer': self.printer.printer_name
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _handle_printers(self):
        """List printers"""
        return {
            'success': True,
            'printers': self.printer.get_printers(),
            'current': self.printer.printer_name,
        }

    async def run(self):
        """Start server"""
        print()
        print("=" * 55)
        print("  Tony ERP - Local Print Agent")
        print("=" * 55)
        print(f"  Printer:  {self.printer.printer_name or '[NOT FOUND]'}")
        print(f"  Port:     {AGENT_PORT}")
        print(f"  OS:       {platform.system()}")
        print(f"  win32:    {'Yes' if WIN32_AVAILABLE else 'No (fallback mode)'}")
        print("=" * 55)

        if not self.printer.printer_name:
            print()
            print("  [WARNING] No printer detected!")
            print("  Make sure your printer is connected and drivers installed.")
            print()

        printers = self.printer.get_printers()
        if printers:
            print()
            print("  Available Printers:")
            for p in printers:
                mark = " <-- selected" if p['name'] == self.printer.printer_name else ""
                default = " (default)" if p.get('is_default') else ""
                print(f"     * {p['name']}{default}{mark}")
            print()

        print(f"  [OK] Agent ready on ws://localhost:{AGENT_PORT}")
        print("  Do not close this window while working!")
        print("  Press Ctrl+C to stop")
        print("=" * 55)
        print()

        async with ws_serve(
            self.handle_connection,
            "0.0.0.0",
            AGENT_PORT,
            origins=None,  # Allow any origin (needed for remote server connection)
        ):
            await asyncio.Future()  # Run forever


if __name__ == '__main__':
    agent = PrintAgentServer()
    try:
        asyncio.run(agent.run())
    except KeyboardInterrupt:
        print("\nPrint Agent stopped.")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        input("\nPress Enter to close...")
