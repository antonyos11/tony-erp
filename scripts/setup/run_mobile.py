#!/usr/bin/env python
"""تشغيل النظام ليعمل على موبايلك بسهولة (أبسط وضع ممكن)"""
import socket, subprocess, sys, re, shutil, os
from contextlib import closing

PORT = 8000

ANSI = shutil.get_terminal_size().columns if sys.stdout.isatty() else 0

try:
    from core.utils.console import safe_print  # type: ignore
except Exception:
    def safe_print(*args, **kwargs):  # pragma: no cover
        try:
            print(*args, **kwargs)
        except UnicodeEncodeError:
            cleaned = []
            for a in args:
                try:
                    s = str(a)
                except Exception:
                    s = repr(a)
                s2 = ''.join(ch for ch in s if (ord(ch) < 128) or ch.isalnum() or ch.isspace() or '\u0600' <= ch <= '\u06FF')
                cleaned.append(s2)
            try:
                print(*cleaned, **kwargs)
            except Exception:
                pass


def banner(msg):
    line = '=' * min(60, (ANSI or 60))
    safe_print('\n' + line)
    safe_print(msg)
    safe_print(line)

def detect_ips():
    ips = []
    # طريقة ipconfig (Windows)
    try:
        out = subprocess.check_output(['ipconfig'], encoding='utf-8', errors='ignore')
        for m in re.finditer(r'IPv4 Address[ .:]*([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)', out):
            ip = m.group(1)
            if not ip.startswith('169.254.') and ip != '127.0.0.1':
                ips.append(ip)
    except Exception:
        pass
    # طريقة المقبس
    try:
        with closing(socket.socket(socket.AF_INET, socket.SOCK_DGRAM)) as s:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            if ip not in ips and ip != '127.0.0.1':
                ips.append(ip)
    except Exception:
        pass
    return ips

def choose_ip(ips):
    # اختر أول عنوان من العائلة الخاصة 192/10/172
    for ip in ips:
        if ip.startswith(('192.168.', '10.', '172.')):
            return ip
    return ips[0] if ips else '127.0.0.1'

def open_firewall(port):
    rule = f"TonyERPDev_{port}"
    try:
        subprocess.run(['netsh','advfirewall','firewall','delete','rule',f'name={rule}'], capture_output=True)
        r = subprocess.run(['netsh','advfirewall','firewall','add','rule',f'name={rule}','dir=in','action=allow','protocol=TCP',f'localport={port}','profile=any'], capture_output=True, text=True)
        if r.returncode == 0:
            safe_print(f"تم فتح المنفذ {port} في الجدار الناري (قد يتطلب صلاحيات مسؤول)")
        else:
            safe_print(f"تنبيه: لم أستطع فتح الجدار (تابع عادي). إذا تعذر الوصول من الجوال شغّل كمسؤول")
    except Exception:
        safe_print("تنبيه: تخطيت إعداد الجدار الناري")

def main():
    banner('تهيئة السيرفر للوصول من الموبايل')
    ips = detect_ips()
    if not ips:
        safe_print('خطأ: لم أستطع تحديد أي عنوان شبكة. تأكد أنك متصل بالواي فاي.')
        sys.exit(1)
    ip = choose_ip(ips)
    safe_print('العناوين المكتشفة:')
    for i in ips:
        safe_print('  -', i)
    safe_print(f'\nسيتم استخدام العنوان: {ip}:{PORT}')

    open_firewall(PORT)

    safe_print('\nافتح من الموبايل (نفس شبكة الواي فاي) هذا الرابط:')
    safe_print(f'  http://{ip}:{PORT}/')
    safe_print('\nملاحظات:')
    safe_print('  - لا تكتب 127.0.0.1 على الموبايل أبداً.')
    safe_print('  - أوقف VPN / Data Saver / Private DNS مؤقتاً.')
    safe_print('  - لو لم يفتح جرّب إطفاء الجدار مؤقتاً (الشبكة الخاصة فقط).')
    safe_print('\nلإيقاف السيرفر اضغط Ctrl + C\n')

    # شغل Django
    os.execv(sys.executable, [sys.executable, 'manage.py', 'runserver', f'{ip}:{PORT}'])

if __name__ == '__main__':
    main()
