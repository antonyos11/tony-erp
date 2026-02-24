#!/usr/bin/env python
"""تشغيل الخادم على الشبكة المحلية مع إخراج آمن (بدون رموز قد تسبب UnicodeError)."""
import os
import sys
import socket
import subprocess
from pathlib import Path
from contextlib import closing

try:
    from core.utils.console import safe_print  # noqa: F401
except Exception:  # pragma: no cover
    def safe_print(*args, **kwargs) -> None:
        try:
            print(*args, **kwargs)
            return
        except UnicodeEncodeError:
            cleaned: list[str] = []
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
        except Exception:
            pass

try:
    import psutil  # noqa: F401
except Exception:  # pragma: no cover
    psutil = None  # type: ignore[assignment]
try:
    import qrcode  # noqa: F401
except Exception:  # pragma: no cover
    qrcode = None  # type: ignore[assignment]


def get_all_ips():
    ips = []
    if psutil:
        try:
            for iface, addrs in psutil.net_if_addrs().items():
                for a in addrs:
                    if getattr(socket, 'AF_INET', None) == a.family and a.address != '127.0.0.1':
                        ips.append((iface, a.address))
        except Exception:
            pass
    if not ips and os.name == 'nt':
        try:
            proc = subprocess.run(["ipconfig"], capture_output=True, text=True, encoding='utf-8', errors='ignore')
            import re
            pattern = re.compile(r"IPv4[^:]*:\s*([0-9]+(?:\.[0-9]+){3})")
            for line in proc.stdout.splitlines():
                m = pattern.search(line)
                if m and m.group(1) != '127.0.0.1':
                    ips.append(("iface", m.group(1)))
        except Exception:
            pass
    if not ips:
        try:
            with closing(socket.socket(socket.AF_INET, socket.SOCK_DGRAM)) as s:
                s.connect(("8.8.8.8", 80))
                ips.append(("primary", s.getsockname()[0]))
        except Exception:
            pass
    seen = set()
    uniq = []
    for iface, addr in ips:
        if addr not in seen:
            uniq.append((iface, addr))
            seen.add(addr)
    return uniq or [("loopback", "127.0.0.1")]


def choose_ip(ips):
    if not ips:
        return "127.0.0.1"
    for iface, addr in ips:
        low = iface.lower()
        if 'wi' in low or 'wlan' in low:
            return addr
    return ips[0][1]


def check_dependencies():
    safe_print("فحص المتطلبات ...")
    if sys.version_info < (3, 8):
        safe_print("خطأ: يتطلب Python 3.8+")
        return False
    try:
        import django  # type: ignore
        safe_print(f"Django {django.get_version()} جاهز")
    except Exception:
        safe_print("خطأ: Django غير مثبت")
        return False
    if not Path("db.sqlite3").exists():
        safe_print("تنبيه: سيتم إنشاء قاعدة البيانات (sqlite)")
    return True


def setup_environment():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
    p = Path(__file__).resolve().parent
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


def run_migrations():
    safe_print("تحديث قاعدة البيانات ...")
    try:
        r = subprocess.run([sys.executable, 'manage.py', 'migrate'], capture_output=True, text=True, cwd=Path(__file__).parent)
        if r.returncode == 0:
            safe_print("تم تحديث قاعدة البيانات")
            return True
        safe_print(f"خطأ: {r.stderr}")
        return False
    except Exception as exc:
        safe_print(f"خطأ: {exc}")
        return False


def collect_static():
    safe_print("جمع الملفات الثابتة ...")
    try:
        r = subprocess.run([sys.executable, 'manage.py', 'collectstatic', '--noinput'], capture_output=True, text=True, cwd=Path(__file__).parent)
        if r.returncode == 0:
            safe_print("تم الجمع")
        else:
            safe_print("تحذير أثناء الجمع (يمكن المتابعة)")
        return True
    except Exception as exc:
        safe_print(f"تحذير: {exc}")
        return True


def setup_firewall_rules(port=8000):
    safe_print("إعداد قواعد الجدار الناري ...")
    rule = f"Django_Server_{port}"
    try:
        subprocess.run(["netsh", "advfirewall", "firewall", "delete", "rule", f"name={rule}"], capture_output=True)
        res = subprocess.run([
            "netsh", "advfirewall", "firewall", "add", "rule",
            f"name={rule}", "dir=in", "action=allow", "protocol=TCP", f"localport={port}", "profile=any"
        ], capture_output=True, text=True)
        if res.returncode == 0:
            safe_print("تمت إضافة قاعدة جدار ناري")
        else:
            safe_print("تنبيه: ربما تحتاج تشغيل كمسؤول لإضافة القاعدة")
    except Exception as exc:
        safe_print(f"تعذر إعداد الجدار: {exc}")


def start_server(ip, port=8000):
    # تأمين ALLOWED_HOSTS في .env بإضافة IP المختار لتفادي DisallowedHost
    try:
        import subprocess, sys
        subprocess.run([sys.executable, 'prepare_portable.py', '--ip', ip], cwd=Path(__file__).parent, capture_output=True)
    except Exception:
        pass
    safe_print(f"تشغيل الخادم على {ip}:{port}")
    safe_print("=" * 50)
    safe_print(f"رابط: http://{ip}:{port}")
    safe_print("دخول: superadmin / admin123")
    safe_print("Ctrl+C للإيقاف")
    safe_print("=" * 50)
    if qrcode:
        try:
            Path('server_url.txt').write_text(f"http://{ip}:{port}", encoding='utf-8')
            safe_print("تم حفظ الرابط في server_url.txt (ثبّت qrcode لتوليد صورة)")
        except Exception:
            pass
    else:
        safe_print("(اختياري) pip install qrcode[pil] لتوليد QR")
    try:
        subprocess.run([sys.executable, 'manage.py', 'runserver', f'{ip}:{port}'], cwd=Path(__file__).parent)
    except KeyboardInterrupt:
        safe_print("تم إيقاف الخادم")
    except Exception as exc:
        safe_print(f"خطأ في تشغيل الخادم: {exc}")


def main():
    safe_print("وضع الشبكة المحلية")
    if not check_dependencies():
        if not os.getenv('NO_INTERACTIVE'):
            input("اضغط Enter للخروج...")
        return
    setup_environment()
    if not run_migrations():
        if not os.getenv('NO_INTERACTIVE'):
            input("اضغط Enter للخروج...")
        return
    collect_static()
    ips = get_all_ips()
    safe_print("العناوين المتاحة:")
    for i, (iface, addr) in enumerate(ips, 1):
        safe_print(f"  {i}. {addr} ({iface})")
    chosen = choose_ip(ips)
    if len(ips) > 1 and not os.getenv('NO_INTERACTIVE'):
        sel = input(f"اختر رقم أو Enter لاستخدام {chosen}: ").strip()
        if sel.isdigit():
            idx = int(sel) - 1
            if 0 <= idx < len(ips):
                chosen = ips[idx][1]
    port = int(os.getenv('PORT', '8000'))
    safe_print(f"استخدام العنوان: {chosen}:{port}")
    setup_firewall_rules(port)
    if not os.getenv('NO_INTERACTIVE'):
        input("اضغط Enter للتشغيل...")
    start_server(chosen, port)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        safe_print("تم إلغاء التشغيل")
    except Exception as exc:  # pragma: no cover
        safe_print(f"خطأ غير متوقع: {exc}")
        input("اضغط Enter للخروج...")
