#!/usr/bin/env python
"""تشخيص الوصول من الأجهزة الأخرى
يشغّل خادم بسيط ويرصد الطلبات ويطبع العناوين المتاحة.
Usage:
  python diagnose_network_access.py [PORT]
ثم جرّب من الموبايل http://IP:PORT/
راقب ما إذا كان يظهر طلب جديد في الطرفية.
"""
import socket, sys, threading, time
from typing import Set, List
from http.server import BaseHTTPRequestHandler, HTTPServer
from contextlib import closing

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8010

# جمع كل الـ IPs المحلية
ips: Set[str] = set()
try:
    host = socket.gethostname()
    for ai in socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP):
        addr = ai[4][0]
        if isinstance(addr, str):
            if isinstance(addr, str) and (':' in addr or addr.startswith('127.')):
                continue
            if isinstance(addr, str): ips.add(addr)
except Exception:
    pass
# طريقة بديلة
if not ips:
    try:
        with closing(socket.socket(socket.AF_INET, socket.SOCK_DGRAM)) as s:
            s.connect(("8.8.8.8", 80))
            ips.add(s.getsockname()[0])
    except Exception:
        ips.add('127.0.0.1')

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return  # كتم الضجيج الافتراضي
    def do_GET(self):
        client_ip = self.client_address[0]
        print(f"[REQ] {client_ip} -> {self.path}")
        body = f"OK\nYou reached {socket.gethostname()} on {self.server.server_address}\nYour IP: {client_ip}\nPath: {self.path}\n".encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

servers: list[HTTPServer] = []

def serve_on(ip):
    try:
        httpd = HTTPServer((ip, PORT), Handler)
    except OSError as e:
        print(f"[X] فشل ربط {ip}:{PORT} -> {e}")
        return
    print(f"[+] يستمع على http://{ip}:{PORT}/")
    servers.append(httpd)
    httpd.serve_forever()

print("\nالعناوين المتاحة:")
for ip in ips:
    print(f"  - {ip}")
print(f"\nافتح من الموبايل: http://IP_OF_PC:{PORT}/ (استبدل IP_OF_PC بأحد العناوين أعلاه)")
print("سيتم طباعة كل طلب مع IP المصدر. اضغط Ctrl+C للإيقاف.\n")

threads: list[threading.Thread] = []
# نضيف 0.0.0.0 إن لم يكن موجوداً بشكل آمن بدون استخدام اتحاد المجموعات | لتبسيط التحليل
all_ips = list(ips)
if '0.0.0.0' not in ips:
    all_ips.append('0.0.0.0')
for ip in all_ips:
    t = threading.Thread(target=serve_on, args=(ip,), daemon=True)
    t.start()
    threads.append(t)

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nإيقاف...")
    for s in servers:
        s.shutdown()
